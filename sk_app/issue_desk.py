"""Problem / Suggestion desk (SK 29-Oct-2026): one window where every user sends a problem in their work, a "how do
I...?" question or a suggestion. Each one is an ERPNext Issue in the project "SK App – Issues & Suggestions", sent at
once to the owner of its area. The owner solves small items directly; an app, process or ERPNext setting change, or
anything that costs money, goes to the CEO for approval first (approved → an ERPNext Task for AI & ERP). When the
Issue is set to Resolved (here or in ERPNext) the person gets the reply by themselves and the answer goes into the FAQ
of their role in Training. Customer complaints (complaints.py) also use Issue; they have a customer and an sk_stage,
these have sk_kind, so the two never mix.
"""

import frappe
from frappe import _
from frappe.utils import add_days, getdate, now_datetime, nowdate, strip_html

from sk_app.store import _todo, _users_with_function, attach

PROJECT = "SK App – Issues & Suggestions"
KINDS = {"Problem": "Internal Problem", "Question": "Internal Question", "Suggestion": "Suggestion"}
# area → function that owns it (same owners as Report Problem, point 12); every suggestion goes to AI & ERP
AREAS = {"App / ERPNext": "AI", "Machine": "Production", "Material": "Stores", "Quality": "Quality", "Safety": "Production",
	"Customer": "Sales", "HR / Leave": "HR", "Other": "AI"}
HIGH = ("Machine", "Safety")
SMALL = ("Answer only", "Training needed", "Data correction", "Not needed")
MAJOR = ("ERPNext setting / role", "App change", "Process change", "Needs money")
SOLUTIONS = SMALL + MAJOR
REPLY_DAYS, FIX_DAYS, AUTO_CLOSE_DAYS = 1, 3, 3
TAG = "[Desk]"
FIELDS = ["name", "subject", "description", "status", "issue_type", "opening_date", "sk_kind", "sk_area", "sk_screen",
	"sk_solution", "sk_ceo_approval", "sk_ceo_note", "sk_concerned_user", "sk_concerned_function", "sk_fix_by",
	"sk_registered_by", "sk_user_ok", "sk_faq_item", "resolution_details", "modified"]


def ensure_setup():
	"""The project, the three Issue Types and the desk fields on Issue."""
	if not frappe.db.exists("DocType", "Issue"):
		return
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	for t in KINDS.values():
		if frappe.db.exists("DocType", "Issue Type") and not frappe.db.exists("Issue Type", t):
			frappe.get_doc({"doctype": "Issue Type", "description": t}).insert(ignore_permissions=True, set_name=t)
	if frappe.db.exists("DocType", "Project") and not frappe.db.exists("Project", {"project_name": PROJECT}):
		frappe.get_doc({"doctype": "Project", "project_name": PROJECT, "status": "Open",
			"notes": "Every problem, question and suggestion sent from SK App (Problem / Suggestion tile and ❓ on every screen)."
		}).insert(ignore_permissions=True)
	create_custom_fields({"Issue": [
		{"fieldname": "sk_desk_section", "label": "SK App desk", "fieldtype": "Section Break", "insert_after": "sk_registered_by",
			"collapsible": 1, "depends_on": "eval:doc.sk_kind"},
		{"fieldname": "sk_kind", "label": "Kind", "fieldtype": "Select", "options": "\n" + "\n".join(KINDS), "insert_after": "sk_desk_section",
			"read_only": 1, "in_standard_filter": 1},
		{"fieldname": "sk_area", "label": "Area", "fieldtype": "Data", "insert_after": "sk_kind", "read_only": 1, "in_standard_filter": 1},
		{"fieldname": "sk_screen", "label": "Screen", "fieldtype": "Data", "insert_after": "sk_area", "read_only": 1},
		{"fieldname": "sk_function", "label": "Role of the person (FAQ)", "fieldtype": "Data", "insert_after": "sk_screen", "read_only": 1},
		{"fieldname": "sk_desk_col", "fieldtype": "Column Break", "insert_after": "sk_function"},
		{"fieldname": "sk_solution", "label": "Solution type", "fieldtype": "Select", "options": "\n" + "\n".join(SOLUTIONS),
			"insert_after": "sk_desk_col", "in_standard_filter": 1},
		{"fieldname": "sk_ceo_approval", "label": "CEO approval", "fieldtype": "Select", "options": "\nPending\nApproved\nRejected\nHold",
			"insert_after": "sk_solution", "in_standard_filter": 1},
		{"fieldname": "sk_ceo_note", "label": "CEO note", "fieldtype": "Small Text", "insert_after": "sk_ceo_approval"},
		{"fieldname": "sk_task", "label": "Change task", "fieldtype": "Link", "options": "Task", "insert_after": "sk_ceo_note", "read_only": 1},
		{"fieldname": "sk_faq_item", "label": "FAQ entry", "fieldtype": "Link", "options": "SK Library Item", "insert_after": "sk_task",
			"read_only": 1},
		{"fieldname": "sk_user_ok", "label": "Person says solved", "fieldtype": "Select", "options": "\nYes\nNo", "insert_after": "sk_faq_item",
			"read_only": 1},
	]}, update=True)


