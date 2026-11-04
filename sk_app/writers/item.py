"""The one Item writer (linear flow map: Item was made in 6 places, each with its own fields and groups, so the same
thing ended up under different names). Service items (cabin, building, job, labour), the store's new item and a new
product size all come through here. Same inputs and outputs for the user (SK 4-Nov)."""

import frappe
from frappe import _

from sk_app.core.rules import report
from sk_app.writers.item_rules import problems, same_name


def _group(group: str | None, like: str | None = None) -> str | None:
	if group and frappe.db.exists("Item Group", group):
		return group
	if like:
		hit = frappe.db.get_value("Item Group", {"is_group": 0, "name": ["like", f"%{like}%"]})
		if hit:
			return hit
	return frappe.db.get_value("Item Group", {"is_group": 0}, "name")


def get_or_make(code: str, name: str, *, group: str | None = None, group_like: str | None = None, uom: str = "Nos",
		stock: bool = False, sales: bool = True, purchase: bool = True, description: str | None = None,
		hsn_like: str | None = None, disabled: bool = False, manufacturing: bool = False, extra: dict | None = None,
		warehouse: str | None = None) -> str:
	"""Returns the item code; makes the Item once, always the same way."""
	from sk_app.cabin_quote import hsn_fields

	if frappe.db.exists("Item", code):
		return code
	doc = frappe.new_doc("Item")
	doc.update({"item_code": code, "item_name": (name or code)[:140], "item_group": _group(group, group_like),
		"stock_uom": uom if frappe.db.exists("UOM", uom) else "Nos", "is_stock_item": int(stock), "is_sales_item": int(sales),
		"is_purchase_item": int(purchase), "include_item_in_manufacturing": int(manufacturing), "disabled": int(disabled),
		"description": description or name or code, **hsn_fields(hsn_like), **(extra or {})})
	if warehouse:
		doc.append("item_defaults", {"company": frappe.db.get_value("Warehouse", warehouse, "company"), "default_warehouse": warehouse})
	doc.flags.ignore_permissions = True
	doc.insert()
	return doc.name


def on_validate(doc, method=None):
	"""Every Item, from the app, ERPNext or SK Hub, on the New path of Store: name, group, unit, HSN, no same-name item."""
	from sk_app.core.switch import use_new

	if not use_new("Store", doc.owner or frappe.session.user):
		return
	others = frappe.get_all("Item", filters={"disabled": 0, "name": ["!=", doc.name or ""]}, fields=["item_code", "item_name"],
		limit_page_length=5000, as_list=True)
	hsn = doc.get("gst_hsn_code") if doc.meta.has_field("gst_hsn_code") else "n/a"
	report("Store", doc, problems(doc.item_code, doc.item_name, doc.item_group, doc.stock_uom, hsn,
		same_name(doc.item_name, [tuple(r) for r in others], doc.item_code)), title=_("Item data missing"))
