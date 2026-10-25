import frappe


def after_install():
	"""Save SK App Settings once so its defaults are stored (single DocTypes start empty)."""
	settings = frappe.get_single("SK App Settings")
	for df in settings.meta.fields:
		if df.default and settings.get(df.fieldname) in (None, ""):
			settings.set(df.fieldname, df.default)
	settings.save(ignore_permissions=True)
	after_migrate()


def after_migrate():
	ensure_crm_fields()
	from sk_app.training import seed_lessons

	seed_lessons()


def ensure_crm_fields():
	"""Segment on CRM Lead and CRM Deal (Cabin, Machine Shifting, Job Work ...), used by the app's new-lead form."""
	if not frappe.db.exists("DocType", "CRM Lead"):
		return
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	from sk_app.crm import SEGMENTS

	field = {"fieldname": "sk_segment", "label": "Segment", "fieldtype": "Select", "options": "\n" + "\n".join(SEGMENTS),
		"insert_after": "source", "in_standard_filter": 1}
	create_custom_fields({"CRM Lead": [field], "CRM Deal": [field]}, update=True)