def _project() -> str | None:
	return frappe.db.get_value("Project", {"project_name": PROJECT}) if frappe.db.exists("DocType", "Project") else None


def _functions(user: str) -> list[str]:
	from sk_app.logins import profile_functions

	return profile_functions(user) or []


def _ceos() -> list[str]:
	from sk_app.requisition import _ceos

	return _ceos()


def is_ceo(user: str) -> bool:
	return user == "Administrator" or user in _ceos()


def _desk_staff(user: str) -> bool:
	"""AI & ERP (Samir) sees and solves everything on the desk, like the CEO."""
	return is_ceo(user) or bool({"AI", "IT / ERP"} & set(_functions(user)))


def owner_of(user: str, kind: str, area: str) -> tuple[str, str | None]:
	"""(function, person) the request goes to: the head of the area's function, else anyone in it, else AI & ERP."""
	function = "AI" if kind == "Suggestion" else AREAS.get(area, "AI")
	for fn in (function, "AI"):
		people = [p for p in _users_with_function(fn) if p != user]
		heads = [p for p in people if frappe.db.exists("SK App User", {"manager": p, "enabled": 1})]
		if heads or people:
			return fn, (heads or people)[0]
	ceos = [c for c in _ceos() if c != user]
	return "Management", ceos[0] if ceos else None


def _tell(to: str, by: str, text: str, issue: str):
	"""The reply reaches the person at once: My Day (ToDo), a pop-up if the app is open, and e-mail if they have one."""
	frappe.get_doc({"doctype": "ToDo", "allocated_to": to, "assigned_by": by, "status": "Open", "priority": "Low",
		"reference_type": "Issue", "reference_name": issue, "description": text[:500], "date": nowdate()}).insert(ignore_permissions=True)
	frappe.publish_realtime("sk_desk_reply", {"issue": issue, "text": text[:500]}, user=to, after_commit=True)
	from sk_app.otp import _sender, has_real_email

	email = frappe.db.get_value("User", to, "email")
	if has_real_email(email):
		try:
			frappe.sendmail(recipients=[email], sender=_sender(), subject=_("SK App: reply to your request {0}").format(issue),
				message=frappe.utils.escape_html(text).replace("\n", "<br>"), reference_doctype="Issue", reference_name=issue)
		except Exception:
			frappe.log_error("SK App desk reply mail")


def _close_todos(issue: str, user: str | None = None):
	filters = {"reference_type": "Issue", "reference_name": issue, "status": "Open", "description": ["like", f"{TAG}%"]}
	if user:
		filters["allocated_to"] = user
	for name in frappe.get_all("ToDo", filters=filters, pluck="name"):
		frappe.db.set_value("ToDo", name, "status", "Closed")


# ---------- the person ----------

