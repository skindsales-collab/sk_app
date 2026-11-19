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


# ---------- Plan A (SK 9-Nov): moved here unchanged from finance.py ----------
from frappe import _
from frappe.utils import flt, getdate
from sk_app.core.switch import use_new
from sk_app.finance import ACCOUNTS, APPROVED, MANAGEMENT, PROMISE_DATE, PROMISE_NOTE, _approved, _fill_payment, _functions, _money
from sk_app.purchase import po_limit
from sk_app.store import _todo, _users_with_function, attach, draft_reason, need, try_submit
import frappe


def promise(user: str, sales_invoice: str, text: str, promised_on=None) -> dict:
	"""After the call: what the customer said (spoken) and the promised date; a reminder for that day."""
	need(user, ACCOUNTS, MANAGEMENT, "Sales")
	if not (text or "").strip() and not promised_on:
		frappe.throw(_("Please say what the customer promised"))
	si = frappe.get_doc("Sales Invoice", sales_invoice)
	note = _("Promise {0}: {1}").format(promised_on or "-", text or "")
	si.add_comment("Comment", note)
	if frappe.get_meta("Sales Invoice").has_field(PROMISE_DATE):
		frappe.db.set_value("Sales Invoice", si.name, {PROMISE_DATE: getdate(promised_on) if promised_on else None,
			PROMISE_NOTE: (text or "").strip()[:500]})
	if promised_on:
		frappe.get_doc({"doctype": "ToDo", "allocated_to": user, "reference_type": "Sales Invoice", "reference_name": si.name,
			"description": _("Payment promised today by {0}: {1}").format(si.customer_name, _money(si.outstanding_amount)),
			"date": getdate(promised_on), "priority": "High"}).insert(ignore_permissions=True)
	return {"ok": True}

def receive_payment(user: str, reference_doctype: str, reference_name: str, amount, mode=None, reference_no=None,
		reference_date=None, photo=None) -> dict:
	"""Money received against an invoice (or an advance against a Sales Order), from the payment screenshot."""
	need(user, ACCOUNTS, MANAGEMENT)
	if reference_doctype not in ("Sales Invoice", "Sales Order"):
		frappe.throw(_("Unknown document"))
	amount = flt(amount)
	if amount <= 0:
		frappe.throw(_("Please give the amount received"))
	if use_new("Finance", user):  # rebuild: the one Payment Entry writer (linear flow map, Flow 6)
		from sk_app.writers import payment as pw

		pe, posted = pw.write(user, reference_doctype, reference_name, amount, mode, reference_no, reference_date, photo,
			fill=_fill_payment, attach=attach, try_submit=try_submit)
	else:
		from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

		pe = get_payment_entry(reference_doctype, reference_name, party_amount=amount)
		_fill_payment(pe, mode, reference_no, reference_date)
		pe.insert()
		attach(photo, "Payment Entry", pe.name, user)
		posted = try_submit(pe)
	reason = draft_reason()
	# the salesperson of the order hears that the money came (F06 link Finance -> Sales)
	owner = frappe.db.get_value(reference_doctype, reference_name, "owner")
	if owner and owner != user and owner in _users_with_function("Sales"):
		_todo(owner, reference_doctype, reference_name, _("Payment received: {0} from {1}").format(_money(amount), pe.party_name))
	return {"name": pe.name, "posted": posted, "reason": reason}

def approve_payment(user: str, purchase_invoice: str) -> dict:
	need(user, MANAGEMENT)
	frappe.get_doc("Purchase Invoice", purchase_invoice).add_comment("Comment", APPROVED)
	frappe.db.set_value("ToDo", {"reference_type": "Purchase Invoice", "reference_name": purchase_invoice, "status": "Open",
		"allocated_to": user}, "status", "Closed")
	for a in _users_with_function(ACCOUNTS):
		_todo(a, "Purchase Invoice", purchase_invoice, _("SK approved, please pay {0}").format(purchase_invoice))
	return {"ok": True}

def ask_approval(user: str, purchase_invoice: str) -> dict:
	need(user, ACCOUNTS)
	pi = frappe.db.get_value("Purchase Invoice", purchase_invoice, ["supplier_name", "outstanding_amount"], as_dict=True)
	for a in _users_with_function(MANAGEMENT):
		_todo(a, "Purchase Invoice", purchase_invoice, _("OK to pay {0}: {1}?").format(pi.supplier_name, _money(pi.outstanding_amount)))
	return {"ok": True}

def pay(user: str, purchase_invoice: str, amount=None, mode=None, reference_no=None, reference_date=None, photo=None) -> dict:
	"""Payment made (from the bank transfer screenshot). Above the limit only after SK's OK."""
	need(user, ACCOUNTS, MANAGEMENT)
	pi = frappe.get_doc("Purchase Invoice", purchase_invoice)
	amount = flt(amount) or flt(pi.outstanding_amount)
	is_boss = MANAGEMENT in _functions(user)
	if amount > po_limit() and not is_boss and not _approved(pi.name):
		frappe.throw(_("Above {0}: waiting for SK's OK").format(_money(po_limit())))
	if use_new("Finance", user):  # rebuild: the one Payment Entry writer (linear flow map, Flow 6)
		from sk_app.writers import payment as pw

		pe, posted = pw.write(user, "Purchase Invoice", pi.name, amount, mode, reference_no, reference_date, photo,
			fill=_fill_payment, attach=attach, try_submit=try_submit)
	else:
		from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

		pe = get_payment_entry("Purchase Invoice", pi.name, party_amount=amount)
		_fill_payment(pe, mode, reference_no, reference_date)
		pe.insert()
		attach(photo, "Payment Entry", pe.name, user)
		posted = try_submit(pe)
	frappe.db.set_value("ToDo", {"reference_type": "Purchase Invoice", "reference_name": pi.name, "status": "Open"}, "status", "Closed")
	return {"name": pe.name, "posted": posted, "reason": draft_reason()}
