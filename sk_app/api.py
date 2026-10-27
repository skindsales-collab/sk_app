"""Endpoints used by the SK App phone screens. Every call works on the logged-in ERPNext user only."""

import json

import frappe
from frappe import _
from frappe.utils import add_to_date, cint, flt, getdate, now_datetime, strip_html

from sk_app import ai_desk, applock, calendar_view, flows, claude, colours, comms, complaints, crm, dashboards, day_report, finance, guide, home_kpi, hr, kpi, lead_sources, ledger, logins, mailbox, photocheck, production, products, purchase, quality, sales_owner, segments, store, training, view_member, work
from sk_app import library as lib
from sk_app.functions import home_for, sections_for
from sk_app.logic import rank_items

CARD_REUSE_MINUTES = 10


def _me(unlocked=True):
	user = frappe.session.user
	if user in ("Guest", None):
		frappe.throw(_("Please log in"), frappe.PermissionError)
	# point 20: the app opens only with face / finger (or PIN until set up) and locks after 30 min idle. In View Member
	# App the CEO's own lock was checked by view_as; the member's session lock does not apply to the CEO's view.
	if unlocked and not frappe.flags.sk_viewing:
		applock.check()
	profile = guide.app_user(user)
	if not profile and "System Manager" in frappe.get_roles(user) and not frappe.db.exists("SK App User", {"user": user}):
		# admins can try the app at once: Administrator cannot be picked in the SK App User form (ERPNext hides it)
		frappe.get_doc({"doctype": "SK App User", "user": user, "home": "Sales", "enabled": 1}).insert(ignore_permissions=True)
		profile = guide.app_user(user)
	if not profile:
		frappe.throw(_("Your login is not set up for the SK App yet. Please ask the ERPNext admin."), frappe.PermissionError)
	return profile


def _item_dict(item):
	return {"kind": item.kind, "title": item.title, "doctype": item.doctype, "name": item.name,
		"due": str(item.due) if item.due else None, "minutes": item.minutes, "priority": item.priority, **item.extra}


def _latest_card(user):
	rows = frappe.get_all("SK Guide Card", filters={"user": user}, fields=["*"], order_by="slot_start desc", limit=1)
	return rows[0] if rows else None


@frappe.whitelist()
def home():
	profile = _me()
	me = frappe.db.get_value("User", profile.user, ["mobile_no", "phone"], as_dict=True) or {}
	team = _has_team(profile.user)
	functions = logins.profile_functions(profile.user)
	main = home_for(profile.home, has_team=team)
	# point 17 (SK 26-Oct): every Home has two parts: "my function" (with its process flow) and "for everyone"
	sections = sections_for(functions or [profile.home], has_team=team) if (functions or profile.home) else None
	# Logins only for the CEO (point 20, SK 26-Oct): HR and ERPNext roles left over from before no longer bring it
	if logins._can_manage(profile.user) and "Management" in set(functions or [profile.home]):
		if "logins" not in main["tiles"]:
			main["tiles"] = main["tiles"][:1] + ["logins"] + main["tiles"][1:]
		if sections and sections["sections"] and not any("logins" in x["tiles"] for x in sections["sections"]):
			sections["sections"][0]["tiles"] = ["logins"] + sections["sections"][0]["tiles"]
	# Electrical points: only the electrician's workstation among the subcontractors (Quality / Production always)
	if sections and "Subcontractor" in (functions or [profile.home]) and not production._is_electrical(production.my_workstation(profile.user)) \
			and not {"Quality", "Production"} & set(functions or [profile.home]):
		for x in sections["sections"]:
			for k in ("tiles", "main", "more"):
				x[k] = [t for t in x.get(k) or [] if t != "el_points"]
	from sk_app.www.sk.index import asset_version

	return {"user": profile.user, "full_name": profile.full_name, "language": profile.language, "v": asset_version(),
		"mobile": me.get("mobile_no") or me.get("phone"),
		# photo reading skips our own GSTIN on a supplier's bill (SK 27-Oct test)
		"own_gstins": [g for g in frappe.get_all("Company", pluck="tax_id") if g],
		"home": main, "functions": functions,
		# SK: a person in several functions sees all of them on one Home, one labelled row each
		"sections": sections,
		"must_set_pin": bool(frappe.db.get_value("SK App User", profile.name, "must_set_pin")),
		"card": _latest_card(profile.user),
		"new_files": crm.files_to_send(profile.user), "day_report_sent": bool(day_report._find(profile.user, getdate())),
		"due_reminders": comms.due_reminders(profile.user), "badges": _colours(profile, functions)}


def _colours(profile, functions):
	"""Point 15: each icon's pending work as red / amber / blue / green with a count."""
	counts = _badges(profile.user, functions)
	try:
		items = work.collect(profile.user, profile.home)
		out = colours.for_user(profile.user, items, bool(frappe.db.exists("SK DSI Entry", {"user": profile.user, "date": getdate()})),
			bool(day_report._find(profile.user, getdate())), counts)
	except Exception:
		frappe.log_error("SK App icon colours")
		out = counts
	if "Management" in functions:  # point 13: red number on each live dashboard icon
		try:
			out.update(dashboards.badges(profile.user))
		except Exception:
			frappe.log_error("SK App dashboard badges")
	return out


def _badges(user, functions):
	"""Red counts on Store / Purchase / approval icons; never breaks Home if ERPNext data is odd."""
	try:
		return {**store.badges(user, functions), **purchase.badges(user, functions), **production.badges(user, functions),
			**quality.badges(user, functions), **finance.badges(user, functions), **ai_desk.badges(user, functions),
			**({"mail": n} if (n := mailbox.badge(user)) else {}), **complaints.badge(user), **hr.badges(user, functions)}
	except Exception:
		frappe.log_error("SK App badges")
		return {}


def _has_team(user):
	"""Team Reports: a person with team members (Reports to) or the CEO / Management, never by ERPNext role alone."""
	return bool(frappe.db.exists("SK App User", {"manager": user, "enabled": 1})) or \
		"Management" in logins.profile_functions(user)


