"""Store screens (SK, 26-Oct-2026 draft F01): stock check, receive, issue to a job, requests, dispatch, low stock,
monthly count and new item. Every record is made under the person's own login; the phone sends photos and taps,
ERPNext keeps the documents (Purchase Receipt, Stock Entry, Material Request, Delivery Note, Stock Reconciliation).

Documents that change money (receipt, dispatch, count) stay as drafts for the owner / Accounts to post; a material
issue to a job is posted at once when ERPNext allows it, otherwise it stays as a draft and the screen says so.
"""

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, nowdate

from sk_app import logins

STORE = "Stores"


def need(user: str, *functions: str):
	"""Only people in the function (or the ERPNext admin) may use its screens. Records are then saved under their
	own login with ignore_permissions, because Store helpers do not carry every ERPNext stock role."""
	if "System Manager" in frappe.get_roles(user):
		return
	have = set(logins.profile_functions(user))
	if not have & set(functions):
		frappe.throw(_("This screen is for {0}").format(" / ".join(functions)), frappe.PermissionError)


def attach(file_url: str | None, doctype: str, name: str, user: str):
	"""Attach a photo the person uploaded from the phone to the ERPNext record."""
	if not file_url:
		return
	file_name = frappe.db.get_value("File", {"file_url": file_url, "owner": user, "attached_to_name": ["is", "not set"]})
	if file_name:
		frappe.db.set_value("File", file_name, {"attached_to_doctype": doctype, "attached_to_name": name})


def insert_for(doc, user: str):
	"""Insert as the system, kept in the person's name. ERPNext fills the supplier's payable account while saving and
	refuses when the person (Store) may not read accounts (SK 27-Oct, Yogesh: "User don't have permissions to
	select/read this account")."""
	current = frappe.session.user
	frappe.set_user("Administrator")
	try:
		doc.flags.ignore_permissions = True
		doc.insert()
	finally:
		frappe.set_user(current)
	frappe.db.set_value(doc.doctype, doc.name, {"owner": user, "modified_by": user}, update_modified=False)
	doc.owner = doc.modified_by = user
	return doc


def try_submit(doc) -> bool:
	"""Post the document if ERPNext accepts it (stock available, accounts set); else keep the draft."""
	frappe.db.savepoint("sk_submit")
	try:
		doc.flags.ignore_permissions = True
		doc.submit()
		return True
	except Exception as e:
		frappe.db.rollback(save_point="sk_submit")
		frappe.clear_messages()
		doc.reload()
		doc.add_comment("Comment", _("Kept as draft by SK App: {0}").format((str(e) or type(e).__name__)[:200]))
		return False


def uom(item_code: str) -> dict:
	"""Unit fields ERPNext wants on every item row (rows made by hand, not mapped from another document)."""
	u = frappe.db.get_value("Item", item_code, "stock_uom")
	return {"uom": u, "stock_uom": u, "conversion_factor": 1}


def _company():
	return frappe.defaults.get_user_default("Company") or frappe.db.get_single_value("Global Defaults", "default_company") \
		or frappe.db.get_value("Company", {}, "name")


# ---------- Stock Check ----------

