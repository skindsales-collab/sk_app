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
from sk_app.store import _company, _todo, _users_with_function, attach, need, try_submit

ACCOUNTS = "Accounts"
MANAGEMENT = "Management"
APPROVED = "Approved for payment in SK App"
# SK's month-end rules (F06): stock closing 2nd, P&L 7th, MAR 10th; GST returns by their due dates
MONTH_CLOSE = [("stock_close", 2), ("pnl", 7), ("mar", 10), ("gstr1", 11), ("gstr3b", 20)]


def _money(v) -> str:
	return fmt_money(flt(v), currency=frappe.db.get_value("Company", _company(), "default_currency") or "INR")


# ---------- Cash Today ----------

def cash_today(user: str) -> dict:
	"""Bank and cash balances now, and money in / out today."""
	need(user, ACCOUNTS, MANAGEMENT)
	from erpnext.accounts.utils import get_balance_on

	company = _company()
	accounts = frappe.get_all("Account", filters={"company": company, "is_group": 0, "account_type": ["in", ["Bank", "Cash"]],
		"disabled": 0}, fields=["name", "account_name", "account_type"], order_by="account_type asc, account_name asc")
	for a in accounts:
		a["balance"] = flt(get_balance_on(account=a.name, date=nowdate(), company=company))
	today = frappe.get_all("Payment Entry", filters={"docstatus": 1, "posting_date": nowdate(), "company": company},
		fields=["name", "payment_type", "party_name", "paid_amount", "mode_of_payment", "reference_no"], order_by="creation desc")
	return {"accounts": accounts, "total": sum(a["balance"] for a in accounts),
		"in": sum(p.paid_amount for p in today if p.payment_type == "Receive"),
		"out": sum(p.paid_amount for p in today if p.payment_type == "Pay"), "today": today}


# ---------- To Collect ----------

def _bucket(days_late: int) -> str:
	return "not_due" if days_late <= 0 else "d0_30" if days_late <= 30 else "d31_60" if days_late <= 60 else "d60_plus"


def to_collect(user: str) -> list[dict]:
	"""Customer dues, oldest first, with the customer's mobile for Call / WhatsApp and the last promise."""
	need(user, ACCOUNTS, MANAGEMENT, "Sales")
	rows = frappe.get_all("Sales Invoice", filters={"docstatus": 1, "outstanding_amount": [">", 0], "company": _company()},
		fields=["name", "customer", "customer_name", "posting_date", "due_date", "grand_total", "outstanding_amount", "owner"],
		order_by="due_date asc, posting_date asc")
	for r in rows:
		late = date_diff(nowdate(), r.due_date or r.posting_date)
		r.update({"days_late": late, "bucket": _bucket(late), "mobile": frappe.db.get_value("Customer", r.customer, "mobile_no"),
			"due_date": str(r.due_date or ""), "posting_date": str(r.posting_date),
			"promise": frappe.db.get_value("Comment", {"reference_doctype": "Sales Invoice", "reference_name": r.name,
				"comment_type": "Comment", "content": ["like", "%Promise%"]}, "content", order_by="creation desc")})
	return rows


def promise(user: str, sales_invoice: str, text: str, promised_on=None) -> dict:
	"""After the call: what the customer said (spoken) and the promised date; a reminder for that day."""
	need(user, ACCOUNTS, MANAGEMENT, "Sales")
	if not (text or "").strip() and not promised_on:
		frappe.throw(_("Please say what the customer promised"))
	si = frappe.get_doc("Sales Invoice", sales_invoice)
	note = _("Promise {0}: {1}").format(promised_on or "-", text or "")
	si.add_comment("Comment", note)
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
	from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

	pe = get_payment_entry(reference_doctype, reference_name, party_amount=amount)
	_fill_payment(pe, mode, reference_no, reference_date)
	pe.insert()
	attach(photo, "Payment Entry", pe.name, user)
	posted = try_submit(pe)
	# the salesperson of the order hears that the money came (F06 link Finance -> Sales)
	owner = frappe.db.get_value(reference_doctype, reference_name, "owner")
	if owner and owner != user and owner in _users_with_function("Sales"):
		_todo(owner, reference_doctype, reference_name, _("Payment received: {0} from {1}").format(_money(amount), pe.party_name))
	return {"name": pe.name, "posted": posted}


