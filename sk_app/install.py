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
	from sk_app import segments

	segments.ensure_customer_groups()
	from sk_app.complaints import ensure_setup

	ensure_setup()
	from sk_app.products import ensure_fields as product_fields

	product_fields()
	segments.sync_user_permissions()
	from sk_app.crm import setup_deal_customer_column

	setup_deal_customer_column()  # Swati item 8
	from sk_app.lead_status import ensure_statuses

	from sk_app.sales_owner import ensure_sales_persons

	ensure_sales_persons()  # SK 27-Oct: no salesperson had an ERPNext Sales Person, so Tally sales counted for nobody
	ensure_statuses()  # SK 27-Oct: New, Qualified, Drawing, Quotation, Negotiations, Deal Won, Junk Lead, Deal Loss
	from sk_app.training import seed_lessons

	seed_lessons()
	from sk_app.function_faq import seed_faq

	seed_faq()  # SK 27-Oct: HR, Production and Accounts FAQ in Training
	from sk_app.hr import ensure_holiday_setup

	ensure_holiday_setup()  # trial 26-Oct: leave needs a company holiday list


def ensure_crm_fields():
	"""Two-level segment on CRM Lead and CRM Deal (Cabin: Standard / LGSF / Modular; Non-Cabin: Machine Shifting /
	Job Work / Other), used by the app's new-lead form."""
	from sk_app.segments import ensure_fields

	ensure_fields()


def ensure_mail_fields():
	"""Team mailbox status on each mail (New → Taken by … → Replied / Lead made), so two people never answer one mail."""
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	create_custom_fields({"Communication": [
		{"fieldname": "sk_mail_status", "label": "SK App mail status", "fieldtype": "Select",
			"options": "\nNew\nTaken\nReplied\nLead made\nNot a lead", "insert_after": "status", "read_only": 1},
		{"fieldname": "sk_taken_by", "label": "Taken by (SK App)", "fieldtype": "Link", "options": "User",
			"insert_after": "sk_mail_status", "read_only": 1},
	]}, update=True)
