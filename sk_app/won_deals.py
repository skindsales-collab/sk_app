"""SK 28-Oct "why night ... they can see live update": the moment a Sales Order is submitted in ERPNext, the CRM lead or
deal it came from turns Won in the salesperson's CRM, with the order value, customer and date.

Frappe CRM only sends data to ERPNext (customer, quotation); nothing comes back when ERPNext submits the order. The
app's own order step already marks its deal Won (order_w._won). This does the same for orders submitted straight in
ERPNext, such as the draft orders made from the old CRM's won leads ("Source: CRM-LEAD-…" on the item, "From CRM-…" in
the PO no until the real PO number is typed). A won lead with no deal gets its deal made, owned by the lead's salesperson.
"""

import re

import frappe
from sk_app.writers import order as order_w

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
	"""SK 4-Nov rebuild (S1, S2): before this a failure here was only logged, so orders stayed submitted while their deal
	never turned Won (4-Nov: 66 won leads, 56 won deals, 111 orders). Now every gap goes to SK Rule Log with its link;
	with Sales rules on Enforce the submit itself is stopped with the reason, so it is never half done."""
	from sk_app.core.rules import report

	if not frappe.db.exists("DocType", "CRM Deal"):
		return
	found = refs(doc)
	problems = []
	if not found:
		found, problem = deals_by_customer(doc)
		if problem:
			problems.append(problem)
	for ref in found:
		try:
			frappe.db.savepoint("sk_won_deal")
			won_from_order(ref, doc)
		except Exception as e:
			frappe.db.rollback(save_point="sk_won_deal")  # a half-made deal never stays behind
			frappe.log_error(f"SK App won deal from {doc.name} ({ref})")
			problems.append(("won_deal_failed", f"Order {doc.name}: {ref} could not be marked Won: "
				+ frappe.utils.strip_html(str(e) or type(e).__name__)[:200]))
	report("Sales", doc, problems, title="Deal not marked Won")


def deals_by_customer(so) -> tuple[list[str], tuple | None]:
	"""An order with no CRM reference: the customer's one open deal. Two or more open deals, or none, is a gap to look at."""
	meta = frappe.get_meta("CRM Deal")
	if not meta.has_field("erpnext_customer") or not so.get("customer"):
		return [], ("order_without_deal", f"Order {so.name} ({so.get('customer_name') or so.get('customer')}) has no CRM lead or deal")
	closed = frappe.get_all("CRM Deal Status", filters={"type": ["in", ["Won", "Lost"]]}, pluck="name") or ["Won", "Lost"]
	won = frappe.get_all("CRM Deal Status", filters={"type": "Won"}, pluck="name") or ["Won"]
	open_deals = frappe.get_all("CRM Deal", filters={"erpnext_customer": so.customer, "status": ["not in", closed]},
		pluck="name", order_by="modified desc")
	if len(open_deals) == 1:
		return open_deals, None
	if open_deals:
		return [], ("order_many_deals", f"Order {so.name}: customer {so.customer} has {len(open_deals)} open deals "
			f"({', '.join(open_deals[:5])}); please put the right deal number in the order")
	if frappe.db.exists("CRM Deal", {"erpnext_customer": so.customer, "status": ["in", won]}):
		return [], None  # the customer's deal is already Won (repeat order): nothing to change
	return [], ("order_without_deal", f"Order {so.name} ({so.get('customer_name') or so.customer}) has no CRM lead or deal")


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
		order_w._won(deal, so)
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


# ---- SK 14-Nov (KF-05180): Won = PO received = Sales Order exists ----
def order_of_deal(deal: str, customer: str | None = None) -> str | None:
	"""The deal's submitted Sales Order: through its quotations (Quotation.crm_deal), else the first order of its customer."""
	if frappe.get_meta("Quotation").has_field("crm_deal"):
		quotes = frappe.get_all("Quotation", filters={"crm_deal": deal}, pluck="name")
		if quotes:
			so = frappe.db.get_value("Sales Order Item", {"prevdoc_docname": ["in", quotes], "docstatus": 1}, "parent")
			if so:
				return so
	# SK 18-Nov: an order whose Customer's PO names the deal or its lead ('From CRM-LEAD-2026-00635')
	from sk_app.gates import orders_by_po

	by_po = [o for o in orders_by_po([deal, frappe.db.get_value("CRM Deal", deal, "lead")]) if o.docstatus == 1]
	if by_po:
		return sorted(by_po, key=lambda o: str(o.transaction_date), reverse=True)[0].name
	if customer:
		return frappe.db.get_value("Sales Order", {"customer": customer, "docstatus": 1}, "name", order_by="transaction_date desc")
	return None


def check_won(doc, method=None):
	"""CRM Deal validate: a deal marked Won by hand with no Sales Order is a rule gap (Warn under the Sales Path Switch,
	Enforce later). The app's way to win is "make the Sales Order from the deal", which marks it Won itself."""
	from sk_app.core.rules import report
	from sk_app.writers.lead_rules import deal_won_gap

	won = set(frappe.get_all("CRM Deal Status", filters={"type": "Won"}, pluck="name") or ["Won"])
	before = doc.get_doc_before_save()
	is_won = doc.get("status") in won
	so = order_of_deal(doc.name, doc.get("erpnext_customer")) if is_won else None
	if is_won and so:
		# SK 17-Nov: the Won date is the order's date, never the day the status was typed (Indeva 16-Sep showed under October)
		d = frappe.db.get_value("Sales Order", so, ["transaction_date", "base_grand_total", "customer"], as_dict=True)
		if d:
			if doc.meta.has_field("closed_date"):
				doc.closed_date = d.transaction_date
			if doc.meta.has_field("deal_value") and not doc.get("deal_value"):
				doc.deal_value = d.base_grand_total
			if doc.meta.has_field("erpnext_customer") and not doc.get("erpnext_customer"):
				doc.erpnext_customer = d.customer
	problems = deal_won_gap(bool(before and before.get("status") in won), is_won, bool(frappe.flags.sk_won_from_order), bool(so))
	report("Sales", doc, problems, title="Deal Won without an order")


def won_without_order() -> list[dict]:
	"""Every deal with a Won status and no submitted Sales Order (the night check lists them to their owner)."""
	won = frappe.get_all("CRM Deal Status", filters={"type": "Won"}, pluck="name") or ["Won"]
	meta = frappe.get_meta("CRM Deal")
	fields = [f for f in ("name", "organization", "deal_owner", "erpnext_customer", "modified") if f in ("name", "modified") or meta.has_field(f)]
	return [d for d in frappe.get_all("CRM Deal", filters={"status": ["in", won]}, fields=fields, limit=0) if not order_of_deal(d.name, d.get("erpnext_customer"))]