def _fill_payment(pe, mode, reference_no, reference_date):
	if mode and frappe.db.exists("Mode of Payment", mode):
		pe.mode_of_payment = mode
	pe.reference_no = reference_no or pe.get("reference_no") or _("SK App {0}").format(nowdate())
	pe.reference_date = getdate(reference_date or nowdate())
	pe.flags.ignore_permissions = True


# ---------- To Pay ----------

def _approved(pi: str) -> bool:
	return bool(frappe.db.exists("Comment", {"reference_doctype": "Purchase Invoice", "reference_name": pi, "content": APPROVED}))


def to_pay(user: str) -> list[dict]:
	"""Supplier and contractor dues by due date; above the limit SK's OK is needed before paying."""
	need(user, ACCOUNTS, MANAGEMENT)
	rows = frappe.get_all("Purchase Invoice", filters={"docstatus": 1, "outstanding_amount": [">", 0], "company": _company()},
		fields=["name", "supplier", "supplier_name", "bill_no", "posting_date", "due_date", "outstanding_amount"],
		order_by="due_date asc, posting_date asc")
	limit = po_limit()
	for r in rows:
		r.update({"due_date": str(r.due_date or ""), "posting_date": str(r.posting_date), "days_late": date_diff(nowdate(), r.due_date or r.posting_date),
			"needs_ok": flt(r.outstanding_amount) > limit, "approved": _approved(r.name)})
	return rows


def pay_approvals(user: str) -> list[dict]:
	need(user, MANAGEMENT)
	return [r for r in to_pay(user) if r["needs_ok"] and not r["approved"]]


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
	from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

	pe = get_payment_entry("Purchase Invoice", pi.name, party_amount=amount)
	_fill_payment(pe, mode, reference_no, reference_date)
	pe.insert()
	attach(photo, "Payment Entry", pe.name, user)
	posted = try_submit(pe)
	frappe.db.set_value("ToDo", {"reference_type": "Purchase Invoice", "reference_name": pi.name, "status": "Open"}, "status", "Closed")
	return {"name": pe.name, "posted": posted}


def _functions(user: str) -> list[str]:
	from sk_app import logins

	return logins.profile_functions(user) + (["Management"] if "System Manager" in frappe.get_roles(user) else [])


# ---------- Bills to Post ----------

def bills_to_post(user: str) -> dict:
	"""Bill photos sent by Purchase / Store (tasks on the supplier) and draft Purchase Invoices to check and post."""
	need(user, ACCOUNTS)
	photos = frappe.get_all("ToDo", filters={"reference_type": "Supplier", "status": "Open", "allocated_to": user},
		fields=["name", "reference_name", "description", "creation"], order_by="creation asc")
	for p in photos:
		p["supplier_name"] = frappe.db.get_value("Supplier", p.reference_name, "supplier_name")
		p["photo"] = frappe.db.get_value("File", {"attached_to_doctype": "Supplier", "attached_to_name": p.reference_name},
			"file_url", order_by="creation desc")
		p["orders"] = frappe.get_all("Purchase Order", filters={"supplier": p.reference_name, "docstatus": 1, "per_billed": ["<", 100]},
			fields=["name", "grand_total", "transaction_date"], order_by="creation desc", limit=10)
		# SK 27-Oct (Yogesh): material came without a PO; the bill is made from the store's receipt instead
		p["receipts"] = frappe.get_all("Purchase Receipt", filters={"supplier": p.reference_name, "docstatus": 1, "per_billed": ["<", 100],
			"is_return": 0}, fields=["name", "grand_total", "posting_date", "supplier_delivery_note"], order_by="creation desc", limit=10)
		for x in p["receipts"]:
			x["posting_date"] = str(x.posting_date)
		p["creation"] = str(p.creation)
	drafts = frappe.get_all("Purchase Invoice", filters={"docstatus": 0, "company": _company()},
		fields=["name", "supplier_name", "bill_no", "grand_total", "posting_date"], order_by="creation asc")
	for d in drafts:
		d["posting_date"] = str(d.posting_date)
	return {"photos": photos, "drafts": drafts}


