"""Tally-style Accounts (SK 27-Oct-2026: "our team has 10 years of experience on Tally, make ERP and app suitable and
user friendly to them"). Mock-up Rev 0 approved by SK 27-Oct.

- One "Accounts Gateway" menu, like Gateway of Tally, with the same four sections and Tally names, in ERPNext (desk page
  /app/accounts-gateway) and in the app (Shraddha's Accounts screen). Each line opens the ERPNext screen behind it.
- Tally keys in ERPNext: F4 Contra, F5 Payment, F6 Receipt, F7 Journal, F8 Sales, F9 Purchase, Ctrl+F8 Sales Order,
  Ctrl+F9 Purchase Order, Alt+F5 Debit Note, Alt+F6 Credit Note, Alt+D Day Book, Alt+L Ledger, Ctrl+A accept (save and post), Esc back to the Gateway.
- Day Book: every voucher of a day with Tally voucher types (Payment / Receipt / Contra / Journal / Sales / Purchase ...).
- "Narration" on every voucher (ERPNext's remark field).
"""

import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate

ACCOUNTS_ROLES = ("Accounts User", "Accounts Manager")

# (section, key, English, Marathi, icon, Tally key, desk URL, app screen or None, note)
GATEWAY = [
	("Masters", "create_ledger", "Create Ledger", "लेजर तयार करा", "📒", "Alt+C", "/app/accounts-gateway?create=1", None,
		"Customer (Sundry Debtor), Supplier (Sundry Creditor), Bank, Expense, Income"),
	("Masters", "alter_ledger", "Alter Ledger", "लेजर बदला", "✏️", "Alt+A", "/app/accounts-gateway?alter=1", None, "Search any ledger by name"),
	("Masters", "chart", "Chart of Accounts", "खात्यांचा तक्ता", "🏛️", "", "/app/account/view/tree", None, "Groups and ledgers"),
	("Transactions", "payment", "Payment", "पेमेंट", "₹", "F5", "/app/payment-entry/new?payment_type=Pay", "to_pay", "Payment Entry · Pay"),
	("Transactions", "receipt", "Receipt", "पावती", "₹", "F6", "/app/payment-entry/new?payment_type=Receive", "to_collect", "Payment Entry · Receive"),
	("Transactions", "contra", "Contra", "कॉन्ट्रा", "⇄", "F4", "/app/payment-entry/new?payment_type=Internal%20Transfer", None,
		"Cash ↔ bank, bank ↔ bank"),
	("Transactions", "journal", "Journal", "जर्नल", "📖", "F7", "/app/journal-entry/new", "expenses", "Journal Entry"),
	("Transactions", "sales", "Sales", "विक्री", "🧾", "F8", "/app/sales-invoice/new", "invoices", "Sales Invoice"),
	("Transactions", "purchase", "Purchase", "खरेदी", "🧾", "F9", "/app/purchase-invoice/new", "bills_to_post", "Purchase Invoice"),
	("Transactions", "credit_note", "Credit Note", "क्रेडिट नोट", "↩️", "Alt+F6", "/app/sales-invoice/new?is_return=1", None, "Sales return"),
	("Transactions", "debit_note", "Debit Note", "डेबिट नोट", "↪️", "Alt+F5", "/app/purchase-invoice/new?is_return=1", None, "Purchase return"),
	("Transactions", "sales_order", "Sales Order", "विक्री ऑर्डर", "📝", "Ctrl+F8", "/app/sales-order/new", None, "Customer order"),
	("Transactions", "purchase_order", "Purchase Order", "खरेदी ऑर्डर", "📝", "Ctrl+F9", "/app/purchase-order/new", None, "Order to supplier"),
	("Transactions", "day_book", "Day Book", "डे बुक", "📅", "Alt+D", "/app/query-report/Day Book", "day_book", "All vouchers of a day"),
	("Transactions", "expenses_cash", "Expenses (petty cash)", "खर्च (रोख)", "💸", "", "/app/journal-entry/new", "dir_expenses", "Direct / Indirect"),
	("Utilities", "bank_reco", "Bank Reconciliation", "बँक जुळवणी", "🏦", "", "/app/bank-reconciliation-tool", None, ""),
	("Utilities", "import", "Import Transactions", "व्यवहार आयात", "⬆️", "", "/app/bank-statement-import/new", None, "Bank statement / Excel"),
	("Utilities", "month_close", "Month Close", "महिना बंद", "✅", "", "/app/accounts-gateway", "month_close", ""),
	("Utilities", "approvals", "Pending Approvals", "मंजुरी बाकी", "⏰", "", "/app/accounts-gateway?pending=1", "pay_approvals",
		"Draft vouchers to post, payments above Rs 5,000"),
	("Reports", "balance_sheet", "Balance Sheet", "ताळेबंद", "📊", "", "/app/query-report/Balance Sheet", None, ""),
	("Reports", "pnl", "Profit & Loss A/c", "नफा-तोटा", "📈", "", "/app/query-report/Profit and Loss Statement", "segment_pnl", "Cabin / Non-Cabin"),
	("Reports", "trial_balance", "Trial Balance", "ट्रायल बॅलन्स", "⚖️", "", "/app/query-report/Trial Balance", None, ""),
	("Reports", "ledger", "Ledger", "लेजर", "📚", "Alt+L", "/app/query-report/General Ledger", "cash_today", "Ledger vouchers, date-wise"),
	("Reports", "stock_summary", "Stock Summary", "स्टॉक सारांश", "📦", "", "/app/query-report/Stock Balance", None, ""),
	("Reports", "gst", "GST Reports", "GST अहवाल", "🧮", "", "/app/india-compliance", None, "GSTR-1, GSTR-3B"),
	("Reports", "more_reports", "Display More Reports", "आणखी अहवाल", "📄", "", "/app/accounting", None,
		"Bills Receivable / Payable, Cash Flow, Sales & Purchase Register"),
	("Reports", "dashboard", "Dashboard", "डॅशबोर्ड", "🟥", "", "/app/dashboard-view/Accounts", None, ""),
]
SECTIONS = ("Masters", "Transactions", "Utilities", "Reports")
# extra reports behind "Display More Reports" (Tally names → ERPNext report)
MORE_REPORTS = [("Bills Receivable", "Accounts Receivable"), ("Bills Payable", "Accounts Payable"), ("Cash Flow", "Cash Flow"),
	("Sales Register", "Sales Register"), ("Purchase Register", "Purchase Register"), ("Group Summary (Debtors)", "Customer Ledger Summary"),
	("Group Summary (Creditors)", "Supplier Ledger Summary"), ("Gross Profit", "Gross Profit")]
