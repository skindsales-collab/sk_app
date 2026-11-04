"""The one Payment Entry writer (linear flow map, Flow 6 Money). Money in (against a Sales Invoice or a Sales Order
advance) and money out (against a Purchase Invoice) are made the same way: ERPNext's own mapping from the document
paid, the mode from the Mode of Payment master, the photo attached, then submitted. Used on the New path of Finance.
Same inputs and outputs for the user (SK 4-Nov)."""

import frappe
from frappe import _
from frappe.utils import flt

from sk_app.core.rules import report
from sk_app.writers.payment_rules import direction, problems


def write(user: str, against_doctype: str, against_name: str, amount, mode=None, reference_no=None, reference_date=None,
		photo=None, fill=None, attach=None, try_submit=None) -> tuple:
	"""Returns (payment entry, posted). fill / attach / try_submit are finance's own helpers, passed in so the
	writer has one path and finance keeps its tested mode and bank rules."""
	from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

	if not direction(against_doctype):
		frappe.throw(_("Unknown document"))
	amount = flt(amount)
	pe = get_payment_entry(against_doctype, against_name, party_amount=amount)
	fill(pe, mode, reference_no, reference_date)
	pe.insert()  # on_validate checks it, as for a payment made in ERPNext or by Claude
	attach(photo, "Payment Entry", pe.name, user)
	return pe, try_submit(pe)


def on_validate(doc, method=None):
	"""Every Payment Entry, from the app, ERPNext or SK Hub (SK 4-Nov), on the New path of Finance: linked back to what
	it pays, amount not above what is due, a bank payment with its UTR."""
	from sk_app.core.switch import use_new

	if doc.docstatus == 1 or doc.payment_type not in ("Receive", "Pay") or doc.party_type not in ("Customer", "Supplier"):
		return
	if not use_new("Finance", doc.owner or frappe.session.user):
		return
	refs = [r for r in doc.get("references") or [] if direction(r.reference_doctype)]
	ref = refs[0] if refs else None
	due = sum(flt(r.outstanding_amount) for r in refs) if refs else None
	mode_type = frappe.db.get_value("Mode of Payment", doc.mode_of_payment, "type") if doc.get("mode_of_payment") else None
	found = problems(ref.reference_doctype if ref else "", ref.reference_name if ref else None, flt(doc.paid_amount),
		due if due else None, mode_type, doc.get("reference_no"))
	report("Finance", doc, found, title=_("Payment data missing"))
