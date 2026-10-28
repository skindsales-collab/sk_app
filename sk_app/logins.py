"""Logins by mobile number (SK, 26-Oct-2026): the CEO makes every login (point 20; HR did until then) from the person's mobile number and gives a PIN.

ERPNext still needs an email as the user ID, so people without one get a hidden ID <mobile>@staff.skind.local that
is never mailed. Email login keeps working as an option. The person sets their own PIN at the first login.
"""

import re
import secrets

import frappe
from frappe import _
from frappe.utils.password import check_password, update_password

from sk_app.functions import FUNCTIONS

HIDDEN_DOMAIN = "staff.skind.local"
LOGIN_ROLES = {"HR Manager", "HR User", "System Manager"}
# functions that give full admin rights: only an admin may hand them out, never HR alone
ADMIN_FUNCTIONS = {f for f, spec in FUNCTIONS.items() if "System Manager" in spec["erpnext_roles"]}


def clean_mobile(mobile) -> str:
	"""10-digit Indian mobile from what people type: +91 98xxx xxxxx, 098xxxxxxxx, 98xxx-xxxxx."""
	digits = re.sub(r"\D", "", str(mobile or ""))
	if len(digits) == 12 and digits.startswith("91"):
		digits = digits[2:]
	elif len(digits) == 11 and digits.startswith("0"):
		digits = digits[1:]
	if not re.fullmatch(r"[6-9]\d{9}", digits):
		frappe.throw(_("Please give a 10-digit mobile number"))
	return digits


def new_pin() -> str:
	return f"{secrets.randbelow(10**6):06d}"


def check_pin(pin) -> str:
	pin = str(pin or "").strip()
	if not re.fullmatch(r"\d{4,8}", pin):
		frappe.throw(_("PIN must be 4 to 8 digits"))
	return pin


def _can_manage(user: str) -> bool:
	"""Point 20 (SK 26-Oct): only the CEO (Sunil = SK) makes logins and resets PIN / face / finger, no longer HR."""
	return user == "Administrator" or "Management" in profile_functions(user)


def _check_manager(user: str):
	if not _can_manage(user):
		frappe.throw(_("Only the CEO can make logins or reset a PIN"), frappe.PermissionError)


# every role the app hands out through a function, plus the roles that bring admin screens (Logins, all leads)
FUNCTION_ROLES = {r for spec in FUNCTIONS.values() for r in spec["erpnext_roles"]} | LOGIN_ROLES | {"Sales Manager"}


def old_function_roles(user: str, keep: set) -> set:
	"""Roles from functions the person does not have any more (e.g. HR Manager left from before the app)."""
	have = set(frappe.get_all("Has Role", filters={"parent": user, "parenttype": "User"}, pluck="role"))
	return (have & FUNCTION_ROLES) - set(keep)


def profile_functions(user: str) -> list[str]:
	from sk_app.functions import function_list

	profile = frappe.db.get_value("SK App User", {"user": user}, ["name", "home"], as_dict=True)
	if not profile:
		return []
	rows = frappe.get_all("SK App User Function", filters={"parent": profile.name, "parenttype": "SK App User"},
		fields=["function"], order_by="idx asc")
	return function_list({"home": profile.home, "functions": rows})


def people(user: str) -> list[dict]:
	"""Every active employee and every app user, with their login state, for the HR Logins screen."""
	_check_manager(user)
	emps = frappe.get_all("Employee", filters={"status": "Active"},
		fields=["name", "employee_name", "designation", "department", "user_id", "cell_number"], order_by="employee_name asc")
	app_users = {r.user: r for r in frappe.get_all("SK App User", fields=["name", "user", "full_name", "enabled", "home",
		"employee", "manager", "workstation", "must_set_pin", "company"])}
	users = {u.name: u for u in frappe.get_all("User", filters={"name": ["in", list({e.user_id for e in emps if e.user_id} | set(app_users))]},
		fields=["name", "enabled", "mobile_no", "full_name", "last_login"])} if (emps or app_users) else {}
	out, seen = [], set()
	for e in emps:
		u = users.get(e.user_id) if e.user_id else None
		a = app_users.get(e.user_id) if e.user_id else None
		seen.add(e.user_id)
		out.append(_row(e.employee_name, e.designation, e.name, u, a, e.cell_number))
	for name, a in app_users.items():
		if name not in seen:
			out.append(_row(a.full_name or name, None, a.employee, users.get(name), a, None))
	# people without a login first: that is HR's to-do
	out.sort(key=lambda r: (r["state"] == "active", r["name"].lower()))
	return out


