"""Home screen per function. Each person logs in with their own ERPNext user; SK App User.home picks the function.

Sales is the pilot and is fully live. Every other function already gets the common screens (My Day, Work Book,
DSI, Report Problem, My KPI) driven by their ERPNext tasks, and its own tiles are switched on in later phases.
"""

COMMON_TILES = ["my_day", "calendar", "reminders", "day_report", "work_book", "dsi", "problem", "my_kpi", "training"]
# free contact tiles: the phone's own dialer / WhatsApp / mail, logged in CRM; paid parts show locked inside them
CONTACT_TILES = ["calls", "whatsapp", "mail"]

FUNCTIONS = {
	"Sales": {
		"label": {"English": "Sales", "Marathi": "विक्री"},
		"tiles": ["my_day", "calendar", "follow_up", "new_lead", *CONTACT_TILES, "my_leads", "my_deals", "reminders", "library",
			"day_report", "my_kpi", "work_book", "dsi", "problem", "training"],
		"live": True,
		"erpnext_roles": ["Sales User", "Sales Manager"],
		"desk": "/crm",
	},
	"Marketing": {
		"label": {"English": "Marketing", "Marathi": "मार्केटिंग"},
		"tiles": ["my_day", "calendar", "follow_up", "new_lead", *CONTACT_TILES, "my_leads", "reminders", "library", "day_report",
			"my_kpi", "work_book", "dsi", "problem", "training"],
		"live": True,  # uses the same CRM lead screens as Sales
		"erpnext_roles": ["Sales User"],
		"desk": "/crm",
	},
	"Production": {
		"label": {"English": "Production", "Marathi": "उत्पादन"},
		"tiles": ["my_day", "order_board", "job_cards", "need_material", "progress_photos", "ready_dispatch", "non_conformance", *COMMON_TILES[1:]],
		"live": True,
		"erpnext_roles": ["Manufacturing User", "Manufacturing Manager"],
		"desk": "/app/manufacturing",
	},
	"Quality": {
		"label": {"English": "Quality", "Marathi": "गुणवत्ता"},
		"tiles": ["my_day", "inspect", "final_check", "non_conformance", "order_board", *COMMON_TILES[1:]],
		"live": True,
		"erpnext_roles": ["Quality Manager"],
		"desk": "/app/quality",
	},
	"Stores": {
		"label": {"English": "Stores", "Marathi": "स्टोअर"},
		# SK draft F01: My Day first, then the Store icons, then the common ones
		"tiles": ["my_day", "stock_check", "receive", "issue", "store_requests", "dispatch", "low_stock", "stock_count", "new_item", *COMMON_TILES[1:]],
		"live": True,
		# Stock Manager: needed to make stock count drafts and to pick accounts on receipts / delivery notes
		"erpnext_roles": ["Stock User", "Stock Manager"],
		"desk": "/app/stock",
	},
	"Purchase": {
		"label": {"English": "Purchase", "Marathi": "खरेदी"},
		"tiles": ["my_day", "buy_requests", "get_rates", "compare", "po_follow_up", "suppliers", "bills", "last_rates", "stock_check", *COMMON_TILES[1:]],
		"live": True,
		"erpnext_roles": ["Purchase User"],
		"desk": "/app/buying",
	},
	"Accounts": {
		"label": {"English": "Accounts", "Marathi": "लेखा"},
		# SK draft F06: My Day, the Finance icons, then calls / WhatsApp for collections and the common ones
		"tiles": ["my_day", "cash_today", "to_collect", "to_pay", "bills_to_post", "invoices", "expenses", "segment_pnl", "month_close",
			*CONTACT_TILES, *COMMON_TILES[1:]],
		"live": True,
		"erpnext_roles": ["Accounts User", "Accounts Manager"],
		"desk": "/app/accounting",
	},
	"HR": {
		"label": {"English": "HR", "Marathi": "एचआर"},
		"tiles": COMMON_TILES + ["logins", "team_scorecards"],
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
	"Subcontractor": {
		"label": {"English": "Production (subcontractor)", "Marathi": "उत्पादन (कंत्राटदार)"},
		# very simple screen (SK): own jobs only; job tiles come with the Production screens
		"tiles": ["my_day", "my_jobs", "need_material", "my_fixes", "problem", "training", "day_report"],
		"live": True,
		"erpnext_roles": ["SK Subcontractor"],
		"desk": "/sk",
	},
	"AI": {
		"label": {"English": "AI desk", "Marathi": "AI डेस्क"},
		"tiles": COMMON_TILES,
		"live": False,
		"erpnext_roles": ["Projects User"],
		"desk": "/app/todo",
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
		"tiles": ["ceo_view", "po_approvals", "pay_approvals", "cash_today", "segment_pnl", "team_reports", "logins", "calls", "my_day", "calendar", "reminders", "day_report", "my_kpi", "dsi", "problem",
			"library", "training"],
		"live": False,
		"erpnext_roles": ["System Manager", "Purchase Manager", "Purchase User"],  # SK approves big POs
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
	# a sales manager reviews the whole team's leads and deals next to his own (SK, 26-Oct-2026)
	if has_team and "my_leads" in home["tiles"] and "team_leads" not in home["tiles"]:
		i = home["tiles"].index("my_leads")
		home["tiles"] = home["tiles"][:i] + ["team_leads"] + home["tiles"][i:]
	# SK: My Day is always the first tile; DSI and the Day Report are the day's last jobs, so their tiles come last
	last = [t for t in ("dsi", "day_report") if t in home["tiles"]]
	middle = [t for t in home["tiles"] if t not in last and t != "my_day"]
	home = {**home, "tiles": ["my_day"] + middle + last}
	return home


# tiles every person gets whatever their function (SK): they appear once, in the "For everyone" row
SHARED_TILES = ["my_day", "calendar", "reminders", "calls", "whatsapp", "mail", "problem", "training", "library", "my_kpi",
	"work_book", "team_reports", "dsi", "day_report"]


def function_list(profile) -> list[str]:
	"""Main function first, then the other functions of the person (no repeats, unknown names dropped)."""
	names = [profile.get("home")] + [r.get("function") for r in (profile.get("functions") or [])]
	out = []
	for n in names:
		if n and n in FUNCTIONS and n not in out:
			out.append(n)
	return out


def sections_for(functions: list[str], has_team: bool = False) -> dict:
	"""Home for one or several functions (SK: a person in two functions sees both on one screen, no switching).
	Each function gets a labelled row of its own tiles; the shared tiles come once at the end, with
	My Day first and DSI / Day Report last as on the single-function Home."""
	if not functions:
		return {"sections": [], "shared": home_for(None, has_team)["tiles"]}
	homes = [home_for(f, has_team) for f in functions]
	sections, seen = [], set()
	for h in homes:
		own = [t for t in h["tiles"] if t not in SHARED_TILES and t not in seen]
		seen.update(own)
		sections.append({"function": h["function"], "label": h["label"], "tiles": own, "live": h["live"], "desk": h["desk"]})
	shared = []
	for h in homes:
		shared += [t for t in h["tiles"] if t in SHARED_TILES and t not in shared]
	last = [t for t in ("dsi", "day_report") if t in shared]
	shared = ["my_day"] + [t for t in shared if t not in last and t != "my_day"] + last
	return {"sections": sections, "shared": shared}
