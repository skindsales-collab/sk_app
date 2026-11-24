from sk_app import sales_screens
from sk_app.writers import requisition as req_w
from sk_app import purchase_screens
from sk_app import store_screens
app_name = "sk_app"
app_title = "SK App"
app_publisher = "SK Ind Tech Solutions Pvt Ltd"
app_description = "Mobile work app (PWA) for SK Ind Tech inside ERPNext, with Claude guidance"
app_email = "skind.tech.ai@gmail.com"
app_license = "Proprietary"
required_apps = ["frappe", "erpnext"]

# The phone app lives at /sk (installable from the browser: Add to Home Screen)
website_route_rules = [
	{"from_route": "/sk/<path:app_path>", "to_route": "sk"},
]

# SK 27-Oct: Tally keys in ERPNext for the accounts team (F4-F9, Ctrl+A, Alt+D Day Book ...)
app_include_js = ["/assets/sk_app/js/sk_tally_keys.js", "/assets/sk_app/js/sk_help_desk.js", "/assets/sk_app/js/sk_safe_cancel.js", "/assets/sk_app/js/sk_bank_return.js"]  # SK 28-Oct: ❓ help on every ERPNext page

# SK 27-Oct: standard cabin quotation print (SK's quote template), {{ sk_cabin_quote_html(doc) }}
# SK 28-Oct: "Post Tally invoices" button for Accounts (sk_app.tally_invoices)
doctype_list_js = {"Sales Invoice": "public/js/sales_invoice_list.js"}

# SK 29-Oct: GST tax invoice, delivery challan, order acknowledgement and PO prints with Bill to and Ship to, {{ sk_tax_invoice_html(doc) }}
jinja = {"methods": ["sk_app.cabin_quote.sk_cabin_quote_html", "sk_app.tax_invoice.sk_tax_invoice_html", "sk_app.print_rules.sk_customer_desc", "sk_app.cabin_quote.sk_doc_noncabin"]}

scheduler_events = {
	"hourly": ["sk_app.deal_quotes.sync", "sk_app.guide.hourly", "sk_app.day_report.auto_reports", "sk_app.activities.noon_nudge", "sk_app.mailbox.remind",
		"sk_app.hiring.hourly",  # SK 17-Nov hiring: 48 h hand-over to HR, interview reminders, 6-month and 7-day clean-ups
		"sk_app.old_crm_load.hourly"],  # SK 6-Nov: old CRM leads SK uploads as a File are loaded once
	# IndiaMART / JustDial / GeM mails to the team mailboxes become CRM leads (free route, point 14)
	"cron": {"*/5 * * * *": ["sk_app.lead_sources.scan", "sk_app.mailbox.link_known", "sk_app.mailbox.route_suppliers", "sk_app.mailbox.auto_leads"],
		# SK 27-Oct: the AI's actions to lift each graph, every morning before work
		"0 7 * * *": ["sk_app.ai_actions.morning", "sk_app.doubles.morning", "sk_app.core.night_check.morning"],  # SK 14-Nov: each owner's open items + CEO summary  # SK 4-Nov: possible doubles to Shraddha and SK
		# SK 28-Oct: customers tagged Cabin / Non-Cabin and every order and customer given its salesperson
		"30 1 * * *": ["sk_app.sales_owner.nightly"],
		# SK 29-Oct: a solved desk request the person did not answer for 3 days is closed
		"0 2 * * *": ["sk_app.issue_desk.auto_close", "sk_app.mailbox.ensure_fetch_all"],  # SK 21-Nov: mailboxes stay on ALL mails
		# SK 4-Nov before / after rebuild scorecard: the day's numbers saved once, the same way on the old and the new path
		# SK 6-Nov KF-04447: every payment against its bill(s), nightly before the scorecard
		"15 23 * * *": ["sk_app.writers.payment_allocate.link_unallocated"],
		# SK 6-Nov people rule: every active employee / service supplier in the app, nightly before the scorecard counts
		"30 23 * * *": ["sk_app.writers.app_user.nightly", "sk_app.core.imports.check", "sk_app.core.gate.nightly"],  # SK 6-Nov: source vs ERPNext per import
		# rebuild Flow 6 HR (New path): yesterday's punches -> Attendance once the Optick file is in (by 10 AM), one missed-punch
		# ToDo to HR; holiday list vs SK's paid holidays
		"30 10 * * *": ["sk_app.writers.attendance.daily", "sk_app.writers.leave.check_holidays"],
		"20 23 * * *": ["sk_app.writers.attendance.today"],  # job J 9-Nov: today's punches (any machine) at the end of the day
		"45 23 * * *": ["sk_app.core.scorecard.nightly"],
		# SK 14-Nov "approve": the night check of all data since 1-Apr, after the payment linking and login runs above
		"55 23 * * *": ["sk_app.core.night_check.nightly"],
		# SK 17-Nov hiring: 10 AM and 4 PM Mon-Sat, the HR owners forward the WhatsApp resumes to the HR Gmail
		"0 10,16 * * 1-6": ["sk_app.hiring.resume_forward_reminder"]},
}

