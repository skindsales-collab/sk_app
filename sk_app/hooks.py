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
app_include_js = "/assets/sk_app/js/sk_tally_keys.js"

# SK 27-Oct: standard cabin quotation print (SK's quote template), {{ sk_cabin_quote_html(doc) }}
jinja = {"methods": ["sk_app.cabin_quote.sk_cabin_quote_html"]}

scheduler_events = {
	"hourly": ["sk_app.guide.hourly", "sk_app.day_report.auto_reports", "sk_app.activities.noon_nudge"],
	# IndiaMART / JustDial / GeM mails to the team mailboxes become CRM leads (free route, point 14)
	"cron": {"*/5 * * * *": ["sk_app.lead_sources.scan"],
		# SK 27-Oct: the AI's actions to lift each graph, every morning before work
		"0 7 * * *": ["sk_app.ai_actions.morning"]},
}

doc_events = {
	"SK DSI Entry": {"before_insert": "sk_app.permissions.stamp_user"},
	"SK Work Log": {"before_insert": "sk_app.permissions.stamp_user"},
	"SK Day Report": {"before_insert": "sk_app.permissions.stamp_user"},
	"File": {"after_insert": "sk_app.crm.on_file_attached"},
	"SK Library Item": {"validate": "sk_app.library.make_public"},
	"CRM Lead": {"validate": "sk_app.segments.set_main"},
	"CRM Deal": {"validate": ["sk_app.segments.set_main", "sk_app.crm.set_deal_customer"]},
	"Customer": {"before_insert": "sk_app.segments.customer_group_from_deal"},
	"SK App User": {"on_update": "sk_app.segments.on_app_user_update"},
	"Job Card": {"validate": "sk_app.store.set_job_card_cabin"},  # SK 27-Oct: customer + cabin size, not just the number
}

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
