"""One KPI chart against target on top of every main screen (SK 26-Oct-2026, main screen Rev 2).

"everyone have graphical one important kpi on main screen in chart against target" · "all graph is need in sale way,
month to month tracking in progressive way, it help to know improvement is there or not, trend monitoring".

Sales people see their orders, the CEO two lines (order booking and invoicing, SK 26-Oct): amount up the side, week by
week this month or month by month along the bottom. Every other function sees its KPI month by month (last 7 months) against its target, so a
better or worse trend shows at once. Everything is read live from ERPNext; a month with no data stays empty and the
card says what has to be entered in ERPNext for it to fill.

Under it the "Decide now" strip (SK 26-Oct: "data needed for taking decisions on main screen, same for others") is
made on the phone from this chart (gap to target) and the live flow (the three most delayed stages).
"""

import re

import frappe
from frappe.utils import add_days, add_months, date_diff, flt, get_first_day, get_last_day, getdate, nowdate

from sk_app import dashboards, segments
from sk_app.dashboards import _safe

MONTHS = 7
# targets SK gave or the change list proposed (SK to confirm the ones marked "proposed"); Sales targets come from SK KPI Target
COMPANY_TARGET = 9920000  # Rs 99.2 L a month, all salespeople together (SK 25-Oct), used when no SK KPI Target is set
TARGETS = {
	"Production": 4,  # days to build 100 sq ft (proposed)
	"Accounts": 100,  # % of finished, invoiced projects whose material is posted to the project (SK 26-Oct)
	"HR": 30,  # days to recruit (proposed)
	"Stores": 99,  # stock accuracy % (proposed)
	"Quality": 95,  # first-time pass % (proposed)
	"Purchase": 90,  # POs received on time % (proposed)
	"AI": 20,  # ERP tasks finished a month (proposed)
	"Subcontractor": 20,  # jobs finished a month (proposed)
}
# cabin size in the item name: "12x10", "12 ft x 10 ft", "12' X 10'", "3000 x 2400" (mm)
SIZE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:ft|feet|'|’|mm)?\s*[xX×*]\s*(\d+(?:\.\d+)?)")


def _months():
	"""The last MONTHS months, oldest first: (label, first day, last day)."""
	this = get_first_day(getdate())
	out = []
	for i in range(MONTHS - 1, -1, -1):
		start = add_months(this, -i)
		out.append((start.strftime("%b"), start, get_last_day(start)))
	return out


# ---------- Day / Week / Month (SK 27-Oct: "along with weekly / month, pl add daily & split target accordingly",
# "this will do for everyone"): the month target is split over the working days, Monday to Saturday less the
# company's festival holidays (e.g. Rs 99.2 L / 26 days = Rs 3.8 L a day); a week's target = daily × its working days.

DAYS_SHOWN = 10  # working days on the Day view
WEEKS_SHOWN = 6


def _holidays(start, end) -> set:
	"""Festival holidays (any holiday list; Sundays are off anyway), read once per request."""
	every = getattr(frappe.local, "sk_festivals", None)
	if every is None:
		every = frappe.local.sk_festivals = {getdate(d) for d in frappe.get_all("Holiday", filters={"weekly_off": 0}, pluck="holiday_date")} \
			if frappe.db.exists("DocType", "Holiday") else set()
	start, end = getdate(start), getdate(end)
	return {d for d in every if start <= d <= end}


def working_days(start, end, off=None) -> int:
	"""Mon-Sat days from start to end (both included), less festival holidays."""
	start, end = getdate(start), getdate(end)
	off = _holidays(start, end) if off is None else off
	n, d = 0, start
	while d <= end:
		if d.weekday() < 6 and d not in off:
			n += 1
		d = add_days(d, 1)
	return n


def _month_days(day) -> int:
	first = get_first_day(day)
	return working_days(first, get_last_day(first)) or 1


def _days_back(today=None):
	"""The last DAYS_SHOWN working days up to today, oldest first: (label, day, day)."""
	today = getdate(today or nowdate())
	off = _holidays(add_days(today, -40), today)
	out, d = [], today
	while len(out) < DAYS_SHOWN:
		if d.weekday() < 6 and d not in off:
			out.append((d.strftime("%d"), d, d))
		d = add_days(d, -1)
	return out[::-1]


def _weeks_back(today=None):
	"""The last WEEKS_SHOWN weeks (Monday to Sunday) up to today, oldest first: (label, Monday, Sunday or today)."""
	today = getdate(today or nowdate())
	monday = add_days(today, -today.weekday())
	out = []
	for i in range(WEEKS_SHOWN - 1, -1, -1):
		s = add_days(monday, -7 * i)
		out.append((s.strftime("%d/%m"), s, min(add_days(s, 6), today)))
	return out