@frappe.whitelist()
def my_day():
	profile = _me()
	items = rank_items(work.collect(profile.user, profile.home), now_datetime())
	# point 10: Work Book is inside My Day now, as "Done today" + "I did extra work"
	return {"items": [_item_dict(i) for i in items], "card": _latest_card(profile.user),
		"done": calendar_view.done_today(profile.user, getdate()), "attendance": _attendance_line(profile.user)}


def _attendance_line(user):
	"""Point 16: today's Optick / thumb check-in on top of My Day; never breaks My Day."""
	try:
		return hr.my_line(user)
	except Exception:
		frappe.log_error("SK App attendance line")
		return None


@frappe.whitelist(methods=["POST"])
def next_card(force=0):
	"""Return the current guide card, making a new one if the last is older than 10 minutes (or force=1)."""
	profile = _me()
	last = _latest_card(profile.user)
	fresh = last and last.slot_start >= add_to_date(now_datetime(), minutes=-CARD_REUSE_MINUTES) and not last.response
	if fresh and not cint(force):
		return last
	return guide.make_card(profile.user)


@frappe.whitelist(methods=["POST"])
def respond_card(card, response):
	"""Start / Done / Need more time / Problem. Done and Problem re-plan the next card at once."""
	profile = _me()
	if response not in ("Started", "Done", "Need more time", "Problem"):
		frappe.throw(_("Unknown response"))
	doc = frappe.get_doc("SK Guide Card", card)
	if doc.user != profile.user:
		frappe.throw(_("Not your card"), frappe.PermissionError)
	doc.db_set({"response": response, "responded_on": now_datetime()})
	if response == "Done" and doc.reference_doctype == "File" and doc.reference_name:
		crm.mark_file_sent(profile.user, doc.reference_name)
	if response in ("Done", "Problem"):
		return guide.make_card(profile.user)
	return doc.as_dict()


@frappe.whitelist()
def my_leads():
	profile = _me()
	now = now_datetime()
	leads = rank_items(work.open_leads(profile.user), now)
	deals = rank_items(work.open_deals(profile.user), now)
	return {"leads": [_item_dict(i) for i in leads], "deals": [_item_dict(i) for i in deals]}


@frappe.whitelist()
def my_kpi(day=None):
	profile = _me()
	from sk_app import sas

	# SK 26-Oct: the TLC SAS score next to My Score
	return {**kpi.scorecard(profile.user, day), "sas": sas.for_user(profile.user)}


@frappe.whitelist()
def my_day_plan(day=None):
	"""Today's calls / leads / quotes from the person's monthly target (Target Action Plan, SK 26-Oct)."""
	from sk_app import plan

	return plan.day_plan(_me().user, day)


@frappe.whitelist()
def leadership():
	from sk_app import sas

	return sas.leadership(_me().user)


@frappe.whitelist()
def team_kpi():
	"""Scorecards of the people whose SK App manager is the logged-in user."""
	profile = _me()
	team = frappe.get_all("SK App User", filters={"manager": profile.user, "enabled": 1}, fields=["user", "full_name"])
	return [{"full_name": t.full_name, **kpi.scorecard(t.user)} for t in team]


@frappe.whitelist(methods=["POST"])
def add_dsi(what_changed, before_text=None, after_text=None, saving_type=None, saving_value=None, photo=None):
	profile = _me()
	if not (what_changed or "").strip():
		frappe.throw(_("Please say what you improved"))
	doc = frappe.get_doc({
		"doctype": "SK DSI Entry", "user": profile.user, "date": getdate(),
		"what_changed": what_changed.strip(), "before_text": before_text, "after_text": after_text,
		"saving_type": saving_type, "saving_value": flt(saving_value), "photo": photo,
	}).insert(ignore_permissions=True)
	return doc.name


@frappe.whitelist(methods=["POST"])
def add_work(description, entry_type="Extra Work", problem_type=None, reference_doctype=None,
		reference_name=None, assigned_to=None, photo=None):
	"""Daily Work Book: extra work, task update, problem report or hand-off."""
	profile = _me()
	if entry_type not in ("Extra Work", "Task Update", "Problem", "Handoff"):
		frappe.throw(_("Unknown entry type"))
	if reference_doctype and reference_name and not frappe.has_permission(reference_doctype, "read", reference_name):
		frappe.throw(_("No access to {0}").format(reference_name), frappe.PermissionError)
	owner = problem_owner(profile.user, problem_type) if entry_type == "Problem" and not assigned_to else None
	doc = frappe.get_doc({
		"doctype": "SK Work Log", "user": profile.user, "date": getdate(), "entry_type": entry_type,
		"problem_type": problem_type, "description": description, "reference_doctype": reference_doctype,
		"reference_name": reference_name, "assigned_to": assigned_to, "photo": photo,
	}).insert(ignore_permissions=True)
	if assigned_to:
		from frappe.desk.form.assign_to import add as assign

		assign({"assign_to": [assigned_to], "doctype": "SK Work Log", "name": doc.name, "description": description})
	elif owner:  # point 12: the function owner gets it as a ToDo (the sender may not share documents themselves)
		frappe.get_doc({"doctype": "ToDo", "allocated_to": owner, "reference_type": "SK Work Log", "reference_name": doc.name,
			"description": f"Problem ({problem_type or 'Other'}) from {profile.full_name or profile.user}: {description}", "priority": "High",
			"date": getdate(), "assigned_by": profile.user}).insert(ignore_permissions=True)
	return doc.name


# point 12 (SK 26-Oct): a problem goes to the owner of the function it belongs to; app / ERP problems to AI & ERP
# (Samir). Every problem also stays in the AI & ERP Improvement Inbox.
PROBLEM_OWNER = {"Machine breakdown": "Production", "Safety": "Production", "Material shortage": "Stores",
	"Quality issue": "Quality", "Customer complaint": "Sales", "IT / app": "AI", "Leave": "HR", "Pay / leave": "HR", "Other": "AI"}


