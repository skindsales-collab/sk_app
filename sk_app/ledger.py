"""Ledger-wise Accounts screens (SK / Shraddha, 26-Oct-2026): Cash / Bank, Receivables, Payables, Purchase Invoice and
Debit Note, Sales Invoice and Credit Note, Journal Voucher, Direct and Indirect Expenses, Segment Wise P&L (Cabin /
Non-Cabin net) and the Month Wise Report. Every list is one row per ledger (account or party) for the month; tapping a
row shows its entries, read straight from ERPNext's General Ledger.
"""

import frappe
from frappe import _
from frappe.utils import add_months, flt, get_first_day, get_last_day, getdate, nowdate

from sk_app.store import _company, need

ACCOUNTS = "Accounts"
MANAGEMENT = "Management"
MACHINE_SHIFTING = "Machine Shifting"
KINDS = ("bank", "receivable", "payable", "purchase", "sales", "journal", "expenses")
CABIN, NON_CABIN, COMMON = "Cabin", "Non-Cabin", "Common"
# cost centres of each segment (SK: SGSF / LGSF and modular are Cabin; machine shifting and job work are Non-Cabin)
CABIN_CC = ("Portable Cabin",)
NON_CABIN_CC = ("Machine Shifting", "Machine Maintenance")


def _month(month=None):
	start = get_first_day(getdate(month or nowdate()))
	return start, get_last_day(start)


def _accounts(**filters) -> list[str]:
	return frappe.get_all("Account", filters={"company": _company(), "is_group": 0, **filters}, pluck="name")


def _gl_by(field: str, start, end, **filters) -> list[dict]:
	"""Opening, debit, credit and closing per ledger (account or party) for the month."""
	company = _company()
	cond, args = ["company = %(company)s", "is_cancelled = 0"], {"company": company, "start": start, "end": end}
	for i, (k, v) in enumerate(filters.items()):
		if isinstance(v, (list, tuple)):
			cond.append(f"`{k}` in %(f{i})s")
		else:
			cond.append(f"`{k}` = %(f{i})s")
		args[f"f{i}"] = tuple(v) if isinstance(v, (list, tuple)) else v
	if field == "party":
		cond.append("ifnull(party, '') != ''")
	where = " and ".join(cond)
	return frappe.db.sql(f"""
		select `{field}` as ledger,
			sum(case when posting_date < %(start)s then debit - credit else 0 end) as opening,
			sum(case when posting_date between %(start)s and %(end)s then debit else 0 end) as debit,
			sum(case when posting_date between %(start)s and %(end)s then credit else 0 end) as credit
		from `tabGL Entry` where {where} and posting_date <= %(end)s
		group by `{field}` order by `{field}`""", args, as_dict=True)


def _close(rows):
	for r in rows:
		r["closing"] = flt(r.opening) + flt(r.debit) - flt(r.credit)
	return rows


def ledgers(user: str, kind: str, month=None) -> dict:
	"""One row per ledger for the month, with totals."""
	need(user, ACCOUNTS, MANAGEMENT)
	if kind not in KINDS:
		frappe.throw(_("Unknown list"))
	start, end = _month(month)
	if kind == "bank":
		accts = _accounts(account_type=["in", ["Bank", "Cash"]], disabled=0)
		rows = _close(_gl_by("account", start, end, account=accts)) if accts else []
		have = {r.ledger for r in rows}
		rows += [frappe._dict(ledger=a, opening=0, debit=0, credit=0, closing=0) for a in accts if a not in have]
	elif kind in ("receivable", "payable"):
		accts = _accounts(account_type="Receivable" if kind == "receivable" else "Payable")
		rows = _close(_gl_by("party", start, end, account=accts)) if accts else []
		rows = [r for r in rows if abs(flt(r.closing)) > 0.5 or flt(r.debit) or flt(r.credit)]
		if kind == "payable":
			for r in rows:  # suppliers: show what we owe as a plus amount
				r["opening"], r["closing"] = -flt(r.opening), -flt(r.closing)
		rows.sort(key=lambda r: -abs(flt(r.closing)))
	elif kind in ("purchase", "sales"):
		dt, party = ("Purchase Invoice", "supplier") if kind == "purchase" else ("Sales Invoice", "customer")
		docs = frappe.get_all(dt, filters={"company": _company(), "docstatus": ["<", 2], "posting_date": ["between", [start, end]]},
			fields=["name", party, f"{party}_name as party_name", "is_return", "grand_total", "docstatus"], limit=2000)
		by = {}
		for d in docs:
			r = by.setdefault(d[party], frappe._dict(ledger=d[party], title=d.party_name, bills=0, returns=0, count=0, drafts=0))
			r.count += 1
			r.drafts += 1 if d.docstatus == 0 else 0
			if d.is_return:
				r.returns += abs(flt(d.grand_total))
			else:
				r.bills += flt(d.grand_total)
		rows = sorted(by.values(), key=lambda r: -r.bills)
		for r in rows:
			r["net"] = r.bills - r.returns
	elif kind == "journal":
		rows = _gl_by("account", start, end, voucher_type="Journal Entry")
		rows = [r for r in rows if flt(r.debit) or flt(r.credit)]
	else:  # expenses: every expense ledger under Direct / Indirect Expenses
		rows = _expense_rows(start, end)
	return {"kind": kind, "from": str(start), "to": str(end), "rows": rows,
		"total": {k: sum(flt(r.get(k)) for r in rows) for k in ("opening", "debit", "credit", "closing", "bills", "returns", "net", "amount")}}


