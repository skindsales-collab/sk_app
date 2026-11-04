"""Bank statement into ERPNext from the SK App (SK 4-Nov-2026: "why put the UTR by hand, can it be filled from the
statement"; picked: ERPNext import now, app upload next).

Accounts uploads the SBI statement PDF. Every line becomes an ERPNext Bank Transaction (once: a second upload of the same
statement adds nothing), and is reconciled at once with its payment in ERPNext (same UTR, else same amount within 5 days,
else the party name the bank shows), with ERPNext's own Bank Reconciliation. A payment without a UTR gets the bank's UTR
and date. The result lists:
- bank lines with no payment in ERPNext (make them in the Bank Reconciliation Tool: Create Voucher fills UTR and date),
- payments in ERPNext that are not in the bank (a double, or booked to the wrong account, e.g. ACC-PAY-2026-00203).
"""

import io
import json

import frappe
from frappe import _
from frappe.utils import add_days, get_url_to_form, getdate

from sk_app import double_rules as DR
from sk_app import statement_rules as SR
from sk_app.store import _company, need, try_submit

ACCOUNTS, MANAGEMENT = "Accounts", "Management"
DAYS = 5


def _pdf_text(file_url: str) -> str:
	fid = frappe.db.get_value("File", {"file_url": file_url}, "name")
	if not fid:
		frappe.throw(_("Statement file not found"))
	content = frappe.get_doc("File", fid).get_content()
	if isinstance(content, str):
		content = content.encode()
	if not content[:5] == b"%PDF-":
		frappe.throw(_("Please upload the statement as the PDF downloaded from SBI"))
	from pypdf import PdfReader

	reader = PdfReader(io.BytesIO(content))
	if reader.is_encrypted:
		try:
			reader.decrypt("")
		except Exception:
			frappe.throw(_("This statement PDF has a password. Please download it again without a password."))
	return "\n".join(p.extract_text(extraction_mode="layout") or "" for p in reader.pages)


def default_bank_account(company: str) -> str | None:
	return frappe.db.get_value("Bank Account", {"company": company, "is_company_account": 1, "disabled": 0},
		"name", order_by="is_default desc, creation asc")


def _bank_line(ba: str, r: dict) -> str:
	"""The Bank Transaction for this statement line: the one made at an earlier upload, else a new one (submitted)."""
	filters = {"bank_account": ba, "date": r["date"], "deposit": r["deposit"], "withdrawal": r["withdrawal"], "docstatus": 1}
	if r["reference_number"]:
		filters["reference_number"] = r["reference_number"]
	else:
		filters["description"] = r["description"]
	have = frappe.db.get_value("Bank Transaction", filters, "name")
	if have:
		return have
	bt = frappe.get_doc({"doctype": "Bank Transaction", "date": r["date"], "bank_account": ba, "deposit": r["deposit"],
		"withdrawal": r["withdrawal"], "description": r["description"], "reference_number": r["reference_number"] or None,
		"currency": "INR"})
	bt.flags.ignore_permissions = True
	bt.insert()
	try_submit(bt)
	return bt.name


def _candidates(ledger: str, r: dict, taken: set) -> list[dict]:
	"""Submitted payments / journals through this bank ledger, same side, same amount, within 5 days, not yet cleared."""
	d = getdate(r["date"])
	amount, pay = (r["withdrawal"], True) if r["withdrawal"] else (r["deposit"], False)
	lo, hi = amount - 0.5, amount + 0.5
	out = []
	for p in frappe.get_all("Payment Entry", filters={"docstatus": 1, "payment_type": "Pay" if pay else "Receive",
			"paid_from" if pay else "paid_to": ledger, ("paid_amount" if pay else "received_amount"): ["between", [lo, hi]],
			"posting_date": ["between", [add_days(d, -DAYS), add_days(d, DAYS)]], "clearance_date": ["is", "not set"]},
			fields=["name", "party", "reference_no", "posting_date"]):
		if ("Payment Entry", p.name) not in taken:
			out.append({**p, "doctype": "Payment Entry"})
	side = "credit" if pay else "debit"  # money out of the bank is a credit on the bank ledger
	for j in frappe.db.sql(f"""select je.name, je.cheque_no as reference_no, je.posting_date,
			(select max(x.party) from `tabJournal Entry Account` x where x.parent = je.name) as party
		from `tabJournal Entry` je join `tabJournal Entry Account` a on a.parent = je.name
		where je.docstatus = 1 and a.account = %s and a.{side} between %s and %s and je.posting_date between %s and %s
			and je.clearance_date is null group by je.name""", (ledger, lo, hi, add_days(d, -DAYS), add_days(d, DAYS)), as_dict=True):
		if ("Journal Entry", j.name) not in taken:
			out.append({**j, "doctype": "Journal Entry"})
	return out


