"""Endpoints used by the SK App phone screens. Every call works on the logged-in ERPNext user only."""

import frappe
from frappe import _
from frappe.utils import add_to_date, cint, flt, getdate, now_datetime

from sk_app import claude, crm, day_report, guide, kpi, training, work
from sk_app.functions import home_for
from sk_app.logic import rank_items

CARD_REUSE_MINUTES = 10


def _me():
	user = frappe.session.user
	if user in ("Guest", None):
		frappe.throw(_("Please log in"), frappe.PermissionError)
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
	return {"user": profile.user, "full_name": profile.full_name, "language": profile.language,
		"home": home_for(profile.home, has_team=_has_team(profile.user)), "card": _latest_card(profile.user),
		"new_files": crm.new_files(profile.user), "day_report_sent": bool(day_report._find(profile.user, getdate()))}


def _has_team(user):
	return bool(frappe.db.exists("SK App User", {"manager": user, "enabled": 1})) or bool(
		{"System Manager", "HR Manager"} & set(frappe.get_roles(user)))


@frappe.whitelist()
def my_day():
	profile = _me()
	items = rank_items(work.collect(profile.user, profile.home), now_datetime())
	return {"items": [_item_dict(i) for i in items], "card": _latest_card(profile.user)}


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
	return kpi.scorecard(profile.user, day)


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
	doc = frappe.get_doc({
		"doctype": "SK Work Log", "user": profile.user, "date": getdate(), "entry_type": entry_type,
		"problem_type": problem_type, "description": description, "reference_doctype": reference_doctype,
		"reference_name": reference_name, "assigned_to": assigned_to, "photo": photo,
	}).insert(ignore_permissions=True)
	if assigned_to:
		from frappe.desk.form.assign_to import add as assign

		assign({"assign_to": [assigned_to], "doctype": "SK Work Log", "name": doc.name, "description": description})
	return doc.name


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
		requirement=None, photo=None):
	return crm.new_lead(_me().user, first_name, mobile_no, organization, email, source, segment, requirement, photo)


@frappe.whitelist(methods=["POST"])
def set_crm_status(doctype, name, status):
	_me()
	return crm.set_status(doctype, name, status)


@frappe.whitelist(methods=["POST"])
def add_crm_note(doctype, name, text=None, photo=None):
	return crm.add_note(_me().user, doctype, name, text, photo)


@frappe.whitelist(methods=["POST"])
def log_contact(doctype, name, channel, outcome=None, text=None, photo=None):
	return crm.log_contact(_me().user, doctype, name, channel, outcome, text, photo)


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
def share_link(doctype, name):
	_me()
	return crm.share_link(doctype, name)


# ---- Training ----

@frappe.whitelist()
def training_lessons():
	profile = _me()
	return training.lessons(profile.user, profile.home)


@frappe.whitelist(methods=["POST"])
def training_done(lesson):
	return training.mark_done(_me().user, lesson)


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