def _expense_groups() -> dict:
	"""{account: (Direct / Indirect, Cabin / Non-Cabin / Common)} from the chart of accounts."""
	company = _company()
	groups = frappe.get_all("Account", filters={"company": company, "root_type": "Expense", "is_group": 1}, fields=["name", "lft", "rgt"])
	out = {}
	for a in frappe.get_all("Account", filters={"company": company, "root_type": "Expense", "is_group": 0}, fields=["name", "lft"]):
		inside = [g.name for g in groups if g.lft < a.lft < g.rgt]
		kind = "Indirect" if any("indirect" in g.lower() for g in inside) else "Direct"
		seg = _segment_of_names([a.name] + inside)
		if not seg and any(g.startswith("Purchase Accounts") for g in inside):
			seg = CABIN  # SK 28-Oct "split all data as Cabin & Non-Cabin": a purchase not marked Non-Cabin is factory (cabin) material
		out[a.name] = (kind, seg)
	return out


def _segment_of_names(names) -> str | None:
	for n in names:
		low = n.lower()
		if "non cabin" in low or "non-cabin" in low or "noncabin" in low:
			return NON_CABIN
		if "cabin" in low:
			return CABIN
	return None


def _expense_rows(start, end) -> list[dict]:
	kinds = _expense_groups()
	rows = _gl_by("account", start, end, account=list(kinds) or [""])
	out = []
	for r in rows:
		amount = flt(r.debit) - flt(r.credit)
		if not amount:
			continue
		kind, seg = kinds.get(r.ledger, ("Direct", None))
		out.append(frappe._dict(ledger=r.ledger, group=kind, segment=seg or COMMON, amount=amount))
	out.sort(key=lambda r: (r.group, -r.amount))
	return out


def entries(user: str, kind: str, ledger: str, month=None) -> dict:
	"""The ledger's entries for the month (General Ledger lines, or the bills for Purchase / Sales)."""
	need(user, ACCOUNTS, MANAGEMENT)
	start, end = _month(month)
	company = _company()
	if kind in ("purchase", "sales"):
		dt, party = ("Purchase Invoice", "supplier") if kind == "purchase" else ("Sales Invoice", "customer")
		rows = frappe.get_all(dt, filters={"company": company, party: ledger, "docstatus": ["<", 2], "posting_date": ["between", [start, end]]},
			fields=["name", "posting_date", "is_return", "grand_total", "outstanding_amount", "docstatus", "status"], order_by="posting_date asc")
		for r in rows:
			r["doctype"] = dt
		return {"ledger": ledger, "rows": rows}
	filters = {"company": company, "is_cancelled": 0, "posting_date": ["between", [start, end]]}
	if kind in ("receivable", "payable"):
		filters["party"] = ledger
		filters["account"] = ["in", _accounts(account_type="Receivable" if kind == "receivable" else "Payable") or [""]]
	else:
		filters["account"] = ledger
		if kind == "journal":
			filters["voucher_type"] = "Journal Entry"
	opening = flt(frappe.db.sql("""select sum(debit - credit) from `tabGL Entry` where company = %s and is_cancelled = 0
		and posting_date < %s and """ + ("party = %s and account in %s" if "party" in filters else "account = %s"),
		(company, start, ledger, tuple(filters["account"][1])) if "party" in filters else (company, start, ledger))[0][0])
	rows = frappe.get_all("GL Entry", filters=filters, fields=["posting_date", "voucher_type", "voucher_no", "debit", "credit",
		"against", "remarks", "party"], order_by="posting_date asc, creation asc", limit=0)
	bal = opening
	for r in rows:
		bal += flt(r.debit) - flt(r.credit)
		r["balance"] = bal
		r["doctype"] = r.voucher_type
		r["name"] = r.voucher_no
		r["remarks"] = (r.remarks or "")[:120]
	sign = -1 if kind == "payable" else 1
	return {"ledger": ledger, "opening": opening * sign, "closing": bal * sign, "rows": rows, "sign": sign}


def _segment_of(account_segment: str | None, cost_center: str | None, cc_parents: dict) -> str:
	if account_segment:
		return account_segment
	cc = cost_center
	while cc:
		short = cc.rsplit(" - ", 1)[0]
		if short in CABIN_CC:
			return CABIN
		if short in NON_CABIN_CC:
			return NON_CABIN
		cc = cc_parents.get(cc)
	return COMMON


