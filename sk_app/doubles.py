"""Stop double entries (SK 4-Nov-2026), live on every save from the app, the ERPNext desk or the API.

Layer 2: before a Payment Entry, Purchase Invoice, Sales Invoice or Journal Entry is saved, it is compared with what is
already in ERPNext: the same party and amount within 7 days, or the same reference / bill number. A CRM lead with the same
mobile or e-mail, or a second deal from the same lead, is stopped too. The message gives the existing entry's link.
A real second entry (two equal bills in a week) is saved by ticking "Not a double (checked)" (Accounts only); that is
written on the entry's timeline with the person's name.

Shraddha 4-Nov: a Net Banking / bank-reference payment booked from Cash is stopped (it never shows in Bank Reconciliation),
and a Cash mode cannot go to a bank account. Cash is allowed (some cabin payments are cash) with its reason.

Layer 4: every morning the list of possible doubles in ERPNext goes to Accounts (Shraddha) and the CEO (SK) by e-mail and
app notification, each entry with its link. The rules are in double_rules.py.
"""

import frappe
from frappe import _
from frappe.utils import add_days, flt, get_url_to_form, getdate, nowdate

from sk_app import double_rules as R

OK_FIELD = "sk_not_double"
CASH_REASON = "sk_cash_reason"
MONEY_DOCTYPES = ("Payment Entry", "Purchase Invoice", "Sales Invoice", "Journal Entry")
OK_ROLES = {"System Manager", "Accounts Manager", "Accounts User"}
# entries ERPNext makes by itself
SYSTEM_JE = {"Exchange Gain Or Loss", "Exchange Rate Revaluation", "Depreciation Entry", "Deferred Revenue", "Deferred Expense",
	"Period Closing Voucher"}
LEAD_DAYS = 0  # SK 7-Nov (KF-04801): the same lead on the same date is a double, on another date a new lead


def ensure_setup():
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	field = {"fieldname": OK_FIELD, "label": "Not a double (checked)", "fieldtype": "Check", "no_copy": 1,
		"description": "Tick only when ERPNext stopped this as a possible double and you checked it is a separate entry"}
	create_custom_fields({dt: [field] for dt in MONEY_DOCTYPES}, update=True)
	create_custom_fields({"Payment Entry": [{"fieldname": CASH_REASON, "label": "Cash reason (only for a cash payment)",
		"fieldtype": "Small Text", "insert_after": "mode_of_payment", "no_copy": 1}]}, update=True)


def _skip(doc) -> bool:
	f = frappe.flags
	return bool(f.in_install or f.in_migrate or f.in_patch or f.in_import or f.sk_no_double or doc.flags.get("sk_no_double"))


def _link(doctype: str, name: str) -> str:
	return f'<a href="{get_url_to_form(doctype, name)}">{name}</a>'


def _stop(rows: list, why: str, ok_hint: bool = True):
	lines = [_("This looks like a double entry ({0}). Already in ERPNext:").format(why)]
	for r in rows[:5]:
		bits = [_link(r["doctype"], r["name"]), str(r.get("date") or ""), f"₹{flt(r['amount']):,.0f}" if r.get("amount") else ""]
		lines.append("• " + " · ".join(b for b in bits if b) + (" (draft)" if r.get("docstatus") == 0 else ""))
	lines.append(_("Open it and check. If this is really a separate entry, tick 'Not a double (checked)' and save again.")
		if ok_hint else _("Open it and add your update there."))
	frappe.throw("<br>".join(lines), title=_("Possible double entry"), exc=frappe.DuplicateEntryError)


def _ok_ticked(doc) -> bool:
	if not doc.get(OK_FIELD):
		return False
	if not OK_ROLES & set(frappe.get_roles()):
		frappe.throw(_("Only Accounts can tick 'Not a double (checked)'. Please ask Shraddha."))
	if doc.is_new():
		return True  # the record does not exist yet, so no comment can point at it; its owner is the one who ticked
	before = doc.get_doc_before_save()
	if not before or not before.get(OK_FIELD):
		doc.add_comment("Comment", _("Ticked 'Not a double (checked)' by {0}").format(frappe.session.user))
	return True


