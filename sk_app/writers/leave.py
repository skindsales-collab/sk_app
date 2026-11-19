"""The one Leave writer (linear flow map, Flow 6). On the New path of HR:

person applies in the app -> Leave Application (Open) with the HR person as approver -> HR approves: it goes to the CEO
(approver changed, ToDo) -> CEO approves: posted. Rules on every Leave Application (app, ERPNext, SK Hub): paid leave
only after 6 months and as earned (1 per 20 days worked). The holiday list is checked nightly against SK's paid holidays."""

import frappe
from frappe import _
from frappe.utils import cint, getdate, nowdate

from sk_app.core.rules import report
from sk_app.writers.leave_rules import eligible_from, holiday_problems, leave_problems, next_step

MODULE = "HR"
HR_OK = "[HR approved]"
BUILD_FROM_JOINING = True  # waits for SK's answer (decision card 7-Nov)


def _use_new(user=None) -> bool:
	from sk_app.core.switch import use_new

	return use_new(MODULE, user if user is not None else frappe.session.user)


def approver(user: str) -> str | None:
	"""First the HR person (not the one applying), else the CEO. No names in code: from the SK App User functions."""
	from sk_app import hr
	from sk_app.core.people import ceo_users

	return next((u for u in hr._hr_people() + list(ceo_users()) if u != user), None)


def _paid(leave_type: str) -> bool:
	return not cint(frappe.db.get_value("Leave Type", leave_type, "is_lwp"))


def worked_and_used(employee: str, since, leave_name: str | None = None) -> tuple[float, float]:
	"""Days worked (present 1, half day 0.5) and paid leave already taken or waiting, both since `since`."""
	worked = 0.0
	for a in frappe.get_all("Attendance", filters={"employee": employee, "docstatus": 1, "attendance_date": [">=", since],
			"status": ["in", ["Present", "Half Day", "Work From Home"]]}, fields=["status"]):
		worked += 0.5 if a.status == "Half Day" else 1
	used = 0.0
	for l in frappe.get_all("Leave Application", filters={"employee": employee, "docstatus": ["<", 2], "from_date": [">=", since],
			"status": ["in", ["Open", "Approved"]], "name": ["!=", leave_name or ""]}, fields=["leave_type", "total_leave_days"]):
		if _paid(l.leave_type):
			used += float(l.total_leave_days or 0)
	return worked, used


def problems(doc) -> list:
	joined = frappe.db.get_value("Employee", doc.employee, "date_of_joining")
	joined = getdate(joined) if joined else None
	# leave builds up from joining, usable after 6 months (recommended to SK 7-Nov; BUILD_FROM_JOINING False = from the 6-month day)
	since = (joined if BUILD_FROM_JOINING else eligible_from(joined)) if joined else None
	worked, used = worked_and_used(doc.employee, since, doc.name) if joined else (0, 0)
	return leave_problems(_paid(doc.leave_type), doc.total_leave_days or 1, joined, getdate(doc.from_date), worked, used)


def on_validate(doc, method=None):
	if doc.docstatus != 0 or doc.status not in ("Open", "Approved") or not _use_new(doc.owner):
		return
	report(MODULE, doc, problems(doc), title=_("Leave check"))


def ensure_allocation(doc, method=None):
	"""before_validate (New path): ERPNext needs a Leave Allocation before any paid leave, and the live site has none
	(Mac test 9-Nov). The allocation is the earned leave of SK's rule (1 per 20 days worked), made or topped up here,
	so nobody allocates by hand and the ERPNext check and SK's rule agree."""
	if doc.docstatus != 0 or not _use_new(doc.owner) or not _paid(doc.leave_type):
		return
	from sk_app.core.dates import fy_start
	from sk_app.writers.leave_rules import earned

	joined = frappe.db.get_value("Employee", doc.employee, "date_of_joining")
	if not joined:
		return
	since = getdate(joined) if BUILD_FROM_JOINING else eligible_from(getdate(joined))
	total = earned(worked_and_used(doc.employee, since, doc.name)[0])
	if total <= 0:  # nothing earned yet: say so plainly here, before ERPNext's own "outside allocation period"
		frappe.throw(_("No paid leave earned yet (1 per {0} days worked since joining); take Leave Without Pay").format(
			__import__("sk_app.writers.leave_rules", fromlist=["x"]).DAYS_PER_LEAVE))
	start = fy_start(getdate(doc.from_date))
	end = frappe.utils.add_days(start.replace(year=start.year + 1), -1)
	have = frappe.db.get_value("Leave Allocation", {"employee": doc.employee, "leave_type": doc.leave_type, "docstatus": 1,
		"from_date": ["<=", doc.from_date], "to_date": [">=", doc.from_date]}, ["name", "total_leaves_allocated"], as_dict=True)
	if not have:
		frappe.get_doc({"doctype": "Leave Allocation", "employee": doc.employee, "leave_type": doc.leave_type, "from_date": max(start, getdate(joined)),
			"to_date": end, "new_leaves_allocated": total, "description": "SK App: earned leave, 1 per 20 days worked"}).insert(ignore_permissions=True).submit()
	elif total > float(have.total_leaves_allocated or 0):
		from hrms.hr.doctype.leave_ledger_entry.leave_ledger_entry import create_leave_ledger_entry

		alloc = frappe.get_doc("Leave Allocation", have.name)
		diff = total - float(have.total_leaves_allocated or 0)
		alloc.db_set({"new_leaves_allocated": float(alloc.new_leaves_allocated or 0) + diff, "total_leaves_allocated": total}, update_modified=False)
		create_leave_ledger_entry(alloc, frappe._dict(leaves=diff, from_date=alloc.from_date, to_date=alloc.to_date, is_carry_forward=0), submit=True)


