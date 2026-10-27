"""Home screen per function. Each person logs in with their own ERPNext user; SK App User.home picks the function.

Sales is the pilot and is fully live. Every other function already gets the common screens (My Day, Work Book,
DSI, Report Problem, My KPI) driven by their ERPNext tasks, and its own tiles are switched on in later phases.
"""

# SK 26-Oct (point 10): Work Book is part of My Day now ("I did extra work"), so it has no icon of its own
# point 15 (SK 26-Oct): My Calendar is inside My Day (Today / Week / Month tabs), so it has no icon of its own
COMMON_TILES = ["my_day", "reminders", "day_report", "dsi", "problem", "my_kpi", "training"]
# free contact tiles: the phone's own dialer / WhatsApp / mail, logged in CRM; paid parts show locked inside them
CONTACT_TILES = ["calls", "whatsapp", "mail"]
# point 13: the CEO's live dashboards, one icon per function (sk_app.dashboards.PAGES)
DASH_TILES = ["dash_overview", "dash_daily_review", "dash_sales", "dash_marketing", "dash_machine_shifting", "dash_job_work",
	"dash_finance", "dash_manufacturing", "dash_purchase", "dash_store", "dash_quality", "dash_hr", "dash_ai", "dash_cr100"]

FUNCTIONS = {
	"Sales": {
		"label": {"English": "Sales", "Marathi": "विक्री"},
		# point 17 (SK's mock-up 26-Oct): own icons in work order New Lead → My Leads → My Deals → Customers → Follow-up → Complaints
		"tiles": ["my_day", "new_lead", "my_leads", "cold_calls", "marketing_list", "my_deals", "customers", "follow_up", "complaints", *CONTACT_TILES, "activities", "reminders", "library",
			"day_report", "my_kpi", "dsi", "problem", "training"],
		"live": True,
		# not Sales Manager: in Frappe CRM that role shows every lead of the company (SK 26-Oct: each salesperson sees
		# only their own; the sales manager sees his team on the Team Leads icon)
		"erpnext_roles": ["Sales User"],
		"desk": "/crm",
	},
	"Marketing": {
		"label": {"English": "Marketing", "Marathi": "मार्केटिंग"},
		"tiles": ["my_day", "new_lead", "my_leads", "cold_calls", "marketing_list", "follow_up", "complaints", *CONTACT_TILES, "activities", "reminders", "library", "day_report",
			"my_kpi", "dsi", "problem", "training"],
		"live": True,  # uses the same CRM lead screens as Sales
		"erpnext_roles": ["Sales User"],
		"desk": "/crm",
	},
	"Production": {
		"label": {"English": "Production", "Marathi": "उत्पादन"},
		# point 17 (SK's mock-up): Need Material → Job Cards → Order Board → Progress Photos → Ready to Dispatch → Non-Conformance
		"tiles": ["my_day", "to_plan", "need_material", "job_cards", "order_board", "progress_photos", "ready_dispatch", "non_conformance", "complaints", *COMMON_TILES[1:]],
		"live": True,
		"erpnext_roles": ["Manufacturing User", "Manufacturing Manager"],
		"desk": "/app/manufacturing",
	},
	"Quality": {
		"label": {"English": "Quality", "Marathi": "गुणवत्ता"},
		"tiles": ["my_day", "inspect", "final_check", "non_conformance", "el_points", "order_board", "complaints", *COMMON_TILES[1:]],
		"live": True,
		"erpnext_roles": ["Quality Manager"],
		"desk": "/app/quality",
	},
	"Stores": {
		"label": {"English": "Stores", "Marathi": "स्टोअर"},
		# SK draft F01: My Day first, then the Store icons, then the common ones
		# point 17 (SK's mock-up): Requests → Stock Check → Receive → Issue → Stock Count → New Item → Low Stock → Dispatch
		"tiles": ["my_day", "store_requests", "stock_check", "receive", "issue", "stock_count", "new_item", "low_stock", "dispatch", "complaints", *COMMON_TILES[1:]],
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
		# SK / Shraddha 26-Oct: ledger-wise screens; Expenses is the Journal Voucher list, plus Direct and Indirect Expenses
		# SK 27-Oct: the team knows Tally, so Accounts opens on the Accounts Gateway (Gateway of Tally sections and names)
		# SK 27-Oct: every entry can start from a photo of the bill / e-invoice / voucher / payment proof (Photo entry)
		"tiles": ["my_day", "gateway", "photo_entry", "day_book", "cash_today", "to_collect", "to_pay", "bills_to_post", "invoices", "expenses", "dir_expenses",
			"segment_pnl", "month_close", "new_product", "complaints",
			*CONTACT_TILES, *COMMON_TILES[1:]],
		"live": True,
		"erpnext_roles": ["Accounts User", "Accounts Manager"],
		"desk": "/app/accounts-gateway",
	},
	"HR": {
		"label": {"English": "HR", "Marathi": "एचआर"},
		# point 16 + HR draft Rev 2: Attendance (Optick file upload, today, month, fixes); leave and expense approvals
		# point 20 (SK 26-Oct): Logins / Reset PIN are the CEO's only, so HR has no Logins icon any more
		"tiles": COMMON_TILES[:1] + ["attendance", "new_joiner"] + COMMON_TILES[1:] + ["team_scorecards", "mail"],
		"live": True,
		"erpnext_roles": ["HR User", "HR Manager"],
		"desk": "/app/hr",
	},
	"Machine Shifting": {
		"label": {"English": "Machine Shifting", "Marathi": "मशीन शिफ्टिंग"},
		"tiles": COMMON_TILES + ["my_deals", "customers", "complaints", "site_checklist"],
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
		"tiles": ["my_day", "my_jobs", "el_points", "need_material", "my_fixes", "problem", "training", "day_report", "dsi", "my_kpi"],
		"live": True,
		"erpnext_roles": ["SK Subcontractor"],
		"desk": "/sk",
	},
	"AI": {
		# SK 26-Oct: Samir's desk. Main job ERP implementation, plus technology improvements in every department
		"label": {"English": "AI & ERP", "Marathi": "AI आणि ERP"},
		"tiles": ["my_day", "improvement_inbox", "dept_visits", "erp_gaps", "app_users", "lead_sources", "change_list", "projects", "complaints",
			"training_progress", "erpnext_desk", *COMMON_TILES[1:]],
		"live": True,
		"erpnext_roles": ["Projects User", "Projects Manager"],
		"desk": "/app/project",
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
		"tiles": [*DASH_TILES, "leadership", "view_member", "attendance", "lead_sources", "customers", "sales_owner", "complaints", "po_approvals", "pay_approvals", "cabin_discounts", "cash_today", "segment_pnl", "team_reports", "logins", "calls", "mail", "my_day", "reminders", "day_report", "my_kpi", "dsi", "problem",
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
	# SK 27-Oct: the sales manager says who sells to each customer (Tally sale on each graph)
	if has_team and "my_leads" in home["tiles"] and "sales_owner" not in home["tiles"]:
		home["tiles"] = home["tiles"] + ["sales_owner"]
	# a manager opens each team member's full app, as the CEO does for everyone (Rushi, SK 26-Oct-2026)
	if has_team and "view_member" not in home["tiles"]:
		home["tiles"] = home["tiles"] + ["view_member"]
	# HR draft Rev 2: everyone applies for leave and claims expenses (managers approve there); not subcontractors
	if (function or "") != "Subcontractor" and "leave_expense" not in home["tiles"]:
		home["tiles"] = home["tiles"] + ["leave_expense"]
	# SK: My Day is always the first tile; DSI and the Day Report are the day's last jobs, so their tiles come last
	last = [t for t in ("dsi", "day_report") if t in home["tiles"]]
	middle = [t for t in home["tiles"] if t not in last and t != "my_day"]
	home = {**home, "tiles": ["my_day"] + middle + last}
	return home


# tiles every person gets whatever their function (SK): they appear once, in the "For everyone" row
SHARED_TILES = ["my_day", "reminders", "calls", "whatsapp", "mail", "problem", "training", "library", "my_kpi",
	"team_reports", "leave_expense", "dsi", "day_report"]


def function_list(profile) -> list[str]:
	"""Main function first, then the other functions of the person (no repeats, unknown names dropped)."""
	names = [profile.get("home")] + [r.get("function") for r in (profile.get("functions") or [])]
	out = []
	for n in names:
		if n and n in FUNCTIONS and n not in out:
			out.append(n)
	return out


# SK 26-Oct: "main screen should not be long, only essentials; the rest on a second / third screen in a logical
# sequence; applicable on each screen". Level 1 = function icons (or, for one function, its flow + these few
# icons), level 2 = the function page, level 3 = "More" with the rest in groups. Order = the order the work goes.
MAIN_TILES = {
	# main screen Rev 2 (SK 26-Oct): four own icons; a sales manager gets Team Leads in place of My Deals
	"Sales": ["new_lead", "my_leads", "follow_up", "team_leads", "my_deals"],
	"Marketing": ["new_lead", "my_leads", "follow_up", "my_deals"],
	"Machine Shifting": ["my_deals", "customers", "site_checklist", "complaints"],
	"Production": ["to_plan", "job_cards", "need_material", "order_board"],
	"Quality": ["inspect", "final_check", "non_conformance", "el_points"],
	"Stores": ["store_requests", "receive", "issue", "stock_count"],
	"Purchase": ["buy_requests", "get_rates", "po_follow_up", "bills"],
	"Accounts": ["gateway", "to_collect", "to_pay", "day_book"],
	# SK 26-Oct: attendance is not on the main screen (it is in More)
	"HR": ["leave_expense", "team_scorecards"],
	"Subcontractor": ["my_jobs", "el_points", "need_material", "my_fixes"],
	"AI": ["improvement_inbox", "erp_gaps", "app_users", "dept_visits"],
	# the CEO's first screen = overview, approvals, team; the other dashboards and Leadership are in More (SK 26-Oct)
	"Management": ["dash_overview", "po_approvals", "pay_approvals", "view_member"],
}
MAIN_COUNT = 4
# main screen Rev 2 (SK 26-Oct): every main screen has the same common row, the Call / WhatsApp / Mail row and
# My Day + DSI at the bottom (with More); Attendance, Leadership, Training and the Product library are in More
MAIN_COMMON = ["day_report", "my_kpi", "reminders", "problem"]
MAIN_CONTACT = ["calls", "whatsapp", "mail"]
MAIN_SHARED = ["my_day", "dsi"]
# level 3 "More": the shared tiles in groups, in the order of a working day
SHARED_GROUPS = [
	("grp_work", ["team_reports", "leave_expense"]),
	("grp_me", ["training", "library"]),
]


def split_main(function: str, tiles: list[str]) -> tuple[list[str], list[str]]:
	"""(main, more) of a function's own tiles: the essentials first in the function's order, the rest in theirs.
	Functions without a list keep their first four on the main screen."""
	want = MAIN_TILES.get(function)
	main = ([t for t in want if t in tiles] if want else tiles)[:MAIN_COUNT]
	return main, [t for t in tiles if t not in main]


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
		main, more = split_main(h["function"], own)
		sections.append({"function": h["function"], "label": h["label"], "tiles": own, "main": main, "more": more,
			"live": h["live"], "desk": h["desk"]})
	shared = []
	for h in homes:
		shared += [t for t in h["tiles"] if t in SHARED_TILES and t not in shared]
	last = [t for t in ("dsi", "day_report") if t in shared]
	shared = ["my_day"] + [t for t in shared if t not in last and t != "my_day"] + last
	on_main = set(MAIN_SHARED + MAIN_COMMON + MAIN_CONTACT)
	grouped = [(g, [t for t in keys if t in shared and t not in on_main]) for g, keys in SHARED_GROUPS]
	rest = [t for t in shared if t not in on_main and not any(t in keys for _g, keys in grouped)]
	if rest:
		grouped[0] = (grouped[0][0], grouped[0][1] + rest)
	return {"sections": sections, "shared": shared, "main_shared": [t for t in MAIN_SHARED if t in shared],
		"main_common": [t for t in MAIN_COMMON if t in shared], "main_contact": MAIN_CONTACT,
		"more_groups": [{"group": g, "tiles": keys} for g, keys in grouped if keys]}


# Fixed work in each function's week (change list point 9c; 26-Oct also the daily checklists of the manuals). The week planner puts these first and fills
# the rest of each day's free hours with open work. days: Mon..Sat or "daily"; at: "HH:MM" or None (any time that day).
ROUTINE = {
	"Sales": [("Mon", "10:00", 60, "Team meeting (Rushi)"), ("daily", "09:30", 30, "Call today's new leads first"),
		("Tue Wed Thu Fri", None, 120, "Customer visits"), ("Sat", "16:00", 60, "Weekly report + pipeline review")],
	"Marketing": [("daily", "09:30", 30, "Call today's new leads first"), ("daily", "10:00", 20, "GeM: new cabin tenders"),
		("daily", None, 30, "IndiaMART / JustDial: answer new enquiries in 5 minutes"),
		("Sat", "12:00", 30, "Google Business: 3 site photos + review links"), ("Sat", "16:00", 60, "Weekly report + pipeline review")],
	"Machine Shifting": [("Mon", "09:30", 60, "Jobs plan for the week"), ("Tue Thu", None, 120, "Site surveys"),
		("Sat", "16:00", 60, "Weekly report")],
	"Stores": [("daily", "09:30", 30, "Receipts and issues"), ("Wed", "11:00", 30, "Low-stock list to Purchase"),
		("Sat", "15:00", 60, "Stock count (one rack)"), ("daily", "15:00", 15, "5S (15 minutes)")],
	"Purchase": [("daily", "09:30", 30, "Today's buy requests"), ("Thu", "11:00", 60, "Rate comparison"),
		("Fri", "11:00", 60, "PO follow-up calls")],
	"Production": [("daily", "09:15", 15, "Job plan for the day"), ("Mon", "09:30", 30, "Capacity vs orders, contractor plan"),
		("daily", "15:00", 15, "5S (15 minutes)"), ("Fri", "15:00", 45, "Dispatch plan")],
	"Subcontractor": [("daily", "15:00", 15, "5S (15 minutes)")],
	"Quality": [("daily", "09:15", 15, "Job plan for the day"), ("daily", "16:00", 30, "Final checks before dispatch"),
		("daily", "15:00", 15, "5S (15 minutes)"), ("Wed", "11:00", 30, "Top 3 defects with root cause")],
	"Accounts": [("daily", "10:00", 45, "Collection calls"), ("Mon", "11:00", 45, "Payments plan for the week"),
		("Fri", "15:00", 60, "Bank reconciliation"), ("Fri", "16:00", 30, "Friday cash statement")],
	"HR": [("daily", "09:45", 30, "Attendance check"), ("Mon", "11:00", 30, "Training lesson for one function"), ("Fri", "15:00", 60, "Leave and expense approvals")],
	"AI": [("daily", "09:30", 30, "Improvement Inbox sorting"),
		("Mon", "11:00", 150, "Department visit: Sales & Marketing (leads, quotes, CRM data)"),
		("Tue", "11:00", 150, "Department visit: Store & Purchase (receipts, stock, POs, suppliers)"),
		("Wed", "11:00", 150, "Department visit: Production, subcontractors, Quality"),
		("Thu", "11:00", 150, "Department visit: Finance & HR (bills, payments, attendance, leave)"),
		("Fri", "11:00", 150, "ERP data clean-up + test new app changes on sk-dev"),
		("Sat", "11:00", 90, "Review with SK + weekly report")],
	"Management": [("daily", "09:30", 10, "Dashboard: orders, quotes, dispatch, cash"), ("Mon", "10:00", 60, "Sales team meeting"),
		("Wed", "11:00", 60, "Factory + dispatch review"), ("Fri", "16:00", 30, "Cash review"), ("Sat", "11:00", 90, "Weekly review (AI & ERP report)")],
}
