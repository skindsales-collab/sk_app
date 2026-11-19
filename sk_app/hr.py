"""HR: attendance from Optick / thumb machine, leave and expenses (change list point 16 + HR draft F05 Rev 2, SK 26-Oct-2026).

Attendance: male staff check in on Optick (face), female office staff on the thumb machine. Step 1 (now, free): Aarti
downloads the day's Optick file (Excel / CSV) and uploads it in the app. Each row becomes an ERPNext Employee Checkin
(IN / OUT, device "Optick") and, while no ERPNext Shift Type does auto attendance, an Attendance (Present, late after
the SK App Settings time). People are matched once by Employee → Attendance Device ID, then mobile number, then name;
a person not found is picked once on the upload screen and remembered. "23:00:00 Auto Checkout" in the Optick file is a
missed out-punch: no OUT is made and HR sees it. Absent is never written from the file (a person on the thumb machine
or at a site would be marked absent by mistake); it is shown as "no check-in".

Selfie check-in (with location) is only the backup. Leave and expenses go through ERPNext Leave Application and
Expense Claim, approved on the phone by the person's manager; Accounts pays approved claims (Finance → Expenses).
"""

import re
from datetime import datetime, time, timedelta

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, get_datetime, get_first_day, get_last_day, getdate, now_datetime, nowdate

from sk_app import logins
from sk_app.logic import DAY_NAMES, parse_lines
from sk_app.store import _company, _todo, _users_with_function, attach
from sk_app.store import _company, _users_with_function


HR = "HR"

FIX_TAG = "[Attendance fix]"

AUTO_OUT = ("auto checkout", "auto check out", "auto-checkout")

def _is_hr(user: str) -> bool:
	return "System Manager" in frappe.get_roles(user) or bool({HR, "Management"} & set(logins.profile_functions(user)))

def _need_hr(user: str):
	if not _is_hr(user):
		frappe.throw(_("This screen is for HR"), frappe.PermissionError)

def _settings():
	s = frappe.get_cached_doc("SK App Settings")
	late = s.get("late_after") or "09:15:00"
	return {"late_after": _to_time(late) or time(9, 15), "half_day_below": flt(s.get("half_day_below")),
		"from_file": cint(s.get("attendance_from_file") if s.get("attendance_from_file") is not None else 1),
		"working": parse_lines((s.working_days or "").replace(",", "\n")) or DAY_NAMES[:6]}

def _to_time(v):
	if v in (None, "", "-"):
		return None
	if isinstance(v, time):
		return v
	if isinstance(v, datetime):
		return v.time()
	if isinstance(v, timedelta):
		return (datetime.min + v).time()
	if isinstance(v, (int, float)) and 0 <= v < 1:  # Excel time as a fraction of a day
		return (datetime.min + timedelta(seconds=round(v * 86400))).time()
	m = re.search(r"(\d{1,2}):(\d{2})(?::(\d{2}))?\s*([AaPp][Mm])?", str(v))
	if not m:
		return None
	h, mi, s = int(m.group(1)), int(m.group(2)), int(m.group(3) or 0)
	if m.group(4):
		h = h % 12 + (12 if m.group(4).lower() == "pm" else 0)
	return time(h, mi, s) if h < 24 else None

def _to_date(v):
	if v in (None, "", "-"):
		return None
	if isinstance(v, datetime):
		return v.date()
	try:
		s = str(v).strip()[:11].rstrip(" :")
		for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y", "%m/%d/%Y", "%d-%b-%Y", "%d-%b-%y", "%d/%b/%Y"):  # eSSL: 06-Nov-2026
			try:
				return datetime.strptime(s, fmt).date()
			except ValueError:
				continue
		return getdate(s)
	except Exception:
		return None

def _digits(v) -> str:
	d = re.sub(r"\D", "", str(v or ""))
	return d[-10:] if len(d) >= 10 else d

def _hm(t) -> str:
	return t.strftime("%H:%M") if t else ""

def _employees() -> list[dict]:
	fields = ["name", "employee_name", "attendance_device_id", "cell_number", "user_id", "company", "holiday_list", "gender", "date_of_joining"]
	if frappe.get_meta("Employee").has_field("thumb_id"):
		fields.append("thumb_id")
	rows = frappe.get_all("Employee", filters={"status": "Active"}, fields=fields, order_by="employee_name asc")
	mobiles = {u.name: u.mobile_no for u in frappe.get_all("User", filters={"name": ["in", [r.user_id for r in rows if r.user_id] or [""]]},
		fields=["name", "mobile_no"])}
	for r in rows:
		r["mobile"] = _digits(r.cell_number) or _digits(mobiles.get(r.user_id))
	return rows

