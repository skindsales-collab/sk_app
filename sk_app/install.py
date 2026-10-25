import frappe


def after_install():
	"""Save SK App Settings once so its defaults are stored (single DocTypes start empty)."""
	settings = frappe.get_single("SK App Settings")
	for df in settings.meta.fields:
		if df.default and settings.get(df.fieldname) in (None, ""):
			settings.set(df.fieldname, df.default)
	settings.save(ignore_permissions=True)