def _lock(doctype: str, name: str | None):
	"""Two saves of the same party at the same moment (a double tap) wait for each other, so the second one sees the first."""
	if name and doctype in ("Customer", "Supplier", "Employee", "Shareholder", "CRM Lead"):
		frappe.db.sql(f"select name from `tab{doctype}` where name = %s for update", name)


def _window(d, days=None):
	d = getdate(d or nowdate())
	return [add_days(d, -(days or R.DAYS)), add_days(d, days or R.DAYS)]


def _amount_range(amount):
	return [flt(amount) - R.AMOUNT_GAP, flt(amount) + R.AMOUNT_GAP]


def _rows(doctype, filters, date_field, amount_field, name=None, extra=()):
	filters = {**filters, "docstatus": ["<", 2]}
	if name:
		filters["name"] = ["!=", name]
	out = frappe.get_all(doctype, filters=filters, fields=["name", "docstatus", f"{date_field} as date", f"{amount_field} as amount",
		*extra], order_by=f"{date_field} desc", limit=10)
	return [{**r, "doctype": doctype} for r in out]


def _same_ref(doctype: str, field: str, ref, name, extra: str = "", values: tuple = ()) -> list:
	key = R.norm_ref(ref)
	if not key:
		return []
	date_field, amount_field = {"Payment Entry": ("posting_date", "paid_amount"), "Journal Entry": ("posting_date", "total_debit"),
		"Purchase Invoice": ("posting_date", "grand_total")}[doctype]
	got = frappe.db.sql(f"""select name, docstatus, {date_field} as date, {amount_field} as amount from `tab{doctype}`
		where docstatus < 2 and name != %s and upper(regexp_replace(ifnull({field}, ''), '[^A-Za-z0-9]', '')) = %s {extra}
		order by {date_field} desc limit 5""", (name or "", key, *values), as_dict=True)
	return [{**r, "doctype": doctype} for r in got]


def _je_party_rows(party_type, party, amount, side: str, d, name=None) -> list:
	"""Journal entries with a row for this party of this amount on this side (debit / credit) within 7 days."""
	got = frappe.db.sql(f"""select je.name, max(je.docstatus) as docstatus, max(je.posting_date) as date, max(a.{side}) as amount,
			max(ifnull(nullif(je.bill_no, ''), je.cheque_no)) as ref
		from `tabJournal Entry` je join `tabJournal Entry Account` a on a.parent = je.name
		where je.docstatus < 2 and je.name != %s and a.party_type = %s and a.party = %s
			and a.{side} between %s and %s and je.posting_date between %s and %s
		group by je.name order by date desc limit 5""",
		(name or "", party_type, party, *_amount_range(amount), *_window(d, R.CROSS_DAYS)), as_dict=True)
	return [{**r, "doctype": "Journal Entry"} for r in got]


def _pe_party_rows(party_type, party, amount, payment_type, d, name=None) -> list:
	field = "paid_amount" if payment_type == "Pay" else "received_amount"
	return _rows("Payment Entry", {"party_type": party_type, "party": party, "payment_type": payment_type,
		field: ["between", _amount_range(amount)], "posting_date": ["between", _window(d, R.CROSS_DAYS)]}, "posting_date", field, name,
		["reference_no as ref"])


# ---------- layer 2: live check on save ----------

def check(doc, method=None):
	"""validate of Payment Entry, Purchase Invoice, Sales Invoice and Journal Entry."""
	if doc.doctype in ("Payment Entry", "Journal Entry"):
		check_cash_reason(doc)
	if doc.doctype == "Payment Entry":
		check_bank_account(doc)
	if _skip(doc) or doc.docstatus == 2 or _ok_ticked(doc):
		return
	{"Payment Entry": _check_payment, "Purchase Invoice": _check_purchase, "Sales Invoice": _check_sale,
		"Journal Entry": _check_journal}[doc.doctype](doc)


