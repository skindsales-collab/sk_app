"""SK 29-Oct-2026: the quick Report Builder "DSI Monthly Summary" made in ERPNext gives way to the app's own report."""

import frappe


def execute():
	if frappe.db.get_value("Report", "DSI Monthly Summary", "is_standard") == "No":
		frappe.delete_doc("Report", "DSI Monthly Summary", force=True, ignore_permissions=True)
