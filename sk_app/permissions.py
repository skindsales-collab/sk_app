"""Record rules: people see and write only their own DSI and Work Book entries; managers see all."""

import frappe

MANAGER_ROLES = {"System Manager", "Sales Manager", "HR Manager"}


def _is_manager(user: str) -> bool:
	return bool(MANAGER_ROLES & set(frappe.get_roles(user)))


def stamp_user(doc, method=None):
	"""Ordinary users can only create entries for themselves."""
	user = frappe.session.user
	if not doc.user or not _is_manager(user) or user == "Guest":
		doc.user = user


def own_or_manager(doc, ptype=None, user=None):
	user = user or frappe.session.user
	if _is_manager(user):
		return True
	return doc.user == user or doc.owner == user