def submit(user: str, kind: str, area: str, text: str, photo: str | None = None, screen: str | None = None) -> dict:
	"""Send: an ERPNext Issue at once, and a ToDo to the owner of the area. Claude drafts an answer for the owner."""
	if kind not in KINDS:
		frappe.throw(_("Please pick Problem, Question or Suggestion"))
	if area not in AREAS:
		area = "App / ERPNext" if (screen or "").strip() else "Other"
	text = (text or "").strip()
	if not text:
		frappe.throw(_("Please speak or type what it is"))
	function, owner = owner_of(user, kind, area)
	mine = _functions(user)
	issue = frappe.get_doc({"doctype": "Issue", "subject": f"{kind}: {strip_html(text)[:120]}", "description": text,
		"issue_type": KINDS[kind] if frappe.db.exists("Issue Type", KINDS[kind]) else None, "status": "Open",
		"priority": _priority("High" if area in HIGH else "Medium"),
		"raised_by": frappe.db.get_value("User", user, "email") or user, "opening_date": nowdate(), "project": _project(),
		"sk_kind": kind, "sk_area": area, "sk_screen": (screen or "").strip()[:140] or None, "sk_function": mine[0] if mine else "All",
		"sk_registered_by": user, "sk_concerned_function": function, "sk_concerned_user": owner,
		"sk_fix_by": add_days(getdate(), REPLY_DAYS)}).insert(ignore_permissions=True)
	attach(photo, "Issue", issue.name, user)
	if owner:
		name = frappe.utils.get_fullname(user)
		_todo(owner, "Issue", issue.name, f"{TAG} {kind} ({area}) from {name}: {strip_html(text)[:300]}")
	frappe.enqueue("sk_app.issue_desk.ai_draft", queue="short", issue=issue.name, enqueue_after_commit=True)
	return {"issue": issue.name, "owner": frappe.utils.get_fullname(owner) if owner else ""}


def _priority(level: str) -> str | None:
	return level if frappe.db.exists("Issue Priority", level) else None


def state_of(r) -> str:
	"""Colour the person sees: sent · solving · ceo · solved · closed."""
	if r.status == "Closed":
		return "closed"
	if r.status == "Resolved":
		return "solved"
	if r.sk_ceo_approval in ("Pending", "Hold"):
		return "ceo"
	return "solving" if r.sk_solution or r.status == "Replied" else "sent"


def _row(r, names: dict) -> dict:
	late = r.status in ("Open", "Replied") and r.sk_fix_by and getdate(r.sk_fix_by) < getdate()
	return {**{k: r.get(k) for k in FIELDS}, "state": state_of(r), "late": bool(late),
		"description": strip_html(r.description or "")[:600], "resolution_details": strip_html(r.resolution_details or ""),
		"by": names.get(r.sk_registered_by, r.sk_registered_by), "owner_name": names.get(r.sk_concerned_user, r.sk_concerned_user or ""),
		"opening_date": str(r.opening_date or ""), "sk_fix_by": str(r.sk_fix_by or "")}


def _names() -> dict:
	return {r.user: r.full_name for r in frappe.get_all("SK App User", fields=["user", "full_name"])}


