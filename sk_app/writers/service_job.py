"""The one subcontractor service job writer (Flow sheet 6-Nov-2026, same for every service subcontractor such as
Technomech for machine shifting). All ERPNext documents, no data in the app:

1. order():   customer Sales Order (with its Project) → service Purchase Order to the subcontractor at his final rate,
              payment term picked on the PO (50% advance + 50% after invoice, or 100% after invoice), placed through the
              one Purchase Order writer (CEO limit as for every PO). The customer order stands as the purchase request.
2. advance:   Accounts pay 50% against the PO in ERPNext when that term is picked (Payment Entry, Flow 6).
3. bill():    the subcontractor's invoice → draft Purchase Invoice from the PO; the Non-Cabin owner gets a ToDo.
4. approve(): the Non-Cabin owner (SK App User function "Machine Shifting", else the CEO) approves the work → service
              Purchase Receipt (GRN) submitted from the PO, linked into the bill; Accounts get a ToDo to post and pay.
5. before_submit: a service bill posts only after that approval (New path of Purchase, Warn then Enforce).
Rate sheet items SR-01 .. SR-14 are service Items with a buying rate in "Subcontract Rates" and a selling rate
(rate x (1 + margin)) in the selling price list, loaded once; SK changes them in ERPNext Item Price."""

import json

import frappe
from frappe import _
from frappe.utils import flt, fmt_money, getdate, nowdate

from sk_app.core.dates import fy_start
from sk_app.core.rules import report
from sk_app.writers.service_job_rules import OWNER_FUNCTION, TERMS, advance_due, bill_problems, order_problems, sale_rate, \
	stage, submit_problems

ORDER_FIELD = "sk_sales_order"  # on Purchase Order / Purchase Invoice: the customer order the subcontract is for
REPORT_FIELD = "sk_service_report"  # on Purchase Order: the customer-signed service report (photo / PDF), before the bill
RATE_FILE = "service_rates_draft.json"
GROUP = "Services"


# ---------- setup ----------

def ensure_setup():
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	link = {"fieldname": ORDER_FIELD, "label": "For customer order", "fieldtype": "Link", "options": "Sales Order",
		"insert_after": "supplier", "read_only": 1, "in_standard_filter": 1}
	report_file = {"fieldname": REPORT_FIELD, "label": "Customer-signed service report", "fieldtype": "Attach", "insert_after": ORDER_FIELD,
		"allow_on_submit": 1}
	create_custom_fields({"Purchase Order": [link, report_file], "Purchase Invoice": [dict(link)], "Purchase Receipt": [dict(link)]}, update=True)
	load_rates()


def load_rates():
	"""Rate sheet items SR-* with the draft buying and selling rate, only where no rate is there yet (SK 6-Nov: the
	yellow cells are SK's to fix, in ERPNext, not in code)."""
	from sk_app.sub_bills import PRICE_LIST, _set_standard_price
	from sk_app.writers.item import get_or_make

	data = json.loads(frappe.read_file(frappe.get_app_path("sk_app", "data", RATE_FILE)))
	if not frappe.db.exists("Price List", PRICE_LIST):
		return
	selling = data["price_list_selling"] if frappe.db.exists("Price List", data["price_list_selling"]) else None
	for r in data["items"]:
		uom = r["uom"] if frappe.db.exists("UOM", r["uom"]) else "Nos"
		get_or_make(r["code"], r["name"], group=GROUP, uom=uom, sales=True, hsn_like="99",
			description=_("Subcontracted service: {0}, per {1}. {2}").format(r["name"], uom, data["revision"]))
		_set_standard_price(r["code"], flt(r["rate"]), uom)
		if selling and not frappe.db.exists("Item Price", {"price_list": selling, "item_code": r["code"]}):
			frappe.get_doc({"doctype": "Item Price", "price_list": selling, "item_code": r["code"], "uom": uom,
				"price_list_rate": sale_rate(r["rate"], r["margin"])}).insert(ignore_permissions=True)


