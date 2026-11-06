"""Link every payment to the bill(s) it pays (Flow 6 Money; SK 6-Nov KF-04447: "how do you know which bill we pay").
Two doors, one rule (payment_allocate_rules.allocate):
- nightly link_unallocated(): every submitted Payment Entry with money not yet against a bill is matched to the party's
  open invoices through ERPNext's own Payment Reconciliation; what cannot be decided is listed for Accounts in one ToDo.
- on a Sales / Purchase Invoice save (New path of Finance): the party's unallocated payments are pulled in as advances,
  oldest first (ERPNext set_advances), so a bill made after its advance is settled at once.
Also used by the bank statement screen for a line that is in the bank but not yet booked (same rule, so the same answer)."""

import frappe
from frappe import _
from frappe.utils import flt, fmt_money, nowdate

from sk_app.writers.payment_allocate_rules import allocate

INVOICE = {"Customer": "Sales Invoice", "Supplier": "Purchase Invoice"}
PARTY_FIELD = {"Customer": "customer", "Supplier": "supplier"}


def open_invoices(party_type: str, party: str, company: str) -> list[dict]:
	dt = INVOICE[party_type]
	fields = ["name", "outstanding_amount as outstanding", "posting_date as date"]
	if dt == "Purchase Invoice":
		fields.append("bill_no")
	return frappe.get_all(dt, filters={PARTY_FIELD[party_type]: party, "company": company, "docstatus": 1, "outstanding_amount": [">", 0.5]},
		fields=fields, order_by="posting_date asc")


def _reconcile(pe, rows: list[dict]) -> bool:
	"""ERPNext's Payment Reconciliation: the payment's unallocated money is set against the chosen invoices."""
	pr = frappe.get_doc({"doctype": "Payment Reconciliation", "company": pe.company, "party_type": pe.party_type, "party": pe.party,
		"receivable_payable_account": pe.paid_from if pe.party_type == "Customer" else pe.paid_to})
	pr.get_unreconciled_entries()
	pay = next((p for p in pr.payments if p.reference_name == pe.name), None)
	if not pay:
		return False
	wanted = {r["name"]: r["amount"] for r in rows}
	pr.allocation = []
	for inv in pr.invoices:
		if inv.invoice_number in wanted:
			pr.append("allocation", {"reference_type": pay.reference_type, "reference_name": pay.reference_name, "reference_row": pay.reference_row,
				"invoice_type": inv.invoice_type, "invoice_number": inv.invoice_number, "allocated_amount": min(wanted[inv.invoice_number], flt(pay.amount)),
				"unreconciled_amount": inv.outstanding_amount, "amount": pay.amount, "is_advance": pay.is_advance,
				"difference_amount": 0, "currency": inv.currency})
	if not pr.allocation:
		return False
	pr.reconcile()
	return True


def link_unallocated(limit: int = 200) -> dict:
	"""Nightly (New path of Finance): every submitted payment with unallocated money → its bill(s), else to Accounts."""
	from sk_app.core.switch import use_new

	if not use_new("Finance"):
		return {"skipped": "Finance on Old path"}
	out = {"linked": 0, "open": []}
	for row in frappe.get_all("Payment Entry", filters={"docstatus": 1, "unallocated_amount": [">", 0.5], "party_type": ["in", list(INVOICE)]},
			fields=["name", "party_type", "party", "unallocated_amount", "remarks", "reference_no", "company"], order_by="posting_date asc", limit=limit):
		invoices = open_invoices(row.party_type, row.party, row.company)
		rows, why = allocate(flt(row.unallocated_amount), invoices, f"{row.remarks or ''} {row.reference_no or ''}")
		if rows:
			try:
				pe = frappe.get_doc("Payment Entry", row.name)
				if _reconcile(pe, rows):
					out["linked"] += 1
					pe.add_comment("Comment", _("Linked by SK App to {0} ({1})").format(", ".join(r["name"] for r in rows), _(why)))
					frappe.db.commit()
					continue
			except Exception:
				frappe.db.rollback()
				frappe.log_error(title=f"SK App payment link {row.name}")
				why = "could not reconcile"
		out["open"].append({"payment": row.name, "party": row.party, "amount": flt(row.unallocated_amount), "why": why,
			"invoices": [i["name"] for i in invoices]})
	if out["open"]:
		_tell_accounts(out["open"])
	return out


def _tell_accounts(items: list[dict]):
	from sk_app.core.people import users_with_function

	lines = [f"{i['payment']} {i['party']} {fmt_money(i['amount'], currency='INR')}: {_(i['why'])}" +
		(f" (open: {', '.join(i['invoices'][:4])})" if i["invoices"] else "") for i in items[:30]]
	text = _("{0} payments are not against any bill. Please pick the bill in Payment Reconciliation:").format(len(items)) + "<br>" + "<br>".join(lines)
	for u in users_with_function("Accounts") or users_with_function("Management"):
		if not frappe.db.exists("ToDo", {"allocated_to": u, "status": "Open", "description": ["like", "%payments are not against any bill%"],
				"date": nowdate()}):
			frappe.get_doc({"doctype": "ToDo", "allocated_to": u, "description": text, "priority": "Medium", "date": nowdate(),
				"reference_type": "Payment Reconciliation"}).insert(ignore_permissions=True)


def pull_advances(doc, method=None):
	"""Sales / Purchase Invoice validate (New path of Finance): the party's unallocated payments become this bill's advances."""
	from sk_app.core.switch import use_new

	if doc.docstatus != 0 or frappe.flags.in_import or doc.get("is_return") or doc.get("advances"):
		return
	if not use_new("Finance", doc.owner or frappe.session.user):
		return
	party_type = "Customer" if doc.doctype == "Sales Invoice" else "Supplier"
	party = doc.get(PARTY_FIELD[party_type])
	if not party or not frappe.db.exists("Payment Entry", {"docstatus": 1, "party_type": party_type, "party": party, "unallocated_amount": [">", 0.5]}):
		return
	try:
		doc.set_advances()
		if doc.get("advances"):
			doc.flags.sk_advances = len(doc.advances)
	except Exception:
		frappe.log_error(title=f"SK App advances {doc.doctype}")
