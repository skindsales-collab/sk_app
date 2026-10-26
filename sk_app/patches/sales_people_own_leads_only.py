"""SK, 26-Oct-2026: after the staff logins were made, salespeople saw every lead in CRM because the Sales function
also gave the ERPNext "Sales Manager" role. Take that role off the app's sales / marketing people (not admins);
each sees only their own leads again, and the sales manager sees his team on the Team Leads icon."""

import frappe

from sk_app import logins


def execute():
	for user in frappe.get_all("SK App User", filters={"enabled": 1}, pluck="user"):
		if not {"Sales", "Marketing"} & set(logins.profile_functions(user)):
			continue
		roles = frappe.get_roles(user)
		if "Sales Manager" in roles and "System Manager" not in roles:
			frappe.get_doc("User", user).remove_roles("Sales Manager")