def split_target(target, start, end) -> float:
	"""The share of a monthly target for these days: daily (target / working days of the month) × working days."""
	return flt(target) * working_days(start, end) / _month_days(start)


def _trend(fn, title, unit, target, value_of, good_low=False, need="", count=False):
	"""count: a number per period (jobs, tasks), so the Day / Week target is the month target split; otherwise a rate
	(days, %), whose target is the same for a day, a week and a month."""
	def pts(periods, per_period_target):
		return [{"m": m, "v": _safe(lambda s=s, e=e: value_of(s, e), None),
			"t": round(split_target(target, s, e), 1) if per_period_target else target} for m, s, e in periods]
	points = pts(_months(), False)
	return {"kind": "trend", "function": fn, "title": title, "unit": unit, "target": target, "good_low": good_low,
		"points": points, "day": pts(_days_back(), count), "week": pts(_weeks_back(), count),
		"need": "" if any(p["v"] is not None for p in points) else need}


def sq_ft(name: str | None) -> float:
	"""Cabin floor area from its item name; sizes over 100 are taken as mm."""
	m = SIZE.search(name or "")
	if not m:
		return 0.0
	a, b = flt(m.group(1)), flt(m.group(2))
	if a > 100 and b > 100:
		a, b = a / 304.8, b / 304.8
	return round(a * b, 1)


# ---------- money: Sales, Non-Cabin, CEO ----------
# SK 26-Oct: "vertical - amount, horizontal - week-wise / month-wise": Week = this month week by week (running total
# against the target line), Month = the last months side by side against the monthly target.

def _weeks(start, today):
	"""(label, first day, last day) of each week of the month up to today: days 1-7, 8-14, ..."""
	end = get_last_day(start)
	out, d = [], start
	while d <= today:
		last = min(add_days(d, 6), end)
		out.append((f"W{len(out) + 1}", d, last))
		d = add_days(last, 1)
	return out


def _money_card(fn, title, line_specs, target):
	"""line_specs: [(label, colour, amount_of(start, end))]. Both views are built for the same lines."""
	today, start = getdate(), get_first_day(getdate())
	weeks = _weeks(start, today)
	week_lines, month_lines = [], []
	for label, c, amount_of in line_specs:
		run, pts = 0.0, []
		for _w, s, e in weeks:
			run += flt(_safe(lambda s=s, e=e: amount_of(s, min(e, today)), 0))
			pts.append(round(run))
		week_lines.append({"label": label, "c": c, "points": pts})
		month_lines.append({"label": label, "c": c, "points": [round(flt(_safe(lambda s=s, e=e: amount_of(s, e), 0))) for _m, s, e in _months()]})
	days = _days_back()
	day_lines = [{"label": label, "c": c, "points": [round(flt(_safe(lambda s=s, e=e: amount_of(s, e), 0))) for _d, s, e in days]}
		for label, c, amount_of in line_specs]
	wd_month = _month_days(start)
	return {"kind": "money", "function": fn, "title": title, "unit": "Rs", "target": target,
		"daily_target": round(flt(target) / wd_month),
		# running total this month against the target split over the working days so far
		"week": {"labels": [w[0] for w in weeks], "target": [round(split_target(target, start, e)) for _w, _s, e in weeks], "lines": week_lines},
		"day": {"labels": [d[0] for d in days], "target": [round(split_target(target, s, e)) for _d, s, e in days], "lines": day_lines},
		"month": {"labels": [m[0] for m in _months()], "lines": month_lines}}


def _sales_target(users) -> float:
	filters = {"active": 1, "kpi_code": ["in", ["orders_value", "digital_orders_value"]]}
	if users is not None:
		filters["user"] = ["in", users or [""]]
	return sum(flt(t) for t in frappe.get_all("SK KPI Target", filters=filters, pluck="monthly_target"))


def _orders_value(owners, segment=None):
	"""Orders (drafts count, DEC-013) between two dates: everyone's, or credited to these people / created by them."""
	from sk_app.kpi import user_sales_orders

	def amount(start, end):
		orders = dashboards._orders(start, end, segment)
		if owners is not None:
			mine = set()
			for o in owners:
				mine.update(user_sales_orders(o, start, end))
			drafts = set(frappe.get_all("Sales Order", filters={"docstatus": 0, "owner": ["in", owners], "transaction_date": ["between", [start, end]]}, pluck="name"))
			# draft orders are real orders too (DEC-013): credit them by their Sales Team row like posted ones
			persons = [p for o in owners for p in _sales_persons(o)]
			if persons:
				drafts.update(frappe.get_all("Sales Team", filters={"parenttype": "Sales Order", "sales_person": ["in", persons],
					"parent": ["in", [s.name for s in orders] or [""]]}, pluck="parent"))
			orders = [s for s in orders if s.name in mine or s.name in drafts]
		return sum(flt(s.base_net_total) for s in orders)
	return amount


