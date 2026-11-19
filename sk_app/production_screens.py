"""Production screens (reads only; the Production writer is writers/work_order.py). Order Board, Job Cards, Ready to
Dispatch, electrical points list, badges, and the helpers the writer shares (workstation, card lookup, labels).
Plan A step 1 (SK 9-Nov): production.py split into this file and the writer; names unchanged."""

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, now_datetime, nowdate, time_diff_in_seconds

from sk_app import cabin_projects
from sk_app.store import _todo, _users_with_function, attach, draft_reason, need, try_submit, uom, users_or_ceo


PRODUCTION = "Production"

SUB = "Subcontractor"

def my_workstation(user: str) -> str | None:
	return frappe.db.get_value("SK App User", {"user": user}, "workstation")

def _is_sub_only(user: str) -> bool:
	from sk_app import logins

	return logins.profile_functions(user) == [SUB] and "System Manager" not in frappe.get_roles(user)

def _card_for(user: str, job_card: str):
	"""Job Card the person may work on: subcontractors only their own workstation's cards."""
	need(user, PRODUCTION, SUB)
	jc = frappe.get_doc("Job Card", job_card)
	if _is_sub_only(user) and jc.workstation != my_workstation(user):
		frappe.throw(_("This job is not on your workstation"), frappe.PermissionError)
	if jc.docstatus != 0:
		frappe.throw(_("Job {0} is already closed").format(job_card))
	return jc

def non_cabin_orders() -> set:
	"""SK 28-Oct (Rev 1 point 9, Babasaheb): Rothe Erde showed on the factory board. Non-Cabin orders (machine shifting,
	job work, ballscrews) are Aditya's jobs, not cabins."""
	from sk_app import segments

	return set(frappe.get_all("Sales Order", filters={"docstatus": ["<", 2], "customer_group": ["in", segments.groups_of(segments.NON_CABIN)]},
		pluck="name", limit=0))

def order_board(user: str) -> list[dict]:
	"""Every cabin in production with its stages (Job Cards in route order) and whether it is late."""
	need(user, PRODUCTION, "Quality", "Stores", "Management", "Sales")
	wos = frappe.get_all("Work Order", filters={"docstatus": 1, "status": ["not in", ["Completed", "Stopped", "Closed", "Cancelled"]]},
		fields=["name", "production_item", "item_name", "qty", "status", "sales_order", "project", "expected_delivery_date", "planned_start_date"],
		order_by="expected_delivery_date asc, planned_start_date asc")
	skip = non_cabin_orders()
	wos = [w for w in wos if not w.sales_order or w.sales_order not in skip]
	for w in wos:
		w["stages"] = [_stage(j) for j in frappe.get_all("Job Card", filters={"work_order": w.name, "docstatus": ["<", 2]},
			fields=["name", "operation", "workstation", "status", "docstatus", "sequence_id", "total_completed_qty"], order_by="sequence_id asc, creation asc")]
		w["customer"] = wo_customer(w.name)  # SK 29-Oct: from the cabin's Project while its Sales Order is a draft
		w["cabin_no"] = cabin_projects.cabin_no(w.project)
		w["late"] = bool(w.expected_delivery_date and getdate(w.expected_delivery_date) < getdate())
		w["no_order"] = not w.sales_order or not w.expected_delivery_date
		w["expected_delivery_date"] = str(w.expected_delivery_date or "")
		w["now"] = next((s["operation"] for s in w["stages"] if s["state"] == "working"), None) \
			or next((s["operation"] for s in w["stages"] if s["state"] == "waiting"), None)
	return wos

def _stage(j) -> dict:
	if j.docstatus == 1 or j.status == "Completed" or flt(j.total_completed_qty) > 0:
		state = "done"
	elif j.status in ("Work In Progress", "Material Transferred"):
		state = "working"
	elif j.status == "On Hold":
		state = "hold"
	else:
		state = "waiting"
	return {"name": j.name, "operation": j.operation, "workstation": j.workstation, "state": state}