def listing(user: str, tab: str = "mine") -> dict:
	"""mine: what I sent · solve: sent to me (desk staff: all open) · ceo: waiting for my approval (CEO)."""
	if not frappe.db.has_column("Issue", "sk_kind"):
		return {"rows": [], "kinds": list(KINDS), "areas": list(AREAS), "solutions": [], "major": [], "counts": {}}
	base = {"sk_kind": ["is", "set"]}
	ceo, staff = is_ceo(user), _desk_staff(user)
	to_me = frappe.get_all("ToDo", filters={"reference_type": "Issue", "allocated_to": user, "status": "Open",
		"description": ["like", f"{TAG}%"]}, pluck="reference_name")
	solve_filters = {**base, "status": ["in", ["Open", "Replied", "On Hold"]]}
	solve_or = None if staff else [["sk_concerned_user", "=", user], ["name", "in", to_me or [""]]]
	ceo_filters = {**base, "sk_ceo_approval": ["in", ["Pending", "Hold"]], "status": ["!=", "Closed"]}
	counts = {"solve": len(frappe.get_all("Issue", filters=solve_filters, or_filters=solve_or, pluck="name", limit=0)),
		"ceo": frappe.db.count("Issue", ceo_filters) if ceo else 0}
	if tab == "solve":
		filters, or_filters, order = solve_filters, solve_or, "opening_date asc"
	elif tab == "ceo" and ceo:
		filters, or_filters, order = ceo_filters, None, "modified asc"
	else:
		filters, or_filters, order = {**base, "sk_registered_by": user, "opening_date": [">=", add_days(getdate(), -90)]}, None, "modified desc"
	rows = frappe.get_all("Issue", filters=filters, or_filters=or_filters, fields=FIELDS, order_by=order, limit=200)
	names = _names()
	return {"rows": [_row(r, names) for r in rows], "kinds": list(KINDS), "areas": list(AREAS), "solutions": list(SOLUTIONS),
		"major": list(MAJOR), "counts": counts, "ceo": ceo, "staff": staff}


def _get(user: str, name: str):
	issue = frappe.get_doc("Issue", name)
	if not issue.get("sk_kind"):
		frappe.throw(_("Not a desk request"))
	return issue


def _can_solve(user: str, issue) -> bool:
	return _desk_staff(user) or issue.sk_concerned_user == user or bool(frappe.db.exists("ToDo", {"reference_type": "Issue",
		"reference_name": issue.name, "allocated_to": user, "status": "Open"}))


def detail(user: str, name: str) -> dict:
	issue = _get(user, name)
	solver = _can_solve(user, issue)
	if not (solver or issue.sk_registered_by == user or is_ceo(user)):
		frappe.throw(_("Not your request"), frappe.PermissionError)
	files = frappe.get_all("File", filters={"attached_to_doctype": "Issue", "attached_to_name": name}, fields=["file_name", "file_url"])
	steps = frappe.get_all("Comment", filters={"reference_doctype": "Issue", "reference_name": name, "comment_type": "Info"},
		fields=["content", "creation"], order_by="creation asc")
	out = _row(issue, _names())
	out.update({"files": files, "steps": [{"when": str(s.creation)[:16], "text": strip_html(s.content)} for s in steps],
		"is_solver": solver, "is_mine": issue.sk_registered_by == user, "is_ceo": is_ceo(user),
		"ai": _draft_of(name) if (solver or is_ceo(user)) else None, "erp_url": f"/app/issue/{name}"})
	return out


def _step(name: str, user: str, text: str):
	frappe.get_doc({"doctype": "Comment", "comment_type": "Info", "reference_doctype": "Issue", "reference_name": name,
		"content": f"{frappe.utils.get_fullname(user)}: {text}"}).insert(ignore_permissions=True)


def feedback(user: str, name: str, ok) -> dict:
	"""The person taps Solved (closes it) or Not solved (back to the same owner)."""
	issue = _get(user, name)
	if issue.sk_registered_by != user:
		frappe.throw(_("Only the person who sent it can say this"), frappe.PermissionError)
	ok = str(ok) in ("1", "true", "True", "Yes")
	issue.sk_user_ok = "Yes" if ok else "No"
	issue.status = "Closed" if ok else "Open"
	if not ok:
		issue.sk_fix_by = add_days(getdate(), REPLY_DAYS)
	issue.save(ignore_permissions=True)
	_close_todos(name, user)
	_step(name, user, "Solved, thank you" if ok else "Not solved yet")
	if not ok and issue.sk_concerned_user:
		_todo(issue.sk_concerned_user, "Issue", name, f"{TAG} NOT SOLVED, please look again: {issue.subject}"[:300])
	return {"status": issue.status}