# Narration = ERPNext's remark field on every voucher
NARRATION = {"Payment Entry": "remarks", "Journal Entry": "user_remark", "Sales Invoice": "remarks", "Purchase Invoice": "remarks"}


def gateway(user: str | None = None) -> dict:
	sections = []
	for s in SECTIONS:
		sections.append({"section": s, "items": [{"key": k, "label": en, "label_mr": mr, "icon": ic, "keys": kb, "url": url, "app": app, "note": note}
			for sec, k, en, mr, ic, kb, url, app, note in GATEWAY if sec == s]})
	more = [{"label": a, "url": f"/app/query-report/{b}"} for a, b in MORE_REPORTS if frappe.db.exists("Report", b)]
	return {"sections": sections, "more": more, "fy": _fy_label()}


def _fy_label() -> str:
	d = getdate(nowdate())
	y = d.year if d.month >= 4 else d.year - 1
	return f"FY {y}-{str(y + 1)[2:]}"


def ensure():
	"""Narration label on every voucher (Tally word)."""
	from frappe.custom.doctype.property_setter.property_setter import make_property_setter

	for dt, field in NARRATION.items():
		if frappe.db.exists("DocType", dt) and frappe.get_meta(dt).has_field(field):
			make_property_setter(dt, field, "label", "Narration", "Data", validate_fields_for_doctype=False)


# ---------- Day Book ----------

def vch_type(voucher_type: str, payment_type=None, is_return=0, je_type=None) -> str:
	"""ERPNext voucher → Tally voucher type name."""
	if voucher_type == "Payment Entry":
		return {"Pay": "Payment", "Receive": "Receipt", "Internal Transfer": "Contra"}.get(payment_type, "Payment")
	if voucher_type == "Journal Entry":
		return {"Contra Entry": "Contra", "Credit Note": "Credit Note", "Debit Note": "Debit Note"}.get(je_type, "Journal")
	if voucher_type == "Sales Invoice":
		return "Credit Note" if is_return else "Sales"
	if voucher_type == "Purchase Invoice":
		return "Debit Note" if is_return else "Purchase"
	return {"Delivery Note": "Delivery Note", "Purchase Receipt": "Receipt Note", "Stock Entry": "Stock Journal",
		"Stock Reconciliation": "Physical Stock"}.get(voucher_type, voucher_type)