def wo_label(work_order: str | None, fallback: str = "") -> str:
	"""SK 27-Oct: a job is known by its customer and product, not by its number: "Customer · Product"."""
	if not work_order:
		return fallback
	cache = getattr(frappe.local, "sk_wo_label", None)
	if cache is None:  # frappe.local has no __dict__ (27-Oct: that error blanked the factory arrows)
		cache = frappe.local.sk_wo_label = {}
	if work_order not in cache:
		wo = frappe.db.get_value("Work Order", work_order, ["item_name", "production_item", "project"], as_dict=True) or {}
		parts = (cabin_projects.cabin_no(wo.get("project")), wo_customer(work_order), wo.get("item_name") or wo.get("production_item"))
		cache[work_order] = " · ".join(x for x in parts if x) or work_order
	return cache[work_order]

def wo_customer(work_order: str | None) -> str | None:
	wo = frappe.db.get_value("Work Order", work_order, ["sales_order", "project"], as_dict=True) if work_order else None
	if not wo:
		return None
	if wo.sales_order:
		return frappe.db.get_value("Sales Order", wo.sales_order, "customer_name")
	return cabin_projects.project_customer(wo.project)

def job_cards(user: str) -> list[dict]:
	"""Open Job Cards. A subcontractor sees only his workstation; the manager sees all, working ones first."""
	need(user, PRODUCTION, SUB, "Quality")
	filters = {"docstatus": 0, "status": ["not in", ["Completed", "Cancelled"]]}
	if _is_sub_only(user):
		ws = my_workstation(user)
		if not ws:
			return []
		filters["workstation"] = ws
	rows = frappe.get_all("Job Card", filters=filters, fields=["name", "work_order", "operation", "workstation", "status", "for_quantity",
		"production_item", "item_name", "expected_start_date", "sequence_id", "project"], order_by="expected_start_date asc, creation asc", limit=0)
	order = {"Work In Progress": 0, "Material Transferred": 1, "On Hold": 2}
	for r in rows:
		r["started"] = _open_log(r.name)
		r["photos"] = frappe.db.count("File", {"attached_to_doctype": "Job Card", "attached_to_name": r.name})
		r["drawing"] = _drawing(r.work_order)
		r["customer"] = wo_customer(r.work_order)
		r["cabin_no"] = cabin_projects.cabin_no(r.project or frappe.db.get_value("Work Order", r.work_order, "project"))
	rows.sort(key=lambda r: (order.get(r.status, 3), str(r.expected_start_date or "")))
	return rows

def _open_log(job_card: str):
	t = frappe.get_all("Job Card Time Log", filters={"parent": job_card, "to_time": ["is", "not set"]}, pluck="from_time", limit=1)
	return str(t[0]) if t else None

def _drawing(work_order: str | None):
	"""Latest PDF / drawing attached to the Work Order, its Sales Order or the cabin item (manufacturing drawing in mm)."""
	if not work_order:
		return None
	wo = frappe.db.get_value("Work Order", work_order, ["production_item", "sales_order"], as_dict=True) or {}
	for dt, name in (("Work Order", work_order), ("Sales Order", wo.get("sales_order")), ("Item", wo.get("production_item"))):
		if not name:
			continue
		f = frappe.get_all("File", filters={"attached_to_doctype": dt, "attached_to_name": name, "file_name": ["like", "%.pdf"]},
			fields=["file_url", "file_name"], order_by="creation desc", limit=1)
		if f:
			return f[0]
	return None

