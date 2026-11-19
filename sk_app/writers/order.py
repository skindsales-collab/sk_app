"""The Sales Order writer (order received with the PO, won deal, confirm order). Plan A step 6 (SK 9-Nov): moved
unchanged from erp_flow.py; names unchanged."""

from frappe import _
from frappe.utils import getdate, nowdate
from sk_app import store
from sk_app import store_screens
from sk_app.erp_flow import _attach_po
from sk_app.writers.quotation import submit_quotation
import frappe


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
	from sk_app.writers.customer import refresh_party

	refresh_party(so)  # SK 16-Nov: GST category / address from the Customer as it is today, not as the quote had it
	so.transaction_date = getdate(order_date or nowdate())
	so.delivery_date = getdate(delivery_date)
	for row in so.items:
		row.delivery_date = so.delivery_date
	so.po_no = (po_no or "").strip() or None
	if po_date:
		so.po_date = getdate(po_date)
	if not frappe.has_permission("Sales Order", "create"):
		frappe.throw(_("You may not make sales orders"), frappe.PermissionError)
	store.insert_for(so, user)
	if po_photo:
		_attach_po(po_photo, so.name, user)
	out = {"name": so.name, "grand_total": so.grand_total, "delivery_date": str(so.delivery_date), "submitted": False}
	if frappe.has_permission("Sales Order", "submit", so.name):
		with store_screens.as_system():
			so.flags.ignore_permissions = True
			so.submit()
		out["submitted"] = True
		_won(deal, so)
	return out

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
		with store_screens.as_system():
			so.flags.ignore_permissions = True
			so.submit()
	deals = {r.prevdoc_docname for r in so.items if r.get("prevdoc_docname")}
	for q in deals:
		_won(frappe.db.get_value("Quotation", q, "crm_deal") if frappe.get_meta("Quotation").has_field("crm_deal") else None, so)
	return {"name": so.name, "status": so.status}
