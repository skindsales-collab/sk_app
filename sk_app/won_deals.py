"""SK 28-Oct "why night ... they can see live update": the moment a Sales Order is submitted in ERPNext, the CRM lead or
deal it came from turns Won in the salesperson's CRM, with the order value, customer and date.

Frappe CRM only sends data to ERPNext (customer, quotation); nothing comes back when ERPNext submits the order. The
app's own order step already marks its deal Won (erp_flow._won). This does the same for orders submitted straight in
ERPNext, such as the draft orders made from the old CRM's won leads ("Source: CRM-LEAD-…" on the item, "From CRM-…" in
the PO no until the real PO number is typed). A won lead with no deal gets its deal made, owned by the lead's salesperson.
"""

import re

import frappe

REF = re.compile(r"CRM-(?:LEAD|DEAL)-\d{4}-\d+")

# lead fields copied onto the new deal when both have them
LEAD_FIELDS = ("salutation", "first_name", "last_name", "lead_name", "email", "mobile_no", "phone", "gender", "source",
	"territory", "industry", "website", "sk_segment", "sk_product")


def refs(so) -> list[str]:
	"""CRM lead / deal names the order points to: its quotation's deal, then any CRM-LEAD / CRM-DEAL in PO no or items."""
	out = []
	if frappe.get_meta("Quotation").has_field("crm_deal"):
		for q in {r.get("prevdoc_docname") for r in so.get("items") or [] if r.get("prevdoc_docname")}:
			out.append(frappe.db.get_value("Quotation", q, "crm_deal"))
	texts = [so.get("po_no")] + [r.get("description") for r in so.get("items") or []]
	for t in texts:
		out += REF.findall(t or "")
	return list(dict.fromkeys(r for r in out if r))


def on_submit(doc, method=None):
	if not frappe.db.exists("DocType", "CRM Deal"):
		return
	for ref in refs(doc):
		try:
			frappe.db.savepoint("sk_won_deal")
			won_from_order(ref, doc)
		except Exception:
			frappe.db.rollback(save_point="sk_won_deal")  # a half-made deal never stays behind; the order still submits
			frappe.log_error(f"SK App won deal from {doc.name} ({ref})")


def won_from_order(ref: str, so) -> str | None:
	from sk_app import erp_flow

	if ref.startswith("CRM-DEAL-"):
		deal = ref if frappe.db.exists("CRM Deal", ref) else None
	elif frappe.db.exists("CRM Lead", ref):
		deal = frappe.db.get_value("CRM Deal", {"lead": ref}) or deal_from_lead(ref, so)
	else:
		deal = None
	if not deal:
		return None
	# the order is already submitted: no gate to pass and no new order to make from the won deal
	flags = frappe.flags.sk_no_gate, frappe.flags.sk_won_from_order
	frappe.flags.sk_no_gate = frappe.flags.sk_won_from_order = True
	try:
		erp_flow._won(deal, so)
		d = frappe.get_meta("CRM Deal")
		if d.has_field("closed_date"):  # won on the order's date, not the day it was submitted
			frappe.db.set_value("CRM Deal", deal, "closed_date", so.transaction_date)
	finally:
		frappe.flags.sk_no_gate, frappe.flags.sk_won_from_order = flags
	return deal


def deal_from_lead(lead: str, so) -> str:
	"""The won lead's deal, as Frappe CRM's convert would make it, owned by the lead's salesperson."""
	ld = frappe.get_doc("CRM Lead", lead)
	meta = frappe.get_meta("CRM Deal")
	deal = frappe.new_doc("CRM Deal")
	deal.lead = lead
	for f in LEAD_FIELDS:
		if meta.has_field(f) and ld.meta.has_field(f) and ld.get(f):
			deal.set(f, ld.get(f))
	org = ld.get("organization") or so.customer_name
	if meta.has_field("organization") and org and frappe.db.exists("CRM Organization", org):
		deal.organization = org
	elif meta.has_field("organization_name"):
		deal.organization_name = org
	if meta.has_field("deal_owner") and ld.get("lead_owner"):
		deal.deal_owner = ld.lead_owner
	if meta.has_field("custom_segment"):
		seg = ld.get("sk_segment") or ""
		deal.custom_segment = "Machine Shifting" if "Machine Shifting" in seg else "Job Work" if "Job Work" in seg else "Cabin"
	if meta.has_field("erpnext_customer"):
		deal.erpnext_customer = so.customer
	won = frappe.get_all("CRM Deal Status", filters={"type": "Won"}, pluck="name", order_by="position asc", limit=1)
	deal.status = won[0] if won else "Won"
	flags = frappe.flags.sk_no_gate, frappe.flags.sk_won_from_order
	frappe.flags.sk_no_gate = frappe.flags.sk_won_from_order = True
	try:
		deal.flags.ignore_permissions = deal.flags.ignore_mandatory = True
		deal.insert()
	finally:
		frappe.flags.sk_no_gate, frappe.flags.sk_won_from_order = flags
	if ld.meta.has_field("converted"):
		frappe.db.set_value("CRM Lead", lead, "converted", 1, update_modified=False)
	return deal.name
