"""The one Purchase Receipt writer (linear flow map, Flow 3 step 4 and Flow 4 Store). Material at the gate becomes a
draft receipt from its PO with the challan and goods photos; Store posts it after checking. Used on the New path of
Store; the rules also run on every Purchase Receipt saved in ERPNext or through SK Hub."""

import frappe
from frappe import _
from frappe.utils import flt, nowdate

from sk_app.core.rules import report
from sk_app.writers.receipt_rules import problems, received_rows


def write(user: str, purchase_order: str, got: dict, *, challan_photo=None, goods_photo=None, note=None, reason=None, bill_no=None,
		insert_for, attach) -> dict:
	from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt

	pr = make_purchase_receipt(purchase_order)
	rows = {r.purchase_order_item: r for r in pr.items}
	keep = received_rows([{"name": r.purchase_order_item, "item_code": r.item_code, "qty": flt(r.qty)} for r in pr.items], got)
	if not keep:
		frappe.throw(_("Please give the quantity received"))
	for k in keep:
		row = rows[k["name"]]
		row.qty = row.received_qty = k["qty"]
	pr.set("items", [rows[k["name"]] for k in keep])
	pr.posting_date = nowdate()
	if bill_no:  # the supplier's invoice / challan number read from the photo (SK 26-Oct)
		pr.supplier_delivery_note = str(bill_no).strip()[:140]
	remarks = [x for x in (note, reason and _("Without PO: {0}").format(reason)) if x]
	if remarks:
		pr.remarks = "\n".join(remarks)
	insert_for(pr, user)  # on_validate checks it, as for a receipt made in ERPNext or by Claude
	attach(challan_photo, "Purchase Receipt", pr.name, user)
	attach(goods_photo, "Purchase Receipt", pr.name, user)
	return {"name": pr.name, "items": len(pr.items)}


def on_validate(doc, method=None):
	"""Every Purchase Receipt on the New path of Store: quantity on every line, against a PO, challan number."""
	from sk_app.core.switch import use_new
	from sk_app.requisition import _is_ceo

	if doc.docstatus == 1 or not use_new("Store", doc.owner or frappe.session.user):
		return
	rows = [{"item_code": r.item_code, "qty": flt(r.qty), "purchase_order": r.purchase_order} for r in doc.get("items") or []]
	found = problems(rows, bool(doc.is_return), _is_ceo(doc.owner or frappe.session.user), doc.get("supplier_delivery_note"))
	report("Store", doc, found, title=_("Receipt data missing"))
