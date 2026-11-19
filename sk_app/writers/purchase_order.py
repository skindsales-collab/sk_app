"""The one Purchase Order writer (linear flow map, Flow 3 Purchase). A PO from the chosen supplier quote and a PO made
straight from an approved requisition end the same way: linked to the CEO-approved requisition rows, saved, and either
placed or kept for the CEO when it is over 10% above the approved value. Used on the New path of Purchase; the rules
also run on every Purchase Order saved in ERPNext or through SK Hub (SK 4-Nov: same checks from any door)."""

import frappe
from sk_app.writers import requisition as req_w
from sk_app import purchase_screens
from frappe import _
from frappe.utils import flt, fmt_money

from sk_app.core.rules import report
from sk_app.writers.purchase_order_rules import ceo_reason, problems

APPROVED = "Approved"


def _rows(po) -> list[dict]:
	return [{"item_code": r.item_code, "qty": flt(r.qty), "rate": flt(r.rate), "material_request": r.material_request,
		"approved": bool(r.material_request and frappe.db.get_value("Material Request", r.material_request, "sk_approval") == APPROVED)}
		for r in po.get("items") or []]


def write(po, user: str, *, is_ceo: bool, ceos: list[str], limit: float, link_requests, approved_value, todo, try_submit, draft_reason) -> dict:
	"""Returns the app's result dict (name, posted, needs_approval, grand_total, why). The helpers are requisition's and
	store's own, passed in so there is one path and the tested pieces stay where they are."""
	link_requests(po)
	for_order = bool(po.get("sk_sales_order"))  # a service job for a customer order: the order is the request (Flow sheet 6-Nov)
	if any(not r.material_request for r in po.items) and not is_ceo and not for_order:
		frappe.throw(_("No CEO-approved purchase requisition for: {0}. Raise a requisition first.").format(
			", ".join(sorted({r.item_code for r in po.items if not r.material_request}))))
	po.flags.ignore_permissions = True
	po.insert()  # on_validate checks it, as for a PO made in ERPNext or by Claude
	po.calculate_taxes_and_totals()
	why = ceo_reason(0 if for_order else sum(1 for r in po.items if not r.material_request), approved_value(po), flt(po.net_total), flt(po.grand_total), limit)
	if why and not is_ceo:  # the CEO's own PO needs no second approval
		po.db_set("sk_needs_ceo", 1)
		po.add_comment("Comment", _("Waits for CEO: {0}").format(_(why)))
		for a in ceos:
			if a != user:
				todo(a, "Purchase Order", po.name, _("Approve PO {0}: {1} for {2} ({3})").format(po.name, po.supplier_name,
					fmt_money(po.grand_total, currency=po.currency), _(why)))
		return {"name": po.name, "posted": False, "needs_approval": True, "grand_total": po.grand_total, "why": _(why)}
	posted = try_submit(po)
	return {"name": po.name, "posted": posted, "reason": draft_reason(), "needs_approval": False, "grand_total": po.grand_total}


def on_validate(doc, method=None):
	"""Every Purchase Order on the New path of Purchase: supplier, date, lines with qty and rate, approved requisition."""
	from sk_app.core.switch import use_new
	from sk_app.requisition import _is_ceo

	if doc.docstatus == 1 or not use_new("Purchase", doc.owner or frappe.session.user):
		return
	user = doc.owner or frappe.session.user
	found = problems(_rows(doc), doc.supplier, doc.schedule_date, _is_ceo(user), bool(doc.get("sk_sales_order")))
	report("Purchase", doc, found, title=_("Purchase order data missing"))
	# SK 9-Nov: a draft PO over the limit made outside the app (ERPNext desk, Claude; PUR-ORD-2026-00017) waits for the CEO
	# like one from the app, so it shows on the PO Approvals tile. The CEO's own PO needs no second approval.
	if doc.docstatus == 0 and not doc.get("sk_needs_ceo") and (user == "Administrator" or not _is_ceo(user)):
		from sk_app.purchase import po_limit
		from sk_app.writers.requisition import approved_value

		limit = po_limit()
		without = 0 if doc.get("sk_sales_order") else sum(1 for r in doc.get("items") or [] if not r.material_request)
		if flt(doc.grand_total) > limit and ceo_reason(without, approved_value(doc), flt(doc.net_total), flt(doc.grand_total), limit):
			doc.sk_needs_ceo = 1


# ---------- Plan A (SK 9-Nov): moved here unchanged from purchase.py ----------
from frappe import _
from frappe.utils import add_days, flt, fmt_money, getdate, nowdate
from sk_app.core.switch import use_new
from sk_app.purchase import PURCHASE, po_limit
from sk_app.purchase_screens import _has_gstin, _supplier_row
from sk_app.store import _company, _todo, _users_with_function, attach, draft_reason, need, try_submit, uom
import frappe


