"""Every essential ERPNext step of the sales-to-factory flow done in the app by its owner (SK 26-Oct: "every essential
action which needs to be performed in the ERP flow must come in the app"). The gaps found in the live data were:
no Quotation, Customer or Sales Order made from the app and no Work Order for the factory. So:

	CRM Deal → Customer (Sales) → Quotation (Sales, PDF to the customer) → Sales Order when the order comes (Sales)
	→ Confirm order (Sales manager / CEO submits it) → Work Order per cabin (Production)

Each step is an ordinary ERPNext document made under the person's own login, so ERPNext's own permissions and
validations apply and every action leaves its data (TLC SAS: proof of each action)."""

import frappe
from frappe import _
from frappe.utils import add_days, flt, getdate, nowdate

from sk_app import crm


def _deal(name: str) -> dict:
	crm._check("CRM Deal", name)
	meta = frappe.get_meta("CRM Deal")
	fields = [f for f in ("name", "organization", "lead_name", "mobile_no", "email", "deal_owner", "erpnext_customer", "sk_customer_name",
		"sk_segment") if f == "name" or meta.has_field(f)]
	return frappe.db.get_value("CRM Deal", name, fields, as_dict=True)


def customer_of(deal: str) -> str | None:
	d = _deal(deal)
	if d.get("erpnext_customer") and frappe.db.exists("Customer", d.erpnext_customer):
		return d.erpnext_customer
	if frappe.get_meta("Customer").has_field("crm_deal"):
		return frappe.db.get_value("Customer", {"crm_deal": deal})
	return None


def make_customer(user: str, deal: str, details: dict | None = None) -> dict:
	"""Step 1 (Sales): the deal's company becomes an ERPNext Customer (once); the segment hook picks the group.
	details (SK 28-Oct mandatory gate): GSTIN or unregistered + reason, billing address with state / PIN, mobile;
	"missing" lists what the customer still needs before its quotation / order can be submitted."""
	from sk_app import gates

	d = _deal(deal)
	have = customer_of(deal)
	if have:
		if details:
			gates.complete_customer(have, **details)
		return {"name": have, "new": False, "missing": [t for _k, t in gates.customer_missing(have)]}
	title = (d.get("organization") or d.get("sk_customer_name") or d.get("lead_name") or "").strip()
	if not title:
		frappe.throw(_("Please give the customer's company or name on the deal first"))
	same = frappe.db.get_value("Customer", {"customer_name": title})
	if same:
		name = same
	else:
		doc = frappe.get_doc({"doctype": "Customer", "customer_name": title, "customer_type": "Company" if d.get("organization") else "Individual",
			"mobile_no": d.get("mobile_no"), "email_id": d.get("email")})
		if doc.meta.has_field("crm_deal"):
			doc.crm_deal = deal
		doc.insert()
		name = doc.name
	if frappe.get_meta("CRM Deal").has_field("erpnext_customer"):
		frappe.db.set_value("CRM Deal", deal, "erpnext_customer", name)
	if details:
		gates.complete_customer(name, **details)
	return {"name": name, "new": not same, "missing": [t for _k, t in gates.customer_missing(name)]}


GST_TERMS = "GST @ 18% extra as applicable."


def gst_terms(terms: str | None) -> str:
	"""SK 28-Oct: quotes show no GST amount, only the rate: totals stay before GST and the terms say GST is extra."""
	terms = (terms or "").strip()
	return terms if "gst" in terms.lower() else (terms + "<br>" if terms else "") + GST_TERMS


def _rate(item_code: str) -> float:
	price_list = frappe.db.get_single_value("Selling Settings", "selling_price_list") or "Standard Selling"
	return flt(frappe.db.get_value("Item Price", {"item_code": item_code, "price_list": price_list, "selling": 1}, "price_list_rate"))


