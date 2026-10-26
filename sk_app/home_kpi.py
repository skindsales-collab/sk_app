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


def _trend(fn, title, unit, target, value_of, good_low=False, need=""):
	points = [{"m": m, "v": _safe(lambda s=s, e=e: value_of(s, e), None)} for m, s, e in _months()]
	return {"kind": "trend", "function": fn, "title": title, "unit": unit, "target": target, "good_low": good_low,
		"points": points, "need": "" if any(p["v"] is not None for p in points) else need}


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
	month_days = get_last_day(start).day
	weeks = _weeks(start, today)
	week_lines, month_lines = [], []
	for label, c, amount_of in line_specs:
		run, pts = 0.0, []
		for _w, s, e in weeks:
			run += flt(_safe(lambda s=s, e=e: amount_of(s, min(e, today)), 0))
			pts.append(round(run))
		week_lines.append({"label": label, "c": c, "points": pts})
		month_lines.append({"label": label, "c": c, "points": [round(flt(_safe(lambda s=s, e=e: amount_of(s, e), 0))) for _m, s, e in _months()]})
	return {"kind": "money", "function": fn, "title": title, "unit": "Rs", "target": target,
		"week": {"labels": [w[0] for w in weeks], "target": [round(target * min(e.day, month_days) / month_days) for _w, _s, e in weeks], "lines": week_lines},
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
			orders = [s for s in orders if s.name in mine or s.name in drafts]
		return sum(flt(s.base_net_total) for s in orders)
	return amount


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
	if owners is not None and len(owners) > 1:
		title = "Team PO booking"
	return _money_card(fn, title, [("Orders", "o", _orders_value(owners, segment))], target)


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
	return _trend("AI", "ERP tasks finished", "", TARGETS["AI"], value, need="Close ERP project tasks in ERPNext.")


def subcontractor(user: str) -> dict:
	ws = frappe.db.get_value("SK App User", {"user": user}, "workstation")

	def value(start, end):
		if not ws:
			return None
		return frappe.db.count("Job Card", {"workstation": ws, "status": "Completed", "modified": ["between", [f"{start} 00:00:00", f"{end} 23:59:59"]]}) or None
	return _trend("Subcontractor", "Jobs finished", "", TARGETS["Subcontractor"], value, need="Mark your jobs done with a photo.")


BUILDERS = {"Sales": sales, "Marketing": sales, "Machine Shifting": lambda u: sales(u, segments.NON_CABIN, "Machine Shifting"),
	"Management": company, "Production": production, "Accounts": accounts, "HR": hr, "Stores": stores, "Quality": quality,
	"Purchase": purchase, "AI": ai, "Subcontractor": subcontractor}


def chart_for(user: str, functions: list[str]) -> dict | None:
	"""The person's one KPI chart: the CEO's company chart first, else the first function that has one."""
	order = ["Management"] + [f for f in functions if f != "Management"] if "Management" in functions else functions
	for fn in order:
		build = BUILDERS.get(fn)
		if build:
			return _safe(lambda: build(user), None)
	return None


def for_user(user: str, functions: list[str]) -> dict:
	return {"chart": chart_for(user, functions), "at": nowdate()}
