"""AI & ERP desk (change list points 9a, 9d, 9e, 11): Samir's screens. Main job ERP implementation, plus technology
improvements in every department. Not an admin desk: no logins, no approvals.

Improvement process: every DSI and Report Problem lands in the Improvement Inbox by itself; Samir sorts each one
(a ToDo "[AI & ERP] <type>: ..." on the item), fixes or trains, the department confirms, Samir closes it and the fix is
posted as his DSI. Nothing new is stored in ERPNext beyond ToDos, Work Log notes and DSI entries.
"""

import json

import frappe
from frappe import _
from frappe.utils import add_days, cint, getdate, strip_html

from sk_app import segments
from sk_app.functions import FUNCTIONS

TAG = "[AI & ERP]"
CATEGORIES = ["App bug", "Training needed", "Process change", "ERPNext setup", "New feature", "Not needed"]

# Samir's weekly department visit (point 9d, proposed to SK); Sat is the review with SK
VISITS = {
	0: ("Sales & Marketing", ["Sales", "Marketing", "Machine Shifting"]),
	1: ("Store & Purchase", ["Stores", "Purchase"]),
	2: ("Production, subcontractors, Quality", ["Production", "Subcontractor", "Quality"]),
	3: ("Finance & HR", ["Accounts", "HR"]),
	4: ("ERP data clean-up + testing on sk-dev", []),
	5: ("Review with SK + weekly report", ["Management"]),
}

# this change list (Rev 13); status is kept in ERPNext defaults so SK / Samir can move it along
CHANGE_LIST = [
	(1, "Check photo / file data before saving"), (2, "Cabin / Non-Cabin segment"), (3, "CEO View Member App"),
	(4, "Mic and camera fixes"), (5, "Customer complaints"), (6, "Satish Aralkar view-only ERPNext"),
	(7, "Finance, HR, Manufacturing manuals"), (8, "Product cards everywhere"), (9, "Samir / admin icons / week plan"),
	(10, "Work Book inside My Day"), (11, "AI & ERP department"), (12, "Where did my new lead go?"),
	(13, "CEO dashboards"), (14, "Mailboxes + IndiaMART / JustDial / GeM"), (15, "Pending work in colour"),
	(16, "Optick attendance"),
]
CHANGE_STATES = ["SK OK", "Building", "Testing", "Live"]
CHANGE_KEY = "sk_change_list_status"


def _check(user: str):
	from sk_app.logins import profile_functions

	if user != "Administrator" and not {"AI", "IT / ERP", "Management"} & set(profile_functions(user)):
		frappe.throw(_("Only the AI & ERP desk can open this"), frappe.PermissionError)


def _names() -> dict:
	return {r.user: r.full_name for r in frappe.get_all("SK App User", fields=["user", "full_name"])}


def _sorted() -> dict:
	"""{(doctype, name): todo} of inbox items already sorted."""
	rows = frappe.get_all("ToDo", filters={"description": ["like", f"{TAG}%"], "reference_type": ["in", ["SK Work Log", "SK DSI Entry"]]},
		fields=["name", "status", "description", "reference_type", "reference_name", "date", "allocated_to"], limit=0)
	return {(r.reference_type, r.reference_name): r for r in rows}


def _category(todo) -> str:
	text = strip_html(todo.description or "")[len(TAG):].strip()
	return text.split(":", 1)[0].strip() if ":" in text else ""


