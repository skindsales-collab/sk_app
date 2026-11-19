"""The one Production writer (linear flow map, Flow 5). On the New path of Production:

order line -> make(): Work Order with the cabin's BOM, posted at once so ERPNext makes the stage Job Cards
stage done (production.done) -> Job Card posted -> when every stage is done, finish(): the cabin goes to finished stock
(Stock Entry Manufacture) by itself; when ERPNext refuses, the draft stays with the reason and Production is told.

Screens are unchanged (Order Board, Job Cards, Ready to Dispatch); the rules also run on every Work Order and Job Card
saved in ERPNext or through SK Hub."""

import frappe
from frappe import _
from frappe.utils import flt, nowdate

from sk_app.core.rules import report
from sk_app.writers.work_order_rules import OPEN_WO, all_done, card_problems, finish_qty, wo_problems

MODULE = "Production"


def _use_new(user=None) -> bool:
	from sk_app.core.switch import use_new

	return use_new(MODULE, user or frappe.session.user)


def _non_cabin(sales_order) -> bool:
	from sk_app.production_screens import non_cabin_orders

	return bool(sales_order) and sales_order in non_cabin_orders()


# ---------- order line -> work order ----------

def make(user: str, sales_order: str, so_item: str) -> dict:
	"""One work order for one order line (what is not yet ordered), posted so the stage cards exist at once."""
	from sk_app import store
	from sk_app.erp_flow import _warehouses

	store.need(user, MODULE, "Management")
	it = frappe.db.get_value("Sales Order Item", {"name": so_item, "parent": sales_order}, ["item_code", "qty", "delivery_date"], as_dict=True)
	if not it:
		frappe.throw(_("Order line not found"))
	so = frappe.db.get_value("Sales Order", sales_order, ["company", "project", "delivery_date"], as_dict=True)
	bom = frappe.db.get_value("BOM", {"item": it.item_code, "is_default": 1, "is_active": 1, "docstatus": 1})
	made = flt(frappe.db.sql("""select sum(qty) from `tabWork Order` where sales_order=%s and sales_order_item=%s and docstatus<2""",
		(sales_order, so_item))[0][0])
	qty = max(flt(it.qty) - made, 0)
	delivery = it.delivery_date or so.delivery_date
	found = wo_problems(it.item_code, bom, qty, sales_order, so.project, delivery, _non_cabin(sales_order))
	report(MODULE, None, found, title=_("Work order data missing"))
	if not bom or qty <= 0:
		frappe.throw(_("No BOM for {0} yet: Design must make and submit the BOM first").format(it.item_code) if not bom
			else _("This order line already has its work order"))
	wo = frappe.get_doc({"doctype": "Work Order", "production_item": it.item_code, "bom_no": bom, "qty": qty, "sales_order": sales_order,
		"sales_order_item": so_item, "company": so.company, "project": so.project, "expected_delivery_date": delivery,
		"planned_start_date": nowdate(), **_warehouses(so.company)})
	if hasattr(wo, "get_items_and_operations_from_bom"):
		wo.get_items_and_operations_from_bom()  # stages (operations) become the factory's job cards at submit
	store.insert_for(wo, user)
	posted = store.try_submit(wo)
	return {"name": wo.name, "qty": wo.qty, "posted": posted, "reason": store.draft_reason()}


def on_validate(doc, method=None):
	"""Every Work Order on the New path of Production: item, BOM, order / project, quantity, delivery date, cabin only."""
	if doc.docstatus == 2 or not _use_new(doc.owner):
		return
	found = wo_problems(doc.production_item, doc.bom_no, doc.qty, doc.sales_order, doc.get("project"), doc.expected_delivery_date,
		_non_cabin(doc.sales_order))
	report(MODULE, doc, found, title=_("Work order data missing"))


# ---------- stage cards ----------

def _photos(job_card: str) -> int:
	return frappe.db.count("File", {"attached_to_doctype": "Job Card", "attached_to_name": job_card}) if job_card else 0


def card_validate(doc, method=None):
	"""Every Job Card on the New path: work order, stage, workstation; a done stage carries a photo."""
	if doc.docstatus == 2 or not _use_new(doc.owner):
		return
	report(MODULE, doc, card_problems(doc.work_order, doc.operation, doc.workstation, doc.status, _photos(doc.name)), title=_("Stage data missing"))


def _cards(work_order: str) -> list[dict]:
	return frappe.get_all("Job Card", filters={"work_order": work_order, "docstatus": ["<", 2]},
		fields=["name", "status", "docstatus", "total_completed_qty as completed_qty"])


# ---------- finished cabin to stock ----------

