"""The one place app logins come from (SK 6-Nov people rule). Nightly, and after migrate:
- every active Employee with a mobile and no enabled login gets one (functions from designation / department, PIN sent
  to the manager's screen as for a login made by hand);
- every service supplier (submitted service PO or labour bill this year) without a login gets one too while SK App
  Settings "Auto-create subcontractor logins" is on (on by default: SK 6-Nov 11 PM "Santosh is still not there");
- people who cannot be made (no mobile) are counted on the scorecard "People without app login" (target 0) and listed
  in one ToDo to HR."""

import frappe
from frappe import _
from frappe.utils import nowdate

from sk_app.writers.app_user_rules import EMPLOYEE, SUPPLIER, missing_logins

SETTING = "auto_supplier_logins"


def ensure_setup():
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	if frappe.db.exists("DocType", "SK App Settings") and not frappe.get_meta("SK App Settings").has_field(SETTING):
		create_custom_fields({"SK App Settings": [{"fieldname": SETTING, "label": "Auto-create subcontractor logins (service suppliers)",
			"fieldtype": "Check", "default": "1", "insert_after": "sub_bill_checker"}]}, update=True)
		frappe.db.set_single_value("SK App Settings", SETTING, 1)  # SK 6-Nov 11 PM: "Santosh is still not there" → on from the start


def service_suppliers(since: str) -> list[dict]:
	"""Suppliers with a submitted service PO (non-stock items) or labour bill this year."""
	since = since or _since()
	names = set(frappe.db.sql_list("""select distinct po.supplier from `tabPurchase Order` po join `tabPurchase Order Item` i on i.parent = po.name
		join `tabItem` it on it.name = i.item_code where po.docstatus = 1 and po.transaction_date >= %s and it.is_stock_item = 0""", since))
	names |= set(frappe.db.sql_list("""select distinct pi.supplier from `tabPurchase Invoice` pi join `tabPurchase Invoice Item` i on i.parent = pi.name
		join `tabItem` it on it.name = i.item_code where pi.docstatus = 1 and pi.posting_date >= %s and it.is_stock_item = 0""", since))
	if not names:
		return []
	out = []
	for s in frappe.get_all("Supplier", filters={"name": ["in", list(names)], "disabled": 0}, fields=["name", "supplier_name", "mobile_no", "supplier_primary_contact"]):
		mobile = s.mobile_no or (s.supplier_primary_contact and frappe.db.get_value("Contact", s.supplier_primary_contact, "mobile_no"))
		out.append({"name": s.name, "supplier_name": s.supplier_name, "mobile": mobile})
	return out


def _supplier_logins() -> set:
	"""Suppliers already in the app: a Workstation's sk_supplier whose login exists, or a login whose name is the supplier's."""
	linked = set()
	if frappe.get_meta("Workstation").has_field("sk_supplier"):
		for w in frappe.get_all("Workstation", filters={"sk_supplier": ["is", "set"]}, fields=["name", "sk_supplier"]):
			if frappe.db.exists("SK App User", {"workstation": w.name, "enabled": 1}):
				linked.add(w.sk_supplier)
	names = {frappe.utils.get_fullname(u).strip().lower() for u in frappe.get_all("SK App User", filters={"enabled": 1}, pluck="user")}
	for s in frappe.get_all("Supplier", fields=["name", "supplier_name"]):
		if (s.supplier_name or "").strip().lower() in names:
			linked.add(s.name)
	return linked


def _since() -> str:
	from frappe.utils import getdate

	from sk_app.core.dates import fy_start

	return str(fy_start(getdate(nowdate())))


def missing() -> list[dict]:
	employees = frappe.get_all("Employee", filters={"status": "Active"}, fields=["name", "employee_name", "user_id", "cell_number", "status"])
	logins = set(frappe.get_all("SK App User", filters={"enabled": 1}, pluck="user"))
	return missing_logins(employees, service_suppliers(_since()), logins, _supplier_logins())


def _make_employee(person: dict, by: str) -> dict | None:
	from sk_app.logins import make_login

	try:
		return make_login(by, person["mobile"], [], employee=person["name"], full_name=person["full_name"])
	except Exception as e:
		frappe.db.rollback()
		frappe.log_error(title=f"SK App auto login {person['name']}")
		person["why"] = str(e)[:140]
		return None


def _make_supplier(person: dict, by: str) -> dict | None:
	from sk_app.logins import make_login

	has_field = frappe.get_meta("Workstation").has_field("sk_supplier")
	ws = frappe.db.get_value("Workstation", {"sk_supplier": person["name"]}, "name") if has_field else None
	if not ws:  # a workstation already named after the subcontractor (e.g. "Machine Shifting - Technomech") is his
		words = [w for w in person["full_name"].replace(".", " ").split() if len(w) > 3 and w.lower() not in ("solutions", "enterprises", "industries", "services")]
		for w in words:
			ws = frappe.db.get_value("Workstation", {"name": ["like", f"%{w}%"]}, "name")
			if ws:
				if has_field:
					frappe.db.set_value("Workstation", ws, "sk_supplier", person["name"])
				break
	if not ws:
		ws = frappe.get_doc({"doctype": "Workstation", "workstation_name": f"{person['full_name']} (service)"[:140], "sk_supplier": person["name"]}) \
			.insert(ignore_permissions=True).name
	try:
		return make_login(by, person["mobile"], ["Subcontractor"], full_name=person["full_name"], workstation=ws)
	except Exception as e:
		frappe.db.rollback()
		frappe.log_error(title=f"SK App auto login {person['name']}")
		person["why"] = str(e)[:140]
		return None


def nightly() -> dict:
	"""Make what can be made, list the rest. Runs as the system in the CEO's name (logins are the CEO's to make)."""
	from sk_app.core.people import ceo_users, users_with_function

	people = missing()
	by = next(iter(ceo_users()), "Administrator")
	auto_suppliers = bool(frappe.db.get_single_value("SK App Settings", SETTING)) if frappe.get_meta("SK App Settings").has_field(SETTING) else False
	made, left = [], []
	current = frappe.session.user
	frappe.set_user("Administrator")
	try:
		for p in people:
			ok = None
			if p["can_make"] and p["kind"] == EMPLOYEE:
				ok = _make_employee(p, by)
			elif p["can_make"] and p["kind"] == SUPPLIER and auto_suppliers:
				ok = _make_supplier(p, by)
			if ok:
				made.append({**p, "user": ok["user"], "pin": ok.get("pin")})
				frappe.db.commit()
			else:
				left.append(p)
	finally:
		frappe.set_user(current)
	if made or left:
		lines = [_("Login made for {0} ({1}), first PIN {2}").format(m["full_name"], m["kind"], m["pin"] or "kept") for m in made]
		lines += [_("No login for {0} ({1}): {2}").format(p["full_name"], p["kind"], p.get("why") or
			("no mobile number in ERPNext" if not p["can_make"] else "subcontractor logins are made when SK says")) for p in left]
		text = _("People in the app: {0} made, {1} still without login").format(len(made), len(left)) + "<br>" + "<br>".join(lines[:40])
		for u in list(dict.fromkeys(users_with_function("HR") + ceo_users())):
			if not frappe.db.exists("ToDo", {"allocated_to": u, "status": "Open", "date": nowdate(), "description": ["like", "People in the app:%"]}):
				frappe.get_doc({"doctype": "ToDo", "allocated_to": u, "description": text, "priority": "Medium", "date": nowdate(),
					"reference_type": "SK App User"}).insert(ignore_permissions=True)
	return {"made": len(made), "without_login": len(left), "people": left}


def count_missing() -> int:
	return len(missing())
