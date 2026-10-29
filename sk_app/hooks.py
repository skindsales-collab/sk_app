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
app_include_js = ["/assets/sk_app/js/sk_tally_keys.js", "/assets/sk_app/js/sk_help_desk.js"]  # SK 28-Oct: ❓ help on every ERPNext page

# SK 27-Oct: standard cabin quotation print (SK's quote template), {{ sk_cabin_quote_html(doc) }}
# SK 28-Oct: "Post Tally invoices" button for Accounts (sk_app.tally_invoices)
doctype_list_js = {"Sales Invoice": "public/js/sales_invoice_list.js"}

# SK 29-Oct: GST tax invoice print with Bill to and Ship to, {{ sk_tax_invoice_html(doc) }}
jinja = {"methods": ["sk_app.cabin_quote.sk_cabin_quote_html", "sk_app.tax_invoice.sk_tax_invoice_html"]}

scheduler_events = {
	"hourly": ["sk_app.deal_quotes.sync", "sk_app.guide.hourly", "sk_app.day_report.auto_reports", "sk_app.activities.noon_nudge", "sk_app.mailbox.remind"],
	# IndiaMART / JustDial / GeM mails to the team mailboxes become CRM leads (free route, point 14)
	"cron": {"*/5 * * * *": ["sk_app.lead_sources.scan", "sk_app.mailbox.link_known", "sk_app.mailbox.route_suppliers", "sk_app.mailbox.auto_leads"],
		# SK 27-Oct: the AI's actions to lift each graph, every morning before work
		"0 7 * * *": ["sk_app.ai_actions.morning"],
		# SK 28-Oct: customers tagged Cabin / Non-Cabin and every order and customer given its salesperson
		"30 1 * * *": ["sk_app.sales_owner.nightly"],
		# SK 29-Oct: a solved desk request the person did not answer for 3 days is closed
		"0 2 * * *": ["sk_app.issue_desk.auto_close"]},
}

doc_events = {
	"SK DSI Entry": {"before_insert": "sk_app.permissions.stamp_user"},
	"SK Work Log": {"before_insert": "sk_app.permissions.stamp_user"},
	"SK Day Report": {"before_insert": "sk_app.permissions.stamp_user"},
	"File": {"after_insert": ["sk_app.crm.on_file_attached", "sk_app.deal_quotes.on_file"]},  # SK 28-Oct: a quote file → Quotation
	"SK Library Item": {"validate": "sk_app.library.make_public"},
	# SK 28-Oct mandatory gate: a lead / deal moves on only with its data and the step's ERPNext document (sk_app.gates)
	"CRM Lead": {"validate": ["sk_app.segments.set_main", "sk_app.gates.check_crm"]},
	"CRM Deal": {"validate": ["sk_app.segments.set_main", "sk_app.crm.set_deal_customer", "sk_app.gates.check_crm"],
		"on_update": "sk_app.deal_quotes.on_deal_update"},
	"Quotation": {"before_submit": "sk_app.gates.check_quotation"},
	"Customer": {"before_insert": "sk_app.segments.customer_group_from_deal", "on_update": "sk_app.segments.on_customer_update"},
	# SK 28-Oct: every order has its salesperson; income ledger and Non-Cabin sub-group cost centre from the customer
	"Sales Order": {"validate": ["sk_app.sales_owner.fill_order_team", "sk_app.segment_accounts.set_segment"],
		"before_submit": "sk_app.gates.check_sales_order",
		"on_submit": "sk_app.won_deals.on_submit"},  # SK 28-Oct: its lead / deal shows Won in the CRM at once
	# SK 29-Oct (Shraddha): a tax invoice is submitted only with the buyer's Bill to address (Ship to defaults to it)
	"Sales Invoice": {"validate": ["sk_app.segment_accounts.set_segment", "sk_app.cabin_projects.set_cost_centre"],
		"before_submit": "sk_app.gates.check_sales_invoice"},
	"SK App User": {"on_update": ["sk_app.segments.on_app_user_update", "sk_app.logins.set_company_default"]},
	"Job Card": {"validate": "sk_app.store.set_job_card_cabin"},  # SK 27-Oct: customer + cabin size, not just the number
	# SK 29-Oct: one Project + cost centre per cabin; its material, bills and sales rows go to that cost centre at once,
	# and stages done before ERPNext close when the cabin's Work Order is submitted (sk_app.cabin_projects)
	"Work Order": {"on_submit": "sk_app.cabin_projects.close_done_stages"},
	"Stock Entry": {"validate": "sk_app.cabin_projects.set_cost_centre"},
	"Delivery Note": {"validate": "sk_app.cabin_projects.set_cost_centre"},
	# SK 27-Oct purchase flow: requisition → CEO approval → PO → receipt against the PO, in ERPNext too
	"Material Request": {"validate": ["sk_app.gates.check_request", "sk_app.cabin_projects.set_cost_centre"], "before_submit": "sk_app.requisition.check_submit"},
	"Purchase Order": {"validate": "sk_app.cabin_projects.set_cost_centre", "before_submit": "sk_app.requisition.check_po"},
	"Purchase Receipt": {"validate": "sk_app.cabin_projects.set_cost_centre", "before_submit": "sk_app.requisition.check_receipt"},
	# SK 28-Oct: subcontractor bills post only after Rushi + CEO; only CEO / Accounts change the rate sheet
	"Purchase Invoice": {"validate": "sk_app.cabin_projects.set_cost_centre", "before_submit": "sk_app.sub_bills.check_submit"},
	"Item Price": {"validate": "sk_app.sub_bills.check_rate_edit"},
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
