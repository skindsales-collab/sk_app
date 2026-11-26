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
		# SK 26-Nov: the person is the owner (a new quote saved as the system had owner Administrator, so the salesperson's
		# own lists and the signature lost it); an existing quote keeps its owner
		owner = doc.owner if doc.owner and doc.owner not in ("Administrator", "Guest") else who
		frappe.db.set_value("Quotation", doc.name, {"owner": owner, "modified_by": who}, update_modified=False)
		doc.owner = owner


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
	refresh_party(doc)  # SK 16-Nov: GST category, GSTIN and address always from the Customer, never from the old quote
	_save_as_system(doc, owner or user)  # on_validate checks it, as for a quote made in ERPNext or by Claude
	if deal:
		_deal_to_quotation(deal)
		from sk_app.deal_quotes import _close_tasks

		_close_tasks(deal)  # SK 23-Nov: the "make the quote in the app" task is done
	return doc


def on_validate(doc, method=None):
	"""Every Quotation, from the app, ERPNext or SK Hub (SK 4-Nov), on the New path of Sales: customer, deal link, items."""
	from sk_app.core.switch import use_new

	if doc.docstatus == 1 or doc.quotation_to != "Customer" or not use_new("Sales", doc.owner or frappe.session.user):
		return
	items = [{"item_code": r.item_code, "qty": r.qty, "rate": r.rate} for r in doc.get("items") or []]
	report("Sales", doc, problems(doc.party_name, doc.get("crm_deal"), items), title=_("Quotation data missing"))


# ---------- Plan A (SK 9-Nov): moved here unchanged from erp_flow.py ----------
from frappe import _
from frappe.utils import add_days, flt, nowdate
from sk_app import crm, store
from sk_app.core.switch import use_new
from sk_app.erp_flow import _rate, gst_terms
from sk_app.writers.customer import make_customer, refresh_party
import frappe


def make_quotation(user: str, deal: str | None, items: list[dict], valid_days: int = 15, note: str | None = None, lead: str | None = None) -> dict:
	"""Step 2 (Sales): a Quotation for the deal's customer, items with qty and rate (rate from the price list when
	left empty). Saved as draft; its PDF opens at once to send to the customer."""
	frappe.flags.sk_quote_in_hand = True  # made by hand: the quote AI must not make a second one (quote_pickup)
	if not deal and not lead:  # Mac test 9-Nov: a crash ('NoneType'.get) instead of a plain word
		frappe.throw(_("Pick the deal or the lead first"))
	if lead and not deal:  # SK 29-Oct: a quote straight from the lead (it becomes a deal, as for cabin quotes)
		from sk_app.cabin_quote import _customer_for

		deal = _customer_for(user, None, lead)[1]
	customer = make_customer(user, deal)["name"]
	rows = []
	for it in items or []:
		code = (it.get("item_code") or "").strip()
		if not code:
			continue
		if not frappe.db.exists("Item", code):
			code = frappe.db.get_value("Item", {"item_name": code}) or code
		if not frappe.db.exists("Item", code):
			frappe.throw(_("Item {0} is not in ERPNext. Pick it from the list").format(it.get("item_code")))
		qty = flt(it.get("qty")) or 1
		rate = flt(it.get("rate")) or _rate(code)
		if rate <= 0:
			frappe.throw(_("Please give the rate for {0}").format(code))
		row = {"item_code": code, "qty": qty, "rate": rate}
		desc = (it.get("description") or "").strip()
		if desc:
			row["description"] = "<br>".join(frappe.utils.escape_html(x) for x in desc.splitlines())
		rows.append(row)
	if not rows:
		frappe.throw(_("Please add at least one item"))
	if use_new("Sales", user):  # rebuild: the one Quotation writer (linear flow map, Flow 1 step 6)
		from sk_app.writers import quotation as qw

		if not frappe.has_permission("Quotation", "create"):
			frappe.throw(_("You may not make quotations"), frappe.PermissionError)
		doc = qw.write(user, customer=customer, items=rows, deal=deal, terms=note, valid_days=int(valid_days or 15))
		return {"name": doc.name, "grand_total": doc.grand_total, "pdf": crm._pdf("Quotation", doc.name), **submit_quotation(user, doc.name, quiet=True)}
	doc = frappe.get_doc({"doctype": "Quotation", "quotation_to": "Customer", "party_name": customer, "transaction_date": nowdate(),
		"valid_till": add_days(nowdate(), int(valid_days or 15)), "items": rows})
	if doc.meta.has_field("crm_deal"):
		doc.crm_deal = deal
	doc.terms = gst_terms(note)
	if not frappe.has_permission("Quotation", "create"):
		frappe.throw(_("You may not make quotations"), frappe.PermissionError)
	# ERPNext fills the GST tax accounts while saving and refuses Sales, who may not read accounts (SK 29-Oct, Aditya:
	# "User don't have permissions to select/read this account"); made by the system, kept in the person's name
	store.insert_for(doc, user)
	return {"name": doc.name, "grand_total": doc.grand_total, "pdf": crm._pdf("Quotation", doc.name), **submit_quotation(user, doc.name, quiet=True)}

def submit_quotation(user: str, quotation: str, quiet: bool = False) -> dict:
	"""SK 28-Oct mandatory gate: the quotation is submitted (sent) only when customer, items, GST and valid-till are
	all there. quiet: when it is just made, say what is missing instead of failing."""
	from sk_app import gates

	q = frappe.get_doc("Quotation", quotation)
	if q.docstatus == 1:
		return {"submitted": True, "missing": []}
	if quiet and not frappe.has_permission("Quotation", "submit", q.name):
		return {"submitted": False, "missing": [_("Sales manager to submit")]}
	q.check_permission("submit")
	current = frappe.session.user
	frappe.set_user("Administrator")  # the account check, as in make_quotation; who may submit is checked above
	try:
		q.flags.ignore_permissions = True
		# SK 23-Nov (Swati / Pranali quotes stuck in draft): the customer's GSTIN and address are often filled AFTER the
		# draft quote was made; the draft still held "Unregistered" and no address, so ERPNext refused the submit
		# ("GST Category cannot be Unregistered for party with GSTIN"). The draft re-reads them from the Customer first.
		if q.quotation_to == "Customer":
			refresh_party(q)
		if not q.get("taxes") and "gst" not in (q.terms or "").lower():
			q.terms = gst_terms(q.terms)
		q.save()
		q.submit()
	except frappe.ValidationError:
		frappe.set_user(current)
		if not quiet:
			raise
		frappe.clear_messages()
		q.reload()
		missing = gates.R.quotation_missing({"party_name": q.party_name, "valid_till": q.valid_till, "items": gates._rows(q),
			"taxes": len(q.get("taxes") or []), "total_taxes_and_charges": q.total_taxes_and_charges, "terms": q.terms})
		missing += gates.customer_missing(q.party_name) if q.quotation_to == "Customer" else []
		return {"submitted": False, "missing": [t for _k, t in missing]}
	finally:
		frappe.set_user(current)
	frappe.db.set_value("Quotation", q.name, "modified_by", user, update_modified=False)
	return {"submitted": True, "missing": []}