def problem_owner(user: str, problem_type: str | None) -> str | None:
	from sk_app.store import _users_with_function

	function = PROBLEM_OWNER.get(problem_type or "Other", "AI")
	for fn in (function, "AI"):
		people = [p for p in _users_with_function(fn) if p != user]
		heads = [p for p in people if frappe.db.exists("SK App User", {"manager": p, "enabled": 1})]
		if heads or people:
			return (heads or people)[0]
	return None


@frappe.whitelist(methods=["POST"])
def report_screen_error(view, message):
	"""A screen that failed on the phone goes to the AI & ERP Improvement Inbox by itself (once a day per screen)."""
	profile = _me()
	text = f"App screen '{str(view)[:40]}' failed: {strip_html(str(message or ''))[:300]}"
	if frappe.db.exists("SK Work Log", {"user": profile.user, "date": getdate(), "description": text}):
		return None
	return frappe.get_doc({"doctype": "SK Work Log", "user": profile.user, "date": getdate(), "entry_type": "Problem",
		"problem_type": "IT / app", "description": text}).insert(ignore_permissions=True).name


@frappe.whitelist()
def my_work_log(days=7):
	profile = _me()
	return frappe.get_all("SK Work Log", filters={"user": profile.user, "date": [">=", add_to_date(getdate(), days=-cint(days))]},
		fields=["name", "date", "entry_type", "problem_type", "description", "status", "reference_doctype", "reference_name"],
		order_by="creation desc", limit=100)


@frappe.whitelist(methods=["POST"])
def set_language(language):
	profile = _me()
	if language not in ("English", "Marathi"):
		frappe.throw(_("Unknown language"))
	frappe.db.set_value("SK App User", profile.name, "language", language)
	return language


# ---- CRM on the phone ----

@frappe.whitelist()
def crm_options():
	_me()
	return crm.options()


@frappe.whitelist()
def follow_up():
	return crm.follow_up(_me().user)


@frappe.whitelist()
def crm_detail(doctype, name):
	_me()
	return crm.detail(doctype, name)


@frappe.whitelist(methods=["POST"])
def new_lead(first_name, mobile_no=None, organization=None, email=None, source=None, segment=None,
		requirement=None, photo=None, product=None, status=None):
	return crm.new_lead(_me().user, first_name, mobile_no, organization, email, source, segment, requirement, photo, product, status)


@frappe.whitelist(methods=["POST"])
def lead_to_design(name):
	"""New Lead "Send to design" switch: the lead becomes a deal that the AI design pickup reads."""
	return crm.send_to_design(_me().user, name)


@frappe.whitelist(methods=["POST"])
def set_crm_status(doctype, name, status):
	_me()
	return crm.set_status(doctype, name, status)


@frappe.whitelist(methods=["POST"])
def add_crm_note(doctype, name, text=None, photo=None):
	return crm.add_note(_me().user, doctype, name, text, photo)


@frappe.whitelist(methods=["POST"])
def log_contact(doctype, name, channel, outcome=None, text=None, photo=None, duration=None):
	return crm.log_contact(_me().user, doctype, name, channel, outcome, text, photo, cint(duration))


@frappe.whitelist(methods=["POST"])
def read_photo(file_url):
	"""Claude reads a visiting card / enquiry photo into the new-lead form. Empty result when Claude is off."""
	profile = _me()
	content, media = crm.own_file_content(profile.user, file_url)
	return claude.read_lead_photo(content, media) or {}


@frappe.whitelist()
def new_files():
	return crm.new_files(_me().user)


@frappe.whitelist(methods=["POST"])
def request_correction(doctype, name, text=None, file=None, photo=None):
	return crm.request_correction(_me().user, doctype, name, text, file, photo)


@frappe.whitelist(methods=["POST"])
def mark_file_sent(file, channel="WhatsApp"):
	return crm.mark_file_sent(_me().user, file, channel)


@frappe.whitelist(methods=["POST"])
def share_link(doctype, name):
	_me()
	return crm.share_link(doctype, name)


# ---- Training ----

@frappe.whitelist()
def training_lessons():
	profile = _me()
	return training.lessons(profile.user, profile.home)


@frappe.whitelist()
def training_lesson(name):
	return training.lesson(_me().user, name)


@frappe.whitelist(methods=["POST"])
def training_done(lesson, answers=None):
	return training.mark_done(_me().user, lesson, frappe.parse_json(answers) if isinstance(answers, str) else answers)


@frappe.whitelist()
def team_training():
	return training.team_progress(_me().user)


# ---- Day Report ----

@frappe.whitelist()
def my_day_report(day=None):
	return day_report.get(_me().user, day)


@frappe.whitelist(methods=["POST"])
def send_day_report(work_done, problems=None, plan_tomorrow=None, photo=None):
	return day_report.submit(_me().user, work_done, problems, plan_tomorrow, photo)


@frappe.whitelist()
def my_day_reports(days=14):
	return day_report.my_history(_me().user, days)


@frappe.whitelist()
def team_day_reports(day=None):
	return day_report.team(_me().user, day)


@frappe.whitelist(methods=["POST"])
def review_day_report(report, rating=None, comment=None):
	return day_report.review(_me().user, report, rating, comment)


# ---- Calendars ----

@frappe.whitelist()
def cal_today():
	return calendar_view.today(_me().user)


@frappe.whitelist()
def cal_week(day=None):
	return calendar_view.week(_me().user, day)


@frappe.whitelist(methods=["POST"])
def cal_move(key, day=None):
	"""Move one open item to another day of the week plan (or back, with no day)."""
	return calendar_view.move_item(_me().user, key, day)


@frappe.whitelist()
def cal_month(year=None, month=None):
	return calendar_view.month(_me().user, year, month)


# ---- Calls (talk time), reminders, mail: free ----