def check_cash_reason(doc):
	"""SK 4-Nov: most payments are net banking; some cabin payments really are cash. A cash entry is fine, with its reason."""
	if _skip(doc) or doc.docstatus == 2:
		return
	if doc.doctype == "Payment Entry":
		accounts, reason = [doc.paid_from, doc.paid_to], doc.get(CASH_REASON)
	else:
		accounts, reason = [a.account for a in doc.accounts], doc.get("user_remark") or doc.get(CASH_REASON)
	cash = [a for a in accounts if a and frappe.get_cached_value("Account", a, "account_type") == "Cash"]
	if cash and not (reason or "").strip():
		frappe.throw(_("{0} is a Cash account. Most payments are by net banking: if this one really was in cash, please write "
			"why in '{1}'; otherwise choose the bank account.").format(cash[0],
			_("Cash reason") if doc.doctype == "Payment Entry" else _("User Remark")), title=_("Cash entry"))


def check_bank_account(doc):
	"""Shraddha 4-Nov: Net Banking (a bank mode) or an IMPS / NEFT / UTR reference booked from or to Cash is stopped."""
	if _skip(doc) or doc.docstatus == 2 or doc.payment_type not in ("Pay", "Receive"):
		return
	account = doc.paid_from if doc.payment_type == "Pay" else doc.paid_to
	account_type = frappe.get_cached_value("Account", account, "account_type") if account else None
	if not doc.mode_of_payment and account_type in ("Bank", "Cash"):
		# no mode picked: Net Banking for a bank account, Cash for the cash account, so every payment carries its mode
		mode = "Net Banking" if account_type == "Bank" else "Cash"
		if frappe.db.exists("Mode of Payment", mode):
			doc.mode_of_payment = mode
	mode_type = frappe.get_cached_value("Mode of Payment", doc.mode_of_payment, "type") if doc.mode_of_payment else None
	if mode_type == "Cash" and account_type == "Bank":
		frappe.throw(_("Mode of payment is {0} (cash) but {1} is a bank account. Please pick Net Banking (or the right bank mode) "
			"for a bank payment, or the Cash account for a cash payment.").format(doc.mode_of_payment, account), title=_("Wrong account"))
	if R.bank_mode_to_cash(mode_type, account_type, doc.reference_no):
		field = _("Account Paid From") if doc.payment_type == "Pay" else _("Account Paid To")
		frappe.throw(_("This is a bank payment ({0}) but {1} is {2}, a Cash account. It would show in the ledger but never in "
			"Bank Reconciliation. Please choose the bank account (e.g. STATE BANK OF INDIA - SITSPL) in {1}.").format(
			doc.mode_of_payment if mode_type == "Bank" else doc.reference_no, field, account), title=_("Wrong account"))


def _check_payment(doc):
	same = _same_ref("Payment Entry", "reference_no", doc.reference_no, doc.name)
	same += _same_ref("Journal Entry", "cheque_no", doc.reference_no, None)
	if same:
		_stop(same, _("same reference number {0}").format(doc.reference_no))
	if doc.payment_type not in ("Pay", "Receive") or not doc.party:
		return
	_lock(doc.party_type, doc.party)
	amount = doc.paid_amount if doc.payment_type == "Pay" else doc.received_amount
	rows = _pe_party_rows(doc.party_type, doc.party, amount, doc.payment_type, doc.posting_date, doc.name)
	# Tally receipts / payments were also booked as journals: a payment to a supplier is a debit on the supplier
	rows += _je_party_rows(doc.party_type, doc.party, amount, "debit" if doc.payment_type == "Pay" else "credit", doc.posting_date)
	# own numbers of the same kind: two real payments (SK 7-Nov); a bank number never clears a pair (checker 7-Nov)
	rows = [r for r in rows if R.voucher_double(doc.reference_no, doc.posting_date, r.get("ref"), r.get("date"))]
	if rows:
		_stop(rows, _("same party and amount within {0} days").format(max(R.pair_days(doc.reference_no, r.get("ref")) for r in rows)))


