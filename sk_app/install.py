import frappe


def after_install():
	"""Save SK App Settings once so its defaults are stored (single DocTypes start empty)."""
	settings = frappe.get_single("SK App Settings")
	for df in settings.meta.fields:
		if df.default and settings.get(df.fieldname) in (None, ""):
			settings.set(df.fieldname, df.default)
	settings.save(ignore_permissions=True)
	after_migrate()


def settings_defaults():
	"""Defaults of SK App Settings fields added after the first install (a single DocType never fills them itself)."""
	meta = frappe.get_meta("SK App Settings")
	have = set(frappe.db.sql_list("select field from `tabSingles` where doctype = 'SK App Settings'"))
	for df in meta.fields:
		if df.default and df.fieldname not in have:
			frappe.db.set_single_value("SK App Settings", df.fieldname, df.default)


def after_migrate():
	from sk_app.logins import setup_site

	settings_defaults()
	setup_site()
	ensure_crm_fields()
	ensure_mail_fields()
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


def ensure_mail_fields():
	"""Team mailbox status on each mail (New → Taken by … → Replied / Lead made), so two people never answer one mail."""
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	create_custom_fields({"Communication": [
		{"fieldname": "sk_mail_status", "label": "SK App mail status", "fieldtype": "Select",
			"options": "\nNew\nTaken\nReplied\nLead made\nNot a lead", "insert_after": "status", "read_only": 1},
		{"fieldname": "sk_taken_by", "label": "Taken by (SK App)", "fieldtype": "Link", "options": "User",
			"insert_after": "sk_mail_status", "read_only": 1},
	]}, update=True)
