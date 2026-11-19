"""The one Employee writer (linear flow map, Flow 6). New joiner: HR photographs the papers in the app (new_joiner,
screen unchanged); the stop-the-save checks and the warnings live in employee_rules, and on the New path of HR the
person's app login is made at once from the mobile (writers.app_user, the same as the nightly people rule)."""

import frappe
from frappe import _

from sk_app.core.rules import report
from sk_app.writers.employee_rules import joiner_warnings

MODULE = "HR"


def _use_new(user=None) -> bool:
	from sk_app.core.switch import use_new

	return use_new(MODULE, user if user is not None else frappe.session.user)


def _photos(name: str) -> int:
	return frappe.db.count("File", {"attached_to_doctype": "Employee", "attached_to_name": name}) if name else 0


def on_validate(doc, method=None):
	"""Every active Employee saved on the New path (app, ERPNext, SK Hub): mobile, papers, joining date (Warn only)."""
	if doc.status != "Active" or doc.is_new() or not _use_new(doc.owner):
		return
	report(MODULE, doc, joiner_warnings(doc.cell_number, _photos(doc.name), doc.date_of_joining), title=_("Employee data missing"))


def after_joiner(user: str, name: str) -> dict | None:
	"""After new_joiner on the New path: warnings for the new record and the app login made now, not at night."""
	from sk_app.core.people import ceo_users
	from sk_app.logins import make_login
	from sk_app.writers.app_user_rules import missing_logins

	if not _use_new(user):
		return None
	doc = frappe.get_doc("Employee", name)
	report(MODULE, doc, joiner_warnings(doc.cell_number, _photos(name), doc.date_of_joining), title=_("Employee data missing"))
	logins = set(frappe.get_all("SK App User", filters={"enabled": 1}, pluck="user"))
	people = missing_logins([{"name": doc.name, "employee_name": doc.employee_name, "user_id": doc.user_id,
		"cell_number": doc.cell_number, "status": doc.status}], [], logins, set())
	if not people or not people[0]["can_make"]:
		return None
	p = people[0]
	frappe.db.savepoint("sk_joiner_login")
	try:
		return make_login(next(iter(ceo_users()), user), p["mobile"], [], employee=p["name"], full_name=p["full_name"])
	except Exception:
		# the Employee stays saved; the nightly people rule tries again and lists it for HR
		frappe.db.rollback(save_point="sk_joiner_login")
		frappe.clear_messages()
		frappe.log_error(title=f"SK App joiner login {name}")
		return None


# ---------- Plan A (SK 9-Nov): moved here unchanged from hr.py ----------
from frappe import _
from frappe.utils import getdate
from sk_app.hr import _date, _need_hr
from sk_app.store import _company, attach
import frappe
import re


def ensure_joiner_fields():
	"""Aadhaar has no standard Employee field: one Custom Field (HR may photograph Aadhaar, SK 26-Oct)."""
	if not frappe.db.exists("DocType", "Employee") or frappe.get_meta("Employee").has_field("sk_aadhaar"):
		return
	from frappe.custom.doctype.custom_field.custom_field import create_custom_field

	create_custom_field("Employee", {"fieldname": "sk_aadhaar", "label": "Aadhaar No", "fieldtype": "Data", "length": 12,
		"insert_after": "pan_number" if frappe.get_meta("Employee").has_field("pan_number") else "date_of_birth"})

def ensure_thumb_field():
	"""Office thumb machine user ID on the Employee (SK 6-Nov, live thumb sync): kept apart from attendance_device_id,
	which holds the Optick IDs, because the two machines number people differently."""
	meta = frappe.get_meta("Employee") if frappe.db.exists("DocType", "Employee") else None
	if not meta or meta.has_field("thumb_id"):
		return
	from frappe.custom.doctype.custom_field.custom_field import create_custom_field

	create_custom_field("Employee", {"fieldname": "thumb_id", "label": "Thumb machine ID", "fieldtype": "Data", "length": 20,
		"insert_after": "attendance_device_id" if meta.has_field("attendance_device_id") else "sk_aadhaar", "in_standard_filter": 1})

def new_joiner(user: str, data: dict, photos: list | None = None) -> dict:
	from sk_app.writers import employee
	from sk_app.writers.employee_rules import joiner_errors

	_need_hr(user)
	errors = joiner_errors(data)
	if errors:
		frappe.throw(_(errors[0][1]))
	name = " ".join((data.get("name") or "").split())
	gender = data.get("gender")
	dob, joined = _date(data.get("dob")), _date(data.get("joining")) or getdate()
	if not dob:
		frappe.throw(_("Please give the date of birth"))
	aadhaar = re.sub(r"\D", "", data.get("aadhaar") or "")
	pan = (data.get("pan") or "").strip().upper()
	mobile = re.sub(r"\D", "", data.get("mobile") or "")[-10:]
	if mobile and frappe.db.exists("Employee", {"cell_number": mobile, "status": "Active"}):
		frappe.throw(_("An employee with mobile {0} already exists").format(mobile))
	first, _sp, last = name.partition(" ")
	doc = frappe.get_doc({"doctype": "Employee", "first_name": first, "last_name": last or None, "gender": gender,
		"date_of_birth": dob, "date_of_joining": joined, "company": _company(), "status": "Active",
		"cell_number": mobile or None, "personal_email": (data.get("email") or "").strip() or None,
		"current_address": (data.get("address") or "").strip() or None,
		"person_to_be_contacted": (data.get("emergency_name") or "").strip() or None,
		"emergency_phone_number": re.sub(r"\D", "", data.get("emergency_mobile") or "")[-10:] or None})
	if pan and doc.meta.has_field("pan_number"):
		doc.pan_number = pan
	if aadhaar and doc.meta.has_field("sk_aadhaar"):
		doc.sk_aadhaar = aadhaar
	if data.get("designation") and frappe.db.exists("Designation", data["designation"]):
		doc.designation = data["designation"]
	doc.insert()
	for p in photos or []:
		attach(p, "Employee", doc.name, user)
	login = employee.after_joiner(user, doc.name)  # rebuild Flow 6 (New path): warnings + app login at once
	return {"name": doc.name, "employee_name": doc.employee_name, "login": (login or {}).get("user")}
