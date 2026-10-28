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


def _safe(step, label: str):
	"""Run one setup step; if it fails, undo it, log it and go on with the update."""
	frappe.db.savepoint("sk_setup")
	try:
		step()
	except Exception:
		try:
			frappe.db.rollback(save_point="sk_setup")
		except Exception:
			pass
		frappe.log_error(title=f"SK App setup step failed: {label}")


def after_migrate():
	from sk_app.logins import setup_site

	settings_defaults()
	setup_site()
	ensure_crm_fields()
	ensure_mail_fields()
	from sk_app import segments

	segments.ensure_customer_groups()
	from sk_app.segment_accounts import ensure_cost_centres

	ensure_cost_centres()  # SK 28-Oct: Job Work next to Machine Shifting / Machine Maintenance
	from sk_app.complaints import ensure_setup

	ensure_setup()
	from sk_app.products import ensure_fields as product_fields

	product_fields()
	segments.sync_user_permissions()
	from sk_app.crm import setup_deal_customer_column

	setup_deal_customer_column()  # Swati item 8
	from sk_app.lead_status import ensure_statuses

	from sk_app.sales_owner import ensure_sales_persons

	from sk_app.customer_names import ensure as customer_names

	customer_names()  # SK 27-Oct points 14 / 19: customers by name, not CUS- numbers
	ensure_sales_persons()  # SK 27-Oct: no salesperson had an ERPNext Sales Person, so Tally sales counted for nobody
	ensure_statuses()  # SK 27-Oct: New, Qualified, Drawing, Quotation, Negotiations, Deal Won, Junk Lead, Deal Loss
	from sk_app.tally import ensure as tally_names

	tally_names()  # SK 27-Oct: Tally words in ERPNext (Narration on every voucher)
	from sk_app.cabin_quote import ensure_setup as cabin_quote_setup
	from sk_app.permissions import ensure_crm_search
	from sk_app.store import ensure_job_card_cabin

	# 27-Oct: two sk-dev updates were rolled back; one setup step that ERPNext refuses on the live data (a master it
	# needs, a mandatory field) is now logged in Error Log for the AI team and no longer stops the whole update
	_safe(cabin_quote_setup, "cabin quotation")  # SK 27-Oct: one rate card, same cabin price from any salesperson, SK's quote print
	_safe(ensure_job_card_cabin, "job card customer / size")  # SK 27-Oct (Yogesh): job card picker shows customer and cabin size
	_safe(ensure_crm_search, "lead search")  # SK 27-Oct: lead search in ERPNext
	from sk_app.cold_calls import ensure_field as cold_calling_field

	_safe(cold_calling_field, "cold calling list")  # SK 27-Oct: cold-calling data out of My Leads
	from sk_app.marketing_list import ensure_setup as marketing_list_setup
	from sk_app.requisition import ensure_setup as requisition_setup
	from sk_app.quality import ensure_setup as self_check_setup

	_safe(self_check_setup, "worker self-check")  # SK 28-Oct: worker check sheet before Aditya's quality check
	from sk_app.hr import ensure_voucher_fields
	from sk_app.sub_bills import ensure_setup as sub_bills_setup

	_safe(ensure_voucher_fields, "cash vouchers")  # SK 28-Oct: paid to, project / cabin, no-bill reason; CEO approves all
	_safe(sub_bills_setup, "subcontractor bills")  # SK 28-Oct: rate sheet → bill → Rushi → CEO → payable
	_safe(requisition_setup, "purchase requisition")  # SK 27-Oct: requisition → CEO → PO → receipt
	_safe(marketing_list_setup, "marketing list")  # SK 27-Oct: potential customers for greetings / promotions, not leads
	from sk_app.cold_calls import move_all_once
	from sk_app.segments import auto_tag
	from sk_app.sales_owner import auto_link

	from sk_app.item_input import ensure_setup as item_photo_setup

	_safe(item_photo_setup, "item photo samples")  # SK 28-Oct: material identified from a photo
	from sk_app.phone_sync import ensure_setup as phone_setup

	_safe(phone_setup, "SK Phone helper")  # SK 28-Oct: calls from company / personal phones into CRM
	_safe(move_all_once, "cold calling → marketing list")  # SK 28-Oct: cold-calling data is not a lead
	_safe(auto_tag, "customer segments")  # SK 28-Oct: Cabin / Non-Cabin from Tally vouchers and CRM deals
	_safe(auto_link, "salesperson on customers and orders")  # SK 28-Oct: graphs had no order in anyone's name
	from sk_app.deal_quotes import ensure_setup as deal_quotes_setup, sync as deal_quotes_sync

	_safe(deal_quotes_setup, "job / service item for quotations")
	_safe(deal_quotes_sync, "quotes on deals → ERPNext Quotations")  # SK 28-Oct: every quote goes through ERPNext
	from sk_app.training import seed_lessons

	seed_lessons()
	from sk_app.function_faq import seed_faq

	seed_faq()  # SK 27-Oct: HR, Production and Accounts FAQ in Training
	from sk_app.hr import ensure_holiday_setup

	ensure_holiday_setup()
	from sk_app.hr import ensure_joiner_fields

	ensure_joiner_fields()  # SK 27-Oct: Aadhaar on the Employee for the New joiner photo form  # trial 26-Oct: leave needs a company holiday list


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
			"options": "\nNew\nTaken\nReplied\nLead made\nNot a lead\nComplaint", "insert_after": "status", "read_only": 1},
		{"fieldname": "sk_taken_by", "label": "Taken by (SK App)", "fieldtype": "Link", "options": "User",
			"insert_after": "sk_mail_status", "read_only": 1},
		# SK 27-Oct: a mail moved to another team's box (info@ → cabin@)
		{"fieldname": "sk_box", "label": "Team mailbox (SK App)", "fieldtype": "Data", "insert_after": "sk_taken_by", "read_only": 1},
	]}, update=True)