def _check_purchase(doc):
	if not doc.supplier:
		return
	_lock("Supplier", doc.supplier)
	if doc.bill_no and R.norm_ref(doc.bill_no):
		rows = _same_ref("Purchase Invoice", "bill_no", doc.bill_no, doc.name, "and supplier = %s", (doc.supplier,))
		if rows:
			_stop(rows, _("same supplier bill number {0}").format(doc.bill_no))
	rows = _rows("Purchase Invoice", {"supplier": doc.supplier, "is_return": doc.is_return or 0,
		"grand_total": ["between", _amount_range(doc.grand_total)], "posting_date": ["between", _window(doc.posting_date)]},
		"posting_date", "grand_total", doc.name, ["bill_no"])
	# two bills with different supplier bill numbers are two real bills
	rows = [r for r in rows if not R.different_refs(doc.bill_no, r.get("bill_no"))]
	if rows and flt(doc.grand_total):
		_stop(rows, _("same supplier and amount within {0} days").format(R.DAYS))


def _check_sale(doc):
	if not doc.customer or not flt(doc.grand_total):
		return
	_lock("Customer", doc.customer)
	rows = _rows("Sales Invoice", {"customer": doc.customer, "is_return": doc.is_return or 0, "company": doc.company,
		"grand_total": ["between", _amount_range(doc.grand_total)], "posting_date": ["between", _window(doc.posting_date)]},
		"posting_date", "grand_total", doc.name, ["po_no", "project", "remarks"])
	# two Tally invoices with their own numbers in the remarks are two real invoices (checker 7-Nov)
	rows = [r for r in rows if not R.different_refs(R.tally_ref(doc.remarks), R.tally_ref(r.get("remarks")))]
	# identical cabins on one order are billed one by one: another customer PO, another cabin project or other order rows
	# make it a separate invoice
	mine = {i.so_detail for i in doc.items if i.get("so_detail")}

	def separate(r) -> bool:
		if R.different_refs(doc.po_no, r.get("po_no")) or (doc.get("project") and r.get("project") and doc.project != r.get("project")):
			return True
		theirs = set(frappe.get_all("Sales Invoice Item", filters={"parent": r["name"], "so_detail": ["is", "set"]}, pluck="so_detail"))
		return bool(mine and theirs and not mine & theirs)

	rows = [r for r in rows if not separate(r)]
	if rows:
		_stop(rows, _("same customer and amount within {0} days").format(R.DAYS))