def make_bill(user: str, purchase_order: str | None, bill_no: str, bill_date=None, todo=None, photo=None, purchase_receipt=None,
		items=None, supplier=None) -> dict:
	"""Purchase Invoice with the supplier's bill number, kept as draft to check: from the PO (ERPNext mapping), from the
	store's receipt when material came without a PO, or (no PO, no receipt) from the items Accounts types (SK 27-Oct)."""
	need(user, ACCOUNTS)
	if not (bill_no or "").strip():
		frappe.throw(_("Please give the supplier's bill number"))
	if purchase_order:
		from erpnext.buying.doctype.purchase_order.purchase_order import get_mapped_purchase_invoice

		# Accounts may not read Purchase Orders in ERPNext; the bill is still made from the PO under her login
		pi = get_mapped_purchase_invoice(purchase_order, ignore_permissions=True)
	elif purchase_receipt:
		from erpnext.stock.doctype.purchase_receipt.purchase_receipt import make_purchase_invoice

		pi = make_purchase_invoice(purchase_receipt)
	else:
		from sk_app.store import uom

		supplier = supplier or (frappe.db.get_value("ToDo", todo, "reference_name") if todo else None)
		rows = [i for i in items or [] if i.get("item_code") and flt(i.get("qty")) > 0]
		if not supplier or not frappe.db.exists("Supplier", supplier):
			frappe.throw(_("Please pick the supplier"))
		if not rows:
			frappe.throw(_("Please give the item, quantity and rate from the bill"))
		pi = frappe.new_doc("Purchase Invoice")
		pi.update({"supplier": supplier, "company": _company()})
		for i in rows:
			pi.append("items", {"item_code": i["item_code"], "qty": flt(i["qty"]), "rate": flt(i.get("rate")), **uom(i["item_code"])})
		pi.set_missing_values()
	pi.bill_no = bill_no.strip()
	pi.bill_date = getdate(bill_date or nowdate())
	pi.flags.ignore_permissions = True
	pi.insert()
	attach(photo, "Purchase Invoice", pi.name, user)
	if todo:
		ref = frappe.db.get_value("ToDo", todo, ["allocated_to", "reference_name"], as_dict=True)
		file_url = frappe.db.get_value("File", {"attached_to_doctype": "Supplier", "attached_to_name": ref and ref.reference_name},
			"file_url", order_by="creation desc") if ref else None
		if file_url:
			frappe.get_doc({"doctype": "File", "file_url": file_url, "attached_to_doctype": "Purchase Invoice",
				"attached_to_name": pi.name}).insert(ignore_permissions=True)
		if ref and ref.allocated_to == user:
			frappe.db.set_value("ToDo", todo, "status", "Closed")
	return {"name": pi.name, "grand_total": pi.grand_total}


def post(user: str, doctype: str, name: str) -> dict:
	"""Checked and correct: post the draft bill / invoice."""
	need(user, ACCOUNTS)
	if doctype not in ("Purchase Invoice", "Sales Invoice"):
		frappe.throw(_("Unknown document"))
	doc = frappe.get_doc(doctype, name)
	if doc.docstatus != 0:
		frappe.throw(_("{0} is already posted").format(name))
	posted = try_submit(doc)
	reason = None if posted else frappe.db.get_value("Comment", {"reference_doctype": doctype, "reference_name": name,
		"content": ["like", "Kept as draft%"]}, "content", order_by="creation desc")
	return {"name": name, "posted": posted, "reason": reason}


def done_bill_photo(user: str, todo: str) -> dict:
	"""Bill photo already handled in ERPNext (or not a bill): take it off the list."""
	need(user, ACCOUNTS)
	if frappe.db.get_value("ToDo", todo, "allocated_to") != user:
		frappe.throw(_("Not your task"), frappe.PermissionError)
	frappe.db.set_value("ToDo", todo, "status", "Closed")
	return {"ok": True}


