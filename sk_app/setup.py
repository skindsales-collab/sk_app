"""One-time setup: SK App users and the Sales KPI targets confirmed by SK on 25-Oct-2026 (proposal Rev 5, Section 1B).

Run from bench after install:  bench --site <site> execute sk_app.setup.load_sales_pilot
People are matched by their ERPNext user full name, so no e-mail addresses are kept in code.
"""

import frappe

L = 100000  # one lakh

SALES_PILOT = [
	{
		"full_name": "Rishikesh Mhase",  # Rushi
		"home": "Sales",
		"targets": [
			("Revenue", "Orders booked (Rs, before GST)", "orders_value", 45 * L, "Rs", 30, "Confirmed by CEO"),
			("Pipeline", "Leads worked (first call made)", "leads_worked", 130, "Count", 10, "Proposed"),
			("Pipeline", "First call within 5 minutes", "first_response_pct", 90, "%", 10, "Proposed"),
			("Conversion", "Quotations sent", "quotes_sent", 20, "Count", 20, "Proposed"),
			("Price discipline", "Orders at approved price", "manual", 90, "%", 10, "Proposed"),
			("Collection", "Payment within 15 days of delivery", "manual", 100, "%", 10, "Proposed"),
			("DSI", "Daily Small Improvements", "dsi_count", 26, "Count", 10, "Proposed"),
		],
	},
	{
		"full_name": "Rahul Raju Jalnil",
		"home": "Sales",
		"targets": [
			("Revenue", "Orders booked (Rs, before GST)", "orders_value", 12.5 * L, "Rs", 30, "Confirmed by CEO"),
			("Activity", "Qualified leads worked", "leads_worked", 150, "Count", 25, "Proposed"),
			("Conversion", "Cabins ordered", "cabins_qty", 5, "Count", 25, "Proposed"),
			("Collection", "Payment follow-up on own orders", "manual", 100, "%", 10, "Proposed"),
			("DSI", "Daily Small Improvements", "dsi_count", 26, "Count", 10, "Proposed"),
		],
	},
	{
		"full_name": "Swati  Mashakhetri",
		"home": "Sales",
		"targets": [
			("Revenue", "Orders booked (Rs, before GST)", "orders_value", 15 * L, "Rs", 30, "Confirmed by CEO"),
			("Order handling", "Orders with drawing, BOM, dispatch date in 2 days", "manual", 100, "%", 25, "Proposed"),
			("Follow-up", "Quotes older than 7 days followed up", "manual", 100, "%", 15, "Proposed"),
			("Purchase support", "Material requests same day as work order", "manual", 100, "%", 20, "Proposed"),
			("DSI", "Daily Small Improvements", "dsi_count", 26, "Count", 10, "Proposed"),
		],
	},
	{
		"full_name": "Pranali Mane",
		"home": "Marketing",
		"targets": [
			("Revenue", "Orders from digital leads (Rs, before GST)", "digital_orders_value", 10 * L, "Rs", 30, "Confirmed by CEO"),
			("Leads", "Digital enquiries", "digital_leads", 120, "Count", 25, "Proposed"),
			("Data quality", "Leads with source, owner and contact", "lead_data_quality_pct", 100, "%", 15, "Proposed"),
			("Presence", "Google photos weekly, GeM daily", "manual", 100, "%", 20, "Proposed"),
			("DSI", "Daily Small Improvements", "dsi_count", 26, "Count", 10, "Proposed"),
		],
	},
]


def _user_by_name(full_name: str) -> str | None:
	return frappe.db.get_value("User", {"full_name": full_name, "enabled": 1}, "name")


def load_sales_pilot(replace_targets: int = 0):
	"""Create SK App User rows and KPI targets for the Sales pilot. Safe to run again."""
	done, missing = [], []
	for person in SALES_PILOT:
		user = _user_by_name(person["full_name"])
		if not user:
			missing.append(person["full_name"])
			continue
		if not frappe.db.exists("SK App User", user):
			frappe.get_doc({"doctype": "SK App User", "user": user, "home": person["home"], "language": "English"}).insert()
		if int(replace_targets):
			frappe.db.delete("SK KPI Target", {"user": user})
		for kra, label, code, target, unit, weight, status in person["targets"]:
			if frappe.db.exists("SK KPI Target", {"user": user, "kpi_label": label}):
				continue
			frappe.get_doc({
				"doctype": "SK KPI Target", "user": user, "kra": kra, "kpi_label": label, "kpi_code": code,
				"monthly_target": target, "unit": unit, "weight": weight, "status": status,
			}).insert()
		done.append(person["full_name"])
	frappe.db.commit()
	return {"set_up": done, "user_not_found": missing}


@frappe.whitelist(methods=["POST"])
def load_sales_pilot_now():
	"""Button on SK App Settings: same as the bench command, for sites without a bench shell (Frappe Cloud)."""
	frappe.only_for("System Manager")
	return load_sales_pilot()
