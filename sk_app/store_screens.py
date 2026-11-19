"""Store screens (reads only; the Store writers are writers/receipt.py, writers/stock_entry.py, writers/item.py).
Stock check, open POs, receipts to post, open work orders, requests, low stock, dispatch list, count list, badges.
Plan A step 2 (SK 9-Nov): split out of store.py; names unchanged. store.py keeps only the helpers every module shares."""

from frappe import _
from frappe.utils import cint, flt, getdate, nowdate
from sk_app.store import STORE, material_pos, need, uom
import frappe


class as_system:
	"""Run ERPNext's own save / submit as the system after the person's own permission was checked: ERPNext fills
	accounts (tax, debtors, stock) while saving and refuses people who may not read Account (SK 29-Oct, horizontal
	fix of Aditya's "User don't have permissions to select/read this account")."""

	def __enter__(self):
		self.user = frappe.session.user
		frappe.set_user("Administrator")

	def __exit__(self, *exc):
		frappe.set_user(self.user)
		return False

def stock_search(user: str, q: str | None = None) -> list[dict]:
	# Accounts: bill items without PO (27-Oct); HR: Aarti's requisitions (SK 28-Oct)
	need(user, STORE, "Purchase", "Production", "Quality", "Accounts", "HR", "Management")
	q = (q or "").strip()
	filters = {"disabled": 0, "is_stock_item": 1}
	if q:
		# SK 28-Oct (Rev 1 point 13): every word may be anywhere, so "c channel 100" finds "C-Channel 100x50"
		from sk_app.item_input import find_items

		codes = [r["item_code"] for r in find_items(q, 40)]
		filters["item_code"] = ["in", codes or [""]]
	items = frappe.get_all("Item", filters=filters, fields=["item_code", "item_name", "item_group", "stock_uom"],
		order_by="item_name asc", limit=40 if q else 0)
	codes = [i.item_code for i in items]
	if not codes:
		return []
	bins = frappe.get_all("Bin", filters={"item_code": ["in", codes]},
		fields=["item_code", "warehouse", "actual_qty", "stock_value", "projected_qty"])
	levels = _reorder_levels(codes)
	by = {}
	for b in bins:
		by.setdefault(b.item_code, []).append(b)
	out = []
	for i in items:
		rows = [b for b in by.get(i.item_code, []) if flt(b.actual_qty)]
		qty = sum(flt(b.actual_qty) for b in rows)
		level = sum(levels.get(i.item_code, {}).values())
		out.append({"item_code": i.item_code, "item_name": i.item_name, "group": i.item_group, "uom": i.stock_uom,
			"qty": qty, "value": sum(flt(b.stock_value) for b in rows), "low": bool(level and qty < level),
			"warehouses": [{"warehouse": b.warehouse, "qty": flt(b.actual_qty)} for b in rows]})
	if not q:
		out.sort(key=lambda r: -r["value"])
		out = out[:40]
	return out

def item_detail(user: str, item_code: str) -> dict:
	need(user, STORE, "Purchase", "Production", "Quality")
	sle = lambda sign: frappe.get_all("Stock Ledger Entry", filters={"item_code": item_code, "is_cancelled": 0,
		"actual_qty": [">" if sign > 0 else "<", 0]}, fields=["posting_date", "actual_qty", "voucher_type", "voucher_no", "warehouse"],
		order_by="posting_date desc, creation desc", limit=3)
	jobs = frappe.get_all("Stock Entry Detail", filters={"item_code": item_code, "docstatus": 1},
		fields=["parent", "qty"], order_by="creation desc", limit=10)
	wos = {}
	for j in jobs:
		wo = frappe.db.get_value("Stock Entry", j.parent, "work_order")
		if wo and wo not in wos:
			wos[wo] = j.qty
	item = frappe.db.get_value("Item", item_code, ["item_code", "item_name", "stock_uom", "item_group", "image"], as_dict=True)
	return {**(item or {}), "received": sle(1), "issued": sle(-1),
		"jobs": [{"work_order": k, "qty": v} for k, v in list(wos.items())[:5]],
		"bins": frappe.get_all("Bin", filters={"item_code": item_code, "actual_qty": ["!=", 0]}, fields=["warehouse", "actual_qty"])}