def finish(user: str, work_order: str, *, tell=True) -> dict:
	"""Every stage done: the cabin is booked into finished stock (Stock Entry Manufacture). Kept as a draft with the
	reason when ERPNext refuses (material not issued, no rate ...), and Production is told."""
	from erpnext.manufacturing.doctype.work_order.work_order import make_stock_entry

	from sk_app import store

	wo = frappe.db.get_value("Work Order", work_order, ["name", "qty", "produced_qty", "status", "docstatus", "item_name"], as_dict=True)
	if not wo or wo.docstatus != 1:
		frappe.throw(_("Work order {0} is not posted").format(work_order))
	qty = finish_qty(wo.qty, wo.produced_qty)
	if qty <= 0 or wo.status in OPEN_WO:
		return {"name": None, "posted": False, "reason": _("Already in finished stock")}
	se = frappe.get_doc(make_stock_entry(work_order, "Manufacture", qty))
	se.remarks = _("Finished by SK App: every stage of {0} done").format(wo.item_name or work_order)
	store.insert_for(se, user)
	posted = store.try_submit(se)
	if not posted and tell:
		for p in store.users_or_ceo(MODULE):
			store._todo(p, "Stock Entry", se.name, _("Cabin finished but not in stock yet: {0}").format(store.draft_reason() or ""))
	return {"name": se.name, "posted": posted, "reason": store.draft_reason()}


def on_card_submit(doc, method=None):
	"""A posted stage card: when it was the last open stage of its work order, the cabin goes to finished stock."""
	if not doc.work_order or not _use_new(doc.owner):
		return
	if all_done(_cards(doc.work_order)):
		try:
			finish(doc.owner or frappe.session.user, doc.work_order)
		except Exception:
			frappe.log_error(f"SK App finish {doc.work_order}")


# ---------- Plan A step 1 (SK 9-Nov): the Production screens' save actions, moved here unchanged from production.py ----------
from frappe import _
from frappe.utils import cint, flt, getdate, now_datetime, nowdate, time_diff_in_seconds
from sk_app.store import _todo, _users_with_function, attach, draft_reason, need, try_submit, uom, users_or_ceo
import frappe
from sk_app.production_screens import EL_POINTS, PRODUCTION, SUB, _card_for, _is_sub_only, _open_log, my_workstation


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
	for q in users_or_ceo("Quality"):  # SK 1-Nov: never to nobody
		_todo(q, "Job Card", jc.name, _("Stage done, self-checked ({0} Not OK), please check: {1} · {2}").format(bad, jc.operation,
			jc.item_name or jc.production_item))
	return {"name": jc.name, "posted": posted, "reason": draft_reason(), "self_check": self_check}

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

	on_points(job_card)  # electrical labour PO is per point, so it waits for the points
	return {"name": doc.name, "total_points": doc.total_points}


# ---------- Plan A (SK 9-Nov): moved here unchanged from erp_flow.py ----------
from frappe import _
from frappe.utils import flt, nowdate
from sk_app import store
from sk_app.erp_flow import _warehouses
import frappe


def make_work_order(user: str, sales_order: str, so_item: str) -> dict:
	"""Step 5 (Production): a Work Order for one order line with its default BOM; Design makes the BOM first when the
	cabin is new (the app says so instead of failing)."""
	from sk_app.store import need

	need(user, "Production", "Management")
	it = frappe.db.get_value("Sales Order Item", {"name": so_item, "parent": sales_order}, ["item_code", "qty", "delivery_date"], as_dict=True)
	if not it:
		frappe.throw(_("Order line not found"))
	bom = frappe.db.get_value("BOM", {"item": it.item_code, "is_default": 1, "is_active": 1, "docstatus": 1})
	if not bom:
		frappe.throw(_("No BOM for {0} yet: Design must make and submit the BOM first").format(it.item_code))
	made = flt(frappe.db.sql("""select sum(qty) from `tabWork Order` where sales_order=%s and sales_order_item=%s and docstatus<2""",
		(sales_order, so_item))[0][0])
	company = frappe.db.get_value("Sales Order", sales_order, "company")
	wo = frappe.get_doc({"doctype": "Work Order", "production_item": it.item_code, "bom_no": bom, "qty": max(flt(it.qty) - made, 1),
		"sales_order": sales_order, "sales_order_item": so_item, "company": company,
		"expected_delivery_date": it.delivery_date, "planned_start_date": nowdate(), **_warehouses(company)})
	if hasattr(wo, "get_items_and_operations_from_bom"):  # stages (operations) become the factory's job cards
		wo.get_items_and_operations_from_bom()
	store.insert_for(wo, user)  # need() above: Production / CEO only; accounts / warehouses read by the system
	return {"name": wo.name, "qty": wo.qty}
