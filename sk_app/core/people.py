"""Who is this user (rebuild plan, Phase 0). Before 4-Nov the "is CEO" check was written in 5 files, not all the same."""

import frappe

MANAGEMENT = "Management"


def functions(user: str) -> list[str]:
	from sk_app.logins import profile_functions

	return profile_functions(user) or []


def users_with_function(function: str) -> list[str]:
	from sk_app.store import _users_with_function

	return _users_with_function(function)


def ceo_users() -> list[str]:
	"""The Management people; if nobody has Management yet, the System Managers (so approvals never go to nobody)."""
	return users_with_function(MANAGEMENT) or [u for u in frappe.get_all("Has Role",
		filters={"role": "System Manager", "parenttype": "User"}, pluck="parent") if u != "Administrator"]


def is_ceo(user: str) -> bool:
	if not user:
		return False
	return user == "Administrator" or MANAGEMENT in functions(user) or user in ceo_users()