def _row(name, designation, employee, u, a, cell):
	if not u:
		state = "none"
	elif not u.enabled or (a and not a.enabled):
		state = "closed"
	else:
		state = "active"
	return {"name": name, "designation": designation, "employee": employee, "user": u.name if u else None,
		"mobile": (u.mobile_no if u else None) or cell, "state": state, "home": a.home if a else None,
		"functions": profile_functions(u.name) if (u and a) else [], "manager": a.manager if a else None,
		"workstation": a.workstation if a else None, "must_set_pin": bool(a and a.must_set_pin), "company": a.get("company") if a else None,
		"last_login": str(u.last_login) if u and u.last_login else None,
		"hidden_id": bool(u and u.name.endswith("@" + HIDDEN_DOMAIN)),
		# SK 26-Oct: the person's ERPNext roles on the Logins screen, so a left-over admin / HR role is easy to see
		"roles": sorted(set(frappe.get_all("Has Role", filters={"parent": u.name, "parenttype": "User"}, pluck="role"))
			& FUNCTION_ROLES) if u else []}


def make_login(by: str, mobile, functions, employee=None, full_name=None, manager=None, language="English",
		workstation=None, company=None) -> dict:
	"""Create (or update) the person's login from their mobile number and give a first PIN."""
	_check_manager(by)
	mobile = clean_mobile(mobile)
	functions = [f for f in (functions or []) if f in FUNCTIONS]
	if not functions:
		frappe.throw(_("Please pick at least one function"))
	if ADMIN_FUNCTIONS & set(functions) and "System Manager" not in frappe.get_roles(by):
		frappe.throw(_("Only the ERPNext admin can give the {0} function").format(", ".join(ADMIN_FUNCTIONS & set(functions))),
			frappe.PermissionError)
	if "Subcontractor" in functions and not workstation:
		frappe.throw(_("Please pick the subcontractor's workstation"))
	if language not in ("English", "Marathi"):
		language = "English"

	emp = frappe.db.get_value("Employee", employee, ["name", "employee_name", "user_id", "first_name"], as_dict=True) if employee else None
	if employee and not emp:
		frappe.throw(_("Employee {0} not found").format(employee))
	full_name = (full_name or (emp and emp.employee_name) or "").strip()
	if not full_name:
		frappe.throw(_("Please give the person's name"))

	# a person without an Employee is found again by the hidden ID from his mobile, so editing works too
	user_id = emp.user_id if emp and emp.user_id else f"{mobile}@{HIDDEN_DOMAIN}"
	other = frappe.db.get_value("User", {"mobile_no": mobile, "name": ["!=", user_id]}, "name")
	if not other and not emp:
		# same mobile, other name: a second person, not an edit of the first
		have = frappe.db.get_value("User", user_id, "full_name")
		if have and have.strip().lower() != full_name.lower():
			other = have
	if other:
		frappe.throw(_("Mobile {0} is already the login of {1}").format(mobile, other))

	roles = {r for f in functions for r in FUNCTIONS[f]["erpnext_roles"] if frappe.db.exists("Role", r)}
	was_new = not frappe.db.exists("User", user_id)
	if not was_new:
		user = frappe.get_doc("User", user_id)
		user.enabled = 1
	else:
		first, _sp, last = full_name.partition(" ")
		user = frappe.get_doc({"doctype": "User", "email": user_id, "first_name": first, "last_name": last or None,
			"send_welcome_email": 0, "user_type": "System User"})
	user.mobile_no = mobile
	have = {r.role for r in user.get("roles")}
	for r in sorted(roles):
		if r not in have:
			user.append("roles", {"role": r})
	user.flags.no_welcome_mail = True
	if was_new:
		user.insert(ignore_permissions=True)
	else:
		user.save(ignore_permissions=True)
	# an admin keeps the password they already have (the person making logins is often the admin himself);
	# everyone else gets a first PIN, which also becomes their ERPNext password
	# an edit of a working login (functions, manager ...) keeps the person's own PIN; HR uses Reset PIN for a new one
	editing = bool(frappe.db.get_value("SK App User", {"user": user.name, "enabled": 1}))
	# the functions decide the ERPNext roles (SK 26-Oct): roles of functions the person no longer has are taken off
	extra = old_function_roles(user.name, roles) if user.name != by and "Management" not in functions else set()
	if "System Manager" in extra and "System Manager" not in frappe.get_roles(by):
		extra.discard("System Manager")  # only the admin takes admin rights off
	if extra:
		user.remove_roles(*sorted(extra))
	keep = not was_new and (editing or "System Manager" in {r.role for r in user.get("roles")})
	pin = None if keep else new_pin()
	if pin:
		update_password(user.name, pin)

	if emp:
		updates = {"cell_number": mobile}
		if not emp.user_id:
			updates["user_id"] = user.name
		frappe.db.set_value("Employee", emp.name, updates)
		# ERPNext keeps the Employee role only on a user linked to an Employee, so it is added after the link;
		# subcontractors stay without it (no ERPNext desk)
		if functions != ["Subcontractor"] and frappe.db.get_value("Employee", {"user_id": user.name}):
			user.reload()
			user.add_roles("Employee")

	name = frappe.db.get_value("SK App User", {"user": user.name})
	app = frappe.get_doc("SK App User", name) if name else frappe.get_doc({"doctype": "SK App User", "user": user.name})
	app.update({"home": functions[0], "enabled": 1, "language": language, "manager": manager or app.get("manager"),
		"workstation": workstation or None, "must_set_pin": 0 if keep else 1, "employee": emp.name if emp else app.get("employee")})
	app.set("functions", [{"function": f} for f in functions[1:]])
	if company and frappe.db.exists("Company", company):
		app.company = company  # SK 28-Oct (Rev 1 point 5): SK Ind Tech or SK Enterprises
	if name:
		app.save(ignore_permissions=True)
	else:
		app.insert(ignore_permissions=True)
	return {"user": user.name, "mobile": mobile, "pin": pin, "full_name": full_name, "functions": functions}


