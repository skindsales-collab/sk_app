"""Production screens (SK, 26-Oct-2026 draft F03): Order Board, Job Cards, Need Material, Progress Photos, Ready to
Dispatch for the Production manager, and a very small screen for each subcontractor: only the Job Cards of his own
workstation, with Start / Photo / Done.

Done closes the Job Card's time log and tries to post it; when ERPNext refuses (for example material not yet issued
to the job) the card keeps the time and photos as a draft and Production / Quality are told, so work is never lost.
"""

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, now_datetime, nowdate, time_diff_in_seconds

from sk_app.store import _todo, _users_with_function, attach, need, try_submit, uom

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


def order_board(user: str) -> list[dict]:
	"""Every cabin in production with its stages (Job Cards in route order) and whether it is late."""
	need(user, PRODUCTION, "Quality", "Stores", "Management", "Sales")
	wos = frappe.get_all("Work Order", filters={"docstatus": 1, "status": ["not in", ["Completed", "Stopped", "Closed", "Cancelled"]]},
		fields=["name", "production_item", "item_name", "qty", "status", "sales_order", "expected_delivery_date", "planned_start_date"],
		order_by="expected_delivery_date asc, planned_start_date asc")
	for w in wos:
		w["stages"] = [_stage(j) for j in frappe.get_all("Job Card", filters={"work_order": w.name, "docstatus": ["<", 2]},
			fields=["name", "operation", "workstation", "status", "docstatus", "sequence_id", "total_completed_qty"], order_by="sequence_id asc, creation asc")]
		w["customer"] = frappe.db.get_value("Sales Order", w.sales_order, "customer_name") if w.sales_order else None
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
		wo = frappe.db.get_value("Work Order", work_order, ["item_name", "production_item", "sales_order"], as_dict=True) or {}
		customer = frappe.db.get_value("Sales Order", wo.get("sales_order"), "customer_name") if wo.get("sales_order") else None
		cache[work_order] = " · ".join(x for x in (customer, wo.get("item_name") or wo.get("production_item")) if x) or work_order
	return cache[work_order]


def wo_customer(work_order: str | None) -> str | None:
	wo = frappe.db.get_value("Work Order", work_order, ["sales_order", "project"], as_dict=True) if work_order else None
	if not wo:
		return None
	if wo.sales_order:
		return frappe.db.get_value("Sales Order", wo.sales_order, "customer_name")
	customer = frappe.db.get_value("Project", wo.project, "customer") if wo.project else None
	return frappe.db.get_value("Customer", customer, "customer_name") if customer else None


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
		"production_item", "item_name", "expected_start_date", "sequence_id"], order_by="expected_start_date asc, creation asc", limit=0)
	order = {"Work In Progress": 0, "Material Transferred": 1, "On Hold": 2}
	for r in rows:
		r["started"] = _open_log(r.name)
		r["photos"] = frappe.db.count("File", {"attached_to_doctype": "Job Card", "attached_to_name": r.name})
		r["drawing"] = _drawing(r.work_order)
		r["customer"] = wo_customer(r.work_order)
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


def start(user: str, job_card: str, photo=None) -> dict:
	jc = _card_for(user, job_card)
	if _open_log(jc.name):
		return {"name": jc.name, "status": jc.status}
	jc.append("time_logs", {"from_time": now_datetime(), "completed_qty": 0})
	jc.status = "Work In Progress"
	jc.flags.ignore_permissions = True
	jc.flags.ignore_validate = True  # route checks (material transferred, sequence) stay with ERPNext when posting
	jc.save()
	attach(photo, "Job Card", jc.name, user)
	return {"name": jc.name, "status": jc.status}


def add_photo(user: str, job_card: str, photo: str, note=None) -> dict:
	jc = _card_for(user, job_card)
	if not photo and not note:
		frappe.throw(_("Please take a photo"))
	attach(photo, "Job Card", jc.name, user)
	if note:
		jc.add_comment("Comment", note)
	return {"ok": True}


def done(user: str, job_card: str, photos=None, workers=None, remark=None, checks=None) -> dict:
	"""Job finished: the worker's own check sheet first (SK 28-Oct), then the time log closed with the quantity, photos
	and spoken remark saved; Quality (Aditya) gets a check task with the self-check beside it."""
	from sk_app import quality

	jc = _card_for(user, job_card)
	quality.check_points(checks)  # no check sheet, no Done
	now = now_datetime()
	open_rows = [r for r in jc.time_logs if r.from_time and not r.to_time]
	if not open_rows:
		jc.append("time_logs", {"from_time": now, "to_time": now, "completed_qty": jc.for_quantity, "time_in_mins": 0})
	for r in open_rows:
		r.to_time = now
		r.time_in_mins = time_diff_in_seconds(now, r.from_time) / 60
		r.completed_qty = jc.for_quantity
	jc.total_completed_qty = flt(jc.for_quantity)
	jc.status = "Completed"
	jc.flags.ignore_permissions = True
	jc.flags.ignore_validate = True
	jc.save()
	for p in photos or []:
		attach(p, "Job Card", jc.name, user)
	notes = [x for x in (cint(workers) and _("Workers used: {0}").format(cint(workers)), remark) if x]
	if notes:
		jc.add_comment("Comment", "\n".join(notes))
	self_check = quality.save_self(user, jc.name, checks, photos)
	posted = try_submit(frappe.get_doc("Job Card", jc.name))
	bad = sum(1 for c in checks if c.get("specification") and not cint(c.get("ok")))
	for q in _users_with_function("Quality"):
		_todo(q, "Job Card", jc.name, _("Stage done, self-checked ({0} Not OK), please check: {1} · {2}").format(bad, jc.operation,
			jc.item_name or jc.production_item))
	return {"name": jc.name, "posted": posted, "self_check": self_check}