# ---------- Photo entry (SK 27-Oct: "when she receives an e-invoice or bill she takes a photo and submits, then the
# further process is captured the earlier way"; "same option she needs for all entries") ----------

# kind -> (label, where Accounts finishes it in ERPNext). Money in / out stays a manual ERPNext entry (SK 27-Oct rule).
PHOTO_KINDS = {
	"supplier_bill": ("Supplier bill / e-invoice", None),
	"expense": ("Expense bill / petty cash voucher", "/app/journal-entry/new?voucher_type=Cash%20Entry"),
	"money_in": ("Payment received (cheque / UTR)", "/app/payment-entry/new?payment_type=Receive"),
	"money_out": ("Payment made (bank slip / UTR)", "/app/payment-entry/new?payment_type=Pay"),
	"other": ("Other document", None),
}
PHOTO_TAG = "Photo entry"


def photo_entry(user: str, kind: str, photo: str, supplier=None, party=None, amount=None, ref_no=None, note=None) -> dict:
	"""Shraddha's photo of a bill / e-invoice / voucher / payment proof. A supplier bill joins Bills to Post (Make bill ->
	draft Purchase Invoice -> Post, as before); every other photo becomes her task with the ERPNext entry to make."""
	need(user, ACCOUNTS)
	if kind not in PHOTO_KINDS:
		frappe.throw(_("Please pick what the photo is"))
	if not photo:
		frappe.throw(_("Please take a photo or pick the PDF"))
	if kind == "supplier_bill":
		from sk_app.purchase import send_bill

		if not supplier or not frappe.db.exists("Supplier", supplier):
			frappe.throw(_("Please pick the supplier"))
		send_bill(user, supplier, photo, amount, ref_no, None, note)
		return {"kind": kind, "go": "bills_to_post"}
	label = PHOTO_KINDS[kind][0]
	extra = [x for x in (party, amount and _("Rs {0}").format(fmt_money(flt(amount))), ref_no and _("Ref {0}").format(ref_no), note) if x]
	text = f"{PHOTO_TAG} [{kind}]: {_(label)}" + (" · " + " · ".join(extra) if extra else "")
	todo = frappe.get_doc({"doctype": "ToDo", "allocated_to": user, "description": text, "priority": "High", "date": nowdate()})
	todo.insert(ignore_permissions=True)
	attach(photo, "ToDo", todo.name, user)
	return {"kind": kind, "todo": todo.name, "go": "photo_entries"}


def photo_entries(user: str) -> list[dict]:
	"""Open photo entries (not supplier bills) with the photo and the ERPNext entry to make."""
	need(user, ACCOUNTS)
	rows = frappe.get_all("ToDo", filters={"allocated_to": user, "status": "Open", "description": ["like", PHOTO_TAG + " [%"]},
		fields=["name", "description", "creation"], order_by="creation asc")
	import re

	for r in rows:
		m = re.match(re.escape(PHOTO_TAG) + r" \[(\w+)\]: (.*)", frappe.utils.strip_html(r.description or ""), re.S)
		r["kind"] = m.group(1) if m else "other"
		r["text"] = m.group(2) if m else r.description
		r["erp_url"] = PHOTO_KINDS.get(r["kind"], (None, None))[1] or f"/app/todo/{r.name}"
		r["photo"] = frappe.db.get_value("File", {"attached_to_doctype": "ToDo", "attached_to_name": r.name}, "file_url")
		r["creation"] = str(r.creation)
	return rows


# ---------- Invoices ----------

def invoices(user: str) -> dict:
	"""Cabins dispatched without invoice (Delivery Notes not billed) and invoice drafts to check and post."""
	need(user, ACCOUNTS)
	company = _company()
	to_bill = frappe.get_all("Delivery Note", filters={"docstatus": 1, "per_billed": ["<", 100], "status": ["not in", ["Closed", "Cancelled"]],
		"company": company, "is_return": 0}, fields=["name", "customer_name", "posting_date", "grand_total", "vehicle_no"], order_by="posting_date asc")
	for d in to_bill:
		d.update({"posting_date": str(d.posting_date), "days": date_diff(nowdate(), d.posting_date)})
	drafts = frappe.get_all("Sales Invoice", filters={"docstatus": 0, "company": company},
		fields=["name", "customer_name", "posting_date", "grand_total"], order_by="creation asc")
	for d in drafts:
		d["posting_date"] = str(d.posting_date)
	return {"to_bill": to_bill, "drafts": drafts}