# ---------- who ----------

def owners() -> list[str]:
	"""The Non-Cabin owner(s) by function; the CEO when nobody has the function (never nobody)."""
	from sk_app.core.people import ceo_users, users_with_function

	return users_with_function(OWNER_FUNCTION) or ceo_users()


def is_owner(user: str) -> bool:
	from sk_app.core.people import is_ceo

	return user in owners() or is_ceo(user)


def _todo(user: str, doctype: str, name: str, text: str):
	from sk_app.store import _todo

	_todo(user, doctype, name, text)


# ---------- 1. service PO ----------

def order(user: str, sales_order: str, supplier: str, rows: list[dict], payment_term: str, *, note=None, schedule_date=None) -> dict:
	"""rows = [{"item_code", "qty", "rate", "description"?}]. Returns the Purchase Order writer's result."""
	from sk_app.writers.purchase_order import place_po

	so = frappe.db.get_value("Sales Order", sales_order, ["name", "project", "customer_name", "company", "cost_center"], as_dict=True) \
		if sales_order else None
	found = order_problems(rows, supplier, payment_term, so and so.name, so and so.project)
	report("Purchase", None, found, title=_("Service job data missing"))
	if not so or not supplier:
		frappe.throw(_("Customer order and subcontractor are needed"))
	po = frappe.new_doc("Purchase Order")
	po.update({"supplier": supplier, "company": so.company, "transaction_date": nowdate(),
		"schedule_date": getdate(schedule_date) if schedule_date else nowdate(), "payment_terms_template": payment_term if payment_term in TERMS else None,
		ORDER_FIELD: so.name, "owner": user})
	if po.meta.has_field("project"):
		po.project = so.project
	for r in rows:
		if flt(r.get("qty")) <= 0:
			continue
		po.append("items", {"item_code": r["item_code"], "qty": flt(r["qty"]), "rate": flt(r.get("rate")), "schedule_date": po.schedule_date,
			"project": so.project, "sales_order": so.name, "description": (r.get("description") or None),
			"cost_center": so.cost_center or None})
	if note:
		po.set("terms", note)
	out = place_po(po, user)
	out["advance_due"] = advance_due(payment_term, out.get("grand_total"))
	out["project"] = so.project
	if out["advance_due"]:
		from sk_app.core.people import users_with_function

		for a in users_with_function("Accounts"):
			_todo(a, "Purchase Order", out["name"], _("Pay 50% advance {0} to {1} on PO {2} (customer {3})").format(
				fmt_money(out["advance_due"], currency="INR"), supplier, out["name"], so.customer_name))
	return out


# ---------- 3. the subcontractor's bill ----------

def bill(user: str, purchase_order: str, bill_no: str, bill_date, *, photo=None, note=None) -> dict:
	from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_invoice

	from sk_app.store import attach, insert_for

	po = frappe.db.get_value("Purchase Order", purchase_order, ["name", "docstatus", "supplier_name", ORDER_FIELD, "grand_total", "project", REPORT_FIELD],
		as_dict=True)
	if not po:
		frappe.throw(_("Service PO {0} not found").format(purchase_order))
	found = bill_problems(bill_no, bill_date, po.docstatus == 1, bool(po.get(REPORT_FIELD)))
	report("Purchase", None, found, title=_("Bill data missing"))
	if po.docstatus != 1:
		frappe.throw(_("Place the service PO {0} first").format(po.name))
	# Mac test 9-Nov: the subcontractor's login may not read Purchase Orders, so the bill is mapped as the system (kept in
	# his name by insert_for below), else ERPNext stops him with a blank permission error
	current = frappe.session.user
	frappe.set_user("Administrator")
	try:
		pi = make_purchase_invoice(po.name)
	finally:
		frappe.set_user(current)
	pi.bill_no = (bill_no or "").strip()[:140] or None
	pi.bill_date = getdate(bill_date) if bill_date else None
	pi.set(ORDER_FIELD, po.get(ORDER_FIELD))
	if note:
		pi.remarks = note
	insert_for(pi, user)
	attach(photo, "Purchase Invoice", pi.name, user)
	for a in owners():
		_todo(a, "Purchase Invoice", pi.name, _("Approve work of {0}: bill {1} {2} on PO {3}").format(po.supplier_name, pi.bill_no or pi.name,
			fmt_money(pi.grand_total, currency=pi.currency), po.name))
	return {"name": pi.name, "grand_total": pi.grand_total, "approvers": owners()}