def _check_journal(doc):
	if doc.voucher_type in SYSTEM_JE:
		return
	same = _same_ref("Journal Entry", "cheque_no", doc.cheque_no, doc.name)
	same += _same_ref("Payment Entry", "reference_no", doc.cheque_no, None)
	if same:
		_stop(same, _("same reference number {0}").format(doc.cheque_no))
	rows, parties = [], [a for a in doc.accounts if a.party_type and a.party]
	for a in parties:
		_lock(a.party_type, a.party)
		for side in ("debit", "credit"):
			if flt(a.get(side)):
				rows += _je_party_rows(a.party_type, a.party, a.get(side), side, doc.posting_date, doc.name)
				# a payment to a supplier is a debit on the supplier, a receipt from a customer a credit
				if a.party_type in ("Supplier", "Customer", "Employee"):
					rows += _pe_party_rows(a.party_type, a.party, a.get(side), "Pay" if side == "debit" else "Receive",
						doc.posting_date)
	mine_ref = doc.get("bill_no") or doc.cheque_no
	# own voucher numbers of the same kind: two real entries (SK 7-Nov); a bank number never clears a pair (checker 7-Nov)
	rows = [r for r in rows if R.voucher_double(mine_ref, doc.posting_date, r.get("ref"), r.get("date"))]
	if not parties and flt(doc.total_debit):
		# no party (expenses, transfers): same accounts, same amount, same day
		mine = sorted({a.account for a in doc.accounts})
		for r in frappe.get_all("Journal Entry", filters={"docstatus": ["<", 2], "name": ["!=", doc.name or ""],
				"posting_date": doc.posting_date, "total_debit": ["between", _amount_range(doc.total_debit)], "company": doc.company},
				fields=["name", "docstatus", "posting_date as date", "total_debit as amount"], limit=20):
			if sorted(set(frappe.get_all("Journal Entry Account", filters={"parent": r.name}, pluck="account"))) == mine:
				rows.append({**r, "doctype": "Journal Entry"})
	if rows:
		uniq = list({(r["doctype"], r["name"]): r for r in rows}.values())
		_stop(uniq, _("same party and amount within {0} days").format(R.DAYS) if parties else _("same accounts and amount on the same day"))


def check_lead(doc, method=None):
	"""CRM Lead before_insert: the same mobile or e-mail in the last 90 days, or the same name saved twice in 10 minutes."""
	if _skip(doc):
		return
	today = ["between", list(R.day_window(nowdate()))]
	rows = []
	key = R.mobile_key(doc.get("mobile_no"))
	if key:
		rows = frappe.get_all("CRM Lead", filters={"mobile_no": ["like", f"%{key}"], "creation": today, "name": ["!=", doc.name or ""]},
			fields=["name", "creation as date", "first_name", "organization"], limit=3)
	if not rows and (doc.get("email") or "").strip():
		rows = frappe.get_all("CRM Lead", filters={"email": doc.email.strip(), "creation": today, "name": ["!=", doc.name or ""]},
			fields=["name", "creation as date", "first_name", "organization"], limit=3)
	if not rows and (doc.get("organization") or "").strip():
		rows = frappe.get_all("CRM Lead", filters={"organization": doc.organization.strip(), "creation": today, "name": ["!=", doc.name or ""]},
			fields=["name", "creation as date", "first_name", "organization"], limit=3)
	if not rows and doc.get("first_name"):
		rows = frappe.get_all("CRM Lead", filters={"first_name": doc.first_name, "organization": doc.get("organization") or "",
			"creation": [">=", frappe.utils.add_to_date(None, minutes=-10)]}, fields=["name", "creation as date"], limit=3)
	if rows:
		_stop([{**r, "doctype": "CRM Lead", "date": str(r["date"])[:16]} for r in rows], _("same customer"), ok_hint=False)


def check_deal(doc, method=None):
	"""CRM Deal before_insert (Catalyst 27-Oct: CRM-DEAL-2026-00031 / 00032 from one lead 17 seconds apart): one deal per lead."""
	if _skip(doc):
		return
	if doc.get("lead"):
		_lock("CRM Lead", doc.lead)
		rows = frappe.get_all("CRM Deal", filters={"lead": doc.lead}, fields=["name", "creation as date"], limit=3)
		if rows:
			_stop([{**r, "doctype": "CRM Deal", "date": str(r["date"])[:16]} for r in rows], _("this lead already has a deal"), ok_hint=False)
	elif doc.get("organization"):
		rows = frappe.get_all("CRM Deal", filters={"organization": doc.organization, "deal_owner": doc.get("deal_owner") or frappe.session.user,
			"creation": [">=", frappe.utils.add_to_date(None, minutes=-10)]}, fields=["name", "creation as date"], limit=3)
		if rows:
			_stop([{**r, "doctype": "CRM Deal", "date": str(r["date"])[:16]} for r in rows], _("same customer saved twice"), ok_hint=False)


# ---------- layer 4: morning list ----------

