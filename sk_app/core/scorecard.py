"""Before / after rebuild scorecard (SK 4-Nov-2026: "both data should be measurable").

Every measure is one number with its unit and the source it is counted from, saved once a day (SK Scorecard Entry) the
same way before and after each module moves to the New path. The day's New-path modules are saved with it, so the
numbers can be put side by side: old path days vs new path days.
"""

import frappe
from frappe.utils import add_days, flt, getdate, nowdate

ENTRY = "SK Scorecard Entry"


def _count(doctype: str, filters) -> int:
	return frappe.db.count(doctype, filters) if frappe.db.table_exists(doctype) else 0


def _won_statuses(doctype: str) -> list[str]:
	if doctype == "CRM Deal":
		return frappe.get_all("CRM Deal Status", filters={"type": "Won"}, pluck="name") or ["Won"]
	return ["Deal Won", "Converted"]


def _day_range(day) -> list:
	return [str(day) + " 00:00:00", str(day) + " 23:59:59.999999"]


def _perf(day) -> dict:
	rows = frappe.get_all("SK Perf Log", filters={"day": day}, fields=["device", "calls", "avg_ms", "errors", "saves", "avg_taps"], limit=0) \
		if frappe.db.table_exists("SK Perf Log") else []
	out = {}
	for device in ("Mobile", "PC"):
		mine = [r for r in rows if r.device == device]
		calls = sum(r.calls for r in mine)
		saves = sum(r.saves for r in mine)
		out[device] = {"avg_ms": round(sum(r.calls * r.avg_ms for r in mine) / calls) if calls else 0,
			"errors": sum(r.errors for r in mine), "calls": calls,
			"taps": round(sum(r.saves * flt(r.avg_taps) for r in mine) / saves, 1) if saves else 0}
	return out


def measures(day=None) -> list[dict]:
	"""[{measure, area, value, unit, source}] for one day (stock numbers are as of now; per-day numbers count that day)."""
	from sk_app import doubles

	day = getdate(day or nowdate())
	span = ["between", _day_range(day)]
	out = []

	def add(area, measure, value, unit, source):
		out.append({"area": area, "measure": measure, "value": flt(value), "unit": unit, "source": source})

	leads = _count("CRM Lead", {"status": ["in", _won_statuses("CRM Lead")], "converted": 0})
	deals = _count("CRM Deal", {"status": ["in", _won_statuses("CRM Deal")]})
	orders = _count("Sales Order", {"docstatus": 1})
	add("Data accuracy", "Won deals", deals, "deals", "CRM Deal with a Won status")
	add("Data accuracy", "Submitted orders", orders, "orders", "Sales Order docstatus 1")
	add("Data accuracy", "Won leads with no deal", leads, "leads", "CRM Lead Deal Won / Converted, not converted to a deal")
	add("Data accuracy", "Orders minus won deals", abs(orders - deals), "orders", "Submitted orders - won deals (0 when every order has its won deal)")
	add("Data accuracy", "Orders 0% billed", _count("Sales Order", {"docstatus": 1, "per_billed": 0}), "orders", "Sales Order docstatus 1, per_billed 0")
	found = doubles.possible_doubles()
	add("Data accuracy", "Possible double entries", len(found["pairs"]) + len(found["deals"]), "pairs",
		"sk_app.doubles.possible_doubles since 1-Apr (money pairs + leads with 2 deals), ticked pairs excluded")
	add("Data accuracy", "Bank payments booked in Cash", len(found["bank_in_cash"]), "payments", "Payment Entry bank mode / UTR through a Cash account")
	add("Silent failures", "SK App errors", _count("Error Log", {"creation": span, "method": ["like", "%SK App%"]}), "errors / day",
		"ERPNext Error Log with 'SK App' in its title, this day")
	add("Silent failures", "Kept as draft", _count("Comment", {"creation": span, "content": ["like", "Kept as draft by SK App%"]}), "drafts / day",
		"Comment 'Kept as draft by SK App', this day")
	add("Rule gaps", "Rule gaps found", _count("SK Rule Log", {"creation": span, "mode": ["!=", "Replay"]}), "gaps / day",
		"SK Rule Log rows (Warn only + Enforce), this day")
	add("Rule gaps", "Replay gaps open", _count("SK Rule Log", {"mode": "Replay"}), "gaps", "SK Rule Log mode Replay (last replay run)")
	perf = _perf(day)
	for device in ("Mobile", "PC"):
		add("Speed", f"Average screen time ({device})", perf[device]["avg_ms"], "ms", f"SK Perf Log, {device}, weighted by calls, this day")
		add("Speed", f"Screen errors ({device})", perf[device]["errors"], "errors / day", f"SK Perf Log, {device}, failed calls, this day")
		add("Ease", f"Taps per save ({device})", perf[device]["taps"], "taps", f"SK Perf Log, {device}, taps between two saves, this day")
	add("Users", "Problems reported", _count("Issue", {"creation": span, "customer": ["is", "not set"]}), "issues / day",
		"Issue (internal desk: no customer), this day")
	return out


def new_modules() -> str:
	if not frappe.db.table_exists("SK Path Switch"):
		return ""
	return ", ".join(frappe.get_all("SK Path Switch", filters={"path": "New"}, pluck="module", order_by="module asc"))


def snapshot(day=None) -> int:
	"""Save the day's numbers (again: the day's old rows are replaced). Nightly at 23:45, and on demand."""
	day = getdate(day or nowdate())
	if not frappe.db.table_exists(ENTRY):
		return 0
	frappe.db.delete(ENTRY, {"day": day})
	paths = new_modules()
	rows = measures(day)
	for r in rows:
		frappe.get_doc({"doctype": ENTRY, "day": day, "paths": paths, **r}).insert(ignore_permissions=True)
	return len(rows)


def nightly():
	snapshot()


def compare() -> list[dict]:
	"""Side by side: the average of days with no New-path module vs days with one or more (per measure)."""
	rows = frappe.get_all(ENTRY, filters={"day": [">=", add_days(nowdate(), -90)]}, fields=["measure", "unit", "value", "paths"], limit=0)
	by = {}
	for r in rows:
		key = (r.measure, r.unit)
		side = "new" if r.paths else "old"
		by.setdefault(key, {"old": [], "new": []})[side].append(flt(r.value))
	return [{"measure": m, "unit": u, "old": round(sum(v["old"]) / len(v["old"]), 2) if v["old"] else None,
		"new": round(sum(v["new"]) / len(v["new"]), 2) if v["new"] else None} for (m, u), v in by.items()]


def log_perf(user: str, rows: list, device: str):
	from sk_app.core.switch import my_paths

	paths = ", ".join(m for m, p in my_paths(user).items() if p == "New")
	device = "PC" if device == "PC" else "Mobile"
	for r in rows[:200]:
		calls = int(r.get("calls") or 0)
		if not calls or not r.get("method"):
			continue
		saves = int(r.get("saves") or 0)
		frappe.get_doc({"doctype": "SK Perf Log", "day": nowdate(), "user": user, "device": device, "paths": paths,
			"method": str(r["method"])[:100], "calls": calls, "avg_ms": int(flt(r.get("ms")) / calls), "max_ms": int(flt(r.get("max"))),
			"errors": int(r.get("errors") or 0), "saves": saves,
			"avg_taps": round(flt(r.get("taps")) / saves, 1) if saves else 0}).insert(ignore_permissions=True)