def badge(user: str) -> dict:
	"""Problem / Suggestion tile: red = requests with me to solve or approve; blue = replies waiting for my Solved tap."""
	if not frappe.db.has_column("Issue", "sk_kind"):
		return {}
	n = frappe.db.count("ToDo", {"reference_type": "Issue", "allocated_to": user, "status": "Open", "description": ["like", f"{TAG}%"]})
	if n:
		return {"problem": {"n": n, "c": "red"}}
	n = frappe.db.count("Issue", {"sk_kind": ["is", "set"], "sk_registered_by": user, "status": "Resolved"})
	return {"problem": {"n": n, "c": "blue"}} if n else {}


# ---------- the owner ----------

def sort(user: str, name: str, solution: str, note: str | None = None, fix_by=None) -> dict:
	"""Owner picks the solution type. Small: owner goes on and solves it. Major: it waits for the CEO."""
	issue = _get(user, name)
	if not _can_solve(user, issue):
		frappe.throw(_("This request is not with you"), frappe.PermissionError)
	if solution not in SOLUTIONS:
		frappe.throw(_("Please pick the solution type"))
	issue.sk_solution = solution
	issue.status = "Replied" if issue.status == "Open" else issue.status
	if fix_by:
		issue.sk_fix_by = getdate(fix_by)
	elif solution not in MAJOR:
		issue.sk_fix_by = add_days(getdate(), FIX_DAYS)
	if solution in MAJOR and issue.sk_ceo_approval != "Approved":
		issue.sk_ceo_approval = "Pending"
	if not issue.first_responded_on:
		issue.first_responded_on = now_datetime()
	issue.save(ignore_permissions=True)
	_step(name, user, f"{solution}" + (f": {note.strip()}" if (note or "").strip() else ""))
	if solution in MAJOR and issue.sk_ceo_approval == "Pending":
		for ceo in _ceos():
			if ceo != user:
				_todo(ceo, "Issue", name, f"{TAG} CEO approval – {solution}: {issue.subject}"[:300])
		_tell(issue.sk_registered_by, user, f"Your request {name} needs a change ({solution}). It has gone to the CEO for approval.", name)
	return {"approval": issue.sk_ceo_approval}


def solve(user: str, name: str, reply: str, add_to_faq=1) -> dict:
	"""Owner writes the reply and marks it solved; on_issue_update sends it and makes the FAQ entry."""
	issue = _get(user, name)
	if not _can_solve(user, issue):
		frappe.throw(_("This request is not with you"), frappe.PermissionError)
	if not (reply or "").strip():
		frappe.throw(_("Please speak or type the reply"))
	if issue.sk_ceo_approval in ("Pending", "Hold"):
		frappe.throw(_("Waiting for CEO approval: this change cannot be closed yet"))
	if not issue.sk_solution:
		issue.sk_solution = "Answer only"
	issue.resolution_details = reply.strip()
	issue.status = "Resolved"
	issue.flags.sk_add_to_faq = str(add_to_faq) in ("1", "true", "True")
	issue.flags.sk_by = user
	issue.save(ignore_permissions=True)
	return {"faq": issue.get("sk_faq_item")}


# ---------- the CEO ----------