def _money_rows(since) -> list[dict]:
	rows = []

	def ok(dt) -> list:
		return [OK_FIELD] if frappe.get_meta(dt).has_field(OK_FIELD) else []

	bank_accounts = set(frappe.get_all("Account", filters={"account_type": "Bank", "is_group": 0}, pluck="name"))
	for r in frappe.get_all("Payment Entry", filters={"docstatus": ["<", 2], "posting_date": [">=", since]},
			fields=["name", "docstatus", "payment_type", "party", "paid_amount", "received_amount", "posting_date", "reference_no",
				"reference_date", "paid_from", "paid_to", *ok("Payment Entry")]):
		pay = r.payment_type == "Pay"
		amount = r.paid_amount if pay else r.received_amount
		rows.append({"doctype": "Payment Entry", "kind": r.payment_type, "name": r.name, "docstatus": r.docstatus, "party": r.party,
			"amount": amount, "date": r.posting_date, "ref": r.reference_no, "ok": r.get(OK_FIELD)})
		# checker 9-Nov (Babasaheb Rs 5,000 PE-00202 = JE-01769): the bank side too, on the bank's date, so a payment entry
		# and a Tally journal for the same transfer meet even when the journal has no party
		bank = r.paid_from if pay else r.paid_to
		if bank in bank_accounts:
			rows.append({"doctype": "Payment Entry", "kind": "bank out" if pay else "bank in", "name": r.name, "docstatus": r.docstatus, "party": bank, "payee": r.party,
				"amount": amount, "date": r.reference_date or r.posting_date, "ref": r.reference_no, "ok": r.get(OK_FIELD)})
	for dt, party in (("Purchase Invoice", "supplier"), ("Sales Invoice", "customer")):
		extra = ["bill_no"] if dt == "Purchase Invoice" else ["remarks"]
		for r in frappe.get_all(dt, filters={"docstatus": ["<", 2], "posting_date": [">=", since]},
				fields=["name", "docstatus", f"{party} as party", "grand_total", "posting_date", "is_return", *ok(dt), *extra]):
			# the bill number within its party: a supplier's bill no, or the Tally invoice no in a migrated sales invoice's remarks
			number = r.get("bill_no") if dt == "Purchase Invoice" else R.tally_ref(r.get("remarks"))
			rows.append({"doctype": dt, "kind": f"{dt} {r.is_return}", "name": r.name, "docstatus": r.docstatus, "party": r.party,
				"amount": r.grand_total, "date": r.posting_date, "ok": r.get(OK_FIELD),
				"ref": f"{r.party} {number}" if number and R.norm_ref(number) else None})
	je_ok = "je." + OK_FIELD if ok("Journal Entry") else "0"
	for r in frappe.db.sql(f"""select je.name, je.docstatus, je.posting_date, ifnull(nullif(je.bill_no, ''), je.cheque_no) as ref, a.party, a.debit, a.credit,
			je.total_debit, {je_ok} as ok
			from `tabJournal Entry` je join `tabJournal Entry Account` a on a.parent = je.name
			where je.docstatus < 2 and je.posting_date >= %s and ifnull(a.party, '') != '' and je.voucher_type not in %s""",
			(since, tuple(SYSTEM_JE)), as_dict=True):
		# a journal debit on a party is a payment to it, a credit a receipt: compared with payment entries too
		amount = flt(r.debit) or flt(r.credit)
		if amount < 10:  # round-off / TDS lines of Rs 0, 1, 2 (checker 7-Nov: 10+ pairs at Rs 0-2) are not money movements
			continue
		kind = "Pay" if flt(r.debit) else "Receive"
		rows.append({"doctype": "Journal Entry", "kind": kind, "name": r.name, "docstatus": r.docstatus, "party": r.party,
			"amount": amount, "total": flt(r.total_debit), "date": r.posting_date, "ref": r.ref, "ok": r.ok})  # Tally voucher no is in bill_no
	# the bank line of every journal (checker 9-Nov): compared with payment entries on the same bank account
	je_payee = {}
	for x in rows:
		if x["doctype"] == "Journal Entry" and x.get("party"):
			je_payee.setdefault(x["name"], x["party"])
	for r in frappe.db.sql(f"""select je.name, je.docstatus, je.posting_date, ifnull(nullif(je.bill_no, ''), je.cheque_no) as ref, a.account, a.debit, a.credit,
			je.user_remark, {je_ok} as ok from `tabJournal Entry` je join `tabJournal Entry Account` a on a.parent = je.name
			join tabAccount acc on acc.name = a.account
			where je.docstatus < 2 and je.posting_date >= %s and acc.account_type = 'Bank' and je.voucher_type not in %s""",
			(since, tuple(SYSTEM_JE)), as_dict=True):
		amount = flt(r.debit) or flt(r.credit)
		if amount < 10:
			continue
		rows.append({"doctype": "Journal Entry", "kind": "bank out" if flt(r.credit) else "bank in", "name": r.name, "docstatus": r.docstatus, "party": r.account,
			"payee": je_payee.get(r.name), "hint": r.user_remark, "amount": amount, "date": r.posting_date, "ref": r.ref, "ok": r.ok})
	return rows


