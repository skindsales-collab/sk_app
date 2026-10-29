"""SK 29-Oct-2026: each DSI keeps the person's function, for the monthly summary by role (sk_app.dsi)."""

import frappe

from sk_app.dsi import main_function


def execute():
	if not frappe.db.has_column("SK DSI Entry", "function"):
		return
	for e in frappe.get_all("SK DSI Entry", filters={"function": ["in", ["", None]]}, fields=["name", "user"]):
		frappe.db.set_value("SK DSI Entry", e.name, "function", main_function(e.user), update_modified=False)
