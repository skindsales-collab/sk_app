"""SK 24-Nov (approved): the BOM is optional at every stage (quote, Sales Order, production).
- Design Status gets "Quote Ready" (and "Drawing Sent" where missing). Old values, "BOM & Quote Sent" too, stay as they are.
- A submitted cabin Sales Order leaves Design one information comment "BOM can be made": no ToDo, never late, not counted."""

import frappe
from frappe import _

ADD = ("Drawing Sent", "Quote Ready")


def with_options(options: str | None) -> str:
	"""The Select's options with ours added (Quote Ready before the old BOM & Quote Sent); nothing is removed or moved."""
	rows = (options or "").split("\n")
	for new in ADD:
		if new not in rows:
			at = next((rows.index(o) for o in ("BOM & Quote Sent", "Order Received", "On Hold") if o in rows), len(rows))
			rows.insert(at, new)
	return "\n".join(rows)


def ensure():
	for f in frappe.get_all("Custom Field", filters={"fieldname": "custom_design_status", "fieldtype": "Select"}, fields=["name", "dt", "options"]):
		new = with_options(f.options)
		if new != f.options:
			frappe.db.set_value("Custom Field", f.name, "options", new)
			frappe.clear_cache(doctype=f.dt)


def tell_design(doc, method=None):
	"""Sales Order on_submit: information only, and never a reason for the submit to fail."""
	try:
		from sk_app import segments

		group = doc.get("customer_group")
		if segments.main_of(group) != segments.CABIN:
			return
		items = {d.item_code for d in doc.items}
		if items and not frappe.db.exists("BOM", {"item": ["in", list(items)], "docstatus": 1}):
			doc.add_comment("Info", _("Design: a BOM can be made for {0} (optional)").format(doc.name))
	except Exception:
		frappe.log_error(f"SK App BOM reminder {doc.name}")
