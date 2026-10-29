"""DSI Monthly Summary (SK 29-Oct-2026): month × person × role, from the SK DSI Entries (sk_app.dsi)."""

from frappe import _
from frappe.utils import getdate, today

from sk_app.dsi import summary


def execute(filters=None):
	filters = filters or {}
	columns = [
		{"label": _("Month"), "fieldname": "month_label", "fieldtype": "Data", "width": 90},
		{"label": _("Person"), "fieldname": "full_name", "fieldtype": "Data", "width": 170},
		{"label": _("User"), "fieldname": "user", "fieldtype": "Link", "options": "User", "width": 170},
		{"label": _("Function / Role"), "fieldname": "function", "fieldtype": "Data", "width": 130},
		{"label": _("DSI Entries"), "fieldname": "entries", "fieldtype": "Int", "width": 90},
		{"label": _("Days Posted"), "fieldname": "days", "fieldtype": "Int", "width": 90},
		{"label": _("Target"), "fieldname": "target", "fieldtype": "Float", "precision": 0, "width": 70},
		{"label": _("% of Target"), "fieldname": "pct", "fieldtype": "Percent", "width": 90},
		{"label": _("Time Saved (min)"), "fieldname": "time_min", "fieldtype": "Float", "precision": 0, "width": 110},
		{"label": _("Cost Saved"), "fieldname": "cost_rs", "fieldtype": "Currency", "width": 110},
		{"label": _("Quality"), "fieldname": "quality", "fieldtype": "Int", "width": 70},
		{"label": _("Safety"), "fieldname": "safety", "fieldtype": "Int", "width": 70},
		{"label": _("Customer"), "fieldname": "customer", "fieldtype": "Int", "width": 80},
		{"label": _("Best of Month"), "fieldname": "best", "fieldtype": "Int", "width": 100},
	]
	rows = summary(filters.get("from_date") or "2026-04-01", filters.get("to_date") or today(),
		filters.get("function"), filters.get("user"))
	for r in rows:
		r["month_label"] = f"{getdate(r['month']):%b %Y}"
	return columns, rows