def _sales_persons(user):
	from sk_app.kpi import _sales_persons as persons

	return persons(user)


def _invoiced(start, end):
	return dashboards._invoiced(start, end)


def sales(user: str, segment=None, fn="Sales") -> dict:
	from sk_app.flows import _owners

	owners = _owners(user)
	if segment == segments.NON_CABIN:
		owners = None  # Aditya handles every Non-Cabin order (SK 26-Oct)
	title = "Non-Cabin sale" if segment == segments.NON_CABIN else "PO booking"
	# SK 26-Oct: for a sales manager (Rushi) the team total counts: the team's orders against all their targets together
	target = _sales_target([user] if owners is None else owners)
	lines = [("Orders", "o", _orders_value(owners, segment))]
	# SK 27-Oct "data in graph is not came for Aditya": the invoiced sale (Tally and ERPNext invoices) is the data the
	# company has for every month, so Non-Cabin and the sales manager's team also see it as a second line
	if segment == segments.NON_CABIN:
		lines.append(("Invoices", "g", lambda s, e: dashboards._invoiced(s, e, segments.NON_CABIN)))
	elif owners is not None and len(owners) > 1:
		title = "Team PO booking"
		lines.append(("Invoices", "g", lambda s, e: dashboards._invoiced(s, e, segments.CABIN)))
	elif owners is not None:
		# SK 27-Oct point 5: the person's customers' invoiced sale (Tally + invoices), once the CEO / sales manager
		# has said who sells to each customer
		from sk_app.sales_owner import invoiced_for

		persons = _sales_persons(user)
		lines.append(("Invoices", "g", lambda s, e: invoiced_for(persons, s, e)))
	card = _money_card(fn, title, lines, target)
	if owners is not None and not any(p for line in card["month"]["lines"] for p in line["points"]):
		# nothing credited to this person: say how an order becomes theirs
		card["need"] = "No sale in your name yet. The CEO / sales manager ticks your customers on Customer → salesperson; then their Tally sale shows here."
	if not target:
		card["need_target"] = "Monthly target not set: SK App Settings → SK KPI Target (orders value)."
	return card


def company(user: str) -> dict:
	"""CEO (SK 26-Oct): two lines, order booking and invoicing, against the company target."""
	return _money_card("Management", "Order booking & invoices", [("Orders", "o", _orders_value(None)), ("Invoices", "g", _invoiced)],
		_sales_target(None) or COMPANY_TARGET)


# ---------- month by month (all other functions) ----------

def production(user: str) -> dict:
	"""SK 26-Oct: each month, the cabins finished that month: total days used ÷ total sq ft × 100."""
	def value(start, end):
		days = area = 0.0
		for w in frappe.get_all("Work Order", filters={"docstatus": 1, "status": "Completed", "actual_end_date": ["between", [f"{start} 00:00:00", f"{end} 23:59:59"]]},
				fields=["item_name", "production_item", "actual_start_date", "planned_start_date", "creation", "actual_end_date"], limit=0):
			size = sq_ft(w.item_name) or sq_ft(w.production_item)
			if not size:
				continue
			began = w.actual_start_date or w.planned_start_date or w.creation
			days += max(1, date_diff(w.actual_end_date, began))
			area += size
		return round(days / area * 100, 1) if area else None
	return _trend("Production", "Days to build 100 sq ft", "d", TARGETS["Production"], value, good_low=True,
		need="Finish Work Orders in ERPNext (start and end dates) for cabins whose item name has the size, e.g. 12x10.")


