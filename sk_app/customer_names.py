"""Customers named by their real name, not CUS-00001 (SK 27-Oct-2026, improvement list points 14 / 19: "customer name
not show" in the Customer Ledger). 1,745 of the 1,821 customers came from Tally with CUS- numbers.

- New customers are named by Customer Name (Selling Settings).
- Link fields show the customer's name next to the number at once (Show Title in Link Fields).
- Each CUS- customer is renamed to its Customer Name (ERPNext's own Rename, which also updates the ledger entries), in a
  background job after deploy, once. Two customers with the same name get " - 2", " - 3".
"""

import frappe

DONE_KEY = "sk_customer_rename_done"


def ensure():
	if not frappe.db.exists("DocType", "Customer"):
		return
	frappe.db.set_single_value("Selling Settings", "cust_master_name", "Customer Name")
	from frappe.custom.doctype.property_setter.property_setter import make_property_setter

	if frappe.get_meta("Customer").title_field:
		make_property_setter("Customer", None, "show_title_field_in_link", 1, "Check", validate_fields_for_doctype=False)
	if not frappe.db.get_default(DONE_KEY) and frappe.db.exists("Customer", {"name": ["like", "CUS-%"]}):
		frappe.enqueue("sk_app.customer_names.rename_all", queue="long", timeout=6 * 3600, enqueue_after_commit=True)


def new_name(customer_name: str, taken) -> str:
	base = " ".join((customer_name or "").replace("/", "-").split())[:130]
	name, n = base, 1
	while name in taken:
		n += 1
		name = f"{base} - {n}"
	return name


def rename_all(limit: int = 0) -> int:
	"""Rename every CUS- customer to its Customer Name. Safe to run again: renamed ones are no longer CUS-."""
	rows = frappe.get_all("Customer", filters={"name": ["like", "CUS-%"]}, fields=["name", "customer_name"], order_by="creation asc",
		limit=limit or 0)
	taken = set(frappe.get_all("Customer", pluck="name"))
	done = 0
	for r in rows:
		if not (r.customer_name or "").strip():
			continue
		target = new_name(r.customer_name, taken - {r.name})
		if target == r.name:
			continue
		try:
			frappe.rename_doc("Customer", r.name, target, force=True, show_alert=False)
			taken.discard(r.name)
			taken.add(target)
			done += 1
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
			frappe.log_error(f"SK customer rename {r.name}")
	if not frappe.db.exists("Customer", {"name": ["like", "CUS-%"]}) or not limit:
		frappe.db.set_default(DONE_KEY, "1")
	return done
