import frappe
from frappe import _

no_cache = 1


def get_context(context):
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=/sk"
		raise frappe.Redirect
	context.no_header = 1
	context.no_breadcrumbs = 1
	context.title = _("SK App")
	context.csrf_token = frappe.sessions.get_csrf_token()
	context.user = frappe.session.user
	return context