def _reconcile(bt: str, doc: dict, amount: float):
	from erpnext.accounts.doctype.bank_reconciliation_tool.bank_reconciliation_tool import reconcile_vouchers

	reconcile_vouchers(bt, json.dumps([{"payment_doctype": doc["doctype"], "payment_name": doc["name"], "amount": amount}]))


def _fill_utr(doc: dict, r: dict):
	"""A payment saved without its UTR gets the bank's UTR and date (written on its timeline)."""
	if doc["doctype"] != "Payment Entry" or not r["reference_number"] or DR.norm_ref(doc.get("reference_no")):
		return
	frappe.db.set_value("Payment Entry", doc["name"], {"reference_no": r["reference_number"], "reference_date": r["date"]})
	frappe.get_doc("Payment Entry", doc["name"]).add_comment("Comment",
		_("UTR {0} dated {1} filled from the bank statement").format(r["reference_number"], r["date"]))


def process(user: str, file_url: str, bank_account: str | None = None) -> dict:
	need(user, ACCOUNTS, MANAGEMENT)
	company = _company()
	ba = bank_account or default_bank_account(company)
	if not ba:
		frappe.throw(_("No company Bank Account in ERPNext yet. Ask the CEO to add it (Bank Account linked to the bank ledger)."))
	ledger = frappe.db.get_value("Bank Account", ba, "account")
	try:
		st = SR.parse_text(_pdf_text(file_url))
	except SR.StatementError as e:
		frappe.throw(str(e), title=_("Statement not read"))
	taken, matched, not_in_erp = set(), [], []
	already = 0
	for r in st["rows"]:
		bt = _bank_line(ba, r)
		if frappe.db.get_value("Bank Transaction", bt, "status") == "Reconciled":
			already += 1
			continue
		amount = r["withdrawal"] or r["deposit"]
		doc, why = SR.pick_match(r, _candidates(ledger, r, taken))
		line = {"date": r["date"], "amount": amount, "out": bool(r["withdrawal"]), "utr": r["reference_number"],
			"bank_name": r["party_hint"], "bank_transaction": bt, "link": get_url_to_form("Bank Transaction", bt)}
		if doc:
			taken.add((doc["doctype"], doc["name"]))
			try:
				_reconcile(bt, doc, amount)
				_fill_utr(doc, r)
				matched.append({**line, "doctype": doc["doctype"], "name": doc["name"], "party": doc.get("party"), "why": why,
					"link": get_url_to_form(doc["doctype"], doc["name"])})
			except Exception:
				frappe.log_error("SK App bank statement reconcile")
				not_in_erp.append({**line, "why": _("could not reconcile, please do it in the Bank Reconciliation Tool")})
		else:
			not_in_erp.append({**line, "why": why})
	start, end = st["rows"][0]["date"], st["rows"][-1]["date"]
	not_in_bank = _not_in_bank(ledger, start, end, taken)
	return {"bank_account": ba, "from": start, "to": end, "lines": len(st["rows"]), "opening": st["opening"],
		"closing": st["closing"], "already": already, "matched": matched, "not_in_erp": not_in_erp, "not_in_bank": not_in_bank,
		"reco_tool": "/app/bank-reconciliation-tool"}


def _not_in_bank(ledger: str, start, end, taken: set) -> list[dict]:
	"""Payments in ERPNext for the statement's dates that the bank does not show: through this ledger and not cleared, or a
	bank mode / bank reference booked through Cash."""
	out = []
	for p in frappe.get_all("Payment Entry", filters={"docstatus": 1, "posting_date": ["between", [start, end]],
			"clearance_date": ["is", "not set"]}, or_filters={"paid_from": ledger, "paid_to": ledger},
			fields=["name", "party", "payment_type", "paid_amount", "posting_date"]):
		if ("Payment Entry", p.name) not in taken:
			out.append({"doctype": "Payment Entry", "name": p.name, "party": p.party, "amount": p.paid_amount,
				"date": str(p.posting_date), "why": _("not in the bank statement: a double?"), "link": get_url_to_form("Payment Entry", p.name)})
	from sk_app.doubles import _bank_in_cash

	for p in _bank_in_cash(start):
		if str(p.date) <= str(end):
			out.append({"doctype": "Payment Entry", "name": p.name, "party": p.party, "amount": p.amount, "date": str(p.date),
				"why": _("bank payment booked through Cash"), "link": get_url_to_form("Payment Entry", p.name)})
	return out
