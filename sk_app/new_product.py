"""New product and vendor from one spoken / typed line (SK 27-Oct-2026: "new product (Cabin 10 x 30 x 8.8) ... subcontracted
to one vendor (AI Portable Cabin) ... add in ERP as per ERP sr number; this command should be by Shraddha in the app,
then connected in ERP through AI").

read(line) understands the line: cabin type, size, height and the vendor (matched to the ERPNext supplier list). The
person checks it, then make() adds it the ERPNext way:
- a cabin size of an existing product (Prod-0009 Portable Office Cabin ...) becomes its size variant, named like the
  others: "Prod-0009-30ft x 10ft x 8.8ft" (length first);
- anything else becomes the next product number, Prod-00NN;
- the vendor is the existing supplier, or a new one; the product is marked as bought from (subcontracted to) that vendor.
"""

import re

import frappe
from frappe import _
from frappe.utils import flt

from sk_app.store import _todo, _users_with_function, need

WHO = ("Accounts", "Purchase", "Management")
# words in the line -> the product template (ERPNext numbers); the first match wins, office is the default cabin
TYPES = [
	("toilet", "Prod-0016"), ("security", "Prod-0013"), ("frp security", "Prod-0012"), ("storage", "Prod-0014"), ("store", "Prod-0014"),
	("farm", "Prod-0004"), ("electric", "Prod-0003"), ("kiosk", "Prod-0017"), ("cafe", "Prod-0017"), ("container", "Prod-0018"),
	("bunk bed office", "Prod-0021"), ("bunk", "Prod-0020"), ("labour camp", "Prod-0022"), ("labor camp", "Prod-0022"),
	("office", "Prod-0009"), ("cabin", "Prod-0009"),
]


def _num(x: str) -> str:
	return f"{flt(x):g}"


def read(user: str, line: str) -> dict:
	"""Understand the line; nothing is saved."""
	need(user, *WHO)
	text = (line or "").strip()
	low = text.lower()
	m = re.search(r"(\d+(?:\.\d+)?)\s*(?:ft|')?\s*[x×*]\s*(\d+(?:\.\d+)?)\s*(?:ft|')?(?:\s*[x×*]\s*(\d+(?:\.\d+)?))?", low)
	length = width = height = None
	if m:
		a, b = flt(m.group(1)), flt(m.group(2))
		length, width = max(a, b), min(a, b)  # ERPNext names put the length first: 30ft x 10ft
		height = flt(m.group(3)) if m.group(3) else 8.6
	template = None
	for word, code in sorted(TYPES, key=lambda t: -len(t[0])):
		if word in low and frappe.db.exists("Item", code):
			template = code
			break
	vendor_text = None
	v = re.search(r"(?:vendor|supplier|sub-?contr\w*(?:\s+to)?|from|by)\s*[:\-]?\s*(.+)$", text, re.I)
	if v:
		vendor_text = re.sub(r"^(to|the|vendor|supplier)\s+", "", v.group(1).strip(" .,()"), flags=re.I).strip(" .,()")
	vendor = match_supplier(vendor_text) if vendor_text else None
	out = {"line": text, "template": template, "length": length, "width": width, "height": height,
		"vendor_text": vendor_text, "vendor": vendor, "subcontracted": bool(re.search(r"sub-?contr", low)) or bool(vendor_text),
		"templates": templates()}
	out["preview"] = preview(template, length, width, height)
	return out


def templates() -> list[dict]:
	return frappe.get_all("Item", filters={"item_code": ["like", "Prod-%"], "variant_of": ["is", "not set"], "disabled": 0},
		fields=["item_code", "item_name", "has_variants"], order_by="item_code asc", limit=0)


def match_supplier(name: str | None) -> str | None:
	"""'AI Poratable cabin' -> 'Ai Portable Cabin' (spelling and case forgiven)."""
	if not name:
		return None
	norm = lambda s: re.sub(r"[^a-z0-9]", "", (s or "").lower())  # noqa: E731
	want = norm(name)
	rows = frappe.get_all("Supplier", fields=["name", "supplier_name"], limit=0)
	for r in rows:
		if norm(r.supplier_name) == want:
			return r.name
	from difflib import SequenceMatcher

	best = max(rows, key=lambda r: SequenceMatcher(None, norm(r.supplier_name), want).ratio(), default=None)
	if best and SequenceMatcher(None, norm(best.supplier_name), want).ratio() >= 0.8:
		return best.name
	return None


def _size(length, width, height) -> str:
	return f"{_num(length)}ft x {_num(width)}ft x {_num(height)}ft"


def preview(template, length, width, height, name=None) -> dict:
	if template and length and width and frappe.db.get_value("Item", template, "has_variants"):
		code = f"{template}-{_size(length, width, height)}"
		return {"item_code": code, "item_name": f"{frappe.db.get_value('Item', template, 'item_name')}-{_size(length, width, height)}",
			"exists": bool(frappe.db.exists("Item", code)), "kind": "size"}
	code = next_number()
	label = name or (f"{frappe.db.get_value('Item', template, 'item_name')} " if template else "") + (_size(length, width, height) if length else "")
	return {"item_code": code, "item_name": label.strip() or code, "exists": False, "kind": "new"}