def make_quotation(user: str, deal: str, items: list[dict], valid_days: int = 15, note: str | None = None) -> dict:
	"""Step 2 (Sales): a Quotation for the deal's customer, items with qty and rate (rate from the price list when
	left empty). Saved as draft; its PDF opens at once to send to the customer."""
	customer = make_customer(user, deal)["name"]
	rows = []
	for it in items or []:
		code = (it.get("item_code") or "").strip()
		if not code:
			continue
		if not frappe.db.exists("Item", code):
			code = frappe.db.get_value("Item", {"item_name": code}) or code
		if not frappe.db.exists("Item", code):
			frappe.throw(_("Item {0} is not in ERPNext. Pick it from the list").format(it.get("item_code")))
		qty = flt(it.get("qty")) or 1
		rate = flt(it.get("rate")) or _rate(code)
		if rate <= 0:
			frappe.throw(_("Please give the rate for {0}").format(code))
		row = {"item_code": code, "qty": qty, "rate": rate}
		desc = (it.get("description") or "").strip()
		if desc:
			row["description"] = "<br>".join(frappe.utils.escape_html(x) for x in desc.splitlines())
		rows.append(row)
	if not rows:
		frappe.throw(_("Please add at least one item"))
	doc = frappe.get_doc({"doctype": "Quotation", "quotation_to": "Customer", "party_name": customer, "transaction_date": nowdate(),
		"valid_till": add_days(nowdate(), int(valid_days or 15)), "items": rows})
	if doc.meta.has_field("crm_deal"):
		doc.crm_deal = deal
	doc.terms = gst_terms(note)
	doc.insert()
	return {"name": doc.name, "grand_total": doc.grand_total, "pdf": crm._pdf("Quotation", doc.name), **submit_quotation(user, doc.name, quiet=True)}


def submit_quotation(user: str, quotation: str, quiet: bool = False) -> dict:
	"""SK 28-Oct mandatory gate: the quotation is submitted (sent) only when customer, items, GST and valid-till are
	all there. quiet: when it is just made, say what is missing instead of failing."""
	from sk_app import gates

	q = frappe.get_doc("Quotation", quotation)
	if q.docstatus == 1:
		return {"submitted": True, "missing": []}
	if quiet and not frappe.has_permission("Quotation", "submit", q.name):
		return {"submitted": False, "missing": [_("Sales manager to submit")]}
	q.check_permission("submit")
	if not q.get("taxes") and "gst" not in (q.terms or "").lower():
		q.terms = gst_terms(q.terms)
		q.save()
	try:
		q.submit()
	except frappe.ValidationError:
		if not quiet:
			raise
		frappe.clear_messages()
		q.reload()
		missing = gates.R.quotation_missing({"party_name": q.party_name, "valid_till": q.valid_till, "items": gates._rows(q),
			"taxes": len(q.get("taxes") or []), "total_taxes_and_charges": q.total_taxes_and_charges, "terms": q.terms})
		missing += gates.customer_missing(q.party_name) if q.quotation_to == "Customer" else []
		return {"submitted": False, "missing": [t for _k, t in missing]}
	return {"submitted": True, "missing": []}


def order_received(user: str, quotation: str, delivery_date=None, po_no: str | None = None, po_photo: str | None = None,
		order_date=None, po_date=None) -> dict:
	"""Step 3 (Sales): the customer said yes = Deal Won (SK 28-Oct). Mandatory gate: order date, promised delivery
	date and the customer's PO number or PO copy; the quotation must be complete. The Sales Order is made from the
	quotation and submitted; the deal then shows Won. When the person may not submit orders it waits for the
	manager's Confirm, and the deal turns Won then."""
	from erpnext.selling.doctype.quotation.quotation import make_sales_order

	from sk_app import gates

	missing = [m for m in gates.R.order_missing({"transaction_date": order_date or nowdate(), "delivery_date": delivery_date,
		"po_no": po_no, "po_file": bool(po_photo), "items": [{"qty": 1, "rate": 1}], "grand_total": 1})]
	if missing:
		gates.stop(_("Order cannot be saved"), missing)
	if getdate(delivery_date) < getdate(order_date or nowdate()):
		frappe.throw(_("The delivery date is before the order date"))
	q = frappe.get_doc("Quotation", quotation)
	q.check_permission("write")
	deal = q.get("crm_deal")
	if deal and frappe.db.exists("CRM Deal", deal):  # the deal's own data first, so Won is not refused at the end
		lead_gaps = gates.record_missing("CRM Deal", frappe.get_doc("CRM Deal", deal))
		if lead_gaps:
			gates.stop(_("Deal {0} cannot be Won").format(deal), lead_gaps)
	if q.docstatus == 0:
		submit_quotation(user, quotation)
	so = make_sales_order(quotation)
	so.transaction_date = getdate(order_date or nowdate())
	so.delivery_date = getdate(delivery_date)
	for row in so.items:
		row.delivery_date = so.delivery_date
	so.po_no = (po_no or "").strip() or None
	if po_date:
		so.po_date = getdate(po_date)
	so.insert()
	if po_photo:
		_attach_po(po_photo, so.name, user)
	out = {"name": so.name, "grand_total": so.grand_total, "delivery_date": str(so.delivery_date), "submitted": False}
	if frappe.has_permission("Sales Order", "submit", so.name):
		so.submit()
		out["submitted"] = True
		_won(deal, so)
	return out