def need_material(user: str, items: list[dict], job_card=None, work_order=None, needed_by=None, spoken=None) -> dict:
	"""Material asked from the job: a Material Request (transfer to the job) for Store; anything the app could not
	match to an item goes to Store as a task with the spoken words, so nothing is lost."""
	need(user, PRODUCTION, SUB)
	if job_card:
		jc = _card_for(user, job_card)
		work_order = jc.work_order
	wo = frappe.get_doc("Work Order", work_order) if work_order else None
	items = [i for i in items or [] if i.get("item_code") and flt(i.get("qty")) > 0]
	out = {}
	if items:
		mr = frappe.new_doc("Material Request")
		mr.material_request_type = "Material Transfer"
		mr.company = wo.company if wo else frappe.db.get_value("Company", {}, "name")
		mr.transaction_date = nowdate()
		mr.schedule_date = getdate(needed_by or nowdate())
		if wo:
			mr.work_order = wo.name
		for i in items:
			src = frappe.db.get_value("Item Default", {"parent": i["item_code"], "company": mr.company}, "default_warehouse") \
				or frappe.db.get_single_value("Stock Settings", "default_warehouse")
			mr.append("items", {"item_code": i["item_code"], "qty": flt(i["qty"]), "schedule_date": mr.schedule_date,
				"warehouse": (wo.wip_warehouse if wo else src), "from_warehouse": src, **uom(i["item_code"])})
		mr.flags.ignore_permissions = True
		mr.insert()
		if spoken:
			mr.add_comment("Comment", spoken)
		try_submit(mr)
		out["request"] = mr.name
	elif (spoken or "").strip():
		ref = ("Job Card", job_card) if job_card else ("Work Order", work_order) if work_order else (None, None)
		for s in _users_with_function("Stores"):
			_todo(s, ref[0], ref[1], _("Material needed ({0}): {1}").format(frappe.utils.get_fullname(user), spoken))
		out["task"] = True
	else:
		frappe.throw(_("Please say what material you need"))
	return out


def progress_photo(user: str, work_order: str, photo: str, note=None) -> dict:
	need(user, PRODUCTION)
	attach(photo, "Work Order", work_order, user)
	if note:
		frappe.get_doc("Work Order", work_order).add_comment("Comment", note)
	return {"ok": True}


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
	jobs = [j for j in frappe.get_all("Job Card", filters={"docstatus": ["<", 2], "modified": [">=", frappe.utils.add_days(nowdate(), -60)]},
		fields=["name", "operation", "workstation", "status", "work_order", "item_name", "docstatus"], order_by="modified desc", limit=0)
		if _is_electrical(j.operation) or _is_electrical(j.workstation)]
	done = {}
	for r in frappe.get_all("SK Electrical Points", filters={"job_card": ["in", [j.name for j in jobs] or [""]]},
			fields=["name", "job_card", "total_points", *EL_POINTS], order_by="creation desc"):
		done.setdefault(r.job_card, r)
	start = frappe.utils.get_first_day(getdate())
	month = sum(cint(v) for v in frappe.get_all("SK Electrical Points", filters={"date": [">=", start]}, pluck="total_points"))
	out = [{**j, "points": done.get(j.name)} for j in jobs]
	out.sort(key=lambda j: (j["status"] == "Completed", bool(j["points"])))
	return {"jobs": out, "month_total": month, "types": list(EL_POINTS)}


def save_el_points(user: str, job_card: str, points: dict, photo=None, note=None) -> dict:
	need(user, PRODUCTION, SUB, "Quality")
	jc = frappe.db.get_value("Job Card", job_card, ["name", "work_order", "item_name", "operation", "workstation"], as_dict=True)
	if not jc:
		frappe.throw(_("Job {0} not found").format(job_card))
	if _is_sub_only(user) and jc.workstation != my_workstation(user):
		frappe.throw(_("This job is not on your workstation"), frappe.PermissionError)
	name = frappe.db.get_value("SK Electrical Points", {"job_card": job_card})
	doc = frappe.get_doc("SK Electrical Points", name) if name else frappe.new_doc("SK Electrical Points")
	doc.update({"job_card": job_card, "work_order": jc.work_order, "cabin": jc.item_name, "user": user, "date": nowdate(),
		**{f: max(0, cint((points or {}).get(f))) for f in EL_POINTS}})
	if note:
		doc.note = note
	if photo:
		doc.photo = photo
	doc.save(ignore_permissions=True)
	attach(photo, "SK Electrical Points", doc.name, user)
	from sk_app.sub_bills import on_points

	on_points(job_card)  # electrical bill is per point, so it waits for the points
	return {"name": doc.name, "total_points": doc.total_points}


def badges(user: str, functions: list[str]) -> dict:
	out = {}
	if SUB in functions or PRODUCTION in functions:
		out["my_jobs" if SUB in functions else "job_cards"] = len(job_cards(user))
	if PRODUCTION in functions:
		out["order_board"] = frappe.db.count("Work Order", {"docstatus": 1, "status": ["not in", ["Completed", "Stopped", "Closed", "Cancelled"]]})
	return {k: v for k, v in out.items() if v}