def make_rfq(user: str, items: list[dict], supplier_names: list[str], need_by=None) -> dict:
	"""Request for Quotation (draft, not e-mailed by ERPNext) + the WhatsApp text and numbers to send from the phone."""
	need(user, PURCHASE)
	items = [i for i in items or [] if i.get("item_code") and flt(i.get("qty")) > 0]
	if not items or not supplier_names:
		frappe.throw(_("Please pick items and suppliers"))
	need_by = getdate(need_by or add_days(nowdate(), 3))
	rfq = frappe.new_doc("Request for Quotation")
	rfq.company = _company()
	rfq.transaction_date = nowdate()
	rfq.schedule_date = need_by
	rfq.message_for_supplier = _("Please send your best rate with GST and delivery days.")
	for s in supplier_names:
		rfq.append("suppliers", {"supplier": s, "send_email": 0})
	for i in items:
		wh = i.get("warehouse") or frappe.db.get_value("Item Default", {"parent": i["item_code"]}, "default_warehouse") \
			or frappe.db.get_single_value("Stock Settings", "default_warehouse")
		rfq.append("items", {"item_code": i["item_code"], "qty": flt(i["qty"]), "schedule_date": need_by, "warehouse": wh,
			"material_request": i.get("request"), "material_request_item": i.get("row"), **uom(i["item_code"])})
	rfq.flags.ignore_permissions = True
	rfq.insert()
	lines = ", ".join(f"{frappe.db.get_value('Item', i['item_code'], 'item_name')} {flt(i['qty']):g} {i.get('uom') or ''}".strip() for i in items)
	text = _("SK Ind Tech Solutions needs your rate for: {0}. Delivery at Taloja by {1}. Please reply with rate + GST and delivery days. Ref {2}").format(
		lines, frappe.utils.formatdate(need_by), rfq.name)
	return {"name": rfq.name, "text": text, "suppliers": [_supplier_row(s) for s in supplier_names]}

def add_quote(user: str, supplier: str, item_code: str, qty, rate, days=None, photo=None, rfq=None) -> dict:
	"""Supplier's reply (photo / screenshot + spoken rate) saved as a Supplier Quotation."""
	need(user, PURCHASE)
	if flt(rate) <= 0 or flt(qty) <= 0:
		frappe.throw(_("Please give the rate and quantity"))
	sq = frappe.new_doc("Supplier Quotation")
	sq.supplier = supplier
	sq.company = _company()
	sq.transaction_date = nowdate()
	sq.valid_till = add_days(nowdate(), 7)
	row = {"item_code": item_code, "qty": flt(qty), "rate": flt(rate), "lead_time_days": int(flt(days or 0)), **uom(item_code)}
	if rfq:
		rfq_item = frappe.db.get_value("Request for Quotation Item", {"parent": rfq, "item_code": item_code}, ["name", "material_request", "material_request_item"], as_dict=True)
		if rfq_item:
			row.update({"request_for_quotation": rfq, "request_for_quotation_item": rfq_item.name,
				"material_request": rfq_item.material_request, "material_request_item": rfq_item.material_request_item})
	sq.append("items", row)
	sq.flags.ignore_permissions = True
	sq.insert()
	attach(photo, "Supplier Quotation", sq.name, user)
	try_submit(sq)
	return {"name": sq.name}

def make_po(user: str, supplier_quotation: str, schedule_date=None, terms=None) -> dict:
	"""Purchase Order from the chosen quote, linked to the CEO-approved requisition of each item (SK 27-Oct). It is
	placed at once unless it is over 10% above the approved value; then it waits as a draft for the CEO."""
	need(user, PURCHASE)
	from erpnext.buying.doctype.supplier_quotation.supplier_quotation import make_purchase_order

	sq = frappe.get_doc("Supplier Quotation", supplier_quotation)
	if sq.docstatus == 0:
		sq.flags.ignore_permissions = True
		sq.submit()
	po = make_purchase_order(supplier_quotation)
	po.schedule_date = getdate(schedule_date or add_days(nowdate(), max([flt(i.lead_time_days) for i in sq.items] + [1])))
	for i in po.items:
		i.schedule_date = po.schedule_date
	if terms:
		po.terms = terms
	return place_po(po, user)

def place_po(po, user: str) -> dict:
	from sk_app import requisition

	if use_new("Purchase", user):  # rebuild: the one Purchase Order writer (linear flow map, Flow 3)
		from sk_app.writers import purchase_order as pw

		return pw.write(po, user, is_ceo=requisition._is_ceo(user), ceos=requisition._ceos(), limit=po_limit(),
			link_requests=req_w.link_requests, approved_value=req_w.approved_value, todo=_todo, try_submit=try_submit,
			draft_reason=draft_reason)
	req_w.link_requests(po)
	if any(not r.material_request for r in po.items) and not requisition._is_ceo(user):
		frappe.throw(_("No CEO-approved purchase requisition for: {0}. Raise a requisition first.").format(
			", ".join(sorted({r.item_code for r in po.items if not r.material_request}))))
	po.flags.ignore_permissions = True
	po.insert()
	po.calculate_taxes_and_totals()
	why = req_w.needs_ceo(po)
	if why and not requisition._is_ceo(user):  # the CEO's own PO needs no second approval
		po.db_set("sk_needs_ceo", 1)
		po.add_comment("Comment", _("Waits for CEO: {0}").format(why))
		for a in requisition._ceos():
			if a != user:
				_todo(a, "Purchase Order", po.name, _("Approve PO {0}: {1} for {2} ({3})").format(po.name, po.supplier_name,
					fmt_money(po.grand_total, currency=po.currency), why))
		return {"name": po.name, "posted": False, "needs_approval": True, "grand_total": po.grand_total, "why": why}
	posted = try_submit(po)
	return {"name": po.name, "posted": posted, "reason": draft_reason(), "needs_approval": False, "grand_total": po.grand_total}