def decide(user: str, name: str, decision: str, note: str | None = None) -> dict:
	"""Approve (→ ERPNext Task for AI & ERP), Reject (→ the person gets the reason) or Hold."""
	if not is_ceo(user):
		frappe.throw(_("Only the CEO approves changes"), frappe.PermissionError)
	issue = _get(user, name)
	if decision not in ("Approved", "Rejected", "Hold"):
		frappe.throw(_("Pick Approve, Reject or Hold"))
	issue.sk_ceo_approval = decision
	issue.sk_ceo_note = (note or "").strip() or None
	task = None
	if decision == "Approved" and frappe.db.exists("DocType", "Task"):
		doer = (_users_with_function("AI") or [issue.sk_concerned_user])[0]
		due = add_days(getdate(), 14)
		task = frappe.get_doc({"doctype": "Task", "subject": f"{issue.sk_solution}: {strip_html(issue.subject)}"[:140],
			"project": _project(), "issue": issue.name, "status": "Open", "priority": "Medium", "exp_end_date": due,
			"description": f"Approved by CEO for {issue.name}." + (f"<br>CEO: {frappe.utils.escape_html(note.strip())}" if (note or "").strip() else "")
				+ f"<br>{issue.description or ''}"}).insert(ignore_permissions=True)
		issue.sk_task = task.name
		issue.sk_fix_by = due
		if doer:
			_todo(doer, "Issue", issue.name, f"{TAG} CEO approved, please build ({task.name}): {issue.subject}"[:300])
	issue.save(ignore_permissions=True)
	_close_todos(name, user)
	for ceo in _ceos():
		_close_todos(name, ceo)
	_step(name, user, f"CEO {decision}" + (f": {note.strip()}" if (note or "").strip() else ""))
	if decision == "Approved":
		_tell(issue.sk_registered_by, user, f"Good news: the change for your request {name} is approved and is being built.", name)
	elif decision == "Rejected":
		solve(user, name, "Not approved by the CEO." + (f" Reason: {note.strip()}" if (note or "").strip() else ""), add_to_faq=0)
	return {"task": task.name if task else None}


# ---------- live reply on every change of the Issue (app or ERPNext) ----------

def on_issue_update(doc, method=None):
	"""SK rule: live, not in batches. Resolved → the person gets the reply now and the answer joins their role's FAQ."""
	if not doc.get("sk_kind"):
		return
	before = doc.get_doc_before_save()
	if doc.status == "Resolved" and (not before or before.status != "Resolved"):
		by = doc.flags.sk_by or frappe.session.user
		reply = strip_html(doc.resolution_details or "").strip() or _("Solved.")
		_close_todos(doc.name)
		_step(doc.name, by, f"Solved: {reply[:300]}")
		if doc.sk_registered_by:
			_tell(doc.sk_registered_by, by, f"Reply to your request {doc.name} (\"{strip_html(doc.subject)[:100]}\"): {reply}\n"
				"Open Problem / Suggestion → My requests and tap Solved or Not solved.", doc.name)
		add = doc.flags.sk_add_to_faq if doc.flags.sk_add_to_faq is not None else doc.sk_solution not in ("Not needed", "Data correction")
		if add and not doc.sk_faq_item and doc.sk_ceo_approval != "Rejected":
			doc.sk_faq_item = _faq(doc, reply)
			frappe.db.set_value("Issue", doc.name, "sk_faq_item", doc.sk_faq_item, update_modified=False)


def _faq(doc, reply: str) -> str | None:
	"""FAQ entry in Training for the person's role (English; Marathi is added in ERPNext or by Claude's draft)."""
	if not frappe.db.exists("DocType", "SK Library Item"):
		return None
	options = (frappe.get_meta("SK Library Item").get_field("function").options or "").split("\n")
	question = strip_html(doc.description or doc.subject).strip()
	draft = _draft_of(doc.name) or {}
	marathi = (draft.get("answer_marathi") or "").strip() if draft.get("answer") and draft["answer"].strip() in reply else ""
	return frappe.get_doc({"doctype": "SK Library Item", "title": question[:140], "category": "FAQ", "audience": "Internal",
		"function": doc.sk_function if doc.sk_function in options else "All", "enabled": 1, "text": reply,
		**({"text_marathi": marathi} if marathi and frappe.get_meta("SK Library Item").has_field("text_marathi") else {})
	}).insert(ignore_permissions=True).name


def auto_close():
	"""Solved and the person has not answered in 3 days: closed by itself (daily)."""
	if not frappe.db.has_column("Issue", "sk_kind"):
		return
	for name in frappe.get_all("Issue", filters={"sk_kind": ["is", "set"], "status": "Resolved",
			"modified": ["<", add_days(now_datetime(), -AUTO_CLOSE_DAYS)]}, pluck="name", limit=500):
		frappe.db.set_value("Issue", name, "status", "Closed")


# ---------- Claude's draft answer for the owner ----------
AI_TAG = "[AI draft]"


