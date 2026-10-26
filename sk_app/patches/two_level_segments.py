"""Change list point 2 (SK, 26-Oct-2026): Cabin / Non-Cabin, two levels like Tally.

Adds the Customer Groups, turns the old plain "Cabin" on leads / deals into Standard Cabin, fills the main segment,
and sets each salesperson's segment once by name: the cabin team (Rushi, Swati, Pranali, Rahul) Cabin, Aditya
Non-Cabin. Old customers are not touched here: they are tagged from Tally (after SK checks the list) or with one tap.
"""

import frappe

from sk_app import segments


def execute():
	segments.ensure_customer_groups()
	segments.ensure_fields()
	if frappe.db.exists("DocType", "CRM Lead"):
		for doctype in ("CRM Lead", "CRM Deal"):
			if not frappe.db.has_column(doctype, "sk_main_segment"):
				continue
			for old, new in segments.LEGACY.items():
				frappe.db.set_value(doctype, {"sk_segment": old}, "sk_segment", new, update_modified=False)
			for main, subs in segments.TREE.items():
				frappe.db.set_value(doctype, {"sk_segment": ["in", subs]}, "sk_main_segment", main, update_modified=False)
	for u in frappe.get_all("SK App User", filters={"enabled": 1}, fields=["name", "user", "full_name", "sk_main_segment"]):
		if u.sk_main_segment:
			continue
		first = (u.full_name or "").lower()
		if first.startswith("aditya") or u.user == "service@skind.tech":
			frappe.db.set_value("SK App User", u.name, "sk_main_segment", segments.NON_CABIN, update_modified=False)
		elif any(first.startswith(n) for n in ("rishikesh", "rushi", "swati", "pranali", "rahul")):
			frappe.db.set_value("SK App User", u.name, "sk_main_segment", segments.CABIN, update_modified=False)
