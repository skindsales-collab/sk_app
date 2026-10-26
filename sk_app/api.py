"""Endpoints used by the SK App phone screens. Every call works on the logged-in ERPNext user only."""

import frappe
from frappe import _
from frappe.utils import add_to_date, cint, flt, getdate, now_datetime

from sk_app import calendar_view, claude, comms, crm, day_report, guide, kpi, logins, purchase, store, training, work
from sk_app import library as lib
from sk_app.functions import home_for, sections_for
from sk_app.logic import rank_items

CARD_REUSE_MINUTES = 10


def _me():
	user = frappe.session.user
	if user in ("Guest", None):
		frappe.throw(_("Please log in"), frappe.PermissionError)
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
	return {"user": profile.user, "full_name": profile.full_name, "language": profile.language,
		"mobile": me.get("mobile_no") or me.get("phone"),
		"home": home_for(profile.home, has_team=team), "functions": functions,
		# SK: a person in several functions sees all of them on one Home, one labelled row each
		"sections": sections_for(functions, has_team=team) if len(functions) > 1 else None,
		"must_set_pin": bool(frappe.db.get_value("SK App User", profile.name, "must_set_pin")),
		"card": _latest_card(profile.user),
		"new_files": crm.files_to_send(profile.user), "day_report_sent": bool(day_report._find(profile.user, getdate())),
		"due_reminders": comms.due_reminders(profile.user), "badges": _badges(profile.user, functions)}


def _badges(user, functions):
	"""Red counts on Store / Purchase / approval icons; never breaks Home if ERPNext data is odd."""
	try:
		return {**store.badges(user, functions), **purchase.badges(user, functions)}
	except Exception:
		frappe.log_error("SK App badges")
		return {}


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
def hr_reset_pin(user):
	_me()
	return logins.reset_pin(frappe.session.user, user)


@frappe.whitelist(methods=["POST"])
def hr_close_login(user):
	_me()
	return logins.close_login(frappe.session.user, user)


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
def store_receive(items, purchase_order=None, challan_photo=None, goods_photo=None, note=None, supplier=None, reason=None):
	return store.receive(_me().user, purchase_order, _list(items), challan_photo, goods_photo, note, supplier, reason)


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
		items = crm.follow_up(p["user"])
		month = kpi.scorecard(p["user"])
		summary.append({**p, "open": len(items), "overdue": sum(1 for r in items if r["overdue"]), "new": sum(1 for r in items if r["new"]),
			"deal_value": sum(flt(r.get("value")) for r in items if r["doctype"] == "CRM Deal"), "score": month.get("score")})
		if not person or person == p["user"]:
			rows += [{**r, "owner": p["user"], "owner_name": p["full_name"]} for r in items]
	rows.sort(key=lambda r: (not r["overdue"], not r["new"]))
	return {"people": summary, "rows": rows}