def _pnl_lines(start, end) -> list[dict]:
	return frappe.db.sql("""
		select gle.account, gle.cost_center, acc.root_type, date_format(gle.posting_date, '%%Y-%%m') as month,
			sum(gle.credit - gle.debit) as income, sum(gle.debit - gle.credit) as cost
		from `tabGL Entry` gle join `tabAccount` acc on acc.name = gle.account
		where gle.company = %s and gle.is_cancelled = 0 and gle.posting_date between %s and %s
			and acc.root_type in ('Income', 'Expense')
		group by gle.account, gle.cost_center, acc.root_type, month""", (_company(), start, end), as_dict=True)


def segment_wise(user: str, month=None) -> dict:
	"""Cabin net P&L and Non-Cabin net P&L for the month (shared costs shown apart as Common), like Tally."""
	need(user, ACCOUNTS, MANAGEMENT)
	start, end = _month(month)
	cc_parents = {c.name: c.parent_cost_center for c in frappe.get_all("Cost Center", fields=["name", "parent_cost_center"])}
	kinds = _expense_groups()
	seg = {s: frappe._dict(segment=s, income=0.0, direct=0.0, indirect=0.0) for s in (CABIN, NON_CABIN, COMMON)}
	for r in _pnl_lines(start, end):
		if r.root_type == "Income":
			s = _segment_of(_segment_of_names([r.account]), r.cost_center, cc_parents)
			seg[s].income += flt(r.income)
		else:
			kind, aseg = kinds.get(r.account, ("Direct", None))
			s = _segment_of(aseg, r.cost_center, cc_parents)
			seg[s]["direct" if kind == "Direct" else "indirect"] += flt(r.cost)
	rows = list(seg.values())
	for r in rows:
		r["gross"] = r.income - r.direct
		r["net"] = r.gross - r.indirect
		r["net_pct"] = round(r.net / r.income * 100, 1) if r.income else None
	return {"from": str(start), "to": str(end), "rows": rows,
		"total": {k: sum(flt(r[k]) for r in rows) for k in ("income", "direct", "indirect", "gross", "net")}}


def month_wise(user: str, year_start=None) -> dict:
	"""All P&L, one row per month of the financial year (April to now): income, direct and indirect cost, net.
	Each row also carries the same figures per segment (Cabin / Non-Cabin / Common), as Tally's segment P&L per month."""
	need(user, ACCOUNTS, MANAGEMENT, MACHINE_SHIFTING)
	# SK 28-Oct "link Aditya to Non-Cabin": Machine Shifting (Aditya) sees the Non-Cabin segment only
	only = None if _sees_all(user) else NON_CABIN
	today = getdate()
	fy = getdate(year_start) if year_start else getdate(f"{today.year if today.month >= 4 else today.year - 1}-04-01")
	end = min(get_last_day(add_months(fy, 11)), get_last_day(today))
	kinds = _expense_groups()
	cc_parents = {c.name: c.parent_cost_center for c in frappe.get_all("Cost Center", fields=["name", "parent_cost_center"])}
	blank = lambda: frappe._dict(income=0.0, direct=0.0, indirect=0.0)
	months = {}
	m = fy
	while m <= end:
		months[str(m)[:7]] = frappe._dict(month=str(m)[:7], income=0.0, direct=0.0, indirect=0.0,
			segments={s: blank() for s in (CABIN, NON_CABIN, COMMON)})
		m = add_months(m, 1)
	for r in _pnl_lines(fy, end):
		row = months.get(r.month)
		if not row:
			continue
		if r.root_type == "Income":
			field, amount = "income", flt(r.income)
			s = _segment_of(_segment_of_names([r.account]), r.cost_center, cc_parents)
		else:
			kind, aseg = kinds.get(r.account, ("Direct", None))
			field, amount = ("direct" if kind == "Direct" else "indirect"), flt(r.cost)
			s = _segment_of(aseg, r.cost_center, cc_parents)
		row[field] += amount
		row.segments[s][field] += amount
	rows = list(months.values())
	for r in rows:
		for x in [r, *r.segments.values()]:
			x["gross"] = x.income - x.direct
			x["net"] = x.gross - x.indirect
	keys = ("income", "direct", "indirect", "gross", "net")
	if only:
		rows = [frappe._dict(month=r.month, **r.segments[only], segments={only: r.segments[only]}) for r in rows]
	segs = (only,) if only else (CABIN, NON_CABIN, COMMON)
	return {"from": str(fy), "to": str(end), "rows": rows, "total": {k: sum(flt(r[k]) for r in rows) for k in keys},
		"segment_total": {s: {k: sum(flt(r.segments[s][k]) for r in rows) for k in keys} for s in segs}, "only": only}


def _sees_all(user: str) -> bool:
	if "System Manager" in frappe.get_roles(user):
		return True
	from sk_app import logins

	return bool({ACCOUNTS, MANAGEMENT} & set(logins.profile_functions(user)))
