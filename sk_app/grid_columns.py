"""SK 23-Nov ("why this needs ..." - the item Description was hidden in the item tables): the Description column shows
for everyone in the item tables of quote, order, invoice, challan, PO, receipt, purchase bill and material request.
DocType-level Property Setters (in_list_view, columns) written on every migrate; a person's own saved grid layout that
leaves Description out is reset, so the standard layout (with Description) shows again."""

import json

import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

# the columns of each item table (desk grids have 10 units; Description next to the item)
LAYOUT = {
	"Quotation Item": {"item_code": 2, "description": 3, "qty": 1, "rate": 2, "amount": 2},
	"Sales Order Item": {"item_code": 2, "delivery_date": 1, "description": 3, "qty": 1, "rate": 1, "amount": 2},
	"Sales Invoice Item": {"item_code": 2, "description": 3, "qty": 1, "rate": 1, "amount": 2, "warehouse": 1},
	"Delivery Note Item": {"item_code": 2, "description": 3, "qty": 1, "uom": 1, "rate": 1, "amount": 1, "warehouse": 1},
	"Purchase Order Item": {"item_code": 2, "schedule_date": 1, "description": 2, "qty": 1, "uom": 1, "rate": 1, "amount": 1, "warehouse": 1},
	"Purchase Receipt Item": {"item_code": 2, "description": 2, "qty": 1, "rejected_qty": 1, "rate": 1, "amount": 1, "warehouse": 2},
	"Purchase Invoice Item": {"item_code": 2, "description": 3, "qty": 1, "rate": 2, "amount": 2},
	"Material Request Item": {"item_code": 2, "schedule_date": 1, "description": 3, "qty": 1, "warehouse": 2, "uom": 1},
}


def _set(doctype: str, field: str, prop: str, value, kind: str):
	current = frappe.db.get_value("Property Setter", {"doc_type": doctype, "field_name": field, "property": prop}, "value")
	if current is not None and str(current) == str(value):
		return
	make_property_setter(doctype, field, prop, value, kind, validate_fields_for_doctype=False)


def ensure() -> dict:
	done = {}
	for child, cols in LAYOUT.items():
		if not frappe.db.exists("DocType", child):
			continue
		meta = frappe.get_meta(child)
		for field, width in cols.items():
			if not meta.has_field(field):
				continue
			_set(child, field, "in_list_view", 1, "Check")
			_set(child, field, "columns", width, "Int")
		frappe.clear_cache(doctype=child)
		done[child] = len(cols)
	done["user_layouts_reset"] = reset_user_grids()
	return done


def reset_user_grids() -> int:
	"""Saved grid layouts (__UserSettings GridView) of these item tables that leave Description out are dropped."""
	n = 0
	for row in frappe.db.sql("select user, doctype, data from __UserSettings where data like %s", "%GridView%", as_dict=True):
		try:
			data = json.loads(row.data or "{}")
		except ValueError:
			continue
		grid = data.get("GridView") or {}
		drop = [c for c, fields in grid.items() if c in LAYOUT and not any((f or {}).get("fieldname") == "description" for f in (fields or []))]
		if not drop:
			continue
		for c in drop:
			grid.pop(c, None)
		data["GridView"] = grid
		frappe.db.sql("update __UserSettings set data=%s where user=%s and doctype=%s", (json.dumps(data), row.user, row.doctype))
		frappe.cache.hdel("_user_settings", f"{row.doctype}::{row.user}")
		n += len(drop)
	return n