@frappe.whitelist()
def my_calls(days=7):
	return comms.my_calls(_me().user, cint(days) or 7)


@frappe.whitelist()
def team_calls(day=None):
	return comms.team_calls(_me().user, day)


@frappe.whitelist(methods=["POST"])
def add_call(doctype, name, direction="Outgoing", outcome=None, minutes=None, text=None):
	return comms.add_call(_me().user, doctype, name, direction, outcome, minutes, text)


@frappe.whitelist()
def my_team():
	"""Team members a manager can give a reminder to."""
	profile = _me()
	return [{"user": p.user, "full_name": p.full_name} for p in day_report._team(profile.user)]


@frappe.whitelist(methods=["POST"])
def add_reminder(title, when, repeat=None, doctype=None, name=None, for_user=None):
	return comms.add_reminder(_me().user, title, when, repeat, doctype, name, for_user)


@frappe.whitelist()
def my_reminders(days=7):
	today = getdate()
	return comms.reminders_between(_me().user, today, add_to_date(today, days=cint(days) or 7))


@frappe.whitelist(methods=["POST"])
def done_reminder(doctype, name):
	return comms.done_reminder(_me().user, doctype, name)


@frappe.whitelist()
def my_mail():
	return comms.my_mail(_me().user)


@frappe.whitelist()
def mail_thread(doctype, name):
	_me()
	return comms.mail_thread(doctype, name)


@frappe.whitelist(methods=["POST"])
def send_mail(doctype, name, to, subject, message, files=None):
	files = frappe.parse_json(files) if isinstance(files, str) else files
	return comms.send_mail(_me().user, doctype, name, to, subject, message, files)


# ---- Company & Products library, customer FAQ, message templates, Sales Manual ----

@frappe.whitelist()
def library(category=None):
	return lib.items(_me().home, category)


@frappe.whitelist()
def library_pdf(item):
	"""Only the pages of one manual section, so the phone never downloads the whole manual."""
	_me()
	data, title = lib.section_pdf(item)
	frappe.local.response.filename = f"{title}.pdf"
	frappe.local.response.filecontent = data
	frappe.local.response.type = "pdf"


# ---- Logins by mobile number (HR) and own PIN ----

@frappe.whitelist(methods=["POST"])
def set_pin(old_pin, new_pin):
	return logins.set_own_pin(_me().user, old_pin, new_pin)


@frappe.whitelist()
def hr_people():
	_me()
	return logins.people(frappe.session.user)


@frappe.whitelist()
def hr_login_options():
	"""Choices for the HR "make login" form: functions, managers and workstations (for subcontractors)."""
	_me()
	logins._check_manager(frappe.session.user)
	from sk_app.functions import FUNCTIONS

	admin = "System Manager" in frappe.get_roles()
	return {"functions": [{"name": f, "label": spec["label"]} for f, spec in FUNCTIONS.items()
			if admin or f not in logins.ADMIN_FUNCTIONS],
		"managers": frappe.get_all("SK App User", filters={"enabled": 1}, fields=["user", "full_name"], order_by="full_name asc"),
		"workstations": frappe.get_all("Workstation", pluck="name", order_by="name asc")}


@frappe.whitelist(methods=["POST"])
def hr_make_login(mobile, functions, employee=None, full_name=None, manager=None, language="English", workstation=None):
	_me()
	functions = frappe.parse_json(functions) if isinstance(functions, str) else functions
	return logins.make_login(frappe.session.user, mobile, functions, employee, full_name, manager, language, workstation)


@frappe.whitelist(methods=["POST"])
def hr_bulk_logins(text):
	_me()
	return logins.bulk_make(frappe.session.user, text)


@frappe.whitelist(methods=["POST"])
def hr_reset_pin(user):
	_me()
	return logins.reset_pin(frappe.session.user, user)


@frappe.whitelist(methods=["POST"])
def hr_close_login(user):
	_me()
	return logins.close_login(frappe.session.user, user)


@frappe.whitelist(methods=["POST"])
def reset_face(user):
	"""Point 20: CEO only. New phone or finger not working: the person sets face / finger up again."""
	_me()
	return applock.reset(frappe.session.user, user)


# ---- App lock (point 20): these work while the app is locked ----

@frappe.whitelist()
def lock_status():
	return applock.status(_me(unlocked=False).user)


@frappe.whitelist(methods=["POST"])
def lock_now():
	return applock.lock(_me(unlocked=False).user)


@frappe.whitelist(methods=["POST"])
def unlock_pin(pin):
	return applock.unlock_pin(_me(unlocked=False).user, pin)


@frappe.whitelist(methods=["POST"])
def face_options(purpose="unlock"):
	user = _me(unlocked=purpose == "setup").user
	return applock.options(user, "setup" if purpose == "setup" else "unlock")


@frappe.whitelist(methods=["POST"])
def face_setup(credential, device=None):
	return applock.register(_me().user, credential, device)


@frappe.whitelist(methods=["POST"])
def face_unlock(credential):
	return applock.verify(_me(unlocked=False).user, credential)


# ---------- Finance (SK draft F06) ----------

@frappe.whitelist()
def fin_cash():
	return finance.cash_today(_me().user)


@frappe.whitelist()
def fin_collect():
	return finance.to_collect(_me().user)


@frappe.whitelist(methods=["POST"])
def fin_promise(sales_invoice, text=None, promised_on=None):
	return finance.promise(_me().user, sales_invoice, text, promised_on)


@frappe.whitelist(methods=["POST"])
def fin_receive(reference_doctype, reference_name, amount, mode=None, reference_no=None, reference_date=None, photo=None):
	return finance.receive_payment(_me().user, reference_doctype, reference_name, amount, mode, reference_no, reference_date, photo)


@frappe.whitelist()
def fin_to_pay():
	return finance.to_pay(_me().user)


@frappe.whitelist()
def fin_pay_approvals():
	return finance.pay_approvals(_me().user)


