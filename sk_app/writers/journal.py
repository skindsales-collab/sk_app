"""The one Journal Entry writer (linear flow map, Flow 6 Money). A petty cash voucher, an expense claim payment and a
bank charge are all made the same way: two balanced lines, the voucher type from the ledger's own type, a reference
for a bank entry, the photo attached, then submitted. Used on the New path of Finance; the rules also run on every
Journal Entry saved in ERPNext or through SK Hub (SK 4-Nov: same checks from any door)."""

import frappe
from frappe import _
from frappe.utils import flt, nowdate

from sk_app.core.rules import report
from sk_app.writers.journal_rules import problems, rows, voucher_type


def write(user: str, expense_account: str, money_account: str, amount, *, cost_center=None, narration=None, photo=None,
		attach=None, try_submit=None) -> tuple:
	"""Returns (journal entry, posted). attach / try_submit are finance's own helpers (one tested place for posting)."""
	from sk_app.store import _company

	amount = flt(amount)
	je = frappe.new_doc("Journal Entry")
	je.company = _company()
	je.posting_date = nowdate()
	je.voucher_type = voucher_type(frappe.db.get_value("Account", money_account, "account_type"))
	je.user_remark = (narration or "").strip()
	if je.voucher_type == "Bank Entry":
		# one reference per voucher (the same text on every voucher of a day looked like a double)
		je.cheque_no, je.cheque_date = _("SK App {0}").format(frappe.generate_hash(length=8).upper()), nowdate()
	for r in rows(expense_account, money_account, amount, cost_center):
		je.append("accounts", r)
	je.flags.ignore_permissions = True
	je.insert()  # on_validate checks it, as for a journal made in ERPNext or by Claude
	if attach:
		attach(photo, "Journal Entry", je.name, user)
	return je, (try_submit(je) if try_submit else False)


def on_validate(doc, method=None):
	"""Every Journal Entry on the New path of Finance: says what it is for, balances, a bank entry has its reference."""
	from sk_app.core.switch import use_new

	if doc.docstatus == 1 or not use_new("Finance", doc.owner or frappe.session.user):
		return
	accounts = [a.account for a in doc.get("accounts") or [] if a.account]
	has_bank = any(frappe.get_cached_value("Account", a, "account_type") == "Bank" for a in accounts)
	found = problems(flt(doc.total_debit), flt(doc.total_credit), doc.get("user_remark"), has_bank, doc.get("cheque_no"))
	report("Finance", doc, found, title=_("Journal data missing"))


# ---------- Plan A (SK 9-Nov): moved here unchanged from finance.py ----------
from frappe import _
from frappe.utils import flt, nowdate
from sk_app.core.switch import use_new
from sk_app.finance import ACCOUNTS, cash_account
from sk_app.store import _company, attach, draft_reason, need, try_submit
import frappe


def petty_cash(user: str, expense_account: str, amount, cash_account: str, cost_center=None, narration=None, photo=None) -> dict:
	"""Petty cash / expense voucher: photo of the voucher + spoken narration -> Journal Entry."""
	need(user, ACCOUNTS)
	amount = flt(amount)
	if amount <= 0:
		frappe.throw(_("Please give the amount"))
	if not (narration or "").strip():
		frappe.throw(_("Please say what the money was spent on"))
	if use_new("Finance", user):  # rebuild: the one Journal Entry writer (linear flow map, Flow 6)
		from sk_app.writers import journal as jw

		je, posted = jw.write(user, expense_account, cash_account, amount, cost_center=cost_center, narration=narration, photo=photo,
			attach=attach, try_submit=try_submit)
		return {"name": je.name, "posted": posted, "reason": draft_reason()}
	je = frappe.new_doc("Journal Entry")
	je.voucher_type = "Cash Entry" if frappe.db.get_value("Account", cash_account, "account_type") == "Cash" else "Bank Entry"
	je.company = _company()
	je.posting_date = nowdate()
	je.user_remark = narration
	if je.voucher_type == "Bank Entry":
		# one reference per voucher (the same text on every voucher of a day looked like a double)
		je.cheque_no, je.cheque_date = _("SK App {0}").format(frappe.generate_hash(length=8).upper()), nowdate()
	je.append("accounts", {"account": expense_account, "debit_in_account_currency": amount, "cost_center": cost_center})
	je.append("accounts", {"account": cash_account, "credit_in_account_currency": amount, "cost_center": cost_center})
	je.flags.ignore_permissions = True
	je.insert()
	attach(photo, "Journal Entry", je.name, user)
	posted = try_submit(je)
	return {"name": je.name, "posted": posted, "reason": draft_reason()}