def open_purchase_orders(user: str) -> list[dict]:
	need(user, STORE, "Purchase", "Accounts")  # SK 2-Nov: Accounts receives material too (Receive screen)
	pos = frappe.get_all("Purchase Order", filters={"docstatus": 1, "status": ["in", ["To Receive and Bill", "To Receive"]], **material_pos()},
		fields=["name", "supplier", "supplier_name", "schedule_date", "grand_total"], order_by="schedule_date asc", limit=0)
	for po in pos:
		po["items"] = frappe.get_all("Purchase Order Item", filters={"parent": po.name},
			fields=["name", "item_code", "item_name", "qty", "received_qty", "uom", "warehouse"], order_by="idx asc")
		for i in po["items"]:
			i["pending"] = flt(i.qty) - flt(i.received_qty)
		po["items"] = [i for i in po["items"] if i["pending"] > 0]
		po["late"] = bool(po.schedule_date and getdate(po.schedule_date) < getdate())
	return pos

def receipts_to_post(user: str) -> list[dict]:
	"""Draft receipts waiting for the store's check and Post (stock goes up only when posted)."""
	need(user, STORE, "Accounts")  # SK 2-Nov: Accounts receives material like Store
	rows = frappe.get_all("Purchase Receipt", filters={"docstatus": 0, **material_pos("Purchase Receipt")}, fields=["name", "supplier", "supplier_name", "posting_date",
		"owner", "supplier_delivery_note", "grand_total", "remarks"], order_by="creation desc", limit=50)
	for r in rows:
		r["items"] = frappe.get_all("Purchase Receipt Item", filters={"parent": r.name}, fields=["item_code", "item_name", "qty", "uom", "rate"],
			order_by="idx asc")
		r["by"] = frappe.utils.get_fullname(r.owner)
		r["posting_date"] = str(r.posting_date)
		r["reason"] = frappe.db.get_value("Comment", {"reference_doctype": "Purchase Receipt", "reference_name": r.name,
			"content": ["like", "Kept as draft%"]}, "content", order_by="creation desc")
	return rows

def open_work_orders(user: str) -> list[dict]:
	need(user, STORE, "Production")
	wos = frappe.get_all("Work Order", filters={"docstatus": 1, "status": ["not in", ["Completed", "Stopped", "Closed", "Cancelled"]]},
		fields=["name", "production_item", "item_name", "qty", "wip_warehouse", "sales_order", "expected_delivery_date"],
		order_by="expected_delivery_date asc, creation asc", limit=0)
	for wo in wos:
		wo["items"] = frappe.get_all("Work Order Item", filters={"parent": wo.name},
			fields=["item_code", "item_name", "required_qty", "transferred_qty", "source_warehouse"], order_by="idx asc")
		wo["job_cards"] = frappe.get_all("Job Card", filters={"work_order": wo.name, "docstatus": ["<", 2]},
			fields=["name", "operation", "workstation"], order_by="sequence_id asc, creation asc")
		wo["customer"] = frappe.db.get_value("Sales Order", wo.sales_order, "customer_name") if wo.sales_order else None
		wo["size"] = cabin_size(wo.item_name or wo.production_item)
	return wos

def cabin_size(item: str | None) -> str:
	"""'Prod-0013-12ft x 10ft x 8.6ft' -> '12ft x 10ft x 8.6ft'."""
	import re

	m = re.search(r"\d+(\.\d+)?\s*ft\s*x\s*\d+(\.\d+)?\s*ft(\s*x\s*\d+(\.\d+)?\s*ft)?", item or "", re.I)
	return m.group(0) if m else (item or "")