# ---------- 4. the Non-Cabin owner approves → service GRN ----------

def approve(user: str, purchase_invoice: str, *, note=None) -> dict:
	from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt

	from sk_app.core.people import users_with_function
	from sk_app.store import insert_for, submit_for

	if not is_owner(user):
		frappe.throw(_("Only the Non-Cabin owner ({0}) approves subcontracted work").format(OWNER_FUNCTION), frappe.PermissionError)
	pi = frappe.get_doc("Purchase Invoice", purchase_invoice)
	if pi.docstatus != 0:
		frappe.throw(_("Bill {0} is already posted").format(pi.name))
	pos = sorted({r.purchase_order for r in pi.items if r.purchase_order})
	if not pos:
		frappe.throw(_("Bill {0} is not against a service PO").format(pi.name))
	receipts = []
	current = frappe.session.user  # Mac test 9-Nov: the owner (a Sales login) may not read POs or accounts; the receipt
	frappe.set_user("Administrator")  # and the bill update run as the system, in his name (insert_for / Comment below)
	try:
		_approve_rows(pi, pos, receipts, user, note)
	finally:
		frappe.set_user(current)
	pi.add_comment("Comment", _("Work approved by {0}").format(frappe.utils.get_fullname(user)))
	for a in users_with_function("Accounts"):
		_todo(a, "Purchase Invoice", pi.name, _("Service approved: post bill {0} of {1} ({2}) and pay as per its term").format(
			pi.name, pi.supplier_name, fmt_money(pi.grand_total, currency=pi.currency)))
	return {"name": pi.name, "receipts": receipts, "approved": all(r["posted"] for r in receipts)}


def _approve_rows(pi, pos, receipts, user, note):
	from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt

	from sk_app.store import insert_for, submit_for

	for po_name in pos:
		pr = make_purchase_receipt(po_name)
		pr.posting_date = nowdate()
		pr.set(ORDER_FIELD, pi.get(ORDER_FIELD))
		pr.remarks = _("Service done, approved by {0}{1}").format(frappe.utils.get_fullname(user), f": {note}" if note else "")
		insert_for(pr, user)
		posted = submit_for(pr, user)
		receipts.append({"name": pr.name, "posted": posted, "reason": frappe.flags.sk_draft_reason})
		if posted:
			by_po_item = {r.purchase_order_item: r for r in pr.items}
			for row in pi.items:
				got = by_po_item.get(row.po_detail)
				if got:
					row.purchase_receipt, row.pr_detail = pr.name, got.name
	pi.flags.ignore_permissions = True
	pi.save()


# ---------- 5. the rule on every service bill ----------

def before_submit(doc, method=None):
	"""Every Purchase Invoice for a service PO (from the app, ERPNext or SK Hub), New path of Purchase: posted only after
	the Non-Cabin owner approved the work (service GRN on every line)."""
	from sk_app.core.switch import use_new

	if not doc.get(ORDER_FIELD) or doc.flags.sk_bill_ok or not use_new("Purchase", doc.owner or frappe.session.user):
		return
	report("Purchase", doc, submit_problems([{"purchase_receipt": r.get("purchase_receipt")} for r in doc.items]),
		title=_("Service bill not approved"))


# ---------- at site: daily photo report and the signed service report (Flow sheet steps 8-9) ----------

def _po(purchase_order: str):
	po = frappe.db.get_value("Purchase Order", purchase_order, ["name", "supplier", "supplier_name", "project", ORDER_FIELD, REPORT_FIELD, "docstatus"],
		as_dict=True)
	if not po:
		frappe.throw(_("Service PO {0} not found").format(purchase_order))
	return po