def day_book(from_date=None, to_date=None, company=None) -> list[dict]:
	"""One line per voucher, like Tally's Day Book: Date, Particulars, Vch Type, Vch No, Debit / Credit amount, Narration.
	Particulars = the party, else the biggest debit ledger; the amount goes in Debit when that ledger is debited."""
	from_date = getdate(from_date or nowdate())
	to_date = getdate(to_date or from_date)
	filters = {"posting_date": ["between", [from_date, to_date]], "is_cancelled": 0}
	if company:
		filters["company"] = company
	gl = frappe.get_all("GL Entry", filters=filters, fields=["posting_date", "voucher_type", "voucher_no", "account", "party", "debit", "credit",
		"creation"], order_by="posting_date asc, creation asc", limit=0)
	by, order = {}, []
	for g in gl:
		key = (g.voucher_type, g.voucher_no)
		if key not in by:
			by[key] = []
			order.append(key)
		by[key].append(g)
	out = []
	for vt, vn in order:
		lines = by[(vt, vn)]
		party = next((x for x in lines if x.party), None)
		main = party or max(lines, key=lambda x: flt(x.debit))
		amount = sum(flt(x.debit) for x in lines)
		info = _voucher_info(vt, vn)
		debited = flt(main.debit) > flt(main.credit)
		out.append({"date": str(lines[0].posting_date), "particulars": (party.party if party else main.account), "vch_type": vch_type(vt, **info["kind"]),
			"vch_no": vn, "voucher_type": vt, "debit": amount if debited else 0, "credit": 0 if debited else amount, "narration": info["narration"]})
	return out


def _voucher_info(vt: str, vn: str) -> dict:
	kind, narration = {}, ""
	try:
		if vt == "Payment Entry":
			r = frappe.db.get_value(vt, vn, ["payment_type", "remarks"], as_dict=True) or {}
			kind, narration = {"payment_type": r.get("payment_type")}, r.get("remarks")
		elif vt == "Journal Entry":
			r = frappe.db.get_value(vt, vn, ["voucher_type", "user_remark"], as_dict=True) or {}
			kind, narration = {"je_type": r.get("voucher_type")}, r.get("user_remark")
		elif vt in ("Sales Invoice", "Purchase Invoice"):
			r = frappe.db.get_value(vt, vn, ["is_return", "remarks"], as_dict=True) or {}
			kind, narration = {"is_return": r.get("is_return")}, r.get("remarks")
	except Exception:
		pass
	return {"kind": kind, "narration": (narration or "")[:200]}


# ---------- Masters: find a ledger (Alter Ledger) ----------

def find_ledger(q: str) -> list[dict]:
	"""Any ledger by name: accounts, customers (Sundry Debtors), suppliers (Sundry Creditors)."""
	q = (q or "").strip()
	if len(q) < 2:
		return []
	like = f"%{q}%"
	out = [{"doctype": "Account", "name": r.name, "title": r.account_name, "group": r.parent_account}
		for r in frappe.get_all("Account", filters={"account_name": ["like", like]}, fields=["name", "account_name", "parent_account"], limit=15)]
	out += [{"doctype": "Customer", "name": r.name, "title": r.customer_name, "group": "Sundry Debtors"}
		for r in frappe.get_all("Customer", filters={"customer_name": ["like", like]}, fields=["name", "customer_name"], limit=15)]
	out += [{"doctype": "Supplier", "name": r.name, "title": r.supplier_name, "group": "Sundry Creditors"}
		for r in frappe.get_all("Supplier", filters={"supplier_name": ["like", like]}, fields=["name", "supplier_name"], limit=15)]
	return out


def pending(user: str | None = None) -> list[dict]:
	"""Pending Approvals: draft vouchers waiting to be posted."""
	out = []
	for dt in ("Payment Entry", "Journal Entry", "Sales Invoice", "Purchase Invoice"):
		amt = {"Payment Entry": "paid_amount", "Journal Entry": "total_debit"}.get(dt, "grand_total")
		for r in frappe.get_all(dt, filters={"docstatus": 0}, fields=["name", "posting_date", amt + " as amount", "owner"], order_by="posting_date desc", limit=0):
			out.append({"doctype": dt, "name": r.name, "date": str(r.posting_date or ""), "amount": flt(r.amount), "by": r.owner,
				"vch_type": vch_type(dt)})
	return out


@frappe.whitelist()
def desk_gateway():
	"""For the ERPNext desk page."""
	_check()
	return gateway()


@frappe.whitelist()
def desk_find_ledger(q: str):
	_check()
	return find_ledger(q)


@frappe.whitelist()
def desk_pending():
	_check()
	return pending()


def _check():
	roles = set(frappe.get_roles())
	if not (roles & {*ACCOUNTS_ROLES, "System Manager", "Auditor"}):
		frappe.throw(_("Only the accounts team can open the Accounts Gateway"), frappe.PermissionError)