def _bank_in_cash(since) -> list[dict]:
	"""Payments with a bank mode or a bank reference that went through a Cash account (missing in Bank Reconciliation)."""
	return frappe.db.sql("""select pe.name, pe.party, pe.posting_date as date, pe.paid_amount as amount, pe.mode_of_payment, pe.reference_no
		from `tabPayment Entry` pe left join `tabMode of Payment` m on m.name = pe.mode_of_payment
		join `tabAccount` acc on acc.name = if(pe.payment_type = 'Pay', pe.paid_from, pe.paid_to)
		where pe.docstatus = 1 and pe.posting_date >= %s and acc.account_type = 'Cash'
			and (m.type = 'Bank' or pe.mode_of_payment = 'Net Banking' or pe.reference_no regexp '^(IMPS|NEFT|RTGS|UTR|UPI)')
		order by pe.posting_date desc""", (since,), as_dict=True)


def _auto_ticked() -> list[dict]:
	"""Records the one-time patch ticked 'Not a double (checked)' in the last 2 days (checker 7-Nov: list them in the mail)."""
	if not frappe.db.table_exists("SK Rule Log"):
		return []
	return frappe.get_all("SK Rule Log", filters={"rule": "double pair ticked by patch", "creation": [">=", add_days(nowdate(), -2)]},
		fields=["reference_doctype", "reference_name", "detail"], order_by="creation asc", limit=200)


def possible_doubles(since=None) -> dict:
	from erpnext.accounts.utils import get_fiscal_year

	since = since or get_fiscal_year(nowdate())[1]
	pairs = R.find_pairs(_money_rows(since))
	deals = frappe.db.sql("""select lead, group_concat(name order by creation) as names from `tabCRM Deal`
		where ifnull(lead, '') != '' group by lead having count(*) > 1""", as_dict=True) if frappe.db.exists("DocType", "CRM Deal") else []
	from sk_app import masters

	return {"since": str(since), "pairs": pairs, "deals": deals, "bank_in_cash": _bank_in_cash(since), "auto_ticked": _auto_ticked(),
		"masters": masters.changed_since(), "master_problems": masters.audit_masters_only()}


def _row_html(r) -> str:
	# a journal shows its voucher total, with the party line when it differs (checker 7-Nov: JE-01718 is Rs 28,000, mail said 20,650)
	amount = f"₹{flt(r.get('total')):,.0f}" if r.get("total") else f"₹{flt(r.get('amount')):,.0f}"
	if r.get("total") and abs(flt(r["total"]) - flt(r.get("amount"))) >= 1:
		amount += f" (party line ₹{flt(r.get('amount')):,.0f})"
	return "{0} {1} · {2} · {3} · {4}{5}{6}".format(r["doctype"], _link(r["doctype"], r["name"]), r.get("party") or "", amount,
		r.get("date") or "", f" · {r['ref']}" if r.get("ref") else "", " (draft)" if r.get("docstatus") == 0 else "")


