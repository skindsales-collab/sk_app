"""Purchase screens (SK, 26-Oct-2026 draft F02): requests to buy, get rates from 3 suppliers on WhatsApp / email,
compare quotes, Purchase Order with SK's approval above a limit, delivery follow-up, new supplier, supplier bills to
Accounts and last rates. Free only: messages go from the person's own WhatsApp / mail app.
"""

import frappe
from frappe import _
from frappe.utils import add_days, flt, fmt_money, getdate, nowdate

from sk_app.store import _company, _todo, _users_with_function, attach, material_pos, material_requests, need, try_submit, uom

PURCHASE = "Purchase"
# SK 26-Oct-2026: Rs 5,000 (draft F02 had proposed Rs 50,000); can be changed in site config "sk_po_approval_limit"
DEFAULT_PO_LIMIT = 5000


def po_limit() -> float:
	return flt(frappe.conf.get("sk_po_approval_limit") or DEFAULT_PO_LIMIT)


def requests(user: str) -> list[dict]:
	need(user, PURCHASE)
	rows = material_requests(user, "purchase")
	for r in rows:
		mr = frappe.db.get_value("Material Request", r["request"], ["sk_priority", "sk_supplier"], as_dict=True) or {}
		r["supplier"] = mr.get("sk_supplier")  # material that came without PO: that supplier
		r["urgent"] = mr.get("sk_priority") == "Urgent" \
			or bool(r["needed_by"] and getdate(r["needed_by"]) <= getdate(add_days(nowdate(), 1))) or r["age_hours"] > 24
		last = last_rate(r["item_code"])
		r["last_rate"], r["last_supplier"] = (last["rate"], last["supplier"]) if last else (None, None)
	return sorted(rows, key=lambda r: (not r["urgent"], r["needed_by"] or "9999"))


def last_rate(item_code: str) -> dict | None:
	for dt, date in (("Purchase Order", "transaction_date"), ("Purchase Invoice", "posting_date")):
		rows = frappe.db.sql(f"""select p.supplier, i.rate, p.{date} as date from `tab{dt} Item` i
			join `tab{dt}` p on p.name = i.parent where p.docstatus = 1 and i.item_code = %s
			order by p.creation desc limit 1""", item_code, as_dict=True)
		if rows:
			return {**rows[0], "date": str(rows[0].date), "from": dt}
	return None


def last_rates(user: str, q: str | None = None) -> list[dict]:
	need(user, PURCHASE, "Stores")
	like = f"%{(q or '').strip()}%"
	rows = frappe.db.sql("""select i.item_code, i.item_name, p.supplier, i.rate, i.uom, p.posting_date as date
		from `tabPurchase Invoice Item` i join `tabPurchase Invoice` p on p.name = i.parent
		where p.docstatus = 1 and (i.item_name like %(q)s or i.item_code like %(q)s)
		union all
		select i.item_code, i.item_name, p.supplier, i.rate, i.uom, p.transaction_date as date
		from `tabPurchase Order Item` i join `tabPurchase Order` p on p.name = i.parent
		where p.docstatus = 1 and (i.item_name like %(q)s or i.item_code like %(q)s)
		order by date desc limit 200""", {"q": like}, as_dict=True)
	seen, out = set(), []
	for r in rows:
		key = (r.item_code, r.supplier)
		if key not in seen:
			seen.add(key)
			out.append({**r, "date": str(r.date)})
	return out[:60]


def suggest_suppliers(user: str, item_code: str) -> list[dict]:
	"""Suppliers who sold this item before (best first), then others of the same supplier group, up to 6."""
	need(user, PURCHASE)
	past = frappe.db.sql("""select supplier, count(*) n, max(d) last from (
			select p.supplier, p.posting_date d from `tabPurchase Invoice Item` i join `tabPurchase Invoice` p on p.name = i.parent
			where p.docstatus = 1 and i.item_code = %(item)s
			union all
			select p.supplier, p.transaction_date d from `tabPurchase Order Item` i join `tabPurchase Order` p on p.name = i.parent
			where p.docstatus = 1 and i.item_code = %(item)s
			union all
			select q.supplier, q.transaction_date d from `tabSupplier Quotation Item` i join `tabSupplier Quotation` q on q.name = i.parent
			where q.docstatus < 2 and i.item_code = %(item)s) x
		group by supplier order by n desc, last desc limit 6""", {"item": item_code}, as_dict=True)
	names = [r.supplier for r in past]
	groups = {g for g in frappe.get_all("Supplier", filters={"name": ["in", names or [""]]}, pluck="supplier_group") if g}
	if len(names) < 6 and groups:
		names += frappe.get_all("Supplier", filters={"supplier_group": ["in", list(groups)], "disabled": 0,
			"name": ["not in", names or [""]]}, pluck="name", limit=6 - len(names))
	return [_supplier_row(s) for s in names]


def _has_gstin() -> bool:
	return frappe.get_meta("Supplier").has_field("gstin")  # India Compliance app adds it


def _supplier_row(name: str) -> dict:
	fields = ["name", "supplier_name", "supplier_group", "mobile_no", "email_id"] + (["gstin"] if _has_gstin() else [])
	s = frappe.db.get_value("Supplier", name, fields, as_dict=True) or {}
	last = frappe.get_all("Purchase Invoice", filters={"supplier": name, "docstatus": 1}, pluck="posting_date",
		order_by="posting_date desc", limit=1)
	last = last[0] if last else None
	return {**s, "last_bill": str(last) if last else None}