def bulk_make(by: str, text: str) -> list[dict]:
	"""Many logins in one go from a pasted list, one person per line:
	Name | Mobile | Function + Function | Employee ID | Workstation | Reports to (mobile) | Language
	Only name, mobile and function are needed. Each line is made on its own, so one bad line does not stop the
	others; "Reports to" is set after all lines are made, so a manager can be lower in the list."""
	_check_manager(by)
	names = {f.lower(): f for f in FUNCTIONS}
	out, managers = [], []
	for n, line in enumerate((text or "").splitlines(), 1):
		if not line.strip() or line.strip().startswith("#"):
			continue
		cols = [c.strip() for c in line.split("|")] + [""] * 7
		name, mobile, fns, employee, workstation, reports_to, language = cols[:7]
		row = {"line": n, "full_name": name, "mobile": mobile}
		try:
			functions = [names.get(f.strip().lower(), f.strip()) for f in fns.split("+") if f.strip()]
			unknown = [f for f in functions if f not in FUNCTIONS]
			if unknown:
				frappe.throw(_("Unknown function: {0}").format(", ".join(unknown)))
			frappe.db.savepoint("sk_bulk")
			row.update(make_login(by, mobile, functions, employee=employee or None, full_name=name, language=language or "English",
				workstation=workstation or None))
			if reports_to:
				managers.append((row["user"], reports_to))
		except Exception as e:
			frappe.db.rollback(save_point="sk_bulk")
			frappe.clear_messages()
			row["error"] = str(e) or e.__class__.__name__
		out.append(row)
	for user, reports_to in managers:
		mgr = frappe.db.get_value("User", {"mobile_no": clean_mobile(reports_to)}, "name") if re.search(r"\d{10}", reports_to) \
			else frappe.db.get_value("User", {"full_name": reports_to}, "name")
		row = next(r for r in out if r.get("user") == user)
		if mgr:
			frappe.db.set_value("SK App User", {"user": user}, "manager", mgr)
			row["manager"] = mgr
		else:
			row["error"] = _("Login made, but manager {0} not found").format(reports_to)
	return out