def decide(user: str, doc, ok, note: str | None = None) -> dict:
	"""HR then CEO. Returns {status} like the old decide_leave."""
	from sk_app import hr
	from sk_app.store import _todo

	hr_done = bool(frappe.db.exists("Comment", {"reference_doctype": "Leave Application", "reference_name": doc.name,
		"content": ["like", f"{HR_OK}%"]}))
	step = next_step(bool(cint(ok)), hr._is_hr(user) and not hr._is_ceo(user), hr._is_ceo(user), hr_done)
	if step == "not_allowed":
		frappe.throw(_("HR approves first, then the CEO"), frappe.PermissionError)
	if step == "to_ceo":
		ceo = next((u for u in hr._ceos() if u != user), None)
		doc.add_comment("Comment", f"{HR_OK} {frappe.utils.get_fullname(user)}{': ' + note.strip()[:200] if note else ''}")
		hr._close_todos("Leave Application", doc.name)
		if ceo:
			doc.db_set("leave_approver", ceo)
			_todo(ceo, "Leave Application", doc.name, f"Leave: {doc.employee_name} {doc.from_date} to {doc.to_date} ({doc.leave_type}). "
				"HR approved, please approve.")
		return {"status": "Waiting CEO"}
	doc.status = "Approved" if step == "approve" else "Rejected"
	doc.flags.ignore_permissions = True
	doc.save()
	doc.submit()
	return {"status": doc.status}


def check_holidays() -> list:
	"""Nightly (New path): the company holiday list of this financial year against SK's paid holidays; gaps to SK Rule Log."""
	from sk_app.core.dates import fy_start
	from sk_app.store import _company

	if not _use_new("") or not frappe.db.exists("DocType", "Holiday List"):
		return []
	start = fy_start(getdate(nowdate()))
	hl = frappe.get_cached_value("Company", _company(), "default_holiday_list")
	rows = [(getdate(h.holiday_date), h.description) for h in frappe.get_all("Holiday", filters={"parent": hl, "weekly_off": 0},
		fields=["holiday_date", "description"])] if hl else []
	found = holiday_problems(rows, start.year)
	if found and frappe.db.table_exists("SK Rule Log") and not frappe.db.exists("SK Rule Log",
			{"rule": "holiday_missing", "creation": [">=", nowdate()]}):
		for key, words in found:
			frappe.get_doc({"doctype": "SK Rule Log", "module": MODULE, "rule": key, "mode": "Warn only",
				"reference_doctype": "Holiday List" if hl else None, "reference_name": hl, "detail": words}).insert(ignore_permissions=True)
	return found


# ---------- Plan A (SK 9-Nov): moved here unchanged from hr.py ----------
from datetime import timedelta
from frappe import _
from frappe.utils import cint, getdate, nowdate
from sk_app.hr import _approver, _close_todos, _may_decide, _my_employee
from sk_app.store import _company, _todo
import frappe
import re


