"""The one Quotation writer (linear flow map, Flow 1 step 6). Used by the cabin quote, building quote, item quote and
the quote file on a deal, on the New path of Sales. Before this, four files each made a Quotation their own way: some
without the GST line, some without a quote number, some saved as the system and not in the person's name.

Same inputs and outputs for the user (SK 4-Nov): each caller still prices its own items and returns the same answer;
only the making of the record is shared."""

import frappe
from frappe import _
from frappe.utils import add_days, nowdate

from sk_app.core.rules import report
from sk_app.writers.quotation_rules import gst_terms, problems, ref_kind, revision


def _segment(deal: str | None) -> str | None:
	if deal and frappe.get_meta("CRM Deal").has_field("sk_main_segment"):
		return frappe.db.get_value("CRM Deal", deal, "sk_main_segment")
	return None


def _save_as_system(doc, user: str):
	"""ERPNext fills the GST tax accounts while saving and refuses Sales, who may not read accounts (SK 29-Oct):
	saved by the system, kept in the person's name."""
	current = frappe.session.user
	frappe.set_user("Administrator")
	try:
		doc.flags.ignore_permissions = True
		doc.save()
	finally:
		frappe.set_user(current)
	who = user if user and frappe.db.exists("User", user) else None
	if who:
		frappe.db.set_value("Quotation", doc.name, {"owner": doc.owner or who, "modified_by": who}, update_modified=False)


def write(user: str, *, customer: str, items: list[dict], deal: str | None = None, kind: str | None = None,
		terms: str | None = None, valid_days: int = 15, revise: str | None = None, contact: str | None = None,
		extra: dict | None = None, owner: str | None = None):
	"""Make (or revise) a Quotation. items = [{item_code, qty, rate, description?, uom?}]. extra = the caller's own
	fields (rate card, discount, cabin request ...). owner = who the quote is for when the system makes it (the deal
	owner for a quote file); else the person making it. Returns the saved draft."""
	from sk_app.cabin_quote import _deal_to_quotation, _new_ref

	old = frappe.get_doc("Quotation", revise) if revise else None
	how = revision({"party_name": old.party_name, "docstatus": old.docstatus, "sk_quote_ref": old.get("sk_quote_ref"),
		"sk_rev": old.get("sk_rev")} if old else None, customer)
	if how["mode"] == "refuse":
		frappe.throw(_(how["why"]))
	if how["mode"] == "in_place":
		doc = old
		doc.set("items", [])
	else:
		doc = frappe.new_doc("Quotation")
		doc.update({"quotation_to": "Customer", "party_name": customer})
		doc.owner = owner or user
	if doc.meta.has_field("sk_quote_ref"):
		doc.sk_quote_ref = how["ref"] or _new_ref(customer, ref_kind(kind, _segment(deal)))
		doc.sk_rev = how["rev"]
	for it in items:
		doc.append("items", {k: v for k, v in it.items() if v not in (None, "")})
	doc.transaction_date = nowdate()
	doc.valid_till = add_days(nowdate(), int(valid_days or 15))
	doc.ignore_pricing_rule = 1
	doc.terms = gst_terms(terms)
	if deal and doc.meta.has_field("crm_deal"):
		doc.crm_deal = deal
	if contact and doc.meta.has_field("contact_person") and frappe.db.exists("Contact", contact):
		doc.contact_person = contact
	for k, v in (extra or {}).items():
		if doc.meta.has_field(k) or k in ("additional_discount_percentage", "apply_discount_on"):
			doc.set(k, v)
	_save_as_system(doc, owner or user)  # on_validate checks it, as for a quote made in ERPNext or by Claude
	if deal:
		_deal_to_quotation(deal)
	return doc


def on_validate(doc, method=None):
	"""Every Quotation, from the app, ERPNext or SK Hub (SK 4-Nov), on the New path of Sales: customer, deal link, items."""
	from sk_app.core.switch import use_new

	if doc.docstatus == 1 or doc.quotation_to != "Customer" or not use_new("Sales", doc.owner or frappe.session.user):
		return
	items = [{"item_code": r.item_code, "qty": r.qty, "rate": r.rate} for r in doc.get("items") or []]
	report("Sales", doc, problems(doc.party_name, doc.get("crm_deal"), items), title=_("Quotation data missing"))