def suppliers(user: str, q: str | None = None) -> list[dict]:
	need(user, PURCHASE, "Stores", "Accounts")
	like = f"%{(q or '').strip()}%"
	gst = _has_gstin()
	return frappe.get_all("Supplier", filters={"disabled": 0},
		or_filters=[["supplier_name", "like", like]] + ([["gstin", "like", like]] if gst else []),
		fields=["name", "supplier_name", "supplier_group", "mobile_no"] + (["gstin"] if gst else []), order_by="supplier_name asc", limit=30)


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


def compare(user: str, item_code: str) -> dict:
	need(user, PURCHASE)
	quotes = frappe.db.sql("""select q.name, q.supplier, i.rate, i.qty, i.lead_time_days, q.transaction_date, q.valid_till, q.docstatus
		from `tabSupplier Quotation Item` i join `tabSupplier Quotation` q on q.name = i.parent
		where q.docstatus < 2 and i.item_code = %s and q.transaction_date >= %s order by i.rate asc""",
		(item_code, add_days(nowdate(), -30)), as_dict=True)
	last = last_rate(item_code)
	best = quotes[0] if quotes else None
	return {"item_code": item_code, "item_name": frappe.db.get_value("Item", item_code, "item_name"),
		"quotes": [{**q, "transaction_date": str(q.transaction_date), "valid_till": str(q.valid_till or "")} for q in quotes],
		"last": last, "saving": (flt(last["rate"]) - flt(best.rate)) * flt(best.qty) if (last and best) else None, "limit": po_limit()}


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

	requisition.link_requests(po)
	if any(not r.material_request for r in po.items) and not requisition._is_ceo(user):
		frappe.throw(_("No CEO-approved purchase requisition for: {0}. Raise a requisition first.").format(
			", ".join(sorted({r.item_code for r in po.items if not r.material_request}))))
	po.flags.ignore_permissions = True
	po.insert()
	po.calculate_taxes_and_totals()
	why = requisition.needs_ceo(po)
	if why and not requisition._is_ceo(user):  # the CEO's own PO needs no second approval
		po.db_set("sk_needs_ceo", 1)
		po.add_comment("Comment", _("Waits for CEO: {0}").format(why))
		for a in requisition._ceos():
			if a != user:
				_todo(a, "Purchase Order", po.name, _("Approve PO {0}: {1} for {2} ({3})").format(po.name, po.supplier_name,
					fmt_money(po.grand_total, currency=po.currency), why))
		return {"name": po.name, "posted": False, "needs_approval": True, "grand_total": po.grand_total, "why": why}
	return {"name": po.name, "posted": try_submit(po), "needs_approval": False, "grand_total": po.grand_total}


def approvals(user: str) -> list[dict]:
	"""Purchase Orders waiting for the CEO (over 10% above the approved requisition)."""
	need(user, "Management")
	rows = frappe.get_all("Purchase Order", filters={"docstatus": 0, "sk_needs_ceo": 1},
		fields=["name", "supplier_name", "grand_total", "schedule_date", "owner", "creation"], order_by="creation asc")
	for r in rows:
		r["why"] = frappe.db.get_value("Comment", {"reference_doctype": "Purchase Order", "reference_name": r.name,
			"content": ["like", "Waits for CEO%"]}, "content", order_by="creation desc")
	return rows


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
			return {"name": po.name, "posted": try_submit(po)}
		finally:
			frappe.flags.sk_ceo_po = False
	po.add_comment("Comment", _("Rejected in SK App: {0}").format(reason or "-"))
	_todo(po.owner, "Purchase Order", po.name, _("PO {0} rejected: {1}").format(po.name, reason or "-"))
	return {"name": po.name, "rejected": True}


def follow_up(user: str) -> list[dict]:
	"""Orders due today or late, with the supplier's phone."""
	need(user, PURCHASE)
	pos = frappe.get_all("Purchase Order", filters={"docstatus": 1, "status": ["in", ["To Receive and Bill", "To Receive"]],
		"schedule_date": ["<=", nowdate()], **material_pos()}, fields=["name", "supplier", "supplier_name", "schedule_date", "grand_total"],
		order_by="schedule_date asc")
	for p in pos:
		p["days_late"] = (getdate() - getdate(p.schedule_date)).days
		p["mobile"] = frappe.db.get_value("Supplier", p.supplier, "mobile_no")
		p["items"] = ", ".join(frappe.get_all("Purchase Order Item", filters={"parent": p.name}, pluck="item_name", limit=3))
		p["schedule_date"] = str(p.schedule_date)
	return pos


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


def badges(user: str, functions: list[str]) -> dict:
	out = {}
	if PURCHASE in functions:
		out["buy_requests"] = len(material_requests(user, "purchase"))
		out["po_follow_up"] = frappe.db.count("Purchase Order", {"docstatus": 1, "status": ["in", ["To Receive and Bill", "To Receive"]],
			"schedule_date": ["<=", nowdate()]})
	if "Management" in functions:
		from sk_app.requisition import badges as req_badges

		out["po_approvals"] = frappe.db.count("Purchase Order", {"docstatus": 0, "sk_needs_ceo": 1}) \
			+ req_badges(user, functions).get("po_approvals", 0)
	return {k: v for k, v in out.items() if v}