@frappe.whitelist(methods=["POST"])
def fin_approve_payment(purchase_invoice):
	return finance.approve_payment(_me().user, purchase_invoice)


@frappe.whitelist(methods=["POST"])
def fin_ask_approval(purchase_invoice):
	return finance.ask_approval(_me().user, purchase_invoice)


@frappe.whitelist(methods=["POST"])
def fin_pay(purchase_invoice, amount=None, mode=None, reference_no=None, reference_date=None, photo=None):
	return finance.pay(_me().user, purchase_invoice, amount, mode, reference_no, reference_date, photo)


@frappe.whitelist()
def fin_bills():
	return finance.bills_to_post(_me().user)


@frappe.whitelist(methods=["POST"])
def fin_make_bill(purchase_order, bill_no, bill_date=None, todo=None, photo=None):
	return finance.make_bill(_me().user, purchase_order, bill_no, bill_date, todo, photo)


@frappe.whitelist(methods=["POST"])
def fin_post(doctype, name):
	return finance.post(_me().user, doctype, name)


@frappe.whitelist(methods=["POST"])
def fin_bill_photo_done(todo):
	return finance.done_bill_photo(_me().user, todo)


@frappe.whitelist()
def fin_invoices():
	return finance.invoices(_me().user)


@frappe.whitelist(methods=["POST"])
def fin_make_invoice(delivery_note):
	return finance.make_invoice(_me().user, delivery_note)


@frappe.whitelist()
def fin_expenses():
	return finance.expenses(_me().user)


@frappe.whitelist(methods=["POST"])
def fin_pay_expense(expense_claim):
	return finance.pay_expense(_me().user, expense_claim)


@frappe.whitelist()
def fin_voucher_options():
	return finance.voucher_options(_me().user)


@frappe.whitelist(methods=["POST"])
def fin_petty_cash(expense_account, amount, cash_account, cost_center=None, narration=None, photo=None):
	return finance.petty_cash(_me().user, expense_account, amount, cash_account, cost_center, narration, photo)


@frappe.whitelist()
def fin_segment_pnl(month=None):
	return finance.segment_pnl(_me().user, month)


@frappe.whitelist()
def fin_month_close():
	return finance.month_close(_me().user)


@frappe.whitelist(methods=["POST"])
def fin_tick_close(key, done=1):
	return finance.tick_close(_me().user, key, done)


# ---------- Store (SK draft F01) ----------

def _list(v):
	return frappe.parse_json(v) if isinstance(v, str) else (v or [])


@frappe.whitelist()
def store_search(q=None):
	return store.stock_search(_me().user, q)


@frappe.whitelist()
def store_item(item_code):
	return store.item_detail(_me().user, item_code)


@frappe.whitelist()
def store_open_pos():
	return store.open_purchase_orders(_me().user)


@frappe.whitelist(methods=["POST"])
def store_receive(items, purchase_order=None, challan_photo=None, goods_photo=None, note=None, supplier=None, reason=None, bill_no=None):
	return store.receive(_me().user, purchase_order, _list(items), challan_photo, goods_photo, note, supplier, reason, bill_no)


@frappe.whitelist()
def store_work_orders():
	return store.open_work_orders(_me().user)


@frappe.whitelist(methods=["POST"])
def store_issue(work_order, items, taken_by=None, job_card=None, photo=None):
	return store.issue(_me().user, work_order, _list(items), taken_by, job_card, photo)


@frappe.whitelist()
def store_requests(kind="store"):
	return store.material_requests(_me().user, kind)


@frappe.whitelist(methods=["POST"])
def store_request_issue(request):
	return store.request_issue(_me().user, request)


@frappe.whitelist(methods=["POST"])
def store_request_to_purchase(request):
	return store.request_to_purchase(_me().user, request)


@frappe.whitelist()
def store_low_stock():
	return store.low_stock(_me().user)


@frappe.whitelist(methods=["POST"])
def store_order_low(item_codes=None):
	return store.order_low(_me().user, _list(item_codes) or None)


@frappe.whitelist()
def store_dispatch_orders():
	return store.orders_to_dispatch(_me().user)


@frappe.whitelist(methods=["POST"])
def store_dispatch(sales_order, vehicle_no=None, driver_mobile=None, cabin_photo=None, plate_photo=None, note=None):
	return store.dispatch(_me().user, sales_order, vehicle_no, driver_mobile, cabin_photo, plate_photo, note)


@frappe.whitelist()
def store_warehouses():
	return store.warehouses(_me().user)


@frappe.whitelist()
def store_count_list(warehouse):
	return store.count_list(_me().user, warehouse)


@frappe.whitelist(methods=["POST"])
def store_count(warehouse, counts, photo=None):
	return store.stock_count(_me().user, warehouse, _list(counts), photo)


@frappe.whitelist()
def store_item_options():
	return store.item_options(_me().user)


@frappe.whitelist()
def store_similar(name):
	return store.similar_items(_me().user, name)


@frappe.whitelist(methods=["POST"])
def store_new_item(item_name, item_group, uom, warehouse=None, photo=None):
	return store.new_item(_me().user, item_name, item_group, uom, warehouse, photo)


# ---------- Purchase (SK draft F02) ----------

@frappe.whitelist()
def buy_requests():
	return purchase.requests(_me().user)


@frappe.whitelist()
def buy_suggest(item_code):
	return purchase.suggest_suppliers(_me().user, item_code)


@frappe.whitelist()
def buy_suppliers(q=None):
	return purchase.suppliers(_me().user, q)


@frappe.whitelist(methods=["POST"])
def buy_rfq(items, suppliers, need_by=None):
	return purchase.make_rfq(_me().user, _list(items), _list(suppliers), need_by)


@frappe.whitelist(methods=["POST"])
def buy_quote(supplier, item_code, qty, rate, days=None, photo=None, rfq=None):
	return purchase.add_quote(_me().user, supplier, item_code, qty, rate, days, photo, rfq)


@frappe.whitelist()
def buy_compare(item_code):
	return purchase.compare(_me().user, item_code)