def job_card_cabin(work_order: str | None) -> str:
	if not work_order:
		return ""
	from sk_app import cabin_projects

	wo = frappe.db.get_value("Work Order", work_order, ["sales_order", "project", "item_name", "production_item"], as_dict=True)
	if not wo:
		return ""
	customer = frappe.db.get_value("Sales Order", wo.sales_order, "customer_name") if wo.sales_order \
		else cabin_projects.project_customer(wo.project)  # SK 29-Oct: cabin Project while the order is a draft
	parts = (cabin_projects.cabin_no(wo.project), customer, cabin_size(wo.item_name or wo.production_item))
	return " · ".join(x for x in parts if x)[:140]

def set_job_card_cabin(doc, method=None):
	"""Job Card hook: 'Customer · 12ft x 10ft x 8.6ft', shown when picking a job card in ERPNext (Stock Entry etc.)."""
	if doc.meta.has_field("sk_cabin"):
		doc.sk_cabin = job_card_cabin(doc.work_order)

def _default_store(item_code: str, company: str):
	return frappe.db.get_value("Item Default", {"parent": item_code, "company": company}, "default_warehouse") \
		or frappe.db.get_single_value("Stock Settings", "default_warehouse")

def material_requests(user: str, kind: str = "store") -> list[dict]:
	"""Open requests. Store sees transfer / issue requests (to give from stock); Purchase sees purchase requests."""
	need(user, STORE, "Purchase", "Production")
	types = ["Purchase"] if kind == "purchase" else ["Material Transfer", "Material Issue", "Manufacture"]
	mrs = frappe.get_all("Material Request", filters={"docstatus": 1, "material_request_type": ["in", types],
		"status": ["not in", ["Stopped", "Cancelled", "Transferred", "Issued", "Ordered", "Received"]]},
		fields=["name", "material_request_type", "schedule_date", "owner", "transaction_date", "creation", "work_order"],
		order_by="schedule_date asc, creation asc", limit=0)
	out = []
	for mr in mrs:
		rows = frappe.get_all("Material Request Item", filters={"parent": mr.name},
			fields=["name", "item_code", "item_name", "qty", "ordered_qty", "uom", "warehouse", "schedule_date"], order_by="idx asc")
		for r in rows:
			pending = flt(r.qty) - flt(r.ordered_qty)
			if pending <= 0:
				continue
			stock = sum(frappe.get_all("Bin", filters={"item_code": r.item_code}, pluck="actual_qty")) if kind != "purchase" else None
			out.append({"request": mr.name, "row": r.name, "item_code": r.item_code, "item_name": r.item_name, "qty": pending,
				"uom": r.uom, "needed_by": str(r.schedule_date or mr.schedule_date or ""), "by": frappe.utils.get_fullname(mr.owner),
				"work_order": mr.work_order, "age_hours": round((frappe.utils.now_datetime() - mr.creation).total_seconds() / 3600, 1),
				"stock": stock, "short": max(0, pending - flt(stock)) if stock is not None else None})
	return out

def request_to_purchase(user: str, request: str) -> dict:
	"""Short quantity of a store request goes to Purchase as a new Material Request (Purchase)."""
	need(user, STORE)
	rows = [r for r in material_requests(user) if r["request"] == request and r["short"]]
	if not rows:
		frappe.throw(_("Nothing is short on {0}").format(request))
	mr = _purchase_request(user, rows, _("Short for {0}").format(request))
	return {"name": mr.name}

def _purchase_request(user: str, rows: list[dict], reason: str):
	"""SK 27-Oct: short / low stock goes the requisition route too (waits for the CEO's approval)."""
	from sk_app.purchase_screens import from_store_request

	return from_store_request(user, rows, reason)

def _reorder_levels(codes: list[str] | None = None) -> dict:
	filters = {"parenttype": "Item"}
	if codes:
		filters["parent"] = ["in", codes]
	out = {}
	for r in frappe.get_all("Item Reorder", filters=filters, fields=["parent", "warehouse", "warehouse_reorder_level", "warehouse_reorder_qty"]):
		out.setdefault(r.parent, {})[r.warehouse] = flt(r.warehouse_reorder_level)
	return out