doc_events = {
	"Notification Log": {"before_insert": "sk_app.mailbox.quiet_auto_assignment"},  # SK 23-Nov: no assignment mail flood
	"*": {"after_insert": "sk_app.view_member.mark_on_behalf"},  # SK 14-Nov: records the CEO enters as a member carry the CEO mark
	"SK DSI Entry": {"before_insert": ["sk_app.permissions.stamp_user", "sk_app.dsi.stamp_function"]},  # SK 29-Oct: role for the monthly summary
	"SK Work Log": {"before_insert": "sk_app.permissions.stamp_user"},
	"SK Day Report": {"before_insert": "sk_app.permissions.stamp_user"},
	"File": {"before_insert": "sk_app.files.check_file",  # PR H (SK 16-Nov KF-05549): only PDF / photos on customer-facing records, no cabin number
		"after_insert": ["sk_app.sales_screens.on_file_attached", "sk_app.deal_quotes.on_file"]},  # SK 28-Oct: a quote file → Quotation
	"SK Library Item": {"validate": "sk_app.library.make_public"},
	# SK 28-Oct mandatory gate: a lead / deal moves on only with its data and the step's ERPNext document (sk_app.gates)
	# SK 4-Nov: no double entry anywhere: same party + amount within 7 days, same reference / bill no, a 2nd deal of a lead (sk_app.doubles)
	"CRM Lead": {"validate": ["sk_app.segments.set_main", "sk_app.gates.check_crm", "sk_app.gates.check_lead_not_back_to_new"], "before_insert": "sk_app.doubles.check_lead"},
	"Job Applicant": {"before_insert": "sk_app.writers.applicant.before_insert"},  # R12: e-mail from the mobile, family from the designation
	"Comment": {"after_insert": "sk_app.writers.interview.on_comment"},  # R12: 'Slot: 18-Nov 10:30' on a Job Applicant books Round 1
	"CRM Deal": {"validate": ["sk_app.segments.set_main", "sk_app.sales_screens.set_deal_customer", "sk_app.quote_pickup.on_deal_validate",
		"sk_app.gates.check_crm", "sk_app.won_deals.check_won"],  # SK 14-Nov KF-05180: Won without a Sales Order is a rule gap
		# SK 4-Nov: no deal from a lead that is still New (call not connected): the lead is Qualified first (sk_app.gates)
		"before_insert": ["sk_app.doubles.check_deal", "sk_app.gates.check_new_deal"], "on_update": "sk_app.deal_quotes.on_deal_update"},
	# SK 4-Nov: members also work in ERPNext or through Claude: the quote / payment checks run on the record, whatever the route
	"Quotation": {"before_validate": "sk_app.party_currency.warm", "before_insert": "sk_app.gates.check_quote_step", "before_submit": ["sk_app.gates.check_quote_step", "sk_app.gates.check_quote_scope", "sk_app.gates.check_quotation"],
		"validate": "sk_app.writers.quotation.on_validate", "on_submit": "sk_app.quote_pdf.attach_on_submit"},
	"Item": {"validate": "sk_app.writers.item.on_validate"},
	# SK 4-Nov rebuild (S3): the customer's salesperson is set at save, not the next night (the nightly run stays as a safety net)
	"Customer": {"before_insert": "sk_app.segments.customer_group_from_deal", "validate": "sk_app.writers.customer.check_same_gstin", "after_insert": "sk_app.writers.customer.after_insert",
		"on_update": ["sk_app.segments.on_customer_update", "sk_app.sales_owner.on_customer_save"]},
	# SK 28-Oct: every order has its salesperson; income ledger and Non-Cabin sub-group cost centre from the customer
	"Sales Order": {"before_validate": "sk_app.party_currency.warm", "validate": ["sk_app.sales_owner.fill_order_team", "sk_app.segment_accounts.set_segment", "sk_app.writers.taxes.on_validate"],
		"on_update": "sk_app.writers.taxes.after_save",  # SK 6-Nov: GST filled by the app when the rows were left empty (New path)
		"before_submit": "sk_app.gates.check_sales_order",
		"on_submit": ["sk_app.won_deals.on_submit", "sk_app.lead_time.on_sales_order_submit", "sk_app.bom_optional.tell_design"]},  # SK 28-Oct: its lead / deal shows Won in the CRM at once
	# SK 29-Oct (Shraddha): a tax invoice is submitted only with the buyer's Bill to address (Ship to defaults to it)
	"Sales Invoice": {"before_validate": "sk_app.party_currency.warm", "validate": ["sk_app.segment_accounts.set_segment", "sk_app.cabin_projects.set_cost_centre", "sk_app.doubles.check",
		"sk_app.writers.taxes.on_validate", "sk_app.writers.payment_allocate.pull_advances"], "on_update": "sk_app.writers.taxes.after_save",
		"before_submit": "sk_app.gates.check_sales_invoice", "on_submit": "sk_app.lead_time.on_sales_invoice_submit",
		"autoname": "sk_app.invoice_naming.autoname"},  # SK 21-Nov: SK/IND/MMYY/### with one running number
	# SK 29-Oct: PO date → invoice date per cabin, days per 100 sq ft for Production (sk_app.lead_time)
	"Project": {"validate": "sk_app.lead_time.on_project_validate"},
	"SK Path Switch": {"validate": "sk_app.core.gate.on_switch"},  # SK 6-Nov: counts saved when a module goes New; checked nightly
	# SK 23-Nov: cancelling a task on a lead / deal keeps its owner (Frappe CRM empties it)
	"ToDo": {"validate": "sk_app.lead_owner_keep.remember_owner", "on_update": "sk_app.lead_owner_keep.keep_owner"},
	"SK App User": {"on_update": ["sk_app.segments.on_app_user_update", "sk_app.logins.set_company_default", "sk_app.user_setup.on_app_user_update"]},
	"Job Card": {"validate": ["sk_app.store_screens.set_job_card_cabin", "sk_app.writers.work_order.card_validate"],  # cabin label (SK 27-Oct) + rebuild Flow 5 (New path)
		# SK 29-Oct labour: each job has its service PO from the rate sheet; done → service GRN at once (sk_app.sub_bills)
		"after_insert": "sk_app.sub_bills.on_job_card_insert",
		"on_update": "sk_app.sub_bills.on_job_card_change", "on_submit": ["sk_app.sub_bills.on_job_card_change", "sk_app.writers.work_order.on_card_submit"]},
	# SK 29-Oct: one Project + cost centre per cabin; its material, bills and sales rows go to that cost centre at once,
	# and stages done before ERPNext close when the cabin's Work Order is submitted (sk_app.cabin_projects)
	"Work Order": {"validate": "sk_app.writers.work_order.on_validate", "before_submit": "sk_app.sub_bills.wo_submitting",
		"on_submit": ["sk_app.cabin_projects.close_done_stages", "sk_app.sub_bills.on_work_order_submit"]},
	"Stock Entry": {"validate": ["sk_app.cabin_projects.set_cost_centre", "sk_app.writers.stock_entry.on_validate"]},  # rebuild Flow 4 (New path)
	"Delivery Note": {"before_validate": "sk_app.party_currency.warm", "validate": "sk_app.cabin_projects.set_cost_centre", "before_submit": "sk_app.gates.check_sales_invoice"},
	# SK 27-Oct purchase flow: requisition → CEO approval → PO → receipt against the PO, in ERPNext too
	"Material Request": {"validate": ["sk_app.gates.check_request", "sk_app.cabin_projects.set_cost_centre"], "before_submit": "sk_app.writers.requisition.check_submit"},
	"Purchase Order": {"before_validate": "sk_app.party_currency.warm", "validate": ["sk_app.cabin_projects.set_cost_centre", "sk_app.writers.purchase_order.on_validate"],  # rebuild Flow 3 (New path)
		"before_submit": ["sk_app.writers.requisition.check_po", "sk_app.sub_bills.check_submit"], "on_submit": "sk_app.sub_bills.on_po_submit"},
	"Purchase Receipt": {"before_validate": "sk_app.party_currency.warm", "validate": ["sk_app.cabin_projects.set_cost_centre", "sk_app.writers.receipt.on_validate"], "before_submit": "sk_app.writers.requisition.check_receipt"},
	# SK 28/29-Oct: labour bill only from the service GRN of a PO Rushi + CEO approved; only CEO / Accounts change the rates
	"Purchase Invoice": {"before_validate": "sk_app.party_currency.warm", "validate": ["sk_app.cabin_projects.set_cost_centre", "sk_app.doubles.check", "sk_app.writers.payment_allocate.pull_advances"],
		"before_submit": ["sk_app.sub_bills.check_submit", "sk_app.writers.service_job.before_submit"]},  # service job bill only after approval (New path)
	"Item Price": {"validate": "sk_app.sub_bills.check_rate_edit"},
	# SK 4-Nov (Shraddha): a Net Banking / IMPS payment booked from Cash never shows in Bank Reconciliation: stopped
	"Payment Entry": {"validate": ["sk_app.doubles.check", "sk_app.writers.payment.on_validate", "sk_app.bank_return.warn_date_gap"],
		"on_submit": "sk_app.writers.bank_match.on_submit"},  # rebuild Flow 6: matched with its bank line at once (New path)
	"Journal Entry": {"validate": ["sk_app.doubles.check", "sk_app.writers.journal.on_validate", "sk_app.bank_return.warn_date_gap"]},
	# rebuild Flow 6 HR (New path): the HR rules on every record, from the app, ERPNext or SK Hub
	"Attendance": {"validate": "sk_app.writers.attendance.on_validate"},
	"Leave Application": {"before_validate": "sk_app.writers.leave.ensure_allocation", "validate": "sk_app.writers.leave.on_validate"},
	"Employee": {"validate": "sk_app.writers.employee.on_validate"},
	# SK 4-Nov "make it foolproof": the money masters only by the CEO / System Manager; a Bank mode needs Bank accounts (sk_app.masters)
	"Mode of Payment": {"validate": ["sk_app.masters.guard", "sk_app.masters.check_mode"]},
	"Accounts Settings": {"validate": "sk_app.masters.guard"},
	"Company": {"validate": "sk_app.masters.guard"},
	"Bank Account": {"validate": "sk_app.masters.guard"},
	"Account": {"validate": "sk_app.masters.guard"},
	# SK 29-Oct: a desk request set to Resolved (app or ERPNext) sends the reply and joins the role's FAQ at once
	"Issue": {"on_update": "sk_app.issue_desk.on_issue_update"},
}

# SK Hub's activity log only records what was done; it must never stop a wrong draft from being deleted (28-Oct)
ignore_links_on_delete = ["SK Hub Log"]

has_permission = {
	"SK DSI Entry": "sk_app.permissions.own_or_manager",
	"SK Work Log": "sk_app.permissions.own_or_manager",
	"SK Day Report": "sk_app.permissions.own_or_manager",
	"CRM Lead": "sk_app.permissions.crm_record",
	"CRM Deal": "sk_app.permissions.crm_record",
}

# SK 27-Oct: in ERPNext / CRM too, a salesperson sees only their own leads and deals; Rushi sees his team's
permission_query_conditions = {
	"CRM Lead": "sk_app.permissions.crm_lead_query",
	"CRM Deal": "sk_app.permissions.crm_deal_query",
}

after_install = "sk_app.install.after_install"
after_migrate = "sk_app.install.after_migrate"

# point 20: logging in opens the app at once; after that it locks after SK App Settings → lock minutes without use
on_session_creation = "sk_app.applock.on_login"