def report_html(found: dict) -> str:
	parts = [f"<p>Possible double entries in ERPNext since {found['since']}. Please open each pair, cancel the wrong one, "
		"or tick 'Not a double (checked)' on it if both are right (then it is not listed again).</p>"]
	if found["pairs"]:
		parts.append("<ol>" + "".join(f"<li>{_row_html(p['first'])}<br>{_row_html(p['second'])}<br><i>{p['why']}</i></li>"
			for p in found["pairs"]) + "</ol>")
	if found["deals"]:
		parts.append("<p><b>Leads with more than one deal</b> (keep one, mark the other Lost / delete the draft):</p><ul>" + "".join(
			"<li>{0}: {1}</li>".format(_link("CRM Lead", d.lead), ", ".join(_link("CRM Deal", n) for n in d.names.split(",")))
			for d in found["deals"]) + "</ul>")
	if found["bank_in_cash"]:
		parts.append("<p><b>Bank payments booked through Cash</b> (they never show in Bank Reconciliation: cancel, amend and choose "
			"the bank account):</p><ul>" + "".join("<li>{0} · {1} · ₹{2:,.0f} · {3} · {4}</li>".format(_link("Payment Entry", r.name),
			r.party or "", flt(r.amount), r.date, r.mode_of_payment or r.reference_no or "") for r in found["bank_in_cash"]) + "</ul>")
	if found.get("auto_ticked"):
		parts.append("<p><b>Ticked 'Not a double' by the SK App update</b> (two entries with their own Tally / bill numbers; untick "
			"if one is wrong):</p><ul>" + "".join("<li>{0} {1} · {2}</li>".format(r["reference_doctype"], _link(r["reference_doctype"],
			r["reference_name"]), r["detail"] or "") for r in found["auto_ticked"]) + "</ul>")
	if found.get("master_problems"):
		parts.append("<p><b>Account masters set up wrong</b> (where money is booked):</p><ul>" + "".join(
			f'<li><a href="{r["link"]}">{r["what"]}</a>: {r["problem"]}</li>' for r in found["master_problems"]) + "</ul>")
	if found.get("masters"):
		parts.append("<p><b>Account masters changed since yesterday</b> (check each change is right):</p><ul>" + "".join(
			"<li>{0} {1} · by {2} · {3}</li>".format(r["doctype"], _link(r["doctype"], r["name"]), r["by"], str(r["modified"])[:16])
			for r in found["masters"]) + "</ul>")
	return "".join(parts)


def _recipients() -> list[str]:
	from sk_app.mailbox import people_of
	from sk_app.requisition import _ceos

	users = [p.user for p in people_of("acc@skind.tech")] + list(_ceos())
	return sorted({u for u in users if u and u not in ("Administrator", "Guest")})


def morning():
	"""Scheduler, every morning: the list of possible doubles to Accounts (Shraddha) and the CEO (SK). Nothing found, no mail."""
	found = possible_doubles()
	count = sum(len(found.get(k) or []) for k in ("pairs", "deals", "bank_in_cash", "masters", "master_problems", "auto_ticked"))
	if not count:
		return 0
	subject = _("SK App: {0} possible double / wrong entries to check").format(count)
	users = _recipients()
	from sk_app.mailbox import _notify

	_notify(users, subject)
	emails = [e for e in (frappe.db.get_value("User", u, "email") for u in users) if e]
	if emails:
		from sk_app.otp import _sender

		frappe.sendmail(recipients=emails, sender=_sender(), subject=subject, message=report_html(found), now=False)
	return count