def decide(user: str, purchase_order: str, approve: bool, reason=None) -> dict:
	need(user, "Management")
	po = frappe.get_doc("Purchase Order", purchase_order)
	if po.docstatus != 0:
		frappe.throw(_("{0} is already decided").format(purchase_order))
	frappe.db.set_value("ToDo", {"reference_type": "Purchase Order", "reference_name": po.name, "status": "Open"}, "status", "Closed")
	if approve:
		po.add_comment("Comment", _("Approved in SK App"))
		po.flags.ignore_permissions = True
		frappe.flags.sk_ceo_po = True
		try:
			posted = try_submit(po)
			return {"name": po.name, "posted": posted, "reason": draft_reason()}
		finally:
			frappe.flags.sk_ceo_po = False
	po.add_comment("Comment", _("Rejected in SK App: {0}").format(reason or "-"))
	_todo(po.owner, "Purchase Order", po.name, _("PO {0} rejected: {1}").format(po.name, reason or "-"))
	return {"name": po.name, "rejected": True}

def follow_up_note(user: str, purchase_order: str, text: str, promised=None) -> dict:
	need(user, PURCHASE)
	msg = (text or "").strip()
	if promised:
		msg += "\n" + _("New promised date: {0}").format(frappe.utils.formatdate(promised))
	if not msg:
		frappe.throw(_("Please speak what the supplier said"))
	frappe.get_doc("Purchase Order", purchase_order).add_comment("Comment", msg)
	return {"ok": True}

def new_supplier(user: str, supplier_name: str, gstin=None, mobile=None, group=None, photo=None, cheque_photo=None) -> dict:
	need(user, PURCHASE)
	supplier_name = (supplier_name or "").strip()
	if not supplier_name:
		frappe.throw(_("Please give the supplier's name"))
	gstin = (gstin or "").strip().upper() or None
	if gstin and _has_gstin():
		other = frappe.db.get_value("Supplier", {"gstin": gstin}, "name")
		if other:
			frappe.throw(_("GSTIN {0} is already supplier {1}").format(gstin, other))
	if frappe.db.exists("Supplier", {"supplier_name": supplier_name}):
		frappe.throw(_("{0} is already in the supplier list").format(supplier_name))
	s = frappe.new_doc("Supplier")
	s.supplier_name = supplier_name
	s.supplier_type = "Company"
	s.supplier_group = group or frappe.db.get_single_value("Buying Settings", "supplier_group") or \
		frappe.db.get_value("Supplier Group", {"is_group": 0}, "name")
	if gstin and _has_gstin():
		s.gstin = gstin
		if s.meta.has_field("gst_category"):
			s.gst_category = "Registered Regular"
	if mobile:
		s.mobile_no = mobile
	s.flags.ignore_permissions = True
	s.insert()
	if mobile:
		c = frappe.new_doc("Contact")
		c.first_name = supplier_name
		c.append("phone_nos", {"phone": mobile, "is_primary_mobile_no": 1})
		c.append("links", {"link_doctype": "Supplier", "link_name": s.name})
		c.flags.ignore_permissions = True
		c.insert()
	attach(photo, "Supplier", s.name, user)
	attach(cheque_photo, "Supplier", s.name, user)
	if cheque_photo:
		for who in _users_with_function("Accounts"):
			_todo(who, "Supplier", s.name, _("Add bank details for new supplier {0} from the cheque photo").format(supplier_name))
	return {"name": s.name}

def send_bill(user: str, supplier: str, photo: str, amount=None, bill_no=None, against=None, note=None) -> dict:
	"""Supplier bill photo goes to Accounts as a task on the supplier, with the photo; Accounts makes the Purchase
	Invoice from it. Accounts also sends her own photos of bills / e-invoices this way (SK 27-Oct)."""
	need(user, PURCHASE, "Stores", "Accounts")
	if not photo:
		frappe.throw(_("Please take a photo of the bill"))
	text = _("Supplier bill from {0}").format(frappe.db.get_value("Supplier", supplier, "supplier_name") or supplier)
	extra = [x for x in (bill_no and _("Bill no {0}").format(bill_no), amount and _("Amount Rs {0}").format(fmt_money(flt(amount))),
		against and _("For {0}").format(against), note) if x]
	if extra:
		text += ": " + " · ".join(extra)
	attach(photo, "Supplier", supplier, user)
	accounts = _users_with_function("Accounts")
	for who in accounts:
		_todo(who, "Supplier", supplier, text)
	return {"sent_to": len(accounts)}