def _attach_copy(file_url: str | None, doctype: str, name: str, user: str):
	from sk_app.crm import _attach

	_attach(file_url, doctype, name, user)


def daily_report(user: str, purchase_order: str, *, photo=None, note=None) -> dict:
	"""One entry per day per job: a Comment with the photo on the Project (else the PO), so the customer's project
	timeline holds the site record."""
	po = _po(purchase_order)
	if not photo and not (note or "").strip():
		frappe.throw(_("Please add the day's photo or a line on the work"))
	doctype, name = ("Project", po.project) if po.project else ("Purchase Order", po.name)
	_attach_copy(photo, doctype, name, user)
	text = _("Daily site report {0} by {1}: {2}").format(nowdate(), frappe.utils.get_fullname(user), (note or "").strip() or _("photo"))
	if photo:
		text += f' <a href="{photo}" target="_blank">📷</a>'
	c = frappe.get_doc({"doctype": "Comment", "comment_type": "Comment", "reference_doctype": doctype, "reference_name": name, "content": text,
		"comment_email": user, "comment_by": frappe.utils.get_fullname(user)}).insert(ignore_permissions=True)
	if doctype == "Project":
		frappe.get_doc("Purchase Order", po.name).add_comment("Comment", text)
	return {"name": c.name, "on": f"{doctype} {name}"}


def service_report(user: str, purchase_order: str, photo: str, *, note=None) -> dict:
	"""The customer-signed service report, on the PO (and the Project): needed before the subcontractor's bill."""
	po = _po(purchase_order)
	if not photo:
		frappe.throw(_("Please add the signed report (photo or PDF)"))
	_attach_copy(photo, "Purchase Order", po.name, user)
	frappe.db.set_value("Purchase Order", po.name, REPORT_FIELD, photo, update_modified=False)
	doc = frappe.get_doc("Purchase Order", po.name)
	doc.add_comment("Comment", _("Customer-signed service report added by {0}{1}").format(frappe.utils.get_fullname(user), f": {note}" if note else "") +
		f' <a href="{photo}" target="_blank">📄</a>')
	if po.project:
		frappe.get_doc("Project", po.project).add_comment("Comment", _("Service report signed by the customer (PO {0})").format(po.name) +
			f' <a href="{photo}" target="_blank">📄</a>')
	return {"name": po.name, "report": photo}


def my_supplier(user: str) -> str | None:
	"""The subcontractor behind this login: the Supplier of his workstation."""
	from sk_app.production_screens import my_workstation
	from sk_app.sub_bills import supplier_of

	return supplier_of(my_workstation(user))


def _PRICE_LIST():
	from sk_app.sub_bills import PRICE_LIST

	return PRICE_LIST


def options() -> dict:
	"""Lists for the New service PO screen: open customer orders, service suppliers, rate items with buying price, payment terms."""
	from sk_app.writers.app_user import service_suppliers

	since = fy_start(getdate(nowdate()))
	orders = frappe.get_all("Sales Order", filters={"docstatus": 1, "status": ["not in", ["Closed", "Completed"]], "transaction_date": [">=", since]},
		fields=["name", "customer_name", "project"], order_by="transaction_date desc", limit=200)
	# service_suppliers returns rows (name, supplier_name, mobile) since #126; the screen needs the names
	suppliers = {s["name"] for s in service_suppliers(since)} | set(frappe.get_all("Workstation", filters={"sk_supplier": ["is", "set"]}, pluck="sk_supplier"))
	prices = {r.item_code: r.price_list_rate for r in frappe.get_all("Item Price", filters={"price_list": _PRICE_LIST()}, fields=["item_code", "price_list_rate"])}
	items = [{"item_code": i.name, "item_name": i.item_name, "uom": i.stock_uom, "rate": prices.get(i.name, 0)} for i in
		frappe.get_all("Item", filters={"item_group": GROUP, "disabled": 0}, fields=["name", "item_name", "stock_uom"], order_by="name asc")]
	return {"orders": [{"value": o.name, "label": f"{o.name} · {o.customer_name}"} for o in orders], "suppliers": sorted(x for x in suppliers if x),
		"items": items, "terms": list(TERMS)}