def stock_search(user: str, q: str | None = None) -> list[dict]:
	need(user, STORE, "Purchase", "Production", "Quality", "Accounts")  # Accounts: bill items without PO (27-Oct)
	q = (q or "").strip()
	filters = {"disabled": 0, "is_stock_item": 1}
	or_filters = None
	if q:
		like = f"%{q}%"
		or_filters = [["item_name", "like", like], ["item_code", "like", like], ["description", "like", like]]
	items = frappe.get_all("Item", filters=filters, or_filters=or_filters, fields=["item_code", "item_name", "item_group", "stock_uom"],
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


# ---------- Receive ----------

def open_purchase_orders(user: str) -> list[dict]:
	need(user, STORE, "Purchase")
	pos = frappe.get_all("Purchase Order", filters={"docstatus": 1, "status": ["in", ["To Receive and Bill", "To Receive"]]},
		fields=["name", "supplier", "supplier_name", "schedule_date", "grand_total"], order_by="schedule_date asc", limit=0)
	for po in pos:
		po["items"] = frappe.get_all("Purchase Order Item", filters={"parent": po.name},
			fields=["name", "item_code", "item_name", "qty", "received_qty", "uom", "warehouse"], order_by="idx asc")
		for i in po["items"]:
			i["pending"] = flt(i.qty) - flt(i.received_qty)
		po["items"] = [i for i in po["items"] if i["pending"] > 0]
		po["late"] = bool(po.schedule_date and getdate(po.schedule_date) < getdate())
	return pos


def receive(user: str, purchase_order: str | None, items: list[dict], challan_photo=None, goods_photo=None, note=None,
		supplier=None, reason=None, bill_no=None) -> dict:
	"""Material at the gate: a draft Purchase Receipt from the PO (or without PO, with a spoken reason), with the
	challan photo. Quality / Store owner posts it after checking."""
	need(user, STORE)
	qty = {i.get("po_detail") or i.get("item_code"): flt(i.get("qty")) for i in items or []}
	if purchase_order:
		from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt

		pr = make_purchase_receipt(purchase_order)
		keep = []
		for row in pr.items:
			got = qty.get(row.purchase_order_item, row.qty) if qty else row.qty
			if flt(got) > 0:
				row.qty = flt(got)
				row.received_qty = flt(got)
				keep.append(row)
		pr.set("items", keep)
	else:
		if not supplier or not (reason or "").strip():
			frappe.throw(_("Without a Purchase Order, please pick the supplier and speak the reason"))
		pr = frappe.new_doc("Purchase Receipt")
		pr.supplier = supplier
		pr.company = _company()
		for code, q in qty.items():
			if q > 0:
				pr.append("items", {"item_code": code, "qty": q, "received_qty": q, **uom(code)})
	if not pr.items:
		frappe.throw(_("Please give the quantity received"))
	pr.posting_date = nowdate()
	if bill_no:  # the supplier's invoice / challan number read from the photo (SK 26-Oct)
		pr.supplier_delivery_note = str(bill_no).strip()[:140]
	remarks = [x for x in (note, reason and _("Without PO: {0}").format(reason)) if x]
	if remarks:
		pr.remarks = "\n".join(remarks)
	insert_for(pr, user)
	attach(challan_photo, "Purchase Receipt", pr.name, user)
	attach(goods_photo, "Purchase Receipt", pr.name, user)
	return {"name": pr.name, "items": len(pr.items)}


# ---------- Issue to a job ----------

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


# ---------- job card names people know (SK 27-Oct, Yogesh: "job card has a number, need cabin customer name & size") ----------

def cabin_size(item: str | None) -> str:
	"""'Prod-0013-12ft x 10ft x 8.6ft' -> '12ft x 10ft x 8.6ft'."""
	import re

	m = re.search(r"\d+(\.\d+)?\s*ft\s*x\s*\d+(\.\d+)?\s*ft(\s*x\s*\d+(\.\d+)?\s*ft)?", item or "", re.I)
	return m.group(0) if m else (item or "")


def job_card_cabin(work_order: str | None) -> str:
	if not work_order:
		return ""
	wo = frappe.db.get_value("Work Order", work_order, ["sales_order", "item_name", "production_item"], as_dict=True)
	if not wo:
		return ""
	customer = frappe.db.get_value("Sales Order", wo.sales_order, "customer_name") if wo.sales_order else None
	return " · ".join(x for x in (customer, cabin_size(wo.item_name or wo.production_item)) if x)[:140]


def set_job_card_cabin(doc, method=None):
	"""Job Card hook: 'Customer · 12ft x 10ft x 8.6ft', shown when picking a job card in ERPNext (Stock Entry etc.)."""
	if doc.meta.has_field("sk_cabin"):
		doc.sk_cabin = job_card_cabin(doc.work_order)


def ensure_job_card_cabin():
	if not frappe.db.exists("DocType", "Job Card"):
		return
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
	from frappe.custom.doctype.property_setter.property_setter import make_property_setter

	create_custom_fields({"Job Card": [{"fieldname": "sk_cabin", "label": "Customer / cabin", "fieldtype": "Data", "insert_after": "work_order",
		"read_only": 1, "in_list_view": 1, "in_standard_filter": 1}]}, update=True)
	make_property_setter("Job Card", None, "search_fields", "sk_cabin,operation,workstation", "Data", validate_fields_for_doctype=False)
	for jc in frappe.get_all("Job Card", filters={"docstatus": ["<", 2], "sk_cabin": ["in", ["", None]]}, fields=["name", "work_order"], limit=0):
		label = job_card_cabin(jc.work_order)
		if label:
			frappe.db.set_value("Job Card", jc.name, "sk_cabin", label, update_modified=False)


def issue(user: str, work_order: str, items: list[dict], taken_by=None, job_card=None, photo=None) -> dict:
	"""Give material to a job: Stock Entry (Material Transfer for Manufacture) from the store to the job's WIP."""
	need(user, STORE)
	items = [i for i in items or [] if i.get("item_code") and flt(i.get("qty")) > 0]
	if not items:
		frappe.throw(_("Please say what is given"))
	wo = frappe.get_doc("Work Order", work_order)
	if wo.docstatus != 1:
		frappe.throw(_("Job {0} is not open").format(work_order))
	source = {r.item_code: r.source_warehouse for r in wo.required_items}
	se = frappe.new_doc("Stock Entry")
	se.stock_entry_type = "Material Transfer for Manufacture"
	se.purpose = "Material Transfer for Manufacture"
	se.work_order = wo.name
	se.company = wo.company
	se.from_bom = 0
	se.to_warehouse = wo.wip_warehouse
	# ERPNext 16 needs each row tied to the job card's material row (SK 27-Oct, Yogesh: "job card item reference is
	# missing"); when an item is not on the job card, the issue stays against the job (work order) only
	card_rows = {r.item_code: r.name for r in frappe.get_all("Job Card Item", filters={"parent": job_card, "parenttype": "Job Card"},
		fields=["name", "item_code"])} if job_card else {}
	use_card = bool(job_card) and all(i["item_code"] in card_rows for i in items)
	if use_card:
		se.job_card = job_card
	for i in items:
		from_wh = i.get("warehouse") or source.get(i["item_code"]) or wo.source_warehouse or _default_store(i["item_code"], wo.company)
		se.append("items", {"item_code": i["item_code"], "qty": flt(i["qty"]), "s_warehouse": from_wh, "t_warehouse": wo.wip_warehouse,
			**({"job_card_item": card_rows[i["item_code"]]} if use_card else {}), **uom(i["item_code"])})
	se.remarks = _("Issued from SK App to {0}").format(taken_by or "-") + (f" · {_('Job card')} {job_card}" if job_card and not use_card else "")
	se.flags.ignore_permissions = True
	se.insert()
	attach(photo, "Stock Entry", se.name, user)
	posted = try_submit(se)
	return {"name": se.name, "posted": posted}


def _default_store(item_code: str, company: str):
	return frappe.db.get_value("Item Default", {"parent": item_code, "company": company}, "default_warehouse") \
		or frappe.db.get_single_value("Stock Settings", "default_warehouse")


# ---------- Material Requests ----------

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


def request_issue(user: str, request: str) -> dict:
	"""Give a transfer / issue request from stock in one tap (Stock Entry from the Material Request)."""
	need(user, STORE)
	from erpnext.stock.doctype.material_request.material_request import make_stock_entry

	se = make_stock_entry(request)
	se.flags.ignore_permissions = True
	se.insert()
	return {"name": se.name, "posted": try_submit(se)}


def request_to_purchase(user: str, request: str) -> dict:
	"""Short quantity of a store request goes to Purchase as a new Material Request (Purchase)."""
	need(user, STORE)
	rows = [r for r in material_requests(user) if r["request"] == request and r["short"]]
	if not rows:
		frappe.throw(_("Nothing is short on {0}").format(request))
	mr = _purchase_request(rows, _("Short for {0}").format(request))
	return {"name": mr.name}


def _purchase_request(rows: list[dict], reason: str):
	mr = frappe.new_doc("Material Request")
	mr.material_request_type = "Purchase"
	mr.company = _company()
	mr.transaction_date = nowdate()
	mr.schedule_date = max((getdate(r.get("needed_by")) for r in rows if r.get("needed_by")), default=getdate())
	if mr.schedule_date < getdate():
		mr.schedule_date = getdate()
	for r in rows:
		mr.append("items", {"item_code": r["item_code"], "qty": flt(r.get("short") or r.get("qty")),
			"schedule_date": mr.schedule_date, "warehouse": r.get("warehouse") or _default_store(r["item_code"], mr.company),
			**uom(r["item_code"])})
	mr.flags.ignore_permissions = True
	mr.insert()
	mr.add_comment("Comment", reason)
	try_submit(mr)
	return mr


# ---------- Low Stock ----------

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
	mr = _purchase_request([{**r, "short": r["order"]} for r in rows], _("Low stock from SK App"))
	return {"name": mr.name, "items": len(rows)}


# ---------- Dispatch ----------

def orders_to_dispatch(user: str) -> list[dict]:
	need(user, STORE, "Production")
	return frappe.get_all("Sales Order", filters={"docstatus": 1, "status": ["in", ["To Deliver and Bill", "To Deliver"]]},
		fields=["name", "customer", "customer_name", "delivery_date", "grand_total", "per_delivered"], order_by="delivery_date asc", limit=0)


def dispatch(user: str, sales_order: str, vehicle_no=None, driver_mobile=None, cabin_photo=None, plate_photo=None, note=None) -> dict:
	"""Cabin leaves the factory: draft Delivery Note from the Sales Order with the photos; Accounts posts it and
	makes the invoice, the salesperson gets a note."""
	need(user, STORE, "Production")
	from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note

	dn = make_delivery_note(sales_order)
	if not dn.items:
		frappe.throw(_("Nothing left to deliver on {0}").format(sales_order))
	dn.vehicle_no = (vehicle_no or "").upper().strip() or None
	dn.instructions = "\n".join(x for x in (driver_mobile and _("Driver: {0}").format(driver_mobile), note) if x) or None
	dn.flags.ignore_permissions = True
	dn.insert()
	attach(cabin_photo, "Delivery Note", dn.name, user)
	attach(plate_photo, "Delivery Note", dn.name, user)
	owner = frappe.db.get_value("Sales Order", sales_order, "owner")
	for who in {owner} | set(_users_with_function("Accounts")):
		if who and who != user:
			_todo(who, "Delivery Note", dn.name, _("Dispatched: {0}. Please make the invoice today.").format(sales_order))
	return {"name": dn.name}


def _users_with_function(function: str) -> list[str]:
	main = frappe.get_all("SK App User", filters={"home": function, "enabled": 1}, pluck="user")
	other = frappe.get_all("SK App User Function", filters={"function": function, "parenttype": "SK App User"}, pluck="parent")
	other = frappe.get_all("SK App User", filters={"name": ["in", other or [""]], "enabled": 1}, pluck="user")
	return list(dict.fromkeys(main + other))


def _todo(user: str, doctype: str, name: str, text: str):
	frappe.get_doc({"doctype": "ToDo", "allocated_to": user, "reference_type": doctype, "reference_name": name,
		"description": text, "priority": "High", "date": nowdate()}).insert(ignore_permissions=True)


# ---------- Monthly stock count ----------

def count_list(user: str, warehouse: str) -> list[dict]:
	need(user, STORE)
	return [{"item_code": b.item_code, "item_name": frappe.db.get_value("Item", b.item_code, "item_name"), "qty": flt(b.actual_qty)}
		for b in frappe.get_all("Bin", filters={"warehouse": warehouse, "actual_qty": ["!=", 0]}, fields=["item_code", "actual_qty"],
			order_by="item_code asc")]


def warehouses(user: str) -> list[str]:
	need(user, STORE, "Production", "Purchase")
	return frappe.get_all("Warehouse", filters={"is_group": 0, "disabled": 0}, pluck="name", order_by="name asc")


def stock_count(user: str, warehouse: str, counts: list[dict], photo=None) -> dict:
	"""Counted quantities that differ from ERPNext go as a draft Stock Reconciliation for the owner / Finance OK."""
	need(user, STORE)
	book = {r["item_code"]: r["qty"] for r in count_list(user, warehouse)}
	diffs = [c for c in counts or [] if c.get("item_code") and c.get("qty") not in (None, "")
		and flt(c["qty"]) != flt(book.get(c["item_code"]))]
	if not diffs:
		return {"name": None, "differences": 0}
	sr = frappe.new_doc("Stock Reconciliation")
	sr.company = frappe.db.get_value("Warehouse", warehouse, "company")
	sr.purpose = "Stock Reconciliation"
	for c in diffs:
		sr.append("items", {"item_code": c["item_code"], "warehouse": warehouse, "qty": flt(c["qty"])})
	sr.flags.ignore_permissions = True
	sr.insert()
	attach(photo, "Stock Reconciliation", sr.name, user)
	return {"name": sr.name, "differences": len(diffs)}


# ---------- New item ----------

def similar_items(user: str, name: str) -> list[dict]:
	need(user, STORE, "Purchase")
	words = [w for w in (name or "").replace("-", " ").split() if len(w) > 2][:4]
	if not words:
		return []
	or_filters = [["item_name", "like", f"%{w}%"] for w in words]
	rows = frappe.get_all("Item", or_filters=or_filters, fields=["item_code", "item_name", "item_group"], limit=50)
	score = lambda r: sum(w.lower() in (r.item_name or "").lower() for w in words)
	return sorted(rows, key=score, reverse=True)[:5]


def new_item(user: str, item_name: str, item_group: str, uom: str, warehouse=None, photo=None) -> dict:
	"""Item made from a photo + voice; kept disabled until the owner (Samir / Store owner) enables it, so no duplicates
	slip into use."""
	need(user, STORE, "Purchase")
	item_name = (item_name or "").strip()
	if not item_name or not item_group or not uom:
		frappe.throw(_("Please give the name, group and unit"))
	if frappe.db.exists("Item", {"item_name": item_name}):
		frappe.throw(_("{0} is already in the item list").format(item_name))
	item = frappe.new_doc("Item")
	item.item_name = item_name
	item.item_code = item_name
	item.item_group = item_group
	item.stock_uom = uom
	item.is_stock_item = 1
	item.disabled = 1
	item.description = _("Made from SK App, waiting for approval")
	if warehouse:
		item.append("item_defaults", {"company": frappe.db.get_value("Warehouse", warehouse, "company"), "default_warehouse": warehouse})
	if photo:
		item.image = photo
	item.flags.ignore_permissions = True
	item.insert()
	attach(photo, "Item", item.name, user)
	for who in _users_with_function("IT / ERP") + _users_with_function("Management")[:1]:
		if who != user:
			_todo(who, "Item", item.name, _("New item from Store: {0}. Check for duplicates and enable it.").format(item_name))
	return {"name": item.name}


def item_options(user: str) -> dict:
	need(user, STORE, "Purchase")
	return {"groups": frappe.get_all("Item Group", filters={"is_group": 0}, pluck="name", order_by="name asc"),
		"uoms": frappe.get_all("UOM", filters={"enabled": 1}, pluck="name", order_by="name asc", limit=0),
		"warehouses": warehouses(user)}


def badges(user: str, functions: list[str]) -> dict:
	"""Red counts on the Store icons (cheap counts only)."""
	if STORE not in functions:
		return {}
	out = {"store_requests": len(material_requests(user)), "low_stock": len(low_stock(user)),
		"receive": frappe.db.count("Purchase Order", {"docstatus": 1, "status": ["in", ["To Receive and Bill", "To Receive"]],
			"schedule_date": ["<=", nowdate()]}),
		"dispatch": frappe.db.count("Sales Order", {"docstatus": 1, "status": ["in", ["To Deliver and Bill", "To Deliver"]],
			"delivery_date": ["<=", nowdate()]})}
	return {k: v for k, v in out.items() if cint(v)}
