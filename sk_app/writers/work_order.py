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
	from sk_app.production import non_cabin_orders

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
