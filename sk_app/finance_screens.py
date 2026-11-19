"""Finance screens (reads only; the Finance writers are writers/payment.py, writers/journal.py, writers/bill.py).
Cash today, To Collect, To Pay, bills to post, photo entries, invoices, expenses, segment P&L, month close, badges.
Plan A step 5 (SK 9-Nov): split out of finance.py; names unchanged. finance.py keeps the helpers the Finance writers share."""

from frappe import _
from frappe.utils import add_days, date_diff, flt, get_first_day, getdate, nowdate
from sk_app.finance import ACCOUNTS, MANAGEMENT, MONTH_CLOSE, PHOTO_KINDS, PHOTO_TAG, PROMISE_DATE, PROMISE_NOTE, _approved, _bucket, _close_key, _promise
from sk_app.purchase import po_limit
from sk_app.store import _company, material_pos, need, try_submit
import frappe


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

def to_collect(user: str) -> list[dict]:
	"""Customer dues, oldest first, with the customer's mobile for Call / WhatsApp and the last promise."""
	need(user, ACCOUNTS, MANAGEMENT, "Sales")
	fields = ["name", "customer", "customer_name", "posting_date", "due_date", "grand_total", "outstanding_amount", "owner"]
	meta = frappe.get_meta("Sales Invoice")
	fields += [f for f in (PROMISE_DATE, PROMISE_NOTE) if meta.has_field(f)]
	rows = frappe.get_all("Sales Invoice", filters={"docstatus": 1, "outstanding_amount": [">", 0], "company": _company()},
		fields=fields, order_by="due_date asc, posting_date asc")
	# Mac data check 9-Nov: a salesperson saw every customer's dues; they collect only from their own customers (Sales Team)
	from sk_app.core.people import functions

	if not {ACCOUNTS, MANAGEMENT} & set(functions(user)):
		from sk_app.sales_owner import _sales_persons, customer_persons

		mine, by_customer = set(_sales_persons(user) or []), customer_persons()
		non_cabin = set()
		if "Machine Shifting" in functions(user):  # the Non-Cabin owner collects from every Non-Cabin customer (SK 26-Oct)
			from sk_app import segments

			non_cabin = set(frappe.get_all("Customer", filters={"customer_group": ["in", segments.groups_of(segments.NON_CABIN)]}, pluck="name"))
		rows = [r for r in rows if r.customer in non_cabin or mine & set(by_customer.get(r.customer) or [])]
	for r in rows:
		late = date_diff(nowdate(), r.due_date or r.posting_date)
		r.update({"days_late": late, "bucket": _bucket(late), "mobile": frappe.db.get_value("Customer", r.customer, "mobile_no"),
			"due_date": str(r.due_date or ""), "posting_date": str(r.posting_date),
			"promise": _promise(r)})
		for f in (PROMISE_DATE, PROMISE_NOTE):
			r.pop(f, None)
	return rows

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

def bills_to_post(user: str) -> dict:
	"""Bill photos sent by Purchase / Store (tasks on the supplier) and draft Purchase Invoices to check and post."""
	need(user, ACCOUNTS)
	photos = frappe.get_all("ToDo", filters={"reference_type": "Supplier", "status": "Open", "allocated_to": user},
		fields=["name", "reference_name", "description", "creation"], order_by="creation asc")
	for p in photos:
		p["supplier_name"] = frappe.db.get_value("Supplier", p.reference_name, "supplier_name")
		p["photo"] = frappe.db.get_value("File", {"attached_to_doctype": "Supplier", "attached_to_name": p.reference_name},
			"file_url", order_by="creation desc")
		# labour POs are billed by themselves from their GRN after Quality (SK 29-Oct): not offered here
		p["orders"] = frappe.get_all("Purchase Order", filters={"supplier": p.reference_name, "docstatus": 1, "per_billed": ["<", 100], **material_pos()},
			fields=["name", "grand_total", "transaction_date"], order_by="creation desc", limit=10)
		# the bill can also be made from the store's receipt (received against the PO)
		p["receipts"] = frappe.get_all("Purchase Receipt", filters={"supplier": p.reference_name, "docstatus": 1, "per_billed": ["<", 100],
			"is_return": 0, **material_pos("Purchase Receipt")}, fields=["name", "grand_total", "posting_date", "supplier_delivery_note"], order_by="creation desc", limit=10)
		for x in p["receipts"]:
			x["posting_date"] = str(x.posting_date)
		p["creation"] = str(p.creation)
	drafts = frappe.get_all("Purchase Invoice", filters={"docstatus": 0, "company": _company()},
		fields=["name", "supplier_name", "bill_no", "grand_total", "posting_date"], order_by="creation asc")
	for d in drafts:
		d["posting_date"] = str(d.posting_date)
	return {"photos": photos, "drafts": drafts}

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

def voucher_options(user: str) -> dict:
	need(user, ACCOUNTS)
	company = _company()
	return {"expense_accounts": frappe.get_all("Account", filters={"company": company, "is_group": 0, "root_type": "Expense", "disabled": 0},
			pluck="name", order_by="account_name asc"),
		# SK 4-Nov: bank first (most money moves by net banking), then Cash
		"cash_accounts": frappe.get_all("Account", filters={"company": company, "is_group": 0, "account_type": ["in", ["Cash", "Bank"]],
			"disabled": 0}, pluck="name", order_by="account_type asc, account_name asc"),
		"cost_centers": frappe.get_all("Cost Center", filters={"company": company, "is_group": 0, "disabled": 0}, pluck="name", order_by="name asc")}

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

def badges(user: str, functions: list[str]) -> dict:
	out = {}
	company = _company()
	if ACCOUNTS in functions:
		# SK 1-Nov logic check C3: from the same ledger dues as the Receivables / Bills to pay arrows (Tally bills too),
		# so the badge never says 0 while the arrow shows lakhs: customers with a bill over 30 days, suppliers due in 3 days
		dues = frappe.cache.get_value("sk_fin_due_badges")
		if dues is None:
			from sk_app import dashboards

			dues = {"to_collect": sum(1 for d in dashboards._party_dues("Customer") if d.late > 30),
				"to_pay": sum(1 for d in dashboards._party_dues("Supplier") if d.late >= 27)}
			frappe.cache.set_value("sk_fin_due_badges", dues, expires_in_sec=300)
		out.update(dues)
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