def reset_pin(by: str, user: str) -> dict:
	_check_manager(by)
	if not frappe.db.exists("User", user) or user in ("Administrator", "Guest"):
		frappe.throw(_("Login not found"))
	if "System Manager" in frappe.get_roles(user) and "System Manager" not in frappe.get_roles(by):
		frappe.throw(_("Only the ERPNext admin can reset an admin's PIN"), frappe.PermissionError)
	pin = new_pin()
	update_password(user, pin)
	frappe.db.set_value("SK App User", {"user": user}, "must_set_pin", 1)
	return {"user": user, "pin": pin, "mobile": frappe.db.get_value("User", user, "mobile_no")}


# ---------- Forgot PIN / password (SK 28-Oct): the person asks, the CEO approves, a new temporary PIN is given ----------
# The PIN is also the person's ERPNext password, so this covers "forgot password" for ERPNext too. The request never says
# whether a mobile number has a login. The CEO gives the new PIN by WhatsApp / call; at the next login the person must
# set their own PIN (must_set_pin), so the CEO never knows the PIN in use.
PIN_TAG = "[PIN reset]"


def _ceos() -> list[str]:
	from sk_app.requisition import _ceos

	return _ceos()


def ask_new_pin(user: str, source: str = "login page") -> dict:
	"""Request from a known login (login page by mobile, or the lock screen). One open request per person."""
	if not user or user in ("Administrator", "Guest") or not frappe.db.get_value("User", user, "enabled"):
		return {"sent": True}
	if frappe.db.exists("ToDo", {"reference_type": "User", "reference_name": user, "status": "Open", "description": ["like", f"{PIN_TAG}%"]}):
		return {"sent": True}
	ceos = [c for c in _ceos() if c != user]
	if not ceos:
		return {"sent": True}
	mobile = frappe.db.get_value("User", user, "mobile_no") or ""
	frappe.get_doc({"doctype": "ToDo", "allocated_to": ceos[0], "assigned_by": "Administrator", "status": "Open", "priority": "High",
		"reference_type": "User", "reference_name": user, "date": frappe.utils.nowdate(),
		"description": f"{PIN_TAG} {frappe.utils.get_fullname(user)} ({mobile}) forgot the PIN. Asked from the {source}."}).insert(ignore_permissions=True)
	return {"sent": True}


def forgot_pin(mobile) -> dict:
	"""Guest: from the login page. Same answer whether or not the number has a login."""
	from sk_app.otp import _user_for

	user = _user_for(clean_mobile(mobile))
	return ask_new_pin(user, "login page") if user else {"sent": True}


