"""Foolproof account masters (SK 4-Nov-2026, "how to make it foolproof").

Cause found on 4-Nov: the "Net Banking" mode of payment was made with type Cash and its default account Cash, so five
bank payments (Neo Curtains Rs 15,600 and Rs 3,900, Technomech, Ai Portable) went to Cash and never showed in Bank
Reconciliation. So:
(a) Mode of Payment, Accounts Settings, Company and Bank / Cash ledgers are created or changed only by the CEO or a
    System Manager (other accounts ledgers stay open to Accounts).
(b) A mode of payment is checked on save: a Bank mode needs Bank accounts, a Cash mode Cash accounts, and every company
    that has such an account needs its row.
(c) audit() lists what is wrong in the masters today (for SK, with links).
(d) changed_since() lists the masters changed since yesterday, for the morning list (sk_app.doubles.morning).
"""

import frappe
from frappe import _
from frappe.utils import add_days, get_url_to_form, nowdate

GUARDED = ("Mode of Payment", "Accounts Settings", "Company", "Bank Account")
WATCHED = ("Mode of Payment", "Account", "Accounts Settings", "Company", "Bank Account")
MONEY_TYPES = ("Bank", "Cash")


def _skip() -> bool:
	f = frappe.flags
	return bool(f.in_install or f.in_migrate or f.in_patch or f.in_setup_wizard or f.sk_no_master_guard)


def can_edit(user: str | None = None) -> bool:
	user = user or frappe.session.user
	if user == "Administrator" or "System Manager" in frappe.get_roles(user):
		return True
	from sk_app.requisition import _ceos

	return user in _ceos()


def guard(doc, method=None):
	"""validate of Mode of Payment, Accounts Settings, Company, Bank Account and Account."""
	if _skip() or can_edit():
		return
	if doc.doctype == "Account":
		before = doc.get_doc_before_save()
		old_type = before.account_type if before else None
		# Accounts may still make expense / income / party ledgers; Bank and Cash ledgers decide where money is booked
		if doc.account_type not in MONEY_TYPES and old_type not in MONEY_TYPES:
			return
	frappe.throw(_("{0} decides where money is booked, so only the CEO or a System Manager can create or change it. "
		"Please send the change to SK.").format(_(doc.doctype)), frappe.PermissionError, title=_("Not allowed"))


def mode_problems(doc) -> list[str]:
	"""What is wrong in one Mode of Payment (doc or dict-like with type and accounts rows)."""
	out = []
	kind = doc.get("type")
	have = {}
	for row in doc.get("accounts") or []:
		if not row.get("company"):
			continue
		have[row.get("company")] = row.get("default_account")
		acc = row.get("default_account")
		if not acc:
			out.append(_("{0}: no default account").format(row.get("company")))
			continue
		acc_type = frappe.db.get_value("Account", acc, "account_type")
		if kind in MONEY_TYPES and acc_type != kind:
			out.append(_("{0}: {1} is a {2} account, but this is a {3} mode").format(row.get("company"), acc, acc_type or "—", kind))
	if kind in MONEY_TYPES:
		for company in frappe.get_all("Company", pluck="name"):
			if company in have:
				continue
			if frappe.db.exists("Account", {"company": company, "account_type": kind, "is_group": 0, "disabled": 0}):
				out.append(_("{0}: no row (add its {1} account)").format(company, kind))
	return out


def check_mode(doc, method=None):
	"""validate of Mode of Payment (b)."""
	if _skip():
		return
	problems = mode_problems(doc)
	if problems:
		frappe.throw(_("Mode of payment {0} ({1}) cannot be saved:").format(doc.name or doc.mode_of_payment, doc.type) + "<br>• "
			+ "<br>• ".join(problems), title=_("Wrong account"))


def audit() -> list[dict]:
	"""(c) Everything wrong in the money masters today, and payments already booked through the wrong account.
	Each row: what, problem, link."""
	return audit_masters_only() + _payments_in_cash()


def audit_masters_only() -> list[dict]:
	"""Modes of payment, company defaults and bank ledgers set up wrong."""
	rows = []
	for name in frappe.get_all("Mode of Payment", filters={"enabled": 1}, pluck="name"):
		for p in mode_problems(frappe.get_doc("Mode of Payment", name)):
			rows.append({"what": f"Mode of Payment {name}", "problem": p, "link": get_url_to_form("Mode of Payment", name)})
	for c in frappe.get_all("Company", fields=["name", "default_bank_account"]):
		banks = frappe.get_all("Account", filters={"company": c.name, "account_type": "Bank", "is_group": 0, "disabled": 0}, pluck="name")
		if not banks:
			rows.append({"what": f"Company {c.name}", "problem": _("no bank ledger at all"), "link": get_url_to_form("Company", c.name)})
		elif not c.default_bank_account:
			rows.append({"what": f"Company {c.name}", "problem": _("no Default Bank Account"), "link": get_url_to_form("Company", c.name)})
		for acc in banks:
			if frappe.db.exists("DocType", "Bank Account") and not frappe.db.exists("Bank Account", {"account": acc}):
				rows.append({"what": f"Ledger {acc}", "problem": _("no Bank Account record, so Bank Reconciliation Tool cannot use it"),
					"link": get_url_to_form("Account", acc)})
	return rows


def _payments_in_cash() -> list[dict]:
	rows = []
	from sk_app.doubles import _bank_in_cash
	from erpnext.accounts.utils import get_fiscal_year

	for r in _bank_in_cash(get_fiscal_year(nowdate())[1]):
		rows.append({"what": f"Payment {r.name} ({r.party}, ₹{r.amount:,.0f}, {r.date})",
			"problem": _("bank payment ({0}) booked through Cash: missing in Bank Reconciliation").format(r.mode_of_payment or r.reference_no),
			"link": get_url_to_form("Payment Entry", r.name)})
	return rows


def changed_since(since=None) -> list[dict]:
	"""(d) Money masters created or changed since yesterday morning, with who did it."""
	since = since or add_days(nowdate(), -1)
	out = []
	for dt in WATCHED:
		if not frappe.db.exists("DocType", dt):
			continue
		if frappe.get_meta(dt).issingle:
			row = frappe.db.get_value(dt, dt, ["modified", "modified_by"], as_dict=True)
			if row and row.modified and str(row.modified)[:10] >= str(since):
				out.append({"doctype": dt, "name": dt, "modified": row.modified, "by": row.modified_by})
			continue
		for r in frappe.get_all(dt, filters={"modified": [">=", since]}, fields=["name", "modified", "modified_by"], limit=50):
			out.append({"doctype": dt, "name": r.name, "modified": r.modified, "by": r.modified_by})
	return out