def make_invoice(user: str, delivery_note: str) -> dict:
	"""Sales Invoice from the Delivery Note (items, rates, taxes copied by ERPNext); a draft to check, then Post."""
	need(user, ACCOUNTS)
	from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice

	si = make_sales_invoice(delivery_note)
	si.flags.ignore_permissions = True
	si.insert()
	return {"name": si.name, "grand_total": si.grand_total}


# ---------- Expenses and petty cash ----------

def expenses(user: str) -> list[dict]:
	"""Approved staff expense claims still to pay (Frappe HR)."""
	need(user, ACCOUNTS)
	if not frappe.db.exists("DocType", "Expense Claim"):
		return []
	rows = frappe.get_all("Expense Claim", filters={"docstatus": 1, "approval_status": "Approved", "status": "Unpaid", "company": _company()},
		fields=["name", "employee_name", "posting_date", "grand_total", "total_sanctioned_amount"], order_by="posting_date asc")
	for r in rows:
		r["posting_date"] = str(r.posting_date)
	return rows


def pay_expense(user: str, expense_claim: str) -> dict:
	need(user, ACCOUNTS)
	from hrms.hr.doctype.expense_claim.expense_claim import make_bank_entry

	je = frappe.get_doc(make_bank_entry("Expense Claim", expense_claim))
	je.cheque_no = je.get("cheque_no") or _("SK App {0}").format(nowdate())
	je.cheque_date = je.get("cheque_date") or nowdate()
	je.flags.ignore_permissions = True
	je.insert()
	return {"name": je.name, "posted": try_submit(je)}


def voucher_options(user: str) -> dict:
	need(user, ACCOUNTS)
	company = _company()
	return {"expense_accounts": frappe.get_all("Account", filters={"company": company, "is_group": 0, "root_type": "Expense", "disabled": 0},
			pluck="name", order_by="account_name asc"),
		"cash_accounts": frappe.get_all("Account", filters={"company": company, "is_group": 0, "account_type": ["in", ["Cash", "Bank"]],
			"disabled": 0}, pluck="name", order_by="account_type desc, account_name asc"),
		"cost_centers": frappe.get_all("Cost Center", filters={"company": company, "is_group": 0, "disabled": 0}, pluck="name", order_by="name asc")}


def petty_cash(user: str, expense_account: str, amount, cash_account: str, cost_center=None, narration=None, photo=None) -> dict:
	"""Petty cash / expense voucher: photo of the voucher + spoken narration -> Journal Entry."""
	need(user, ACCOUNTS)
	amount = flt(amount)
	if amount <= 0:
		frappe.throw(_("Please give the amount"))
	if not (narration or "").strip():
		frappe.throw(_("Please say what the money was spent on"))
	je = frappe.new_doc("Journal Entry")
	je.voucher_type = "Cash Entry" if frappe.db.get_value("Account", cash_account, "account_type") == "Cash" else "Bank Entry"
	je.company = _company()
	je.posting_date = nowdate()
	je.user_remark = narration
	if je.voucher_type == "Bank Entry":
		je.cheque_no, je.cheque_date = _("SK App {0}").format(nowdate()), nowdate()
	je.append("accounts", {"account": expense_account, "debit_in_account_currency": amount, "cost_center": cost_center})
	je.append("accounts", {"account": cash_account, "credit_in_account_currency": amount, "cost_center": cost_center})
	je.flags.ignore_permissions = True
	je.insert()
	attach(photo, "Journal Entry", je.name, user)
	return {"name": je.name, "posted": try_submit(je)}


# ---------- Segment P&L ----------