def pin_requests(by: str) -> list[dict]:
	_check_manager(by)
	rows = frappe.get_all("ToDo", filters={"status": "Open", "reference_type": "User", "description": ["like", f"{PIN_TAG}%"]},
		fields=["name", "reference_name", "description", "creation"], order_by="creation asc", limit=0)
	out = []
	for r in rows:
		out.append({"todo": r.name, "user": r.reference_name, "name": frappe.utils.get_fullname(r.reference_name),
			"mobile": frappe.db.get_value("User", r.reference_name, "mobile_no") or "",
			"function": frappe.db.get_value("SK App User", {"user": r.reference_name}, "home") or "",
			"asked": str(r.creation)[:16], "where": "lock screen" if "lock screen" in (r.description or "") else "login page"})
	return out


def pin_request_count(user: str) -> int:
	if not _can_manage(user):
		return 0
	return frappe.db.count("ToDo", {"status": "Open", "reference_type": "User", "description": ["like", f"{PIN_TAG}%"]})


def pin_request_done(by: str, todo: str, approve) -> dict:
	"""CEO: approve gives a new temporary PIN (shown once, to send by WhatsApp / call); reject just closes the request."""
	_check_manager(by)
	t = frappe.get_doc("ToDo", todo)
	if t.reference_type != "User" or not (t.description or "").startswith(PIN_TAG):
		frappe.throw(_("Not a PIN request"))
	out = {"user": t.reference_name}
	if str(approve) in ("1", "true", "True"):
		out = reset_pin(by, t.reference_name)
	t.db_set("status", "Closed")
	t.add_comment("Comment", f"{'New PIN given' if str(approve) in ('1', 'true', 'True') else 'Not approved'} by {frappe.utils.get_fullname(by)}")
	return out


def close_login(by: str, user: str) -> dict:
	"""Person left: login off. All their past work stays in ERPNext under their name."""
	_check_manager(by)
	if user in ("Administrator", "Guest", by):
		frappe.throw(_("This login cannot be closed here"))
	if "System Manager" in frappe.get_roles(user) and "System Manager" not in frappe.get_roles(by):
		frappe.throw(_("Only the ERPNext admin can close an admin's login"), frappe.PermissionError)
	frappe.db.set_value("User", user, "enabled", 0)
	frappe.db.set_value("SK App User", {"user": user}, "enabled", 0)
	return {"user": user, "closed": True}


def set_own_pin(user: str, old_pin, new_pin_value) -> dict:
	"""The person changes the PIN HR gave them (first login) or any time later."""
	new_pin_value = check_pin(new_pin_value)
	try:
		check_password(user, str(old_pin or ""))
	except frappe.AuthenticationError:
		# not an AuthenticationError: ERPNext would log the person out on that, and the next Save then fails
		frappe.throw(_("The old PIN is wrong. Please type the PIN HR gave you."))
	update_password(user, new_pin_value)
	frappe.db.set_value("SK App User", {"user": user}, "must_set_pin", 0)
	return {"ok": True}


def setup_site():
	"""Run after every migrate: login with mobile number on, and the small subcontractor role."""
	if not frappe.db.get_single_value("System Settings", "allow_login_using_mobile_number"):
		frappe.db.set_single_value("System Settings", "allow_login_using_mobile_number", 1)
	if not frappe.db.exists("Role", "SK Subcontractor"):
		frappe.get_doc({"doctype": "Role", "role_name": "SK Subcontractor", "desk_access": 0}).insert(ignore_permissions=True)
	# a subcontractor asks for material by item: ERPNext checks he may read the Item (only read, no prices screen)
	if not frappe.db.exists("Custom DocPerm", {"parent": "Item", "role": "SK Subcontractor"}):
		from frappe.permissions import add_permission

		add_permission("Item", "SK Subcontractor", 0)


def set_company_default(doc, method=None):
	"""SK App User on_update (SK 28-Oct, Rev 1 point 5): the person's entries go to their company. ERPNext uses the
	user default "Company" for new documents; the app does the same (store._company)."""
	if doc.get("company") and doc.user:
		frappe.defaults.set_user_default("Company", doc.company, doc.user)
	elif doc.user and doc.has_value_changed("company"):
		frappe.defaults.clear_user_default("Company", doc.user)
