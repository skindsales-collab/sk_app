"""Old / New path per module and per pilot user (rebuild plan, Phase 0). The setting is the SK Path Switch list in ERPNext:
SK flips a module back to Old in one click, with no deploy, so work never stops while a module is rebuilt."""

import frappe

from sk_app.core.switch_rules import MODULES, rule_mode, uses_new

DOCTYPE = "SK Path Switch"


def _row(module: str):
	if not frappe.db.table_exists(DOCTYPE):
		return None
	return frappe.db.get_value(DOCTYPE, module, ["path", "pilot_users", "rules"], as_dict=True)


def use_new(module: str, user: str | None = None) -> bool:
	return uses_new(_row(module), user or frappe.session.user)


def rules_for(module: str) -> str:
	return rule_mode(_row(module))


def my_paths(user: str) -> dict:
	"""{module: "New" | "Old"} for this person, sent to the app once at start."""
	return {m: ("New" if use_new(m, user) else "Old") for m in MODULES}


def ensure_rows():
	"""After migrate: one row per module, all Old and Warn only, so nothing changes until SK switches a module."""
	if not frappe.db.table_exists(DOCTYPE):
		return
	for m in MODULES:
		if not frappe.db.exists(DOCTYPE, m):
			frappe.get_doc({"doctype": DOCTYPE, "module": m, "path": "Old", "rules": "Warn only"}).insert(ignore_permissions=True)
