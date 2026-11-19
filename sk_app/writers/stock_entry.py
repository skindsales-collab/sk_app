"""The one Stock Entry writer (linear flow map, Flow 4 Store). Material given to a job from the app is one Stock Entry
(Material Transfer for Manufacture) from the store to the job's WIP, tied to the job card's rows when it can be. Used
on the New path of Store; the rules also run on every Stock Entry saved in ERPNext or through SK Hub."""

import frappe
from frappe import _
from frappe.utils import flt

from sk_app.core.rules import report
from sk_app.writers.stock_entry_rules import TO_JOB, issue_rows, problems


def write(user: str, wo, items: list[dict], *, taken_by=None, job_card=None, photo=None, default_store, uom, insert_for, attach,
		submit_for) -> dict:
	source = {r.item_code: r.source_warehouse for r in wo.required_items}
	card_rows = {r.item_code: r.name for r in frappe.get_all("Job Card Item", filters={"parent": job_card, "parenttype": "Job Card"},
		fields=["name", "item_code"])} if job_card else {}
	wip = wo.wip_warehouse or wip_warehouse(wo)  # Mac test 9-Nov: 14 of 15 live Work Orders had no WIP warehouse
	rows, use_card = issue_rows(items, source, wo.source_warehouse, wip, card_rows)
	se = frappe.new_doc("Stock Entry")
	se.stock_entry_type = se.purpose = TO_JOB
	se.work_order = wo.name
	se.company = wo.company
	se.from_bom = 0
	se.to_warehouse = wip
	if use_card:
		se.job_card = job_card
	for r in rows:
		r["s_warehouse"] = r["s_warehouse"] or default_store(r["item_code"], wo.company)
		se.append("items", {**r, **uom(r["item_code"])})
	se.remarks = _("Issued from SK App to {0}").format(taken_by or "-") + (f" · {_('Job card')} {job_card}" if job_card and not use_card else "")
	insert_for(se, user)  # on_validate checks it; accounts filled by ERPNext (as_system)
	attach(photo, "Stock Entry", se.name, user)
	return {"name": se.name, "posted": submit_for(se, user)}


def wip_warehouse(wo) -> str:
	"""The company's Work In Progress warehouse for a Work Order that has none (made before the rebuild or in ERPNext):
	found by name, made once when missing, and written on the Work Order so every later issue uses the same one."""
	abbr = frappe.get_cached_value("Company", wo.company, "abbr")
	name = f"Work In Progress - {abbr}"
	if not frappe.db.exists("Warehouse", name):
		frappe.get_doc({"doctype": "Warehouse", "warehouse_name": "Work In Progress", "company": wo.company,
			"parent_warehouse": f"All Warehouses - {abbr}"}).insert(ignore_permissions=True)
	frappe.db.set_value("Work Order", wo.name, "wip_warehouse", name, update_modified=False)
	wo.wip_warehouse = name
	return name


def on_validate(doc, method=None):
	"""Every Stock Entry on the New path of Store: lines complete, job named on an issue to a job, who took it."""
	from sk_app.core.switch import use_new

	if doc.docstatus == 1 or not use_new("Store", doc.owner or frappe.session.user):
		return
	rows = [{"item_code": r.item_code, "qty": flt(r.qty), "s_warehouse": r.s_warehouse, "t_warehouse": r.t_warehouse} for r in doc.get("items") or []]
	found = problems(doc.purpose, rows, doc.get("work_order"), doc.get("remarks"))
	report("Store", doc, found, title=_("Issue data missing"))


# ---------- Plan A (SK 9-Nov): moved here unchanged from store.py ----------
from frappe import _
from frappe.utils import flt
from sk_app.core.switch import use_new
from sk_app.store import STORE, _todo, _users_with_function, attach, insert_for, need, submit_for, uom
from sk_app.store_screens import _default_store, count_list, job_card_cabin
import frappe


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
	if use_new("Store", user):  # rebuild: the one Stock Entry writer (linear flow map, Flow 4)
		return write(user, wo, items, taken_by=taken_by, job_card=job_card, photo=photo, default_store=_default_store, uom=uom,
			insert_for=insert_for, attach=attach, submit_for=submit_for)
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
	insert_for(se, user)  # accounts filled by ERPNext (as_system)
	attach(photo, "Stock Entry", se.name, user)
	posted = submit_for(se, user)
	return {"name": se.name, "posted": posted}

def request_issue(user: str, request: str) -> dict:
	"""Give a transfer / issue request from stock in one tap (Stock Entry from the Material Request)."""
	need(user, STORE)
	from erpnext.stock.doctype.material_request.material_request import make_stock_entry

	se = make_stock_entry(request)
	insert_for(se, user)  # accounts filled by ERPNext (as_system)
	return {"name": se.name, "posted": submit_for(se, user)}

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
	insert_for(dn, user)  # accounts filled by ERPNext (as_system)
	attach(cabin_photo, "Delivery Note", dn.name, user)
	attach(plate_photo, "Delivery Note", dn.name, user)
	owner = frappe.db.get_value("Sales Order", sales_order, "owner")
	for who in {owner} | set(_users_with_function("Accounts")):
		if who and who != user:
			_todo(who, "Delivery Note", dn.name, _("Dispatched: {0}. Please make the invoice today.").format(sales_order))
	return {"name": dn.name}

def stock_count(user: str, warehouse: str, counts: list[dict], photo=None) -> dict:
	"""Counted quantities that differ from ERPNext go as a draft Stock Reconciliation for the owner / Finance OK."""
	need(user, STORE)
	from sk_app import gates

	book = {r["item_code"]: r["qty"] for r in count_list(user, warehouse)}
	# SK 28-Oct mandatory gate: every line of the store is counted (0 is a count), not only the differences
	counted = {c.get("item_code"): c.get("qty") for c in counts or [] if c.get("item_code")}
	missing = gates.R.count_missing(warehouse, list(book), counted)
	if missing:
		gates.stop(_("Stock count cannot be sent"), missing)
	diffs = [c for c in counts or [] if c.get("item_code") and c.get("qty") not in (None, "")
		and flt(c["qty"]) != flt(book.get(c["item_code"]))]
	if not diffs:
		return {"name": None, "differences": 0}
	sr = frappe.new_doc("Stock Reconciliation")
	sr.company = frappe.db.get_value("Warehouse", warehouse, "company")
	sr.purpose = "Stock Reconciliation"
	for c in diffs:
		sr.append("items", {"item_code": c["item_code"], "warehouse": warehouse, "qty": flt(c["qty"])})
	insert_for(sr, user)  # accounts filled by ERPNext (as_system)
	attach(photo, "Stock Reconciliation", sr.name, user)
	return {"name": sr.name, "differences": len(diffs)}