def _off(e, day, cfg, holidays: dict) -> bool:
	if DAY_NAMES[day.weekday()] not in cfg["working"]:
		return True
	if e.name not in holidays:  # ERPNext v16: Holiday List Assignment (employee, else company); older: on the Employee
		hl = None
		try:
			from hrms.utils.holiday_list import get_holiday_list_for_employee

			hl = get_holiday_list_for_employee(e.name, raise_exception=False, as_on=day)
		except ImportError:
			pass
		holidays[e.name] = hl or e.holiday_list or frappe.get_cached_value("Company", e.company or _company(), "default_holiday_list")
	hl = holidays[e.name]
	if hl and hl not in holidays:
		holidays[hl] = set(getdate(d) for d in frappe.get_all("Holiday", filters={"parent": hl}, pluck="holiday_date"))
	return bool(hl and day in holidays[hl])

def _leaves(day_from, day_to) -> dict:
	"""{employee: [(from, to, type, half)]} approved leave in the period."""
	out = {}
	if not frappe.db.exists("DocType", "Leave Application"):
		return out
	for l in frappe.get_all("Leave Application", filters={"status": "Approved", "docstatus": 1, "from_date": ["<=", day_to],
			"to_date": [">=", day_from]}, fields=["employee", "from_date", "to_date", "leave_type", "half_day"]):
		out.setdefault(l.employee, []).append(l)
	return out

def _on_leave(leaves, emp, day):
	return next((l for l in leaves.get(emp, []) if getdate(l.from_date) <= day <= getdate(l.to_date)), None)

def _hr_people() -> list[str]:
	return _users_with_function(HR) or _users_with_function("Management")

def _my_employee(user: str):
	emp = frappe.db.get_value("Employee", {"user_id": user, "status": "Active"},
		["name", "employee_name", "company", "leave_approver", "expense_approver", "reports_to"], as_dict=True)
	if not emp:
		frappe.throw(_("Your login is not linked to an ERPNext Employee. Please ask HR."))
	return emp

def _approver(emp, user: str, field: str) -> str | None:
	"""Employee's leave / expense approver, else the manager they report to, else their app manager, else HR."""
	a = emp.get(field)
	if not a and emp.reports_to:
		a = frappe.db.get_value("Employee", emp.reports_to, "user_id")
	if not a:
		a = frappe.db.get_value("SK App User", {"user": user}, "manager")
	if not a or a == user:
		a = next((u for u in _hr_people() if u != user), a)
	return a

def _may_decide(user: str, approver: str | None) -> bool:
	return approver == user or _is_hr(user)

LEAVE_FIELDS = ["name", "employee", "employee_name", "leave_type", "from_date", "to_date", "total_leave_days", "half_day",
	"description", "status", "docstatus", "leave_approver", "posting_date"]

CLAIM_FIELDS = ["name", "employee", "employee_name", "posting_date", "total_claimed_amount", "approval_status", "status",
	"docstatus", "expense_approver", "remark"]

def _claim_fields() -> list[str]:
	extra = ["sk_paid_to", "sk_cabin", "sk_no_bill", "project"] if frappe.get_meta("Expense Claim").has_field("sk_paid_to") else []
	return CLAIM_FIELDS + extra

def _stage(c) -> str:
	"""Waiting CEO → Approved → Paid (or Rejected), as the person sees it."""
	if c.approval_status == "Rejected":
		return "Rejected"
	if c.approval_status != "Approved":
		return "Waiting CEO"
	return "Paid" if c.docstatus == 1 and c.status == "Paid" else "Approved"

def _ceos() -> list[str]:
	from sk_app.requisition import _ceos

	return _ceos()

def _is_ceo(user: str) -> bool:
	from sk_app.requisition import _is_ceo

	return _is_ceo(user)

def _close_todos(doctype: str, name: str):
	for t in frappe.get_all("ToDo", filters={"reference_type": doctype, "reference_name": name, "status": "Open"}, pluck="name"):
		frappe.db.set_value("ToDo", t, "status", "Closed")

def _date(value):
	if not value:
		return None
	v = str(value).strip()
	m = re.match(r"^(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2}|\d{4})$", v)
	if m:
		d, mth, y = m.groups()
		y = int(y) + (2000 if int(y) < 50 else 1900) if len(y) == 2 else int(y)
		return getdate(f"{y}-{int(mth):02d}-{int(d):02d}")
	return getdate(v)
