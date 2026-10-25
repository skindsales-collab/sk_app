"""Count each KPI's actual for a month straight from ERPNext, so nobody types in scores."""

import frappe
from frappe.utils import flt, getdate

from sk_app.logic import expected_by_today, kpi_colour, kpi_score, month_range, parse_lines


def settings():
	return frappe.get_cached_doc("SK App Settings")


def _sales_persons(user: str) -> list[str]:
	employees = frappe.get_all("Employee", filters={"user_id": user}, pluck="name")
	if not employees:
		return []
	return frappe.get_all("Sales Person", filters={"employee": ["in", employees]}, pluck="name")


def user_sales_orders(user: str, start, end) -> list[str]:
	"""Submitted Sales Orders in the month credited to the user: via Sales Team, else created by the user."""
	base = {"docstatus": 1, "transaction_date": ["between", [start, end]]}
	names = set()
	persons = _sales_persons(user)
	if persons:
		names.update(frappe.get_all("Sales Order", filters=[*_as_list(base), ["Sales Team", "sales_person", "in", persons]], pluck="name"))
	# orders without any sales team row count for their creator
	own = frappe.get_all("Sales Order", filters={**base, "owner": user}, pluck="name")
	with_team = set(frappe.get_all("Sales Team", filters={"parenttype": "Sales Order", "parent": ["in", own or [""]]}, pluck="parent"))
	names.update(n for n in own if n not in with_team)
	return sorted(names)


def _as_list(filters: dict) -> list:
	return [[k, *(v if isinstance(v, list) else ["=", v])] for k, v in filters.items()]


def _sum_orders(names: list[str]) -> float:
	if not names:
		return 0.0
	# net total in company currency, i.e. order value before GST
	return sum(flt(v) for v in frappe.get_all("Sales Order", filters={"name": ["in", names]}, pluck="base_net_total"))


def _digital_customers() -> list[str]:
	sources = parse_lines(settings().digital_lead_sources)
	if not sources or not frappe.db.exists("DocType", "CRM Deal"):
		return []
	return [c for c in frappe.get_all("CRM Deal", filters={"source": ["in", sources]}, pluck="erpnext_customer") if c]


def _pct(part: int, whole: int) -> float:
	return round(part * 100.0 / whole, 1) if whole else 0.0


def actual_for(target, start, end) -> float | None:
	"""Actual value of one SK KPI Target for the period. None means the source is not live yet."""
	user, code = target.user, target.kpi_code
	has_crm = frappe.db.exists("DocType", "CRM Lead")
	period = ["between", [start, end]]
	dt_period = ["between", [f"{start} 00:00:00", f"{end} 23:59:59"]]

	if code == "manual":
		return flt(target.manual_actual)
	if code == "orders_value":
		return _sum_orders(user_sales_orders(user, start, end))
	if code == "digital_orders_value":
		customers = _digital_customers()
		if not customers:
			return 0.0
		names = frappe.get_all("Sales Order", filters={"docstatus": 1, "transaction_date": period, "customer": ["in", customers]}, pluck="name")
		return _sum_orders(names)
	if code == "cabins_qty":
		names = user_sales_orders(user, start, end)
		groups = parse_lines(settings().cabin_item_groups)
		if not names or not groups:
			return 0.0
		rows = frappe.get_all("Sales Order Item", filters={"parent": ["in", names], "item_group": ["in", groups]}, fields=["qty"])
		return sum(flt(r.qty) for r in rows)
	if code == "quotes_sent":
		return float(frappe.db.count("Quotation", {"owner": user, "docstatus": 1, "transaction_date": period}))
	if code == "dsi_count":
		return float(frappe.db.count("SK DSI Entry", {"user": user, "date": period}))
	if not has_crm:
		return None
	if code == "leads_worked":
		return float(frappe.db.count("CRM Lead", {"lead_owner": user, "first_responded_on": dt_period}))
	if code == "first_response_pct":
		rows = frappe.get_all("CRM Lead", filters={"lead_owner": user, "creation": dt_period}, fields=["first_response_time"])
		limit = (settings().first_response_minutes or 5) * 60
		ok = sum(1 for r in rows if r.first_response_time and flt(r.first_response_time) <= limit)
		return _pct(ok, len(rows))
	if code == "digital_leads":
		sources = parse_lines(settings().digital_lead_sources)
		return float(frappe.db.count("CRM Lead", {"source": ["in", sources or [""]], "creation": dt_period}))
	if code == "lead_data_quality_pct":
		rows = frappe.get_all("CRM Lead", filters={"creation": dt_period}, fields=["source", "lead_owner", "organization", "mobile_no"])
		good = sum(1 for r in rows if r.source and r.lead_owner and (r.organization or r.mobile_no))
		return _pct(good, len(rows))
	return None


def scorecard(user: str, day=None) -> dict:
	"""The person's live KPI chart for the month: each KPI with actual, target, colour and weighted score."""
	day = getdate(day)
	start, end = month_range(day)
	days = parse_lines((settings().working_days or "").replace(",", "\n"))
	targets = frappe.get_all(
		"SK KPI Target",
		filters={"user": user, "active": 1},
		fields=["name", "user", "kra", "kpi_label", "kpi_code", "monthly_target", "unit", "weight", "manual_actual", "status"],
		order_by="weight desc",
	)
	rows, total = [], 0.0
	for t in targets:
		actual = actual_for(t, start, end)
		live = actual is not None
		actual = actual or 0.0
		score = kpi_score(actual, t.monthly_target, t.weight) if live else 0.0
		total += score
		rows.append({
			"kra": t.kra, "kpi_label": t.kpi_label, "kpi_code": t.kpi_code, "unit": t.unit,
			"monthly_target": flt(t.monthly_target), "weight": flt(t.weight), "actual": actual,
			"expected_by_today": expected_by_today(flt(t.monthly_target), day, days) if t.unit != "%" else flt(t.monthly_target),
			"colour": kpi_colour(actual, t.monthly_target) if live else "grey",
			"score": score, "live": live, "status": t.status,
		})
	return {"user": user, "month": f"{start:%b %Y}", "from": str(start), "to": str(end),
		"total_score": round(total, 1), "kpis": rows, "refreshed_at": str(frappe.utils.now_datetime())}