def accounts(user: str) -> dict:
	"""SK 26-Oct: of the projects finished and invoiced in the month, how many have their material posted to the project,
	so that their project-wise profit & loss is right (e.g. 12 of 20 = 60%). Target 100%; the trend shows if posting improves."""
	points = []
	for m, start, end in _months():
		rows = _safe(lambda start=start, end=end: frappe.get_all("Project", filters={"status": "Completed", "actual_end_date": ["between", [start, end]],
			"total_billed_amount": [">", 0]}, fields=["total_consumed_material_cost", "total_purchase_cost"], limit=0), []) or []
		ok = sum(1 for r in rows if flt(r.total_consumed_material_cost) + flt(r.total_purchase_cost) > 0)
		points.append({"m": m, "v": round(ok * 100 / len(rows)) if rows else None, "note": f"{ok}/{len(rows)}" if rows else ""})
	return {"kind": "trend", "function": "Accounts", "title": "Projects with correct P&L", "unit": "%", "target": TARGETS["Accounts"],
		"good_low": False, "points": points, "need": "" if any(p["v"] is not None for p in points) else
			"Link each order to an ERPNext Project and post its material issues and purchases to that Project; finished, invoiced projects show here."}


def hr(user: str) -> dict:
	def value(start, end):
		days = []
		for e in frappe.get_all("Employee", filters={"date_of_joining": ["between", [start, end]], "job_applicant": ["is", "set"]},
				fields=["date_of_joining", "job_applicant"], limit=0):
			opening = frappe.db.get_value("Job Applicant", e.job_applicant, "job_title")
			posted = opening and frappe.db.get_value("Job Opening", opening, ["posted_on", "creation"], as_dict=True)
			if posted:
				days.append(max(0, date_diff(e.date_of_joining, posted.posted_on or posted.creation)))
		return round(sum(days) / len(days)) if days else None
	return _trend("HR", "Days to recruit", "d", TARGETS["HR"], value, good_low=True,
		need="Add each new joiner from a Job Opening → Job Applicant → Employee in ERPNext.")


def stores(user: str) -> dict:
	def value(start, end):
		recos = frappe.get_all("Stock Reconciliation", filters={"docstatus": 1, "purpose": "Stock Reconciliation", "posting_date": ["between", [start, end]]}, pluck="name")
		if not recos:
			return None
		items = frappe.get_all("Stock Reconciliation Item", filters={"parent": ["in", recos]}, fields=["qty", "current_qty"], limit=0)
		ok = sum(1 for i in items if abs(flt(i.qty) - flt(i.current_qty)) < 0.001)
		return round(ok * 100 / len(items), 1) if items else None
	return _trend("Stores", "Stock accuracy", "%", TARGETS["Stores"], value,
		need="Count stock with the Stock count icon; each posted count shows here.")


def quality(user: str) -> dict:
	def value(start, end):
		first = {}
		for q in frappe.get_all("Quality Inspection", filters={"docstatus": 1, "report_date": ["between", [start, end]], "reference_type": "Job Card"},
				fields=["reference_name", "status", "creation"], order_by="creation asc", limit=0):
			first.setdefault(q.reference_name, q.status)
		return round(sum(1 for s in first.values() if s == "Accepted") * 100 / len(first), 1) if first else None
	return _trend("Quality", "QC first-time pass", "%", TARGETS["Quality"], value,
		need="Do the QC checks in the app; each job's first check shows here.")


def purchase(user: str) -> dict:
	def value(start, end):
		pos = frappe.get_all("Purchase Order", filters={"docstatus": 1, "schedule_date": ["between", [start, end]]}, fields=["name", "schedule_date"], limit=0)
		if not pos:
			return None
		got = {}
		for r in frappe.get_all("Purchase Receipt Item", filters={"docstatus": 1, "purchase_order": ["in", [p.name for p in pos]]},
				fields=["purchase_order", "parent"], limit=0):
			d = frappe.db.get_value("Purchase Receipt", r.parent, "posting_date")
			got[r.purchase_order] = min(got.get(r.purchase_order, d), d)
		return round(sum(1 for p in pos if p.name in got and getdate(got[p.name]) <= getdate(p.schedule_date)) * 100 / len(pos), 1)
	return _trend("Purchase", "POs received on time", "%", TARGETS["Purchase"], value, need="Make POs with a 'required by' date and receive them in ERPNext.")


def ai(user: str) -> dict:
	def value(start, end):
		return frappe.db.count("Task", {"status": "Completed", "project": ["is", "set"], "completed_on": ["between", [start, end]]}) or None
	return _trend("AI", "ERP tasks finished", "", TARGETS["AI"], value, need="Close ERP project tasks in ERPNext.", count=True)


def subcontractor(user: str) -> dict:
	ws = frappe.db.get_value("SK App User", {"user": user}, "workstation")

	def value(start, end):
		if not ws:
			return None
		return frappe.db.count("Job Card", {"workstation": ws, "status": "Completed", "modified": ["between", [f"{start} 00:00:00", f"{end} 23:59:59"]]}) or None
	return _trend("Subcontractor", "Jobs finished", "", TARGETS["Subcontractor"], value, need="Mark your jobs done with a photo.", count=True)