def inbox(user: str) -> dict:
	"""All ideas and problems from every department: open first (oldest first), then sorted ones still being fixed."""
	_check(user)
	names, done = _names(), _sorted()
	since = add_days(getdate(), -60)
	items = []
	for r in frappe.get_all("SK Work Log", filters={"entry_type": "Problem", "date": [">=", since]},
			fields=["name", "user", "date", "problem_type", "description", "status", "photo"], order_by="date asc", limit=0):
		items.append({"doctype": "SK Work Log", "name": r.name, "kind": "problem", "title": r.description, "type": r.problem_type,
			"by": names.get(r.user, r.user), "date": str(r.date), "photo": r.photo, "closed": r.status == "Done"})
	for r in frappe.get_all("SK DSI Entry", filters={"date": [">=", add_days(getdate(), -14)]},
			fields=["name", "user", "date", "what_changed", "photo"], order_by="date asc", limit=0):
		items.append({"doctype": "SK DSI Entry", "name": r.name, "kind": "dsi", "title": r.what_changed, "type": "DSI",
			"by": names.get(r.user, r.user), "date": str(r.date), "photo": r.photo, "closed": False})
	new, working = [], []
	for i in items:
		t = done.get((i["doctype"], i["name"]))
		if t:
			if t.status == "Open":
				working.append({**i, "todo": t.name, "category": _category(t), "due": str(t.date) if t.date else None})
		elif not i["closed"]:
			new.append(i)
	return {"new": new, "working": working, "categories": CATEGORIES}


def sort_item(user: str, doctype: str, name: str, category: str, note: str | None = None, due=None) -> dict:
	"""Samir marks an inbox item: app bug, training, process change, ERPNext setup, new feature or not needed."""
	_check(user)
	if doctype not in ("SK Work Log", "SK DSI Entry") or not frappe.db.exists(doctype, name):
		frappe.throw(_("Item not found"))
	if category not in CATEGORIES:
		frappe.throw(_("Please pick a type"))
	title = frappe.db.get_value(doctype, name, "description" if doctype == "SK Work Log" else "what_changed") or name
	text = f"{TAG} {category}: {strip_html(title)[:140]}" + (f" | {note.strip()}" if (note or "").strip() else "")
	todo = frappe.get_doc({"doctype": "ToDo", "allocated_to": user, "description": text, "reference_type": doctype,
		"reference_name": name, "date": getdate(due) if due else add_days(getdate(), 7 if category != "New feature" else 30),
		"status": "Cancelled" if category == "Not needed" else "Open", "priority": "High" if category == "App bug" else "Medium",
		"assigned_by": user}).insert(ignore_permissions=True)
	if doctype == "SK Work Log":
		frappe.db.set_value("SK Work Log", name, "status", "Done" if category == "Not needed" else "Acknowledged")
	return {"todo": todo.name}


def close_item(user: str, todo: str, note: str | None = None) -> dict:
	"""The department said "works": close the item and post the fix as Samir's DSI."""
	_check(user)
	t = frappe.get_doc("ToDo", todo)
	if not (t.description or "").startswith(TAG):
		frappe.throw(_("Not an AI & ERP item"))
	t.status = "Closed"
	t.save(ignore_permissions=True)
	if t.reference_type == "SK Work Log":
		frappe.db.set_value("SK Work Log", t.reference_name, "status", "Done")
	what = (note or "").strip() or strip_html(t.description)[len(TAG):].strip()
	dsi = frappe.get_doc({"doctype": "SK DSI Entry", "user": user, "date": getdate(), "what_changed": what[:500],
		"saving_type": "Time"}).insert(ignore_permissions=True)
	return {"dsi": dsi.name}


def _people(functions: list[str]) -> list[dict]:
	from sk_app.logins import profile_functions

	rows = frappe.get_all("SK App User", filters={"enabled": 1}, fields=["user", "full_name", "home"])
	out = [r for r in rows if not functions or set(profile_functions(r.user)) & set(functions)]
	last = {u.name: u.last_login for u in frappe.get_all("User", filters={"name": ["in", [r.user for r in out] or [""]]},
		fields=["name", "last_login"])}
	return [{"user": r.user, "full_name": r.full_name, "function": r.home, "last_login": str(last.get(r.user) or "") or None}
		for r in out]


