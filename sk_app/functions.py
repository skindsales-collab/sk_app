"""Home screen per function. Each person logs in with their own ERPNext user; SK App User.home picks the function.

Sales is the pilot and is fully live. Every other function already gets the common screens (My Day, Work Book,
DSI, Report Problem, My KPI) driven by their ERPNext tasks, and its own tiles are switched on in later phases.
"""

COMMON_TILES = ["my_day", "calendar", "day_report", "work_book", "dsi", "problem", "my_kpi", "training"]

FUNCTIONS = {
	"Sales": {
		"label": {"English": "Sales", "Marathi": "विक्री"},
		"tiles": ["my_day", "calendar", "follow_up", "new_lead", "my_leads", "my_deals", "day_report", "my_kpi", "work_book", "dsi", "problem", "training"],
		"live": True,
		"erpnext_roles": ["Sales User", "Sales Manager"],
		"desk": "/crm",
	},
	"Marketing": {
		"label": {"English": "Marketing", "Marathi": "मार्केटिंग"},
		"tiles": ["my_day", "calendar", "follow_up", "new_lead", "my_leads", "day_report", "my_kpi", "work_book", "dsi", "problem", "training"],
		"live": True,  # uses the same CRM lead screens as Sales
		"erpnext_roles": ["Sales User"],
		"desk": "/crm",
	},
	"Production": {
		"label": {"English": "Production", "Marathi": "उत्पादन"},
		"tiles": COMMON_TILES + ["job_cards"],
		"live": False,
		"erpnext_roles": ["Manufacturing User"],
		"desk": "/app/manufacturing",
	},
	"Quality": {
		"label": {"English": "Quality", "Marathi": "गुणवत्ता"},
		"tiles": COMMON_TILES + ["inspections"],
		"live": False,
		"erpnext_roles": ["Quality Manager"],
		"desk": "/app/quality",
	},
	"Stores": {
		"label": {"English": "Stores", "Marathi": "स्टोअर"},
		"tiles": COMMON_TILES + ["stock_alerts"],
		"live": False,
		"erpnext_roles": ["Stock User"],
		"desk": "/app/stock",
	},
	"Purchase": {
		"label": {"English": "Purchase", "Marathi": "खरेदी"},
		"tiles": COMMON_TILES + ["material_requests"],
		"live": False,
		"erpnext_roles": ["Purchase User"],
		"desk": "/app/buying",
	},
	"Accounts": {
		"label": {"English": "Accounts", "Marathi": "लेखा"},
		"tiles": COMMON_TILES + ["invoice_photo", "collections"],
		"live": False,
		"erpnext_roles": ["Accounts User"],
		"desk": "/app/accounting",
	},
	"HR": {
		"label": {"English": "HR", "Marathi": "एचआर"},
		"tiles": COMMON_TILES + ["team_scorecards"],
		"live": False,
		"erpnext_roles": ["HR User", "HR Manager"],
		"desk": "/app/hr",
	},
	"Machine Shifting": {
		"label": {"English": "Machine Shifting", "Marathi": "मशीन शिफ्टिंग"},
		"tiles": COMMON_TILES + ["my_deals", "site_checklist"],
		"live": False,
		"erpnext_roles": ["Projects User", "Sales User"],
		"desk": "/crm",
	},
	"Design": {
		"label": {"English": "Design", "Marathi": "डिझाईन"},
		"tiles": COMMON_TILES + ["my_deals"],
		"live": False,
		"erpnext_roles": ["Projects User"],
		"desk": "/app/projects",
	},
	"IT / ERP": {
		"label": {"English": "IT / ERP", "Marathi": "आयटी / ईआरपी"},
		"tiles": COMMON_TILES,
		"live": False,
		"erpnext_roles": ["System Manager"],
		"desk": "/app",
	},
	"Management": {
		"label": {"English": "Management (CEO)", "Marathi": "व्यवस्थापन (CEO)"},
		"tiles": ["ceo_view", "team_reports", "my_day", "calendar", "day_report", "my_kpi", "dsi", "problem", "training"],
		"live": False,
		"erpnext_roles": ["System Manager"],
		"desk": "/app",
	},
}


def home_for(function: str | None, has_team: bool = False) -> dict:
	"""Home definition for a function; unknown or blank falls back to the common screens.
	Anyone who manages a team also gets the Team Reports tile (daily Day Reports of their people)."""
	spec = FUNCTIONS.get(function or "")
	if spec:
		home = {"function": function, **spec}
	else:
		home = {"function": function or "", "label": {"English": function or "My Work"}, "tiles": COMMON_TILES,
			"live": False, "erpnext_roles": [], "desk": "/app"}
	if has_team and "team_reports" not in home["tiles"]:
		home["tiles"] = home["tiles"][:1] + ["team_reports"] + home["tiles"][1:]
	return home
