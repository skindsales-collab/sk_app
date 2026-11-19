"""Finance screens (SK, 26-Oct-2026 draft F06): Cash Today, To Collect, To Pay (SK approves above the limit), Bills to
Post, Invoices from dispatch, Expenses and petty cash, Segment P&L by cost centre and the Month Close checklist.

Money records are made with ERPNext's own mapping (Payment Entry from the invoice, Sales Invoice from the Delivery
Note, Purchase Invoice from the PO), so accounts, taxes and references are filled the ERPNext way. Posting goes through
try_submit: when ERPNext refuses (for example no bank account set yet) the record stays a draft with the reason.
"""

import frappe
from frappe import _
from frappe.utils import add_days, cint, date_diff, flt, fmt_money, get_first_day, getdate, nowdate

from sk_app.purchase import po_limit
from sk_app.store import _company, _todo, _users_with_function, attach, material_pos, draft_reason, need, try_submit
from sk_app.core.switch import use_new
from sk_app.store import _company, need


ACCOUNTS = "Accounts"

MANAGEMENT = "Management"

APPROVED = "Approved for payment in SK App"

# SK's month-end rules (F06): stock closing 2nd, P&L 7th, MAR 10th; GST returns by their due dates
MONTH_CLOSE = [("stock_close", 2), ("pnl", 7), ("mar", 10), ("gstr1", 11), ("gstr3b", 20)]

def _money(v) -> str:
	return fmt_money(flt(v), currency=frappe.db.get_value("Company", _company(), "default_currency") or "INR")

PROMISE_DATE, PROMISE_NOTE = "sk_promise_date", "sk_promise_note"

def ensure_fields():
	"""SK 4-Nov rebuild (F3): the customer's payment promise is kept on the invoice itself (before it was found by searching
	comments for the word 'Promise', which missed a promise saved in Marathi)."""
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	create_custom_fields({"Sales Invoice": [
		{"fieldname": PROMISE_DATE, "label": "Payment promised on", "fieldtype": "Date", "insert_after": "due_date",
			"allow_on_submit": 1, "no_copy": 1},
		{"fieldname": PROMISE_NOTE, "label": "What the customer promised", "fieldtype": "Small Text", "insert_after": PROMISE_DATE,
			"allow_on_submit": 1, "no_copy": 1}]}, update=True)

def _promise(r) -> str | None:
	if r.get(PROMISE_DATE) or r.get(PROMISE_NOTE):
		return f"{r.get(PROMISE_DATE) or '-'}: {r.get(PROMISE_NOTE) or ''}".strip()
	return frappe.db.get_value("Comment", {"reference_doctype": "Sales Invoice", "reference_name": r.name,
		"comment_type": "Comment", "content": ["like", "%Promise%"]}, "content", order_by="creation desc")  # before 4-Nov

def _bucket(days_late: int) -> str:
	return "not_due" if days_late <= 0 else "d0_30" if days_late <= 30 else "d31_60" if days_late <= 60 else "d60_plus"

def bank_account(company: str, mode: str | None = None) -> str | None:
	"""SK 4-Nov: all payments go through net banking, none in cash. The mode's own Bank account, else the company's default
	bank account, else the bank ledger used most."""
	if mode:
		acc = frappe.db.get_value("Mode of Payment Account", {"parent": mode, "company": company}, "default_account")
		if acc and frappe.db.get_value("Account", acc, "account_type") == "Bank":
			return acc
	acc = frappe.get_cached_value("Company", company, "default_bank_account")
	if acc:
		return acc
	used = frappe.db.sql("""select acc.name from `tabAccount` acc left join `tabGL Entry` gl on gl.account = acc.name and gl.is_cancelled = 0
		where acc.company = %s and acc.account_type = 'Bank' and acc.is_group = 0 and acc.disabled = 0
		group by acc.name order by count(gl.name) desc, acc.name limit 1""", company)
	return used[0][0] if used else None

def payment_modes(user: str) -> list[str]:
	need(user, ACCOUNTS, MANAGEMENT)
	modes = frappe.get_all("Mode of Payment", filters={"enabled": 1}, pluck="name", order_by="name asc")
	first = [m for m in ("Net Banking", "Cash") if m in modes]
	return first + [m for m in modes if m not in first]

def cash_account(company: str, mode: str | None = None) -> str | None:
	acc = frappe.db.get_value("Mode of Payment Account", {"parent": mode, "company": company}, "default_account") if mode else None
	if acc and frappe.db.get_value("Account", acc, "account_type") == "Cash":
		return acc
	return frappe.get_cached_value("Company", company, "default_cash_account")

def _fill_payment(pe, mode, reference_no, reference_date):
	# SK 4-Nov: payments are net banking with their UTR (unique: sk_app.doubles stops a second entry of the same UTR);
	# a cash payment (some cabins) goes to the Cash account with its reason typed in the same box
	# SK 4-Nov rebuild (F1): blank = Net Banking (SK's rule), but a mode ERPNext does not know is refused, never swapped quietly
	if mode and not frappe.db.get_value("Mode of Payment", {"name": mode, "enabled": 1}):
		valid = frappe.get_all("Mode of Payment", filters={"enabled": 1}, pluck="name", order_by="name asc")
		frappe.throw(_("Payment mode {0} is not in ERPNext. Please pick one of: {1}").format(mode, ", ".join(valid)), title=_("Wrong payment mode"))
	mode = mode or "Net Banking"
	if frappe.db.exists("Mode of Payment", mode):
		pe.mode_of_payment = mode
	text = (reference_no or "").strip()
	is_cash = frappe.db.get_value("Mode of Payment", mode, "type") == "Cash"
	if not text:
		frappe.throw(_("Please write why it was paid in cash") if is_cash else _("Please type the UTR / bank reference number of this payment"),
			title=_("Data missing"))
	acc = cash_account(pe.company, mode) if is_cash else bank_account(pe.company, pe.mode_of_payment)
	if acc:
		if pe.payment_type == "Pay":
			pe.paid_from = acc
		else:
			pe.paid_to = acc
	if is_cash:
		pe.sk_cash_reason = text
		text = _("Cash {0}").format(nowdate())
	pe.reference_no = text
	pe.reference_date = getdate(reference_date or nowdate())
	pe.flags.ignore_permissions = True

def _approved(pi: str) -> bool:
	return bool(frappe.db.exists("Comment", {"reference_doctype": "Purchase Invoice", "reference_name": pi, "content": APPROVED}))

def _functions(user: str) -> list[str]:
	from sk_app import logins

	return logins.profile_functions(user) + (["Management"] if "System Manager" in frappe.get_roles(user) else [])

# kind -> (label, where Accounts finishes it in ERPNext). Money in / out stays a manual ERPNext entry (SK 27-Oct rule).
PHOTO_KINDS = {
	"supplier_bill": ("Supplier bill / e-invoice", None),
	"expense": ("Expense bill / petty cash voucher", "/app/journal-entry/new?voucher_type=Cash%20Entry"),
	# SK 4-Nov: payments are net banking: the ERPNext form opens with Net Banking (its bank account comes with it)
	"money_in": ("Payment received (cheque / UTR)", "/app/payment-entry/new?payment_type=Receive&mode_of_payment=Net%20Banking"),
	"money_out": ("Payment made (bank slip / UTR)", "/app/payment-entry/new?payment_type=Pay&mode_of_payment=Net%20Banking"),
	"other": ("Other document", None),
}

PHOTO_TAG = "Photo entry"

def _close_key(month_start, key: str) -> str:
	return f"SK Month Close {str(month_start)[:7]}: {key}"