def low_stock(user: str) -> list[dict]:
	need(user, STORE, "Purchase")
	rows = frappe.get_all("Item Reorder", filters={"parenttype": "Item"},
		fields=["parent", "warehouse", "warehouse_reorder_level", "warehouse_reorder_qty"])
	out = []
	for r in rows:
		have = flt(frappe.db.get_value("Bin", {"item_code": r.parent, "warehouse": r.warehouse}, "projected_qty"))
		if have < flt(r.warehouse_reorder_level):
			out.append({"item_code": r.parent, "item_name": frappe.db.get_value("Item", r.parent, "item_name"), "warehouse": r.warehouse,
				"qty": have, "level": flt(r.warehouse_reorder_level), "order": flt(r.warehouse_reorder_qty) or flt(r.warehouse_reorder_level) - have})
	return sorted(out, key=lambda x: x["qty"] / (x["level"] or 1))

def order_low(user: str, item_codes: list[str] | None = None) -> dict:
	need(user, STORE, "Purchase")
	rows = [r for r in low_stock(user) if not item_codes or r["item_code"] in item_codes]
	if not rows:
		frappe.throw(_("Nothing is below the re-order level"))
	mr = _purchase_request(user, [{**r, "short": r["order"]} for r in rows], _("Low stock from SK App"))
	return {"name": mr.name, "items": len(rows)}

def orders_to_dispatch(user: str) -> list[dict]:
	need(user, STORE, "Production")
	return frappe.get_all("Sales Order", filters={"docstatus": 1, "status": ["in", ["To Deliver and Bill", "To Deliver"]]},
		fields=["name", "customer", "customer_name", "delivery_date", "grand_total", "per_delivered"], order_by="delivery_date asc", limit=0)

def count_list(user: str, warehouse: str) -> list[dict]:
	need(user, STORE)
	return [{"item_code": b.item_code, "item_name": frappe.db.get_value("Item", b.item_code, "item_name"), "qty": flt(b.actual_qty)}
		for b in frappe.get_all("Bin", filters={"warehouse": warehouse, "actual_qty": ["!=", 0]}, fields=["item_code", "actual_qty"],
			order_by="item_code asc")]

def warehouses(user: str) -> list[str]:
	need(user, STORE, "Production", "Purchase")
	return frappe.get_all("Warehouse", filters={"is_group": 0, "disabled": 0}, pluck="name", order_by="name asc")

def similar_items(user: str, name: str) -> list[dict]:
	need(user, STORE, "Purchase")
	words = [w for w in (name or "").replace("-", " ").split() if len(w) > 2][:4]
	if not words:
		return []
	or_filters = [["item_name", "like", f"%{w}%"] for w in words]
	rows = frappe.get_all("Item", or_filters=or_filters, fields=["item_code", "item_name", "item_group"], limit=50)
	score = lambda r: sum(w.lower() in (r.item_name or "").lower() for w in words)
	return sorted(rows, key=score, reverse=True)[:5]

def item_options(user: str) -> dict:
	need(user, STORE, "Purchase")
	return {"groups": frappe.get_all("Item Group", filters={"is_group": 0}, pluck="name", order_by="name asc"),
		"uoms": frappe.get_all("UOM", filters={"enabled": 1}, pluck="name", order_by="name asc", limit=0),
		"warehouses": warehouses(user)}

def _ready() -> list:
	from sk_app.flows import ready_to_dispatch

	return ready_to_dispatch()

def badges(user: str, functions: list[str]) -> dict:
	"""Red counts on the Store icons (cheap counts only)."""
	if STORE not in functions:
		return {}
	out = {"store_requests": len(material_requests(user)), "low_stock": len(low_stock(user)),
		"receive": frappe.db.count("Purchase Order", {"docstatus": 1, "status": ["in", ["To Receive and Bill", "To Receive"]],
			"schedule_date": ["<=", nowdate()], **material_pos()}),
		# SK 1-Nov logic check B6: finished cabins not yet dispatched (same list as the Factory and Store arrows)
		"dispatch": len(_ready())}
	return {k: v for k, v in out.items() if cint(v)}
