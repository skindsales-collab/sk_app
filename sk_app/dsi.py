"""DSI (Daily Small Improvement) monthly summary (SK 29-Oct-2026: "DSI should be captured on ERP & monthly summary can be taken").

Every DSI is an SK DSI Entry in ERPNext; each entry keeps the person's main function when it was posted, so the
summary by role stays right after a role change. One row per month and person: entries, days posted, target
(their DSI KPI target, else 26), time and money saved, Best of Month. Used by the ERPNext report "DSI Monthly
Summary" and the CEO Daily Review dashboard.
"""

import frappe
from frappe.utils import flt, get_first_day, getdate

DEFAULT_TARGET = 26  # one DSI every working day (setup.py KPI "dsi_count")


def main_function(user: str) -> str:
	from sk_app.logins import profile_functions

	functions = profile_functions(user)
	return functions[0] if functions else ""


def stamp_function(doc, method=None):
	if not doc.function:
		doc.function = main_function(doc.user)


def summary(start, end, function=None, user=None) -> list[dict]:
	filters = {"date": ["between", [getdate(start), getdate(end)]]}
	if function:
		filters["function"] = function
	if user:
		filters["user"] = user
	entries = frappe.get_all("SK DSI Entry", filters=filters, order_by="date asc",
		fields=["user", "function", "date", "saving_type", "saving_value", "status"])
	targets = {r.user: flt(r.monthly_target) for r in frappe.get_all("SK KPI Target",
		filters={"active": 1, "kpi_code": "dsi_count"}, fields=["user", "monthly_target"])}
	names = dict(frappe.get_all("SK App User", fields=["user", "full_name"], as_list=True))
	rows = {}
	for e in entries:
		month = get_first_day(e.date)
		r = rows.setdefault((month, e.user), {
			"month": month, "user": e.user, "full_name": names.get(e.user) or e.user, "function": e.function or "",
			"entries": 0, "days": set(), "target": targets.get(e.user) or DEFAULT_TARGET,
			"time_min": 0.0, "cost_rs": 0.0, "quality": 0, "safety": 0, "customer": 0, "best": 0})
		r["entries"] += 1
		r["days"].add(e.date)
		r["function"] = r["function"] or e.function or ""
		if e.saving_type == "Time":
			r["time_min"] += flt(e.saving_value)
		elif e.saving_type == "Cost":
			r["cost_rs"] += flt(e.saving_value)
		elif e.saving_type in ("Quality", "Safety", "Customer"):
			r[e.saving_type.lower()] += 1
		if e.status == "Best of Month":
			r["best"] += 1
	out = []
	for r in sorted(rows.values(), key=lambda x: (x["month"], -x["entries"], x["full_name"])):
		r["days"] = len(r["days"])
		r["pct"] = round(100 * r["entries"] / r["target"]) if r["target"] else 0
		out.append(r)
	return out