def visit(user: str, day=None) -> dict:
	"""Today's department visit: its people, who has not used the app today, its open problems, last visit notes."""
	_check(user)
	day = getdate(day)
	label, functions = VISITS.get(day.weekday(), ("No visit today", []))
	people = _people(functions) if functions else []
	users = [p["user"] for p in people]
	today = str(day)
	problems = frappe.get_all("SK Work Log", filters={"entry_type": "Problem", "status": ["!=", "Done"], "user": ["in", users or [""]]},
		fields=["name", "user", "date", "description", "problem_type"], order_by="date asc", limit=50)
	dsi_week = frappe.get_all("SK DSI Entry", filters={"user": ["in", users or [""]], "date": [">=", add_days(day, -6)]},
		fields=["user"], limit=500)
	notes = frappe.get_all("SK Work Log", filters={"user": user, "entry_type": "Extra Work", "description": ["like", "Visit %"]},
		fields=["date", "description"], order_by="creation desc", limit=5)
	return {"day": today, "department": label, "functions": functions,
		"people": [{**p, "today": bool(p["last_login"] and p["last_login"][:10] == today),
			"dsi_week": sum(1 for d in dsi_week if d.user == p["user"])} for p in people],
		"not_today": sum(1 for p in people if not (p["last_login"] and p["last_login"][:10] == today)),
		"problems": problems, "notes": notes, "plan": [{"day": d, "department": v[0]} for d, v in sorted(VISITS.items())]}


def visit_note(user: str, department: str, text: str) -> str:
	_check(user)
	if not (text or "").strip():
		frappe.throw(_("Please say what you found"))
	return frappe.get_doc({"doctype": "SK Work Log", "user": user, "date": getdate(), "entry_type": "Extra Work",
		"description": f"Visit {department}: {text.strip()}"}).insert(ignore_permissions=True).name


def _count(doctype: str, filters=None) -> int | None:
	try:
		return frappe.db.count(doctype, filters or {}) if frappe.db.exists("DocType", doctype) else None
	except Exception:
		return None


def erp_gaps(user: str) -> list[dict]:
	"""Live counts of data missing in ERPNext (they should count down each week)."""
	_check(user)
	rows = [
		("Suppliers without GSTIN", _count("Supplier", {"disabled": 0, "gstin": ["in", ["", None]]}) if frappe.db.has_column("Supplier", "gstin") else None,
			_count("Supplier", {"disabled": 0}), "/app/supplier?gstin=%5B%22is%22%2C%22not%20set%22%5D"),
		("Customers without segment", _count("Customer", {"disabled": 0, "customer_group": ["not in", segments.all_groups()]}),
			_count("Customer", {"disabled": 0}), "/app/customer"),
		("Customers without mobile", _count("Customer", {"disabled": 0, "mobile_no": ["in", ["", None]]}) if frappe.db.has_column("Customer", "mobile_no") else None,
			_count("Customer", {"disabled": 0}), "/app/customer"),
		("Items without HSN", _count("Item", {"disabled": 0, "gst_hsn_code": ["in", ["", None]]}) if frappe.db.has_column("Item", "gst_hsn_code") else None,
			_count("Item", {"disabled": 0}), "/app/item"),
		("Leads without source", _count("CRM Lead", {"source": ["in", ["", None]]}) if frappe.db.exists("DocType", "CRM Lead") else None,
			_count("CRM Lead"), "/crm/leads"),
		("Employees without app login", _count("Employee", {"status": "Active", "user_id": ["in", ["", None]]}),
			_count("Employee", {"status": "Active"}), "/app/employee"),
		("Purchase Orders made", _count("Purchase Order", {"docstatus": 1}), None, "/app/purchase-order"),
		("Stock Entries made", _count("Stock Entry", {"docstatus": 1}), None, "/app/stock-entry"),
		("Job Cards made", _count("Job Card"), None, "/app/job-card"),
	]
	return [{"label": label, "count": n, "of": total, "link": link, "kind": "made" if total is None else "gap"}
		for label, n, total, link in rows if n is not None]