def is_site_worker(user: str) -> bool:
	"""SK 9-Nov (Santosh): a subcontractor whose workstation stands for a service supplier and has no factory Job Cards
	does site jobs (service POs), so his Home shows only site-job things, never the factory or sales views."""
	ws = frappe.db.get_value("SK App User", {"user": user}, "workstation")
	if not ws or not frappe.get_meta("Workstation").has_field("sk_supplier"):
		return False
	return bool(frappe.db.get_value("Workstation", ws, "sk_supplier")) and not frappe.db.exists("Job Card", {"workstation": ws, "docstatus": ["<", 2]})


def site_flow(user: str) -> list[dict]:
	"""Home arrows of a site-job subcontractor: his service POs by stage (writers.service_job.jobs)."""
	from sk_app.flows import _row, _stage, period_start, span

	supplier = my_supplier(user)
	rows = jobs(supplier) if supplier else []

	def box(key, label, icon, stages, go="service_jobs", recent=False):
		picked = [r for r in rows if r["stage"] in stages and (not recent or str(r.get("transaction_date") or "") >= str(period_start()))]
		return _stage(key, label, icon, [_row(f"{r.get('customer') or r['supplier_name']}", f"{r['name']} · {r.get('work') or ''}") for r in picked], go=go)

	return [box("ordered", "Jobs to do", "🛠️", ("ordered", "advance_paid")),
		box("billed", "Billed, waiting approval", "🧾", ("billed",)),
		box("approved", "Approved, waiting payment", "✅", ("approved",)),
		box("paid", f"Paid {span()}", "💰", ("paid",), recent=True)]


# ---------- the list for the screens and arrows ----------

def jobs(supplier: str | None = None, since: str | None = None) -> list[dict]:
	"""Every service PO with its stage: ordered → advance_paid → billed → approved → paid."""
	filters = {ORDER_FIELD: ["is", "set"], "docstatus": ["<", 2]}
	if supplier:
		filters["supplier"] = supplier
	if since:
		filters["transaction_date"] = [">=", since]
	fields = ["name", "docstatus", "supplier", "supplier_name", "transaction_date", "grand_total", "advance_paid", "per_received",
		"per_billed", "payment_terms_template", ORDER_FIELD, "status", REPORT_FIELD]
	if frappe.get_meta("Purchase Order").has_field("project"):
		fields.append("project")
	out = []
	for po in frappe.get_all("Purchase Order", filters=filters, fields=fields, order_by="transaction_date desc", limit=0):
		billed = frappe.get_all("Purchase Invoice Item", filters={"purchase_order": po.name, "docstatus": ["<", 2]}, pluck="parent", distinct=True)
		paid = bool(billed) and all(frappe.db.get_value("Purchase Invoice", b, ["docstatus", "outstanding_amount"]) == (1, 0) for b in billed)
		po["bills"] = billed
		po["customer"] = frappe.db.get_value("Sales Order", po.get(ORDER_FIELD), "customer_name") if po.get(ORDER_FIELD) else None
		po["work"] = ", ".join(frappe.get_all("Purchase Order Item", filters={"parent": po.name}, pluck="item_name", order_by="idx asc")[:3])
		po["signed_report"] = bool(po.get(REPORT_FIELD))
		po["draft_bill"] = frappe.db.get_value("Purchase Invoice", {"name": ["in", billed or [""]], "docstatus": 0}, "name") if billed else None
		po["stage"] = stage(placed=po.docstatus == 1, advance_paid=flt(po.advance_paid) > 0, billed=bool(billed),
			approved=flt(po.per_received) >= 100, paid=paid)
		out.append(po)
	return out
