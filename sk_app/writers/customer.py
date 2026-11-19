"""Customer checks on the record (linear flow map, Flow 1 step 4). The Customer has one maker (make_customer),
but GSTIN and the billing address were optional, so 1,757 customers have 89 addresses and new quotes / orders stop on
customer_missing. On the New path of Sales every new customer, from any door, is checked once and its gaps logged."""

import frappe
from frappe import _

from sk_app.core.rules import report


def after_insert(doc, method=None):
	from sk_app import gates
	from sk_app.core.switch import use_new

	if not use_new("Sales", doc.owner or frappe.session.user):
		return
	report("Sales", doc, [("customer_" + k, f"Customer {doc.customer_name}: {w}") for k, w in gates.customer_missing(doc.name)],
		title=_("Customer data missing"))


# ---------- Plan A (SK 9-Nov): moved here unchanged from erp_flow.py ----------
from frappe import _
from sk_app import store
from sk_app import store_screens
from sk_app.erp_flow import _deal, customer_of
import frappe


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
		if not frappe.has_permission("Customer", "create"):
			frappe.throw(_("You may not make customers"), frappe.PermissionError)
		store.insert_for(doc, user)  # debtors account filled by ERPNext (see store_screens.as_system)
		name = doc.name
	if frappe.get_meta("CRM Deal").has_field("erpnext_customer"):
		frappe.db.set_value("CRM Deal", deal, "erpnext_customer", name)
	# SK 29-Oct (Aditya: customer details asked 3 times): what the lead / deal already has goes onto the customer
	if not same and d.get("mobile_no"):
		with store_screens.as_system():
			gates.complete_customer(name, mobile=d.mobile_no)
	if not same and frappe.utils.cint(d.get(gates.NO_GSTIN)):
		with store_screens.as_system():  # SK 4-Nov: ticked 'No GSTIN' on the lead: Unregistered, no GSTIN asked again
			gates.complete_customer(name, unregistered=1)
	if details:
		gates.complete_customer(name, **details)
	return {"name": name, "new": not same, "missing": [t for _k, t in gates.customer_missing(name)]}


def refresh_party(doc):
	"""SK 16-Nov (Swati, deal 00126): a revised quote kept the old GST category and no address while the customer had
	just got a GSTIN -> 'GST Category cannot be Unregistered for party with GSTIN', and the app froze. Every quotation /
	order the app writes re-reads GST category, GSTIN and billing address from the Customer, never from the old document."""
	from erpnext.accounts.party import get_party_details

	customer = doc.get("party_name") if doc.doctype == "Quotation" else doc.get("customer")
	if not customer or (doc.doctype == "Quotation" and doc.get("quotation_to") != "Customer"):
		return
	for f in ("customer_address", "address_display", "billing_address_gstin", "gst_category", "customer_group", "territory"):
		if doc.meta.has_field(f):
			doc.set(f, None)
	try:
		d = get_party_details(party=customer, party_type="Customer", doctype=doc.doctype, company=doc.get("company"), ignore_permissions=True) or {}
	except Exception:
		frappe.log_error(f"SK App party details {doc.doctype} {customer}")
		d = {}
	for f in ("customer_address", "address_display", "billing_address_gstin", "gst_category", "customer_group", "territory",
			"contact_person", "contact_display", "contact_mobile", "contact_email", "customer_name"):
		if d.get(f) and doc.meta.has_field(f) and (f not in ("contact_person", "contact_display", "contact_mobile", "contact_email") or not doc.get(f)):
			doc.set(f, d.get(f))
	if doc.meta.has_field("gst_category") and not doc.get("gst_category"):
		doc.gst_category = frappe.db.get_value("Customer", customer, "gst_category")