def app_users(user: str) -> dict:
	"""Who logged in today, who never did, who still has the first PIN."""
	_check(user)
	rows = frappe.get_all("SK App User", filters={"enabled": 1}, fields=["user", "full_name", "home", "must_set_pin"],
		order_by="full_name asc")
	last = {u.name: u.last_login for u in frappe.get_all("User", filters={"name": ["in", [r.user for r in rows] or [""]]},
		fields=["name", "last_login"])}
	problems = {}
	for u in frappe.get_all("SK Work Log", filters={"entry_type": "Problem", "status": "Open", "problem_type": "IT / app"},
			pluck="user", limit=1000):
		problems[u] = problems.get(u, 0) + 1
	today = str(getdate())
	out = []
	for r in rows:
		ll = str(last.get(r.user) or "")
		state = "today" if ll[:10] == today else ("never" if not ll else "earlier")
		out.append({"user": r.user, "full_name": r.full_name, "function": r.home, "last_login": ll or None, "state": state,
			"first_pin": bool(r.must_set_pin), "problems": problems.get(r.user, 0)})
	order = {"never": 0, "earlier": 1, "today": 2}
	out.sort(key=lambda x: (order[x["state"]], x["full_name"] or ""))
	return {"rows": out, "today": sum(1 for x in out if x["state"] == "today"), "total": len(out)}


def _change_status() -> dict:
	try:
		return json.loads(frappe.db.get_default(CHANGE_KEY) or "{}")
	except ValueError:
		return {}


def change_list(user: str) -> list[dict]:
	_check(user)
	st = _change_status()
	return [{"no": n, "title": t, "status": st.get(str(n), "Building")} for n, t in CHANGE_LIST]


def set_change(user: str, no, status: str) -> dict:
	_check(user)
	if status not in CHANGE_STATES:
		frappe.throw(_("Unknown status"))
	st = _change_status()
	st[str(cint(no))] = status
	frappe.db.set_default(CHANGE_KEY, json.dumps(st))
	return {"ok": True}


def projects(user: str) -> list[dict]:
	"""Bigger improvements as ERPNext Projects (e.g. "ERP Implementation 2026-27", "SK App") with their open tasks."""
	_check(user)
	rows = frappe.get_all("Project", filters={"status": "Open"},
		fields=["name", "project_name", "percent_complete", "expected_end_date"], order_by="modified desc", limit=30)
	out = []
	for p in rows:
		tasks = frappe.get_all("Task", filters={"project": p.name}, fields=["status", "exp_end_date"], limit=0)
		late = [t for t in tasks if t.status not in ("Completed", "Cancelled") and t.exp_end_date and getdate(t.exp_end_date) < getdate()]
		out.append({"name": p.name, "title": p.project_name, "percent": round(p.percent_complete or 0),
			"open": sum(1 for t in tasks if t.status not in ("Completed", "Cancelled")), "late": len(late),
			"end": str(p.expected_end_date) if p.expected_end_date else None})
	return out


def training_progress(user: str) -> list[dict]:
	"""Lessons done per function: how many people finished how many of their lessons."""
	_check(user)
	lessons = frappe.get_all("SK Training Lesson", filters={"published": 1}, fields=["name", "function"])
	done = frappe.get_all("SK Training Done", fields=["user", "lesson"], limit=5000)
	by_user = {}
	for d in done:
		by_user.setdefault(d.user, set()).add(d.lesson)
	people = frappe.get_all("SK App User", filters={"enabled": 1}, fields=["user", "home"])
	out = []
	for f in FUNCTIONS:
		staff = [p for p in people if p.home == f]
		if not staff:
			continue
		mine = {l.name for l in lessons if l.function in ("All", f)}
		if not mine:
			out.append({"function": f, "people": len(staff), "lessons": 0, "done_pct": 0, "finished": 0})
			continue
		pcts = [len(by_user.get(p.user, set()) & mine) / len(mine) for p in staff]
		out.append({"function": f, "people": len(staff), "lessons": len(mine), "done_pct": round(100 * sum(pcts) / len(pcts)),
			"finished": sum(1 for x in pcts if x >= 1)})
	return out


def badges(user: str, functions: list[str]) -> dict:
	if "AI" not in functions:
		return {}
	try:
		data = inbox(user)
		return {"improvement_inbox": len(data["new"])}
	except Exception:
		return {}
