"""CEO "View Member App" (change list point 3, SK 26-Oct-2026).

Sunil (CEO) and SK open any member's app exactly as that member sees it: their Home, icons, data and language. Each
screen is built with the member's own ERPNext permissions, so a page that fails for Rahul fails the same way for the
CEO, which is how problems are found. View only: only reading screens can be called this way; every save / send /
call stays blocked, and the PIN page is never shown. Every view is kept in ERPNext's Activity Log (Management only).
"""

import frappe
from frappe import _
from frappe.utils import getdate, now_datetime, strip_html

# reading screens that are never opened for another person
NEVER = {"view_as", "view_members", "view_suggest", "login_methods", "my_pin", "pin_status"}


def can_view(user: str) -> bool:
	from sk_app.logins import profile_functions

	return user == "Administrator" or "Management" in profile_functions(user)


def _check(user: str):
	if not can_view(user):
		frappe.throw(_("Only the CEO can open another member's app"), frappe.PermissionError)


def members(user: str) -> dict:
	"""Everyone with the app, grouped by function, with their last active time."""
	_check(user)
	from sk_app.functions import FUNCTIONS
	from sk_app.logins import profile_functions

	rows = frappe.get_all("SK App User", filters={"enabled": 1, "user": ["!=", user]}, fields=["user", "full_name", "home"],
		order_by="full_name asc")
	last = {u.name: u.last_active for u in frappe.get_all("User", filters={"name": ["in", [r.user for r in rows] or [""]]},
		fields=["name", "last_active"])}
	groups = {}
	for r in rows:
		functions = profile_functions(r.user) or [r.home or "Other"]
		groups.setdefault(functions[0], []).append({"user": r.user, "full_name": r.full_name or r.user, "functions": functions,
			"last_active": str(last.get(r.user) or "")[:16] or None})
	order = list(FUNCTIONS)
	return {"groups": [{"function": f, "label": FUNCTIONS.get(f, {}).get("label"), "people": groups[f]} for f in sorted(groups, key=lambda f: order.index(f) if f in order else 99)]}


def _allowed(method: str):
	from sk_app import api

	fn = getattr(api, method, None) if not method.startswith("_") and method not in NEVER else None
	if not fn or fn not in frappe.whitelisted:
		frappe.throw(_("This screen cannot be opened for another member"), frappe.PermissionError)
	methods = frappe.allowed_http_methods_for_whitelisted_func.get(fn) or ["GET", "POST", "PUT", "DELETE"]
	if "GET" not in methods:
		frappe.throw(_("View only: nothing can be saved, sent or called in the member's name"), frappe.PermissionError)
	return fn


def _log(viewer: str, member: str, view: str | None):
	"""One Activity Log line per member and screen every 10 minutes."""
	key = f"sk_view_member:{viewer}:{member}:{view}"
	if frappe.cache.get_value(key):
		return
	frappe.cache.set_value(key, 1, expires_in_sec=600)
	frappe.get_doc({"doctype": "Activity Log", "subject": f"{frappe.utils.get_fullname(viewer)} viewed {frappe.utils.get_fullname(member)}'s app: {view or 'Home'}"[:140],
		"reference_doctype": "User", "reference_name": member, "user": viewer, "full_name": frappe.utils.get_fullname(viewer),
		"status": "Success", "communication_date": now_datetime()}).insert(ignore_permissions=True)


def view_as(viewer: str, member: str, method: str, args: dict | None = None, view: str | None = None):
	"""Run one reading screen of the app as the member, then switch straight back to the CEO."""
	_check(viewer)
	if member == viewer or not frappe.db.exists("SK App User", {"user": member, "enabled": 1}):
		frappe.throw(_("Pick a member"))
	fn = _allowed(method)
	session = frappe.local.session
	saved = {"user": session.user, "sid": session.sid, "data": session.data}
	form_dict = frappe.local.form_dict
	frappe.db.savepoint("sk_view_member")
	try:
		frappe.set_user(member)
		frappe.flags.sk_viewing = viewer
		result = fn(**(args or {}))
	finally:
		frappe.flags.sk_viewing = None
		try:  # a reading screen never leaves a change behind in the member's name
			frappe.db.rollback(save_point="sk_view_member")
		except Exception:
			pass
		frappe.set_user(saved["user"])
		session.sid, session.data = saved["sid"], saved["data"]
		frappe.local.form_dict = form_dict
	_log(viewer, member, view)
	return result


def suggest(viewer: str, member: str, view: str | None, text: str, photo: str | None = None) -> str:
	"""💡 on a member's page: the CEO's idea goes to the AI & ERP Improvement Inbox (Samir), with whose page it was."""
	_check(viewer)
	if not (text or "").strip():
		frappe.throw(_("Please speak or type the idea"))
	desc = f"💡 CEO idea on {frappe.utils.get_fullname(member)}'s app, page '{view or 'Home'}': {strip_html(text.strip())[:400]}"
	return frappe.get_doc({"doctype": "SK Work Log", "user": viewer, "date": getdate(), "entry_type": "Problem",
		"problem_type": "IT / app", "description": desc, "photo": photo or None}).insert(ignore_permissions=True).name