def ready_to_dispatch(user: str) -> list[dict]:
	"""Cabins whose stages are all done (or Work Order completed) and not yet delivered."""
	need(user, PRODUCTION, "Stores", "Quality", "Management")
	out = []
	for w in frappe.get_all("Work Order", filters={"docstatus": 1, "status": ["!=", "Cancelled"], "modified": [">=", frappe.utils.add_days(nowdate(), -60)]},
			fields=["name", "item_name", "production_item", "status", "sales_order", "expected_delivery_date"]):
		stages = [_stage(j) for j in frappe.get_all("Job Card", filters={"work_order": w.name, "docstatus": ["<", 2]},
			fields=["name", "operation", "workstation", "status", "docstatus", "total_completed_qty"])]
		if not (w.status == "Completed" or (stages and all(s["state"] == "done" for s in stages))):
			continue
		if w.sales_order and frappe.db.get_value("Sales Order", w.sales_order, "per_delivered") >= 100:
			continue
		from sk_app.quality import qc_filter

		final = frappe.get_all("Quality Inspection", filters={"reference_type": "Job Card", "docstatus": 1, **qc_filter(),
			"reference_name": ["in", [s["name"] for s in stages] or [""]]}, fields=["status"], order_by="creation desc", limit=1)
		out.append({**w, "expected_delivery_date": str(w.expected_delivery_date or ""), "qc": final[0].status if final else None,
			"customer": frappe.db.get_value("Sales Order", w.sales_order, "customer_name") if w.sales_order else None})
	return out

# ---------- Electrical points (SK 26-Oct, main screen Rev 2) ----------
# Satish (electrician on the Electrical workstation; Quality checks are Aditya's from 28-Oct) enters the points done in each cabin by
# type with one photo; the count is kept per Job Card and adds up by month (planning and subcontract billing).
EL_POINTS = ("light", "fan", "socket_5a", "socket_15a", "ac_point", "mcb_db", "earthing", "other_points")

EL_WORDS = ("electric", "wiring")

def _is_electrical(text: str | None) -> bool:
	return any(w in (text or "").lower() for w in EL_WORDS)

def el_jobs(user: str) -> dict:
	"""Electrical job cards of the last 60 days, open ones first, with the points already entered; and this month's total."""
	need(user, PRODUCTION, SUB, "Quality")
	from sk_app.core.people import functions

	# Mac data check 9-Nov: among subcontractors only the electrician's workstation sees the electrical points
	if set(functions(user)) <= {SUB} and not _is_electrical(my_workstation(user)):
		frappe.throw(_("Electrical points are for the electrician's workstation"), frappe.PermissionError)
	jobs = [j for j in frappe.get_all("Job Card", filters={"docstatus": ["<", 2], "modified": [">=", frappe.utils.add_days(nowdate(), -60)]},
		fields=["name", "operation", "workstation", "status", "work_order", "item_name", "docstatus"], order_by="modified desc", limit=0)
		if _is_electrical(j.operation) or _is_electrical(j.workstation)]
	done = {}
	for r in (frappe.get_all("SK Electrical Points", filters={"job_card": ["in", [j.name for j in jobs]]},
			fields=["name", "job_card", "total_points", *EL_POINTS], order_by="creation desc") if jobs else []):  # in [''] would match blanks
		done.setdefault(r.job_card, r)
	start = frappe.utils.get_first_day(getdate())
	month = sum(cint(v) for v in frappe.get_all("SK Electrical Points", filters={"date": [">=", start]}, pluck="total_points"))
	out = [{**j, "points": done.get(j.name)} for j in jobs]
	out.sort(key=lambda j: (j["status"] == "Completed", bool(j["points"])))
	return {"jobs": out, "month_total": month, "types": list(EL_POINTS)}

def badges(user: str, functions: list[str]) -> dict:
	out = {}
	if SUB in functions or PRODUCTION in functions:
		out["my_jobs" if SUB in functions else "job_cards"] = len(job_cards(user))
	if PRODUCTION in functions:
		out["order_board"] = frappe.db.count("Work Order", {"docstatus": 1, "status": ["not in", ["Completed", "Stopped", "Closed", "Cancelled"]]})
	return {k: v for k, v in out.items() if v}