def apply_leave(user: str, leave_type: str, from_date, to_date=None, half_day=0, reason: str | None = None) -> dict:
	from sk_app.writers import leave

	emp = _my_employee(user)
	# rebuild Flow 6 (New path of HR): HR approves first, then the CEO (SK 7-Nov)
	approver = leave.approver(user) if leave._use_new(user) else _approver(emp, user, "leave_approver")
	doc = frappe.get_doc({"doctype": "Leave Application", "employee": emp.name, "leave_type": leave_type, "from_date": getdate(from_date),
		"to_date": getdate(to_date or from_date), "half_day": cint(half_day), "half_day_date": getdate(from_date) if cint(half_day) else None,
		"description": (reason or "").strip()[:500], "leave_approver": approver, "status": "Open", "company": emp.company,
		"posting_date": nowdate(), "follow_via_email": 0})
	doc.flags.ignore_permissions = True
	try:
		doc.insert()
	except frappe.ValidationError as e:
		frappe.clear_messages()
		msg = str(e)
		if "balance" in msg.lower():
			msg = _("No {0} left for you. Ask HR to give leave, or pick Leave Without Pay.").format(leave_type)
		elif "holiday list" in msg.lower():
			msg = _("HR has not set your holiday list in ERPNext yet (Holiday List Assignment). Please ask HR.")
		frappe.throw(re.sub(r"<[^>]*>", "", msg))
	if approver:
		_todo(approver, "Leave Application", doc.name, f"Leave: {emp.employee_name} {doc.from_date} to {doc.to_date} ({leave_type}). Please approve.")
	return {"name": doc.name, "approver": frappe.utils.get_fullname(approver) if approver else None, "days": doc.total_leave_days}

def decide_leave(user: str, name: str, ok, note: str | None = None) -> dict:
	doc = frappe.get_doc("Leave Application", name)
	if not _may_decide(user, doc.leave_approver):
		frappe.throw(_("Only the approver or HR can do this"), frappe.PermissionError)
	if doc.docstatus != 0:
		frappe.throw(_("Already decided"))
	from sk_app.writers import leave

	if leave._use_new(user):
		got = leave.decide(user, doc, ok, note)
		if got["status"] == "Waiting CEO":
			return got
	else:
		doc.status = "Approved" if cint(ok) else "Rejected"
		doc.flags.ignore_permissions = True
		doc.save()
		doc.submit()
	if note:
		doc.add_comment("Comment", note.strip()[:300])
	_close_todos("Leave Application", name)
	emp_user = frappe.db.get_value("Employee", doc.employee, "user_id")
	if emp_user:
		_todo(emp_user, "Leave Application", name, f"Your leave {doc.from_date} to {doc.to_date}: {doc.status}{' · ' + note if note else ''}")
	return {"status": doc.status}

SK_HOLIDAYS = "SK Holidays {0}-{1}"

def ensure_holiday_setup():
	"""Trial 26-Oct: leave could not be applied on sk-dev: HRMS needs a Holiday List assigned to the company, and the
	holidays were made as one small list per festival with nothing assigned. Once, after deploy: one list for the
	financial year with every festival from those lists plus Sunday weekly off (Optick shows Sunday as Week_off),
	assigned to the company. Nothing is made when the company already has a holiday list."""
	if not frappe.db.exists("DocType", "Holiday List"):
		return
	try:
		company = _company()
		if not company:
			return
		if frappe.db.exists("DocType", "Holiday List Assignment"):
			if frappe.db.exists("Holiday List Assignment", {"assigned_to": company, "docstatus": 1}):
				return
		elif frappe.db.get_value("Company", company, "default_holiday_list"):
			return
		today = getdate()
		fy = today.year if today.month >= 4 else today.year - 1
		start, end = getdate(f"{fy}-04-01"), getdate(f"{fy + 1}-03-31")
		name = SK_HOLIDAYS.format(fy, str(fy + 1)[2:])
		if not frappe.db.exists("Holiday List", name):
			festivals = frappe.get_all("Holiday", filters={"parenttype": "Holiday List", "holiday_date": ["between", [start, end]], "weekly_off": 0},
				fields=["holiday_date", "description"], order_by="holiday_date")
			seen, rows = set(), []
			for h in festivals:
				if h.holiday_date not in seen:
					seen.add(h.holiday_date)
					rows.append({"holiday_date": h.holiday_date, "description": h.description})
			day = start + timedelta(days=(6 - start.weekday()) % 7)
			while day <= end:
				if day not in seen:
					rows.append({"holiday_date": day, "description": "Sunday", "weekly_off": 1})
				day += timedelta(days=7)
			frappe.get_doc({"doctype": "Holiday List", "holiday_list_name": name, "from_date": start, "to_date": end,
				"holidays": sorted(rows, key=lambda r: r["holiday_date"])}).insert(ignore_permissions=True)
		if frappe.db.exists("DocType", "Holiday List Assignment"):
			frappe.get_doc({"doctype": "Holiday List Assignment", "applicable_for": "Company", "assigned_to": company,
				"holiday_list": name, "from_date": start}).insert(ignore_permissions=True).submit()
		if not frappe.db.get_value("Company", company, "default_holiday_list"):
			frappe.db.set_value("Company", company, "default_holiday_list", name)
	except Exception:
		frappe.log_error("SK App holiday list setup")
