"""SK 20-Nov (Swati / Pranali on the CRM deal page): a Cabin deal showed the Machine Shifting blocks, and the amount
typed in "Annual Revenue" (a company field) was taken for the customer's budget. On the CRM deal page:
- the Machine Shifting blocks move to their own tab "Machine Shifting" (fields there still only show for that segment);
- "Annual Revenue" and "No. of Employees" leave the deal forms; the budget box is "Customer Budget" (Cabin Enquiry)."""
import json

import frappe

MS_SECTIONS = ("ms_enquiry", "ms_machines_section", "ms_output")
DROP = ("annual_revenue", "no_of_employees")


def _drop(node):
	if isinstance(node, dict):
		if isinstance(node.get("fields"), list):
			node["fields"] = [f for f in node["fields"] if (f if isinstance(f, str) else (f or {}).get("fieldname")) not in DROP]
		for v in node.values():
			_drop(v)
	elif isinstance(node, list):
		for v in node:
			_drop(v)


def execute():
	if not frappe.db.exists("DocType", "CRM Fields Layout"):
		return
	name = "CRM Deal-Data Fields"
	if frappe.db.exists("CRM Fields Layout", name):
		layout = json.loads(frappe.db.get_value("CRM Fields Layout", name, "layout") or "[]")
		if layout and isinstance(layout[0], dict) and "sections" in layout[0] and not any(t.get("name") == "ms_tab" for t in layout):
			first = layout[0]
			moved = [s for s in first["sections"] if s.get("name") in MS_SECTIONS]
			if moved:
				first["sections"] = [s for s in first["sections"] if s.get("name") not in MS_SECTIONS]
				first.setdefault("label", "Details")
				layout.append({"name": "ms_tab", "label": "Machine Shifting", "sections": moved})
		_drop(layout)
		frappe.db.set_value("CRM Fields Layout", name, "layout", json.dumps(layout))
	for other in ("CRM Deal-Side Panel", "CRM Deal-Quick Entry"):
		if frappe.db.exists("CRM Fields Layout", other):
			layout = json.loads(frappe.db.get_value("CRM Fields Layout", other, "layout") or "[]")
			_drop(layout)
			frappe.db.set_value("CRM Fields Layout", other, "layout", json.dumps(layout))