@frappe.whitelist()
def buy_quoted_items():
	"""Items with quotes in the last 30 days, for the Compare screen."""
	purchase.need(_me().user, purchase.PURCHASE)
	return frappe.db.sql("""select i.item_code, i.item_name, count(*) quotes from `tabSupplier Quotation Item` i
		join `tabSupplier Quotation` q on q.name = i.parent where q.docstatus < 2 and q.transaction_date >= %s
		group by i.item_code, i.item_name order by max(q.creation) desc""", add_to_date(getdate(), days=-30), as_dict=True)


@frappe.whitelist(methods=["POST"])
def buy_make_po(supplier_quotation, schedule_date=None, terms=None):
	return purchase.make_po(_me().user, supplier_quotation, schedule_date, terms)


@frappe.whitelist()
def buy_approvals():
	return purchase.approvals(_me().user)


@frappe.whitelist(methods=["POST"])
def buy_decide(purchase_order, approve, reason=None):
	return purchase.decide(_me().user, purchase_order, bool(cint(approve)), reason)


@frappe.whitelist()
def buy_follow_up():
	return purchase.follow_up(_me().user)


@frappe.whitelist(methods=["POST"])
def buy_follow_up_note(purchase_order, text, promised=None):
	return purchase.follow_up_note(_me().user, purchase_order, text, promised)


@frappe.whitelist(methods=["POST"])
def buy_new_supplier(supplier_name, gstin=None, mobile=None, group=None, photo=None, cheque_photo=None):
	return purchase.new_supplier(_me().user, supplier_name, gstin, mobile, group, photo, cheque_photo)


@frappe.whitelist()
def buy_supplier_groups():
	return frappe.get_all("Supplier Group", filters={"is_group": 0}, pluck="name", order_by="name asc")


@frappe.whitelist(methods=["POST"])
def buy_send_bill(supplier, photo, amount=None, bill_no=None, against=None, note=None):
	return purchase.send_bill(_me().user, supplier, photo, amount, bill_no, against, note)


@frappe.whitelist()
def buy_last_rates(q=None):
	return purchase.last_rates(_me().user, q)


@frappe.whitelist()
def team_follow_up(person=None):
	"""Sales manager's review (SK, 26-Oct: Rushi sees Swati, Pranali and Rahul's leads and deals with his own):
	one summary line per person and the open leads / deals of everyone, or of one person."""
	profile = _me()
	people = [{"user": profile.user, "full_name": profile.full_name or profile.user}] + [
		{"user": p.user, "full_name": p.full_name or p.user} for p in day_report._team(profile.user)]
	allowed = {p["user"] for p in people}
	if person and person not in allowed:
		frappe.throw(_("{0} is not in your team").format(person), frappe.PermissionError)
	summary, rows = [], []
	for p in people:
		items = crm.follow_up(p["user"], for_manager=p["user"] != profile.user)
		month = kpi.scorecard(p["user"])
		summary.append({**p, "open": len(items), "overdue": sum(1 for r in items if r["overdue"]), "new": sum(1 for r in items if r["new"]),
			"deal_value": sum(flt(r.get("value")) for r in items if r["doctype"] == "CRM Deal"), "score": month.get("score")})
		if not person or person == p["user"]:
			rows += [{**r, "owner": p["user"], "owner_name": p["full_name"]} for r in items]
	rows.sort(key=lambda r: (not r["overdue"], not r["new"]))
	return {"people": summary, "rows": rows}

# ---------- Production + subcontractors (SK draft F03) ----------

@frappe.whitelist()
def prod_board():
	return production.order_board(_me().user)


@frappe.whitelist()
def prod_job_cards():
	return production.job_cards(_me().user)


@frappe.whitelist(methods=["POST"])
def prod_start(job_card, photo=None):
	return production.start(_me().user, job_card, photo)


@frappe.whitelist(methods=["POST"])
def prod_photo(job_card, photo=None, note=None):
	return production.add_photo(_me().user, job_card, photo, note)


@frappe.whitelist(methods=["POST"])
def prod_done(job_card, photos=None, workers=None, remark=None):
	return production.done(_me().user, job_card, _list(photos), workers, remark)


@frappe.whitelist(methods=["POST"])
def prod_need_material(items=None, job_card=None, work_order=None, needed_by=None, spoken=None):
	return production.need_material(_me().user, _list(items), job_card, work_order, needed_by, spoken)


@frappe.whitelist(methods=["POST"])
def prod_progress_photo(work_order, photo, note=None):
	return production.progress_photo(_me().user, work_order, photo, note)


@frappe.whitelist()
def prod_ready():
	return production.ready_to_dispatch(_me().user)


# ---------- Quality (SK draft F04) ----------

@frappe.whitelist()
def qc_pending():
	return quality.pending(_me().user)


@frappe.whitelist()
def qc_templates(reference_type=None, operation=None, item_code=None):
	user = _me().user
	return {"templates": quality.templates(user), "guess": quality.guess_template(reference_type, operation, item_code)}


@frappe.whitelist()
def qc_checklist(template):
	return quality.checklist(_me().user, template)


@frappe.whitelist(methods=["POST"])
def qc_save(reference_type, reference_name, item_code, points, template=None, sample_size=1, accepted_qty=None,
		rejected_qty=None, photos=None, remark=None, inspection_type=None):
	return quality.save(_me().user, reference_type, reference_name, item_code, _list(points), template, sample_size,
		accepted_qty, rejected_qty, _list(photos), remark, inspection_type)


@frappe.whitelist(methods=["POST"])
def qc_raise_nc(subject, details=None, job_card=None, fixer=None, by_when=None, photos=None):
	return quality.raise_nc(_me().user, subject, details, job_card, fixer, by_when, _list(photos))


@frappe.whitelist()
def qc_open_ncs():
	return quality.open_ncs(_me().user)


@frappe.whitelist(methods=["POST"])
def qc_close_nc(name, action, photo=None):
	return quality.close_nc(_me().user, name, action, photo)