def next_number() -> str:
	"""ERP serial number: Prod-0022 is the last product, so the next one is Prod-0023."""
	nums = [int(m.group(1)) for c in frappe.get_all("Item", filters={"item_code": ["like", "Prod-%"]}, pluck="item_code")
		if (m := re.match(r"Prod-(\d+)$", c))]
	return f"Prod-{(max(nums) + 1 if nums else 1):04d}"


def make(user: str, template=None, length=None, width=None, height=None, vendor=None, new_vendor=None, item_name=None,
		subcontracted=1, group=None) -> dict:
	"""Add the product (and the vendor if new) in ERPNext."""
	need(user, *WHO)
	length, width, height = flt(length), flt(width), flt(height) or 8.6
	if vendor and not frappe.db.exists("Supplier", vendor):
		vendor = None
	if not vendor and (new_vendor or "").strip():
		vendor = match_supplier(new_vendor) or _new_supplier(new_vendor.strip())
	p = preview(template, length, width, height, item_name)
	if p["kind"] == "size":
		if not (length and width):
			frappe.throw(_("Please give the size, e.g. 30 x 10 x 8.6"))
		code = p["item_code"] if p["exists"] else _variant(template, length, width, height)
	else:
		if not p["item_name"] or p["item_name"] == p["item_code"]:
			frappe.throw(_("Please give the product name"))
		code = _new_item(p["item_code"], p["item_name"], group or (frappe.db.get_value("Item", template, "item_group") if template else None))
	item = frappe.get_doc("Item", code)
	item.is_purchase_item = 1
	if vendor:
		if not any(s.supplier == vendor for s in item.supplier_items):
			item.append("supplier_items", {"supplier": vendor})
		company = frappe.defaults.get_global_default("company") or frappe.db.get_value("Company", {}, "name")
		row = next((d for d in item.item_defaults if d.company == company), None) or item.append("item_defaults", {"company": company})
		row.default_supplier = vendor
	if subcontracted and vendor and "subcontract" not in (item.description or "").lower():
		item.description = f"{item.description or item.item_name}<br>Subcontracted: made by {frappe.db.get_value('Supplier', vendor, 'supplier_name')}"
	item.flags.ignore_permissions = True
	item.save()
	for who in _users_with_function("IT / ERP"):
		if who != user:
			_todo(who, "Item", code, _("New product from the app: {0}{1}. Check BOM / price.").format(item.item_name,
				f", vendor {vendor}" if vendor else ""))
	return {"item_code": code, "item_name": item.item_name, "vendor": vendor, "new": not p["exists"]}


def _variant(template: str, length, width, height) -> str:
	"""Size variant the way the existing ones are made: one attribute whose value is '<name> 30ft x 10ft x 8.6ft'."""
	from erpnext.controllers.item_variant import copy_attributes_to_variant

	attr = frappe.db.get_value("Item Variant Attribute", {"parent": template, "parenttype": "Item"}, "attribute")
	if not attr:
		frappe.throw(_("{0} has no size attribute: add it in ERPNext").format(template))
	size = _size(length, width, height)
	value = f"{attr} {size}"
	a = frappe.get_doc("Item Attribute", attr)
	if not a.numeric_values and not any(v.attribute_value == value for v in a.item_attribute_values):
		a.append("item_attribute_values", {"attribute_value": value, "abbr": size})
		a.flags.ignore_permissions = True
		a.save()
	# erpnext's create_variant() needs the ERPNext Item create right, which Accounts logins do not have; same steps here
	v = frappe.new_doc("Item")
	v.variant_based_on = "Item Attribute"
	v.set("attributes", [{"attribute": attr, "attribute_value": value}])
	copy_attributes_to_variant(frappe.get_doc("Item", template), v)
	v.item_code = f"{template}-{size}"
	v.item_name = f"{frappe.db.get_value('Item', template, 'item_name')}-{size}"
	v.flags.ignore_permissions = True
	v.insert()
	return v.name


def _new_item(code: str, name: str, group: str | None) -> str:
	it = frappe.new_doc("Item")
	it.update({"item_code": code, "item_name": name, "item_group": group or frappe.db.get_value("Item Group", {"is_group": 0}, "name"),
		"stock_uom": "Nos", "is_stock_item": 1, "is_sales_item": 1, "is_purchase_item": 1, "description": name})
	it.flags.ignore_permissions = True
	it.insert()
	return it.name


def _new_supplier(name: str) -> str:
	s = frappe.new_doc("Supplier")
	s.supplier_name = name
	s.supplier_type = "Company"
	s.supplier_group = frappe.db.get_single_value("Buying Settings", "supplier_group") or frappe.db.get_value("Supplier Group", {"is_group": 0}, "name")
	s.flags.ignore_permissions = True
	s.insert()
	return s.name
