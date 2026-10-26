import os

import frappe
from frappe import _

ASSETS = ("js/sk_app.js", "js/card_parse.js", "css/sk_app.css")

no_cache = 1


def get_context(context):
	context.no_header = 1
	context.v = asset_version()
	# SK: everyone logs in with their mobile number and PIN on the app's own screen; email login stays as an option
	context.guest = frappe.session.user == "Guest"
	if context.guest:
		from sk_app.otp import enabled

		context.title = _("SK App")
		context.otp = enabled()
		return context
	context.no_breadcrumbs = 1
	context.title = _("SK App")
	context.csrf_token = frappe.sessions.get_csrf_token()
	context.user = frappe.session.user
	return context


def asset_version() -> str:
	"""Changes on every deploy. /assets is cached by phones for a year, so the links carry ?v= to fetch new code."""
	public = frappe.get_app_path("sk_app", "public")
	try:
		return str(int(max(os.path.getmtime(os.path.join(public, a)) for a in ASSETS)))
	except OSError:
		return frappe.utils.now_datetime().strftime("%Y%m%d")
