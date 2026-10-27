"""Whose sale is it (SK 27-Oct-2026, improvement list point 5: "no data is received from ERP, it was expected that it is
already imported from Tally"). The year's sales came from Tally as Journal Entries with no salesperson, and nobody had
an ERPNext Sales Person, so every salesperson's graph stayed at 0.

- Every salesperson gets an ERPNext Sales Person linked to their Employee (made on deploy).
- The CEO or the sales manager says once per customer who sells to them (the customer's Sales Team in ERPNext), on
  the "Customer → salesperson" screen, biggest customers first.
- A salesperson's graph then counts the invoiced sale of their customers: Tally sales entries and Sales Invoices.
"""

import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate

from sk_app import dashboards

SALES_FUNCTIONS = ("Sales", "Marketing", "Machine Shifting")
PARENT = "Sales Team"


def ensure_sales_persons():
	"""A Sales Person for each salesperson's Employee (none existed on 27-Oct)."""
	if not frappe.db.exists("DocType", "Sales Person"):
		return
	from sk_app.logins import profile_functions

	parent = PARENT if frappe.db.exists("Sales Person", PARENT) else None
	for p in frappe.get_all("SK App User", filters={"enabled": 1}, fields=["user", "full_name"]):
		if not set(profile_functions(p.user)) & set(SALES_FUNCTIONS):
			continue
		emp = frappe.db.get_value("Employee", {"user_id": p.user, "status": "Active"}, ["name", "employee_name"], as_dict=True)
		if not emp or frappe.db.exists("Sales Person", {"employee": emp.name}):
			continue
		name = emp.employee_name or p.full_name or p.user
		if frappe.db.exists("Sales Person", name):
			frappe.db.set_value("Sales Person", name, "employee", emp.name)
			continue
		try:
			frappe.get_doc({"doctype": "Sales Person", "sales_person_name": name, "employee": emp.name, "enabled": 1,
				"is_group": 0, "parent_sales_person": parent}).insert(ignore_permissions=True)
		except Exception:
			frappe.log_error(f"SK App sales person {name}")


def _fy_start():
	today = getdate(nowdate())
	return getdate(f"{today.year if today.month >= 4 else today.year - 1}-04-01")


def customer_persons() -> dict:
	"""{customer name and customer_name: [Sales Person, ...]} from each customer's Sales Team."""
	rows = frappe.get_all("Sales Team", filters={"parenttype": "Customer"}, fields=["parent", "sales_person"], limit=0)
	by = {}
	for r in rows:
		by.setdefault(r.parent, []).append(r.sales_person)
	out = dict(by)
	if by:
		for c in frappe.get_all("Customer", filters={"name": ["in", list(by)]}, fields=["name", "customer_name"], limit=0):
			out[(c.customer_name or "").strip().lower()] = by[c.name]
	return out


def invoiced_for(persons: list[str], start, end) -> float:
	"""Invoiced sale (before GST) of these Sales Persons' customers: Sales Invoices credited by their Sales Team
	(or of a customer of theirs) and Tally sales entries of their customers."""
	if not persons:
		return 0.0
	owners = customer_persons()
	mine = lambda key: bool(set(owners.get(key) or []) & set(persons))  # noqa: E731
	total = 0.0
	for si in frappe.get_all("Sales Invoice", filters={"docstatus": 1, "is_return": 0, "posting_date": ["between", [start, end]]},
			fields=["name", "customer", "base_net_total"], limit=0):
		team = frappe.get_all("Sales Team", filters={"parenttype": "Sales Invoice", "parent": si.name}, fields=["sales_person", "allocated_percentage"])
		if team:
			total += sum(flt(si.base_net_total) * flt(t.allocated_percentage or 100) / 100 for t in team if t.sales_person in persons)
		elif mine(si.customer):
			total += flt(si.base_net_total)
	for t in dashboards._tally_sales(start, end):
		if mine((t.customer_name or "").strip().lower()):
			total += flt(t.amount)
	return total


def can_assign(user: str) -> bool:
	from sk_app.day_report import _team
	from sk_app.logins import profile_functions

	return user == "Administrator" or "Management" in profile_functions(user) or bool(_team(user))


def assign_list(user: str, q: str | None = None) -> dict:
	"""Customers with their sale this financial year (Tally + invoices), biggest first, and who sells to them."""
	if not can_assign(user):
		frappe.throw(_("Only the CEO or the sales manager says who sells to a customer"), frappe.PermissionError)
	start, end = _fy_start(), getdate(nowdate())
	sale = {}
	for t in dashboards._tally_sales(start, end):
		key = (t.customer_name or "").strip()
		sale[key.lower()] = (key, sale.get(key.lower(), (key, 0))[1] + flt(t.amount))
	for si in frappe.get_all("Sales Invoice", filters={"docstatus": 1, "is_return": 0, "posting_date": ["between", [start, end]]},
			fields=["customer_name", "base_net_total"], limit=0):
		key = (si.customer_name or "").strip()
		sale[key.lower()] = (key, sale.get(key.lower(), (key, 0))[1] + flt(si.base_net_total))
	names = {(c.customer_name or "").strip().lower(): c.name for c in frappe.get_all("Customer", filters={"disabled": 0},
		fields=["name", "customer_name"], limit=0)}
	owners = customer_persons()
	rows = []
	for low, (title, amount) in sale.items():
		if q and q.lower() not in low:
			continue
		cust = names.get(low)
		rows.append({"customer": cust, "title": title, "sale": round(amount), "persons": owners.get(low) or []})
	rows.sort(key=lambda r: -r["sale"])
	persons = frappe.get_all("Sales Person", filters={"enabled": 1, "is_group": 0}, pluck="name", order_by="name asc")
	return {"rows": rows, "persons": persons, "done": sum(1 for r in rows if r["persons"]), "total": len(rows)}


def assign(user: str, customer: str, sales_person: str | None) -> dict:
	if not can_assign(user):
		frappe.throw(_("Only the CEO or the sales manager says who sells to a customer"), frappe.PermissionError)
	if sales_person and not frappe.db.exists("Sales Person", sales_person):
		frappe.throw(_("Unknown salesperson"))
	doc = frappe.get_doc("Customer", customer)
	doc.set("sales_team", [])
	if sales_person:
		doc.append("sales_team", {"sales_person": sales_person, "allocated_percentage": 100})
	doc.flags.ignore_permissions = True
	doc.save()
	return {"customer": customer, "persons": [sales_person] if sales_person else []}