BUILDERS = {"Sales": sales, "Marketing": sales, "Machine Shifting": lambda u: sales(u, segments.NON_CABIN, "Machine Shifting"),
	"Management": company, "Production": production, "Accounts": accounts, "HR": hr, "Stores": stores, "Quality": quality,
	"Purchase": purchase, "AI": ai, "Subcontractor": subcontractor}


def chart_for(user: str, functions: list[str]) -> dict | None:
	"""The person's one KPI chart. SK 27-Oct: people kept getting the Sales graph; a person with Sales plus their own
	function (Aditya: Non-Cabin) gets their own function's graph, the CEO the company graph."""
	rank = lambda fn: 0 if fn == "Management" else 2 if fn in ("Sales", "Marketing") else 1  # noqa: E731
	for fn in sorted(functions, key=rank):
		build = BUILDERS.get(fn)
		if build:
			return _safe(lambda: build(user), None)
	return None


# ---------- Actions to improve the graph (SK 26-Oct) ----------
# "action needs to improve graph on main screen with some icon, that input will be given by AI & other; it helps to
# understand the work to take on priority for graph improvement". Each action is an ERPNext ToDo of the person (so it
# also shows in My Day), added by the person, their manager, the CEO or the AI desk (and Claude's Friday summary).
ACTION_MARK = "[KPI] "
PRIORITY = {"High": 0, "Medium": 1, "Low": 2}


def _may_act_for(user: str, member: str) -> bool:
	from sk_app.day_report import _team
	from sk_app.logins import profile_functions

	if user == member or user == "Administrator" or {"Management", "AI"} & set(profile_functions(user)):
		return True
	return member in {p.user for p in _team(user)}


def _check(user: str, member: str):
	if not _may_act_for(user, member):
		frappe.throw(frappe._("You can add actions only for yourself and your team"), frappe.PermissionError)


def open_actions(user: str) -> int:
	return frappe.db.count("ToDo", {"allocated_to": user, "status": "Open", "description": ["like", ACTION_MARK + "%"]})


def actions(user: str, member=None) -> dict:
	member = member or user
	_check(user, member)
	rows = frappe.get_all("ToDo", filters={"allocated_to": member, "description": ["like", ACTION_MARK + "%"], "status": ["in", ["Open", "Closed"]],
		"modified": [">=", add_days(nowdate(), -30)]}, fields=["name", "description", "priority", "date", "status", "assigned_by", "modified"], limit=200)
	today = getdate()
	out = [{"name": r.name, "text": r.description[len(ACTION_MARK):], "priority": r.priority or "Medium", "date": str(r.date or ""),
		"done": r.status == "Closed", "late": r.status == "Open" and bool(r.date) and getdate(r.date) < today,
		"by": frappe.db.get_value("User", r.assigned_by, "full_name") or r.assigned_by or ""} for r in rows]
	out.sort(key=lambda a: (a["done"], not a["late"], PRIORITY.get(a["priority"], 1), a["date"] or "9999"))
	from sk_app.day_report import _team

	team = [{"user": user, "name": frappe.db.get_value("User", user, "full_name") or user}] + \
		[{"user": p.user, "name": p.full_name or p.user} for p in _team(user)]
	return {"member": member, "actions": out, "team": team}


def add_action(user: str, member: str, text: str, priority="Medium", date=None) -> dict:
	member = member or user
	_check(user, member)
	text = (text or "").strip()
	if not text:
		frappe.throw(frappe._("Please write the action"))
	todo = frappe.get_doc({"doctype": "ToDo", "allocated_to": member, "assigned_by": user, "description": ACTION_MARK + text[:500],
		"priority": priority if priority in PRIORITY else "Medium", "date": getdate(date) if date else add_days(nowdate(), 7)})
	todo.insert(ignore_permissions=True)
	return {"name": todo.name}


def finish_action(user: str, name: str, note=None, photo=None) -> dict:
	from sk_app.store import attach

	todo = frappe.get_doc("ToDo", name)
	if not todo.description.startswith(ACTION_MARK) or todo.allocated_to != user:
		frappe.throw(frappe._("Only the person who has the action can close it"), frappe.PermissionError)
	todo.status = "Closed"
	todo.save(ignore_permissions=True)
	if note:
		todo.add_comment("Comment", note)
	attach(photo, "ToDo", todo.name, user)
	return {"ok": True}


def for_user(user: str, functions: list[str]) -> dict:
	return {"chart": chart_for(user, functions), "actions": _safe(lambda: open_actions(user), 0), "at": nowdate()}
