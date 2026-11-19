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
NEVER = {"view_as", "view_members", "view_suggest", "login_methods", "my_pin", "pin_status", "lock_now", "unlock_pin", "face_options",
	"face_setup", "face_unlock", "reset_face"}


def _is_ceo(user: str) -> bool:
	from sk_app.core.people import is_ceo  # one shared check (rebuild Phase 0)

	return is_ceo(user)


def _team_users(user: str) -> set[str]:
	from sk_app.day_report import _team

	return {p.user for p in _team(user)}


def can_view(user: str) -> bool:
	"""The CEO opens everyone; a manager (Rushi, SK 26-Oct) opens only the people under him."""
	return _is_ceo(user) or bool(frappe.db.exists("SK App User", {"manager": user, "enabled": 1}))


def _check(user: str, member: str | None = None):
	if not can_view(user):
		frappe.throw(_("Only the CEO or a team manager can open another member's app"), frappe.PermissionError)
	if member and not _is_ceo(user) and member not in _team_users(user):
		frappe.throw(_("You can open only your own team members' app"), frappe.PermissionError)


def members(user: str) -> dict:
	"""Everyone with the app, grouped by function, with their last active time."""
	_check(user)
	from sk_app.functions import FUNCTIONS
	from sk_app.logins import profile_functions

	filters = {"enabled": 1, "user": ["!=", user]}
	if not _is_ceo(user):
		filters["user"] = ["in", list(_team_users(user)) or [""]]
	rows = frappe.get_all("SK App User", filters=filters, fields=["user", "full_name", "home"], order_by="full_name asc")
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
	"""Run one reading screen of the app as the member, then switch straight back to the CEO / manager."""
	_check(viewer, member)
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
	_check(viewer, member)
	if not (text or "").strip():
		frappe.throw(_("Please speak or type the idea"))
	who = "CEO" if _is_ceo(viewer) else frappe.utils.get_fullname(viewer)
	desc = f"💡 {who} idea on {frappe.utils.get_fullname(member)}'s app, page '{view or 'Home'}': {strip_html(text.strip())[:400]}"
	return frappe.get_doc({"doctype": "SK Work Log", "user": viewer, "date": getdate(), "entry_type": "Problem",
		"problem_type": "IT / app", "description": desc, "photo": photo or None}).insert(ignore_permissions=True).name


# ---------- SK 14-Nov "Work as": the CEO works in a member's app for them (they are on site) ----------
WORK_MODULE = "Work as"
# records that are never marked (system rows, logs and the mark itself)
NO_MARK = {"Comment", "Version", "Activity Log", "SK Rule Log", "Notification Log", "Communication", "File", "SK Perf Log", "Error Log",
	"Deleted Document", "Email Queue", "Email Queue Recipient", "Route History", "Access Log", "Session Default", "DocShare", "ToDo", "Scheduled Job Log"}


def can_work_as(user: str) -> bool:
	"""Only the CEO (Management function) works in another person's app; managers stay view-only."""
	return _is_ceo(user)


def work_as(viewer: str, member: str, method: str, args: dict | None = None, view: str | None = None):
	"""Run one screen or save of the app as the member and keep it. The record is the member's (owner, arrows, targets),
	and every record made this way is marked "entered by <CEO> on behalf of <member>" (comment + SK Rule Log), so the
	app shows it with the CEO badge. Nothing salary-related is in the app."""
	_check(viewer, member)
	if not can_work_as(viewer):
		frappe.throw(_("Only the CEO can work in another member's app"), frappe.PermissionError)
	if member == viewer or not frappe.db.exists("SK App User", {"user": member, "enabled": 1}):
		frappe.throw(_("Pick a member"))
	from sk_app import api

	fn = getattr(api, method, None) if not method.startswith("_") and method not in NEVER else None
	if not fn or fn not in frappe.whitelisted:
		frappe.throw(_("This screen cannot be opened for another member"), frappe.PermissionError)
	session = frappe.local.session
	saved = {"user": session.user, "sid": session.sid, "data": session.data}
	form_dict = frappe.local.form_dict
	try:
		frappe.set_user(member)
		frappe.flags.sk_viewing = viewer
		frappe.flags.sk_on_behalf = {"by": viewer, "for": member}
		result = fn(**(args or {}))
	finally:
		frappe.flags.sk_viewing = None
		frappe.flags.sk_on_behalf = None
		frappe.set_user(saved["user"])
		session.sid, session.data = saved["sid"], saved["data"]
		frappe.local.form_dict = form_dict
	_log(viewer, member, f"work: {view or method}")
	return result


def mark_on_behalf(doc, method=None):
	"""after_insert of every doctype: a record made while the CEO works as a member gets its mark."""
	who = frappe.flags.get("sk_on_behalf")
	if not who or doc.doctype in NO_MARK or doc.doctype.startswith("SK Hub"):
		return
	by, member = frappe.utils.get_fullname(who["by"]), frappe.utils.get_fullname(who["for"])
	try:
		if frappe.db.table_exists("SK Rule Log"):
			frappe.get_doc({"doctype": "SK Rule Log", "module": WORK_MODULE, "rule": "on_behalf", "mode": "Info", "reference_doctype": doc.doctype,
				"reference_name": doc.name, "user": who["for"], "detail": f"Entered by {by} (CEO) on behalf of {member}"}).insert(ignore_permissions=True)
		doc.add_comment("Comment", _("Entered by {0} (CEO) on behalf of {1}").format(by, member))
	except Exception:
		frappe.log_error(f"SK work-as mark {doc.doctype} {doc.name}")


def on_behalf_names(doctype: str) -> set[str]:
	"""Names of this doctype entered by the CEO for someone (for the badge in lists and cards)."""
	if not frappe.db.table_exists("SK Rule Log"):
		return set()
	cache = frappe.flags.setdefault("sk_on_behalf_names", {})  # once per request
	if doctype not in cache:
		cache[doctype] = set(frappe.get_all("SK Rule Log", filters={"module": WORK_MODULE, "reference_doctype": doctype}, pluck="reference_name"))
	return cache[doctype]