# ---------- AI & ERP desk (Samir) ----------
@frappe.whitelist()
def ai_inbox():
	return ai_desk.inbox(_me().user)


@frappe.whitelist(methods=["POST"])
def ai_sort(doctype, name, category, note=None, due=None):
	return ai_desk.sort_item(_me().user, doctype, name, category, note, due)


@frappe.whitelist(methods=["POST"])
def ai_close(todo, note=None):
	return ai_desk.close_item(_me().user, todo, note)


@frappe.whitelist()
def ai_visit(day=None):
	return ai_desk.visit(_me().user, day)


@frappe.whitelist(methods=["POST"])
def ai_visit_note(department, text):
	return ai_desk.visit_note(_me().user, department, text)


@frappe.whitelist()
def ai_gaps():
	return ai_desk.erp_gaps(_me().user)


@frappe.whitelist()
def ai_app_users():
	return ai_desk.app_users(_me().user)


@frappe.whitelist()
def ai_change_list():
	return ai_desk.change_list(_me().user)


@frappe.whitelist(methods=["POST"])
def ai_set_change(no, status):
	return ai_desk.set_change(_me().user, no, status)


@frappe.whitelist()
def ai_projects():
	return ai_desk.projects(_me().user)


@frappe.whitelist()
def ai_training():
	return ai_desk.training_progress(_me().user)


# ---------- Ledger-wise Accounts screens ----------
@frappe.whitelist()
def fin_ledgers(kind, month=None):
	return ledger.ledgers(_me().user, kind, month)


@frappe.whitelist()
def fin_ledger_entries(kind, ledger_name, month=None):
	return ledger.entries(_me().user, kind, ledger_name, month)


@frappe.whitelist()
def fin_segment_wise(month=None):
	return ledger.segment_wise(_me().user, month)


@frappe.whitelist()
def fin_month_wise(year_start=None):
	return ledger.month_wise(_me().user, year_start)


# ---------- Team mailboxes and auto leads (point 14) ----------
@frappe.whitelist()
def team_mail(days=30):
	return mailbox.inbox(_me().user, cint(days) or 30)


@frappe.whitelist()
def team_mail_read(comm):
	return mailbox.read(_me().user, comm)


@frappe.whitelist(methods=["POST"])
def team_mail_take(comm):
	return mailbox.take(_me().user, comm)


@frappe.whitelist(methods=["POST"])
def team_mail_give(comm, to_user):
	return mailbox.give(_me().user, comm, to_user)


@frappe.whitelist(methods=["POST"])
def team_mail_not_lead(comm):
	return mailbox.not_a_lead(_me().user, comm)


@frappe.whitelist(methods=["POST"])
def team_mail_lead(comm, segment=None):
	return mailbox.make_lead(_me().user, comm, segment)


@frappe.whitelist(methods=["POST"])
def team_mail_reply(comm, message):
	return mailbox.reply(_me().user, comm, message)


@frappe.whitelist(methods=["POST"])
def leads_upload(file_url, source="IndiaMART"):
	return lead_sources.upload(_me().user, file_url, source)


@frappe.whitelist()
def lead_sources_status():
	return lead_sources.status(_me().user)


@frappe.whitelist(methods=["POST"])
def lead_sources_switch(setting, on):
	return lead_sources.switch(_me().user, setting, on)


@frappe.whitelist(methods=["POST"])
def lead_sources_check_now():
	lead_sources.status(_me().user)  # same rights as the page
	return lead_sources.scan()


# point 2: Cabin / Non-Cabin customers
@frappe.whitelist()
def customers(tab="mine", q=None, segment=None):
	return segments.customers(_me().user, tab, q, segment)


@frappe.whitelist(methods=["POST"])
def tag_customer(customer, segment):
	return segments.tag(_me().user, customer, segment)


@frappe.whitelist(methods=["POST"])
def tag_customers_from_tally():
	return segments.tag_from_tally(_me().user)


# point 3: CEO "View Member App"
@frappe.whitelist()
def view_members():
	return view_member.members(_me().user)


@frappe.whitelist()
def view_as(member, method, args=None, view=None):
	viewer = _me().user
	if isinstance(args, str):
		args = json.loads(args or "{}")
	return view_member.view_as(viewer, member, method, args or {}, view)


@frappe.whitelist(methods=["POST"])
def view_suggest(member, text, view=None, photo=None):
	return view_member.suggest(_me().user, member, view, text, photo)


# point 13: CEO live dashboards
@frappe.whitelist()
def my_flow():
	"""Point 17: the live process flow of each of the person's functions (the CEO: one per function)."""
	profile = _me()
	return flows.for_user(profile.user, logins.profile_functions(profile.user) or [profile.home])


@frappe.whitelist()
def sales_assign_list(q=None):
	return sales_owner.assign_list(_me().user, q)


@frappe.whitelist(methods=["POST"])
def sales_assign(customer, sales_person=None):
	return sales_owner.assign(_me().user, customer, sales_person)


@frappe.whitelist(methods=["POST"])
def convert_lead(name):
	return crm.convert_lead(_me().user, name)


@frappe.whitelist()
def flow_stage(src, key):
	"""All records of one flow box, for the full list screen."""
	profile = _me()
	return flows.stage_rows(profile.user, logins.profile_functions(profile.user) or [profile.home], src, key)


@frappe.whitelist()
def el_jobs():
	return production.el_jobs(_me().user)


@frappe.whitelist()
def save_el_points(job_card, points=None, photo=None, note=None):
	points = json.loads(points) if isinstance(points, str) else points
	return production.save_el_points(_me().user, job_card, points or {}, photo, note)


@frappe.whitelist()
def kpi_actions(member=None):
	return home_kpi.actions(_me().user, member)


@frappe.whitelist()
def add_kpi_action(text, member=None, priority="Medium", date=None):
	return home_kpi.add_action(_me().user, member, text, priority, date)


