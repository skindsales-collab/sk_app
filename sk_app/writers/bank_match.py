"""Bank match on the record (Flow 6 Money, New path of Finance). When a payment is submitted and its bank line is
already in ERPNext (from the statement upload), the two are reconciled at once with ERPNext's own tool; the statement
upload (sk_app.bank_statement) does the same from the other side for lines that come later. One matching rule for both
sides: sk_app.statement_rules.pick_match (same UTR, else the only same-amount line near the date, else the party name)."""

import frappe
from frappe.utils import add_days

from sk_app import statement_rules as SR

DAYS = 5


def candidates(ledger: str, payment_type: str, amount: float, posting_date) -> list[dict]:
	"""Unreconciled bank lines of this ledger's bank account, same side and amount, within 5 days."""
	accounts = frappe.get_all("Bank Account", filters={"account": ledger, "is_company_account": 1}, pluck="name")
	if not accounts:
		return []
	side = "withdrawal" if payment_type == "Pay" else "deposit"
	out = []
	for bt in frappe.get_all("Bank Transaction", filters={"docstatus": 1, "bank_account": ["in", accounts], "status": ["!=", "Reconciled"],
			side: ["between", [amount - 0.5, amount + 0.5]], "date": ["between", [add_days(posting_date, -DAYS), add_days(posting_date, DAYS)]]},
			fields=["name", "reference_number", "description", "date"]):
		out.append({"name": bt.name, "reference_no": bt.reference_number, "party": SR.party_hint(bt.description or ""), "date": bt.date})
	return out


def on_submit(doc, method=None):
	"""Payment Entry on_submit: reconcile with its bank line when that line is already in ERPNext."""
	from sk_app.core.switch import use_new

	if doc.payment_type not in ("Pay", "Receive") or not use_new("Finance", doc.owner or frappe.session.user):
		return
	ledger = doc.paid_from if doc.payment_type == "Pay" else doc.paid_to
	if frappe.get_cached_value("Account", ledger, "account_type") != "Bank":
		return
	amount = doc.paid_amount if doc.payment_type == "Pay" else doc.received_amount
	row = {"reference_number": doc.reference_no, "party_hint": doc.party_name}
	bt, why = SR.pick_match(row, candidates(ledger, doc.payment_type, amount, doc.posting_date))
	if not bt:
		return
	try:
		from sk_app.bank_statement import _reconcile

		_reconcile(bt["name"], {"doctype": "Payment Entry", "name": doc.name}, amount)
		doc.add_comment("Comment", frappe._("Matched with bank line {0} ({1})").format(bt["name"], why))
	except Exception:
		frappe.log_error("SK App bank match on submit")
