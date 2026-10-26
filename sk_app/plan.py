"""Target action plan (SK 26-Oct: "monthly target is hard to reach: suggest actions for everyone and add their daily,
weekly and monthly plan"). Each person's monthly order target is turned into a funnel, target ÷ average order =
orders, ÷ win rate = quotes, ÷ lead-to-quote rate = leads, then split into today's numbers on My Day. From the 10th
of the month a person behind the pro-rata target is flagged red for them, their manager and the CEO.
The rates are the Target Action Plan Rev 0 defaults and are corrected from CRM data once the app has a month of use."""

import math

import frappe
from frappe.utils import add_days, add_months, flt, getdate

from sk_app import kpi, segments
from sk_app.logic import DAY_NAMES, expected_by_today, month_range, parse_lines

WIN_RATE = {segments.CABIN: 0.25, segments.NON_CABIN: 0.40}
LEAD_TO_QUOTE = 0.40
DEFAULT_ORDER = 200000.0  # ₹2 L: the year's average cabin / non-cabin bill
CALLS_PER_LEAD = 3  # first call + two follow-ups
FLAG_FROM_DAY = 10  # SK plan: red flag on the 10th and the 20th when the month is behind


def funnel(target: float, avg_order: float, win_rate: float, working_days: int) -> dict:
	"""Monthly target → orders, quotes, leads and calls for the month, the week and the day."""
	if not target or target <= 0:
		return {}
	avg_order = avg_order if avg_order and avg_order > 0 else DEFAULT_ORDER
	orders = max(1, math.ceil(target / avg_order))
	quotes = math.ceil(orders / win_rate)
	leads = math.ceil(quotes / LEAD_TO_QUOTE)
	calls = leads * CALLS_PER_LEAD
	wd = max(1, working_days)
	per = lambda n, d: math.ceil(n / d)  # noqa: E731
	return {"target": target, "avg_order": avg_order, "win_rate": win_rate,
		"month": {"orders": orders, "quotes": quotes, "leads": leads, "calls": calls},
		"week": {"orders": per(orders * 6, wd), "quotes": per(quotes * 6, wd), "leads": per(leads * 6, wd), "calls": per(calls * 6, wd)},
		"day": {"quotes": per(quotes, wd), "leads": per(leads, wd), "calls": per(calls, wd)}}


def _working_days(day) -> tuple[list[str], int]:
	days = parse_lines((kpi.settings().working_days or "").replace(",", "\n")) or ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
	start, end = month_range(day)
	n = sum(1 for i in range((end - start).days + 1) if DAY_NAMES[add_days(start, i).weekday()] in days)
	return days, n


def _target(user: str) -> float:
	return flt(frappe.db.get_value("SK KPI Target", {"user": user, "active": 1, "kpi_code": ["in", ["orders_value", "digital_orders_value"]]},
		"monthly_target"))


def _avg_order(user: str, day) -> float:
	"""The person's own average order of the last 12 months (3 orders or more), else ₹2 L."""
	names = kpi.user_sales_orders(user, add_months(day, -12), day)
	if len(names) < 3:
		return DEFAULT_ORDER
	return kpi._sum_orders(names) / len(names)


def _today_done(user: str, day) -> dict:
	from sk_app.comms import call_totals

	period = ["between", [f"{day} 00:00:00", f"{day} 23:59:59"]]
	leads = frappe.db.count("CRM Lead", {"lead_owner": user, "creation": period}) if frappe.db.exists("DocType", "CRM Lead") else 0
	quotes = frappe.db.count("Quotation", {"owner": user, "docstatus": ["<", 2], "transaction_date": day})
	return {"calls": call_totals(user, day)["calls"], "leads": leads, "quotes": quotes}


def day_plan(user: str, day=None) -> dict | None:
	"""Today's numbers for a person with an order target: to do vs done, the month so far vs pro-rata, and the flag."""
	day = getdate(day)
	target = _target(user)
	if not target:
		return None
	days, wd = _working_days(day)
	win = WIN_RATE.get(segments.user_main(user), WIN_RATE[segments.CABIN])
	f = funnel(target, _avg_order(user, day), win, wd)
	start, end = month_range(day)
	done_month = kpi._sum_orders(kpi.user_sales_orders(user, start, end))
	expected = expected_by_today(target, day, days)
	behind = day.day >= FLAG_FROM_DAY and done_month < 0.8 * expected
	done = _today_done(user, day)
	return {**f, "done_today": done, "orders_done": done_month, "expected_by_today": round(expected),
		"behind": behind, "gap": max(0, round(expected - done_month)),
		"rows": [{"key": k, "plan": f["day"][k], "done": done[k], "c": "green" if done[k] >= f["day"][k] else "amber"}
			for k in ("calls", "leads", "quotes")]}


def behind_list(day=None) -> list[dict]:
	"""Everyone with an order target who is behind the month's pro-rata share (for the CEO and managers)."""
	day = getdate(day)
	if day.day < FLAG_FROM_DAY:
		return []
	out = []
	for user in frappe.get_all("SK KPI Target", filters={"active": 1, "kpi_code": ["in", ["orders_value", "digital_orders_value"]]}, pluck="user"):
		p = day_plan(user, day)
		if p and p["behind"]:
			out.append({"user": user, "gap": p["gap"], "done": p["orders_done"], "expected": p["expected_by_today"]})
	return out
