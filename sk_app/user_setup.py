"""SK 23-Nov (approved): one-click sales login. An SK App User whose home is Sales gets, on save, the same setup as the
working sales logins (Swati, Pranali): roles Sales User + Employee and the module profile "CRM Only" (the desk shows only
CRM / SK App; everything else is done through SK App). Roles already given are kept; a module profile already chosen
is kept. The role profile "SK Sales" (Sales User + Employee) is there to pick by hand in ERPNext too."""

import frappe

SALES_ROLES = ("Sales User", "Employee")
ROLE_PROFILE = "SK Sales"
MODULE_PROFILE = "CRM Only"
# modules a sales login may open in the desk (the rest are blocked), as in the working "CRM Only" profile
OPEN_MODULES = {"FCRM", "SK App", "System", "Build", "Data", "Users", "HR Setup", "Tenure", "Recruitment", "Shift and Attendance",
	"Leaves", "Expenses", "Performance", "Tax and Benefits", "Domain Enrichment", "Frappe Builder", "Helpdesk (Custom)"}


def ensure_profiles():
	if not frappe.db.exists("Role Profile", ROLE_PROFILE):
		frappe.get_doc({"doctype": "Role Profile", "role_profile": ROLE_PROFILE,
			"roles": [{"role": r} for r in SALES_ROLES if frappe.db.exists("Role", r)]}).insert(ignore_permissions=True)
	if not frappe.db.exists("Module Profile", MODULE_PROFILE):
		blocked = [m for m in frappe.get_all("Module Def", pluck="name") if m not in OPEN_MODULES]
		frappe.get_doc({"doctype": "Module Profile", "module_profile_name": MODULE_PROFILE,
			"block_modules": [{"module": m} for m in blocked]}).insert(ignore_permissions=True)


def setup_sales_login(user: str) -> list[str]:
	"""Gives a sales login what it needs; returns what was added."""
	if not user or user in ("Administrator", "Guest") or not frappe.db.exists("User", user):
		return []
	ensure_profiles()
	u = frappe.get_doc("User", user)
	added = []
	have = {r.role for r in u.roles}
	linked = frappe.db.exists("Employee", {"user_id": user})
	for r in SALES_ROLES:
		if r == "Employee" and not linked:
			continue  # ERPNext gives the Employee role only to a login linked to its Employee record (HR links it)
		if r not in have and frappe.db.exists("Role", r):
			u.append("roles", {"role": r})
			added.append(r)
	if not u.get("module_profile") and frappe.db.exists("Module Profile", MODULE_PROFILE):
		u.module_profile = MODULE_PROFILE
		added.append(MODULE_PROFILE)
	if added:
		u.flags.ignore_permissions = True
		u.save()
	return added


def on_app_user_update(doc, method=None):
	"""SK App User on_update: a Sales login (home Sales, or Sales among its functions) is set up at once."""
	if not doc.get("enabled") or not doc.get("user"):
		return
	functions = {r.function for r in (doc.get("functions") or [])} if doc.meta.has_field("functions") else set()
	if doc.get("home") != "Sales" and "Sales" not in functions:
		return
	try:
		added = setup_sales_login(doc.user)
		if added:
			frappe.msgprint(frappe._("Sales login set up for {0}: {1}").format(doc.user, ", ".join(added)), alert=True)
	except Exception:
		frappe.log_error(f"SK App sales login setup {doc.user}")
