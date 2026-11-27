"""Customer checks on the record (linear flow map, Flow 1 step 4). The Customer has one maker (make_customer),
but GSTIN and the billing address were optional, so 1,757 customers have 89 addresses and new quotes / orders stop on
customer_missing. On the New path of Sales every new customer, from any door, is checked once and its gaps logged."""

import frappe
from frappe import _

from sk_app.core.rules import report


def check_same_gstin(doc, method=None):
	"""Customer validate (SK 23-Nov checker: duplicate customers with the same GSTIN): a GSTIN already on another customer
	is refused with that customer's name, so the order goes to the existing one (merge in ERPNext if both are real)."""
	gstin = (doc.get("gstin") or "").strip().upper()
	if not gstin or frappe.flags.in_import or frappe.flags.in_migrate:
		return
	before = doc.get_doc_before_save() if not doc.is_new() else None
	if before and (before.get("gstin") or "").strip().upper() == gstin:
		return  # an old duplicate is listed by the checker, not stopped on every save
	other = frappe.db.get_value("Customer", {"gstin": gstin, "name": ["!=", doc.name], "disabled": 0}, ["name", "customer_name"], as_dict=True)
	if other:
		frappe.throw(_("GSTIN {0} is already on customer {1} ({2}). Use that customer, or ask Accounts to merge them.").format(
			gstin, other.customer_name, other.name), title=_("Same GSTIN"))


def same_gstin(gstin: str | None, not_this: str | None = None) -> dict | None:
	"""SK 27-Nov (HD deal 00190): the active customer that already has this GSTIN (so the app offers 'Use this customer')."""
	gstin = (gstin or "").strip().upper()
	if not gstin:
		return None
	return frappe.db.get_value("Customer", {"gstin": gstin, "name": ["!=", not_this or ""], "disabled": 0}, ["name", "customer_name"], as_dict=True)


def _has_business(customer: str) -> bool:
	return any(frappe.db.exists(dt, {field: customer, "docstatus": ["<", 2]}) for dt, field in (("Quotation", "party_name"),
		("Sales Order", "customer"), ("Sales Invoice", "customer"), ("Delivery Note", "customer"), ("Payment Entry", "party")))


def use_existing(user: str, deal: str, customer: str) -> dict:
	"""SK 27-Nov: the deal moves to the customer that already has the GSTIN. The organization changes too (saving a deal
	re-picks the customer by its organization name, which made the empty CUS-03485 on live); the empty customer made for
	the deal is disabled as a duplicate when it has no business on it."""
	from sk_app import crm

	crm._check("CRM Deal", deal, "write")
	if not frappe.db.exists("Customer", customer) or frappe.db.get_value("Customer", customer, "disabled"):
		frappe.throw(_("Customer {0} not found").format(customer))
	cname = frappe.db.get_value("Customer", customer, "customer_name")
	doc = frappe.get_doc("CRM Deal", deal)
	old = doc.get("erpnext_customer")
	if doc.meta.has_field("organization") and frappe.db.exists("DocType", "CRM Organization"):
		org = frappe.db.get_value("CRM Organization", {"organization_name": cname}) or frappe.db.get_value("CRM Organization", cname)
		if not org:
			org = frappe.get_doc({"doctype": "CRM Organization", "organization_name": cname}).insert(ignore_permissions=True).name
		doc.organization = org
	doc.erpnext_customer = customer
	from sk_app.gates import CUSTOMER_LINK

	if doc.meta.has_field(CUSTOMER_LINK):
		doc.set(CUSTOMER_LINK, customer)
	doc.flags.ignore_permissions = True
	doc.save()
	if frappe.get_meta("Customer").has_field("crm_deal"):
		frappe.db.set_value("Customer", customer, "crm_deal", deal, update_modified=False)
	dropped = None
	if old and old != customer and frappe.db.exists("Customer", old) and not _has_business(old):
		frappe.db.set_value("Customer", old, "disabled", 1)
		frappe.get_doc("Customer", old).add_comment("Comment", _("Duplicate of {0} ({1}): the deal {2} uses that customer (same GSTIN). Disabled by {3}.").format(
			customer, cname, deal, user))
		dropped = old
	from sk_app import gates

	return {"name": customer, "customer_name": cname, "disabled_duplicate": dropped, "missing": [t for _k, t in gates.customer_missing(customer)]}


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
		fill_group(have, deal)
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
	fill_group(name, deal)
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


def fill_group(customer: str, deal: str | None):
	"""SK 23-Nov checker (1,594 of 1,801 customers had no Cabin / Non-Cabin group): a customer used from a deal (new or
	existing) takes the deal's segment as its Customer Group when it has none or only an old one (Commercial, Individual
	...). A group already under Cabin / Non-Cabin is never changed."""
	from sk_app import segments

	group = frappe.db.get_value("Customer", customer, "customer_group")
	if group in segments.all_groups() or not deal:
		return
	sub = segments.sub_of(frappe.db.get_value("CRM Deal", deal, "sk_segment"))
	if sub and frappe.db.exists("Customer Group", segments.GROUP_OF[sub]):
		frappe.db.set_value("Customer", customer, "customer_group", segments.GROUP_OF[sub])


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
