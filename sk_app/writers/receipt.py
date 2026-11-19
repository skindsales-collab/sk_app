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


# ---------- Plan A (SK 9-Nov): moved here unchanged from store.py ----------
from frappe import _
from frappe.utils import flt, nowdate
from sk_app.core.switch import use_new
from sk_app.store import STORE, attach, insert_for, need, submit_for
import frappe


def receive(user: str, purchase_order: str | None, items: list[dict], challan_photo=None, goods_photo=None, note=None,
		supplier=None, reason=None, bill_no=None) -> dict:
	"""Material at the gate: a draft Purchase Receipt from the PO with the challan photo. Store posts it after checking.
	Material without a PO is not received here: it goes through an urgent requisition first (SK 27-Oct)."""
	need(user, STORE, "Accounts")  # SK 2-Nov: Accounts receives material like Store
	qty = {i.get("po_detail") or i.get("item_code"): flt(i.get("qty")) for i in items or []}
	if purchase_order and use_new("Store", user):  # rebuild: the one Purchase Receipt writer (linear flow map, Flow 4)
		from sk_app.writers import receipt as rw

		return rw.write(user, purchase_order, qty, challan_photo=challan_photo, goods_photo=goods_photo, note=note, reason=reason,
			bill_no=bill_no, insert_for=insert_for, attach=attach)
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
		# SK 27-Oct: no receipt without a PO; Store raises an urgent requisition (Receive → Came without PO)
		frappe.throw(_("Material without PO: use Came without PO. It goes to the CEO, then a PO is made and you receive against it."))
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

def post_receipt(user: str, name: str, rates: dict | None = None) -> dict:
	"""Store checked the material: post the receipt (stock goes up). A rate missing on a receipt without PO is taken from
	the supplier's bill, as ERPNext needs it to value the stock."""
	need(user, STORE, "Accounts")  # SK 2-Nov: Accounts receives material like Store
	doc = frappe.get_doc("Purchase Receipt", name)
	if doc.docstatus != 0:
		frappe.throw(_("{0} is already posted").format(name))
	if rates:
		for row in doc.items:
			if flt(rates.get(row.item_code)) > 0:
				row.rate = flt(rates[row.item_code])
		doc.flags.ignore_permissions = True
		doc.save()
	posted = submit_for(doc, user)
	reason = None if posted else frappe.db.get_value("Comment", {"reference_doctype": "Purchase Receipt", "reference_name": name,
		"content": ["like", "Kept as draft%"]}, "content", order_by="creation desc")
	return {"name": name, "posted": posted, "reason": reason}

def drop_receipt(user: str, name: str) -> dict:
	"""A receipt saved twice by mistake: delete the extra draft (only drafts; a posted one is cancelled in ERPNext)."""
	need(user, STORE, "Accounts")  # SK 2-Nov: Accounts receives material like Store
	if frappe.db.get_value("Purchase Receipt", name, "docstatus") != 0:
		frappe.throw(_("Only a draft can be removed"))
	frappe.delete_doc("Purchase Receipt", name, ignore_permissions=True)
	return {"ok": True}
