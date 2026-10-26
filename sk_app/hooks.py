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

scheduler_events = {
	"hourly": ["sk_app.guide.hourly"],
	# IndiaMART / JustDial / GeM mails to the team mailboxes become CRM leads (free route, point 14)
	"cron": {"*/5 * * * *": ["sk_app.lead_sources.scan"]},
}

doc_events = {
	"SK DSI Entry": {"before_insert": "sk_app.permissions.stamp_user"},
	"SK Work Log": {"before_insert": "sk_app.permissions.stamp_user"},
	"SK Day Report": {"before_insert": "sk_app.permissions.stamp_user"},
	"File": {"after_insert": "sk_app.crm.on_file_attached"},
	"SK Library Item": {"validate": "sk_app.library.make_public"},
}

has_permission = {
	"SK DSI Entry": "sk_app.permissions.own_or_manager",
	"SK Work Log": "sk_app.permissions.own_or_manager",
	"SK Day Report": "sk_app.permissions.own_or_manager",
}

after_install = "sk_app.install.after_install"
after_migrate = "sk_app.install.after_migrate"
