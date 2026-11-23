"""SK 23-Nov (approved): bank entries.
- A warning (not a stop) when a Payment Entry / bank Journal Entry is dated far from its bank reference date.
- "Payment failed / returned": a submitted payment that bounced or came back gets a DRAFT reversing Journal Entry
  (same accounts, other side, party kept, reference and reason in the remark). Accounts checks and submits it, so the
  ERPNext flow is kept and the original entry stays as the bank shows it."""

import frappe
from frappe import _
from frappe.utils import getdate, nowdate

from sk_app import bank_rules


def warn_date_gap(doc, method=None):
	ref = doc.get("reference_date") if doc.doctype == "Payment Entry" else doc.get("cheque_date")
	if doc.doctype == "Journal Entry" and doc.get("voucher_type") not in ("Bank Entry", "Cash Entry"):
		return
	w = bank_rules.date_gap_warning(getdate(doc.posting_date) if doc.posting_date else None, getdate(ref) if ref else None)
	if w:
		frappe.msgprint(_(w), title=_("Check the dates"), indicator="orange")


@frappe.whitelist(methods=["POST"])
def payment_returned(doctype: str, name: str, reason: str | None = None) -> dict:
	if doctype not in ("Payment Entry", "Journal Entry"):
		frappe.throw(_("Only a payment or bank entry can be reversed here"))
	src = frappe.get_doc(doctype, name)
	src.check_permission("read")
	if not frappe.has_permission("Journal Entry", "create"):
		frappe.throw(_("You may not make journal entries"), frappe.PermissionError)
	if src.docstatus != 1:
		frappe.throw(_("{0} is not submitted").format(name))
	why = (reason or "").strip() or _("payment failed / returned")
	have = frappe.db.get_value("Journal Entry", {"docstatus": ["<", 2], "user_remark": ["like", f"%Reverses {name}:%"]})
	if have:
		return {"name": have, "existing": True}
	if doctype == "Journal Entry":
		from erpnext.accounts.doctype.journal_entry.journal_entry import make_reverse_journal_entry

		je = make_reverse_journal_entry(name)
		ref_no = src.get("cheque_no")
	else:
		je = frappe.new_doc("Journal Entry")
		je.update({"voucher_type": "Bank Entry", "company": src.company})
		rows = bank_rules.reversal_rows(src.payment_type, src.paid_from, src.paid_to, src.paid_amount, src.received_amount,
			src.party_type, src.party)
		for r in rows:
			je.append("accounts", {k: v for k, v in r.items() if v not in (None, "")})
		ref_no = src.get("reference_no")
	je.posting_date = nowdate()
	je.cheque_no = f"RETURN {ref_no or name}"[:140]  # its own reference: the reversal is not a double of the payment
	je.cheque_date = nowdate()
	je.user_remark = f"Reverses {name}: {why}"
	je.flags.ignore_permissions = True
	from sk_app.store_screens import as_system

	with as_system():  # ERPNext fills accounts; who may do it was checked above
		je.insert()
	frappe.db.set_value("Journal Entry", je.name, "owner", frappe.session.user, update_modified=False)
	src.add_comment("Comment", _("Payment failed / returned ({0}): draft reversal {1} made by {2}").format(why, je.name, frappe.session.user))
	return {"name": je.name, "existing": False}