def segment_pnl(user: str, month=None) -> dict:
	"""This month's income, cost and margin per cost centre (Portable Cabin, Machine Shifting, Service ...)."""
	need(user, ACCOUNTS, MANAGEMENT)
	start = get_first_day(getdate(month or nowdate()))
	end = add_days(get_first_day(add_days(start, 32)), -1)
	rows = frappe.db.sql("""
		select gle.cost_center,
			sum(case when acc.root_type = 'Income' then gle.credit - gle.debit else 0 end) as income,
			sum(case when acc.root_type = 'Expense' then gle.debit - gle.credit else 0 end) as cost
		from `tabGL Entry` gle join `tabAccount` acc on acc.name = gle.account
		where gle.company = %s and gle.is_cancelled = 0 and gle.posting_date between %s and %s
			and acc.root_type in ('Income', 'Expense')
		group by gle.cost_center order by income desc""", (_company(), start, end), as_dict=True)
	for r in rows:
		r["cost_center"] = r.cost_center or _("Not set")
		r["margin"] = flt(r.income) - flt(r.cost)
		r["margin_pct"] = round(r["margin"] / flt(r.income) * 100, 1) if flt(r.income) else None
	total = {k: sum(flt(r[k]) for r in rows) for k in ("income", "cost", "margin")}
	return {"from": str(start), "to": str(end), "rows": rows, "total": total}


# ---------- Month Close ----------

def _close_key(month_start, key: str) -> str:
	return f"SK Month Close {str(month_start)[:7]}: {key}"


def month_close(user: str) -> list[dict]:
	"""This month's closing checklist with dates; ticked items are kept as closed ToDos (who and when)."""
	need(user, ACCOUNTS, MANAGEMENT)
	start = get_first_day(nowdate())
	out = []
	for key, day in MONTH_CLOSE:
		due = add_days(start, day - 1)
		done = frappe.db.get_value("ToDo", {"description": _close_key(start, key), "status": "Closed"}, ["allocated_to", "modified"], as_dict=True)
		out.append({"key": key, "due": str(due), "done": bool(done), "late": not done and getdate(due) < getdate(),
			"by": done and frappe.utils.get_fullname(done.allocated_to), "on": done and str(done.modified)[:16]})
	return out


def tick_close(user: str, key: str, done=1) -> dict:
	need(user, ACCOUNTS)
	if key not in dict(MONTH_CLOSE):
		frappe.throw(_("Unknown step"))
	desc = _close_key(get_first_day(nowdate()), key)
	name = frappe.db.get_value("ToDo", {"description": desc})
	status = "Closed" if cint(done) else "Open"
	if name:
		frappe.db.set_value("ToDo", name, {"status": status, "allocated_to": user})
	else:
		frappe.get_doc({"doctype": "ToDo", "allocated_to": user, "description": desc, "status": status, "date": nowdate()}).insert(ignore_permissions=True)
	return {"ok": True}


def badges(user: str, functions: list[str]) -> dict:
	out = {}
	company = _company()
	if ACCOUNTS in functions:
		out["to_collect"] = frappe.db.count("Sales Invoice", {"docstatus": 1, "outstanding_amount": [">", 0], "due_date": ["<", nowdate()], "company": company})
		out["to_pay"] = frappe.db.count("Purchase Invoice", {"docstatus": 1, "outstanding_amount": [">", 0], "due_date": ["<=", add_days(nowdate(), 3)], "company": company})
		out["bills_to_post"] = frappe.db.count("Purchase Invoice", {"docstatus": 0, "company": company}) \
			+ frappe.db.count("ToDo", {"reference_type": "Supplier", "status": "Open", "allocated_to": user})
		out["invoices"] = frappe.db.count("Delivery Note", {"docstatus": 1, "per_billed": ["<", 100], "status": ["not in", ["Closed", "Cancelled"]],
			"company": company, "is_return": 0}) + frappe.db.count("Sales Invoice", {"docstatus": 0, "company": company})
		if frappe.db.exists("DocType", "Expense Claim"):
			out["expenses"] = frappe.db.count("Expense Claim", {"docstatus": 1, "approval_status": "Approved", "status": "Unpaid", "company": company})
		out["month_close"] = sum(1 for r in month_close(user) if r["late"])
	if MANAGEMENT in functions:
		out["pay_approvals"] = len(pay_approvals(user))
	return {k: v for k, v in out.items() if v}