@frappe.whitelist()
def finish_kpi_action(name, note=None, photo=None):
	return home_kpi.finish_action(_me().user, name, note, photo)


@frappe.whitelist()
def my_home_kpi():
	"""Main screen Rev 2 (SK 26-Oct): the person's one KPI chart against target and the Today strip."""
	profile = _me()
	return home_kpi.for_user(profile.user, logins.profile_functions(profile.user) or [profile.home])


@frappe.whitelist()
def dash_page(key="overview", month=None, segment=None):
	return dashboards.page(_me().user, key, month, segment)


# point 5: customer complaints
@frappe.whitelist()
def complaints_list(tab="mine"):
	return complaints.listing(_me().user, tab)


@frappe.whitelist()
def complaint_orders(customer):
	return complaints.orders(_me().user, customer)


@frappe.whitelist()
def complaint_detail(name):
	return complaints.detail(_me().user, name)


@frappe.whitelist(methods=["POST"])
def complaint_new(customer, text, ctype, sales_order=None, files=None):
	if isinstance(files, str):
		files = json.loads(files or "[]")
	return complaints.register(_me().user, customer, text, ctype, sales_order, files)


@frappe.whitelist(methods=["POST"])
def complaint_accept(name, fix_by=None, note=None):
	return complaints.accept(_me().user, name, fix_by, note)


@frappe.whitelist(methods=["POST"])
def complaint_fixed(name, note=None, photo=None, cost=None):
	return complaints.fixed(_me().user, name, note, photo, cost)


@frappe.whitelist(methods=["POST"])
def complaint_customer(name, ok, note=None, photo=None):
	return complaints.customer_answer(_me().user, name, ok, note, photo)


# point 7: FAQ per function with "Ask a question"
@frappe.whitelist()
def training_faq(q=None):
	return training.faq(_me().user, q)


@frappe.whitelist(methods=["POST"])
def training_ask(question, function=None):
	return training.ask(_me().user, question, function)


@frappe.whitelist(methods=["POST"])
def training_answer(todo, text, add_to_faq=1):
	return training.answer(_me().user, todo, text, add_to_faq)


# point 8: product cards
@frappe.whitelist()
def product_catalogue(main=None):
	_me()
	return products.catalogue(main=main)


# point 1: check before saving
@frappe.whitelist()
def photo_check(kind, values=None):
	if isinstance(values, str):
		values = json.loads(values or "{}")
	return photocheck.check(_me().user, kind, values or {})


@frappe.whitelist(methods=["POST"])
def photo_learn(kind, read_text, chosen):
	return photocheck.learn(_me().user, kind, read_text, chosen)


# point 16 + HR step 5: Optick / thumb attendance, leave and expenses
@frappe.whitelist()
def hr_today(day=None):
	return hr.today(_me().user, day)


@frappe.whitelist()
def hr_month(month=None):
	return hr.month(_me().user, month)


@frappe.whitelist(methods=["POST"])
def hr_upload_preview(file_url, device="Optick"):
	return hr.upload_preview(_me().user, file_url, device)


@frappe.whitelist(methods=["POST"])
def hr_upload_save(file_url, matches=None, device="Optick"):
	if isinstance(matches, str):
		matches = json.loads(matches or "{}")
	return hr.upload_save(_me().user, file_url, matches, device)


@frappe.whitelist(methods=["POST"])
def hr_fix(employee, day, status, reason, todo=None):
	return hr.fix_attendance(_me().user, employee, day, status, reason, todo)


@frappe.whitelist(methods=["POST"])
def attendance_selfie(photo, lat=None, lng=None):
	return hr.selfie_checkin(_me().user, photo, lat, lng)


@frappe.whitelist(methods=["POST"])
def attendance_ask_fix(text, day=None):
	return hr.ask_fix(_me().user, day, text)


@frappe.whitelist()
def leave_expense():
	user = _me().user
	return {**hr.options(user), **hr.listing(user)}


@frappe.whitelist(methods=["POST"])
def leave_apply(leave_type, from_date, to_date=None, half_day=0, reason=None):
	return hr.apply_leave(_me().user, leave_type, from_date, to_date, half_day, reason)


@frappe.whitelist(methods=["POST"])
def leave_decide(name, ok, note=None):
	return hr.decide_leave(_me().user, name, ok, note)


@frappe.whitelist(methods=["POST"])
def expense_claim(expense_type, amount, expense_date=None, note=None, photo=None):
	return hr.claim_expense(_me().user, expense_type, amount, expense_date, note, photo)


@frappe.whitelist(methods=["POST"])
def expense_decide(name, ok, note=None):
	return hr.decide_expense(_me().user, name, ok, note)


# ---- ERP flow in the app (SK 26-Oct): Customer → Quotation → Sales Order → Work Order ----

@frappe.whitelist(methods=["POST"])
def flow_make_customer(deal):
	from sk_app import erp_flow

	return erp_flow.make_customer(_me().user, deal)


@frappe.whitelist(methods=["POST"])
def flow_make_quotation(deal, items, valid_days=15, note=None):
	from sk_app import erp_flow

	return erp_flow.make_quotation(_me().user, deal, _list(items), int(valid_days or 15), note)


@frappe.whitelist(methods=["POST"])
def flow_order_received(quotation, delivery_date=None, po_no=None):
	from sk_app import erp_flow

	return erp_flow.order_received(_me().user, quotation, delivery_date, po_no)


@frappe.whitelist(methods=["POST"])
def flow_confirm_order(sales_order):
	from sk_app import erp_flow

	return erp_flow.confirm_order(_me().user, sales_order)


@frappe.whitelist()
def flow_orders_to_plan():
	from sk_app import erp_flow

	return erp_flow.orders_to_plan(_me().user)


@frappe.whitelist(methods=["POST"])
def flow_make_work_order(sales_order, so_item):
	from sk_app import erp_flow

	return erp_flow.make_work_order(_me().user, sales_order, so_item)