def _attach_po(file_url: str, sales_order: str, user: str):
	crm._attach(file_url, "Sales Order", sales_order, user)


def _won(deal: str | None, so) -> None:
	"""The submitted Sales Order makes the deal (and its lead) Won with the order value (SK: deal won = sales order)."""
	if not deal or not frappe.db.exists("CRM Deal", deal):
		return
	won = frappe.get_all("CRM Deal Status", filters={"type": "Won"}, pluck="name", order_by="position asc", limit=1)
	doc = frappe.get_doc("CRM Deal", deal)
	if won and doc.status != won[0]:
		doc.status = won[0]
	if doc.meta.has_field("deal_value"):
		doc.deal_value = so.base_grand_total or so.grand_total
	if doc.meta.has_field("erpnext_customer") and not doc.get("erpnext_customer"):
		doc.erpnext_customer = so.customer
	doc.flags.ignore_permissions = True
	doc.save()
	if doc.get("lead") and frappe.db.exists("CRM Lead Status", "Deal Won"):
		frappe.db.set_value("CRM Lead", doc.lead, "status", "Deal Won")


def confirm_order(user: str, sales_order: str) -> dict:
	"""Step 4 (Sales manager / CEO): submit the Sales Order so the factory can plan it; the deal shows Won then."""
	so = frappe.get_doc("Sales Order", sales_order)
	so.check_permission("submit")
	if so.docstatus == 0:
		so.submit()
	deals = {r.prevdoc_docname for r in so.items if r.get("prevdoc_docname")}
	for q in deals:
		_won(frappe.db.get_value("Quotation", q, "crm_deal") if frappe.get_meta("Quotation").has_field("crm_deal") else None, so)
	return {"name": so.name, "status": so.status}


def orders_to_plan(user: str) -> list[dict]:
	"""For Production: confirmed orders whose items have no Work Order yet, with the BOM that will be used."""
	from sk_app.store import need

	need(user, "Production", "Management")
	out = []
	for so in frappe.get_all("Sales Order", filters={"docstatus": 1, "status": ["not in", ["Closed", "Completed", "On Hold"]]},
			fields=["name", "customer_name", "delivery_date", "base_net_total"], order_by="delivery_date asc", limit=0):
		for it in frappe.get_all("Sales Order Item", filters={"parent": so.name}, fields=["name", "item_code", "item_name", "qty", "delivery_date"]):
			made = flt(frappe.db.sql("""select sum(qty) from `tabWork Order` where sales_order=%s and sales_order_item=%s and docstatus<2""",
				(so.name, it.name))[0][0])
			if made >= flt(it.qty):
				continue
			bom = frappe.db.get_value("BOM", {"item": it.item_code, "is_default": 1, "is_active": 1, "docstatus": 1})
			out.append({"sales_order": so.name, "so_item": it.name, "customer": so.customer_name, "item_code": it.item_code,
				"item_name": it.item_name, "qty": flt(it.qty) - made, "delivery_date": str(it.delivery_date or so.delivery_date or ""),
				"bom": bom, "late": bool(so.delivery_date and getdate(so.delivery_date) < getdate())})
	return out


def _warehouses(company: str) -> dict:
	"""Work-in-progress and finished-goods stores of the company (ERPNext's standard names), else the default store."""
	abbr = frappe.db.get_value("Company", company, "abbr")
	default = frappe.db.get_value("Warehouse", {"company": company, "is_group": 0, "warehouse_name": "Stores"}) or frappe.db.get_value(
		"Warehouse", {"company": company, "is_group": 0})
	pick = lambda name: name if frappe.db.exists("Warehouse", name) else default  # noqa: E731
	return {"wip_warehouse": pick(f"Work In Progress - {abbr}"), "fg_warehouse": pick(f"Finished Goods - {abbr}"), "source_warehouse": default}


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
	wo.flags.ignore_permissions = True  # need() above: Production / CEO only, saved under their login like the Store screens
	wo.insert()
	return {"name": wo.name, "qty": wo.qty}