def ai_draft(issue: str):
	from sk_app import claude
	from sk_app.training import _faq_context

	if not claude.available():
		return
	doc = frappe.get_doc("Issue", issue)
	images = []
	for url in frappe.get_all("File", filters={"attached_to_doctype": "Issue", "attached_to_name": issue}, pluck="file_url", limit=2):
		try:
			ext = url.rsplit(".", 1)[-1].lower()
			media = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}.get(ext)
			content = frappe.get_doc("File", {"file_url": url}).get_content()
			if media and len(content) < 4.5 * 1024 * 1024:
				images.append((content, media))
		except Exception:
			continue
	question = f"{doc.sk_kind} about {doc.sk_area}: {strip_html(doc.description or '')}"
	draft = claude.help_draft(question, doc.sk_function or "All", doc.sk_screen or "",
		frappe.utils.get_fullname(doc.sk_registered_by) if doc.sk_registered_by else "", _faq_context(doc.sk_function or "All"), images)
	if draft:
		doc.add_comment("Comment", AI_TAG + " " + frappe.as_json(draft, indent=None))


def _draft_of(issue: str) -> dict | None:
	c = frappe.get_all("Comment", filters={"reference_doctype": "Issue", "reference_name": issue, "comment_type": "Comment",
		"content": ["like", f"{AI_TAG}%"]}, pluck="content", order_by="creation desc", limit=1)
	if not c:
		return None
	try:
		return frappe.parse_json(strip_html(c[0])[len(AI_TAG):].strip())
	except Exception:
		return None


# ---------- one-time move of the old open items (SK to confirm, point 4) ----------

def move_old(user: str) -> dict:
	"""Open Report Problems (SK Work Log) and open ❓ questions to the CEO become desk Issues, so nothing is lost."""
	if not _desk_staff(user):
		frappe.throw(_("Only the CEO or AI & ERP can do this"), frappe.PermissionError)
	from sk_app.training import FAQ_TAG, split_screen

	moved = 0
	area_of = {"Machine breakdown": "Machine", "Material shortage": "Material", "Quality issue": "Quality", "Safety": "Safety",
		"Customer complaint": "Customer", "IT / app": "App / ERPNext", "Leave": "HR / Leave", "Pay / leave": "HR / Leave"}
	for w in frappe.get_all("SK Work Log", filters={"entry_type": "Problem", "status": ["!=", "Done"]},
			fields=["name", "user", "problem_type", "description", "photo"], limit=0):
		r = submit(w.user, "Problem", area_of.get(w.problem_type or "", "Other"), strip_html(w.description or "") or "Problem")
		if w.photo:
			try:
				frappe.get_doc({"doctype": "File", "file_url": w.photo, "attached_to_doctype": "Issue", "attached_to_name": r["issue"]}
					).insert(ignore_permissions=True)
			except Exception:
				frappe.log_error("SK App desk: old problem photo")
		frappe.db.set_value("SK Work Log", w.name, "status", "Done")
		for t in frappe.get_all("ToDo", filters={"reference_type": "SK Work Log", "reference_name": w.name, "status": "Open"}, pluck="name"):
			frappe.db.set_value("ToDo", t, "status", "Closed")
		moved += 1
	for t in frappe.get_all("ToDo", filters={"status": "Open", "description": ["like", f"{FAQ_TAG}%"]},
			fields=["name", "description", "assigned_by"], limit=0):
		if not t.assigned_by:
			continue
		body = strip_html(t.description)[len(FAQ_TAG):].strip()
		question, screen = split_screen(body.partition(": ")[2] or body)
		r = submit(t.assigned_by, "Question", "App / ERPNext" if screen else "Other", question, screen=screen or None)
		for f in frappe.get_all("File", filters={"attached_to_doctype": "ToDo", "attached_to_name": t.name}, pluck="name"):
			frappe.db.set_value("File", f, {"attached_to_doctype": "Issue", "attached_to_name": r["issue"]})
		frappe.db.set_value("ToDo", t.name, "status", "Closed")
		moved += 1
	return {"moved": moved}
