"""CEO live dashboards on the phone (change list point 13, SK 26-Oct-2026: "Add all live dashboard").

One page per function, built live from ERPNext each time it is opened (no copy of the numbers): Overview, Daily
Review, Sales, Marketing, Machine Shifting, Job Work, 100 Cr, Finance, Manufacturing, Purchase, Store, Quality, HR
and AI & ERP. Every number opens its list and every row opens the full record (3 taps deep). Filters: month,
Cabin / Non-Cabin; each money card also shows last month. Only Management (Sunil, SK) can open them.
"""

import frappe
from frappe import _
from frappe.utils import add_days, add_months, date_diff, flt, get_first_day, get_last_day, getdate, now_datetime, nowdate

from sk_app import segments

PAGES = [
	("overview", "CEO Overview", "CEO आढावा", "🏁"), ("daily_review", "Daily Review", "दैनिक आढावा", "🗓️"),
	("sales", "Sales", "विक्री", "💼"), ("marketing", "Marketing", "मार्केटिंग", "📣"),
	("machine_shifting", "Machine Shifting", "मशीन शिफ्टिंग", "🏗️"), ("job_work", "Job Work", "जॉब वर्क", "⚙️"),
	("finance", "Finance", "वित्त", "💰"),
	("manufacturing", "Manufacturing", "उत्पादन", "🏭"), ("purchase", "Purchase", "खरेदी", "🛒"),
	("store", "Store", "स्टोअर", "📦"), ("quality", "Quality", "गुणवत्ता", "✅"), ("hr", "HR", "एचआर", "👥"),
	("ai", "AI & ERP", "AI आणि ERP", "🤖"),
	("cr100", "100 Cr", "100 कोटी", "🎯"),  # SK 26-Oct: "100 Cr on the second screen, not the first"
]
PAGE_KEYS = [p[0] for p in PAGES]
GOAL_CR, GOAL_FY = 100, 2030  # SK: Rs 100 Cr sales in FY 2030-31
CRORE, LAKH = 1e7, 1e5


def check(user: str):
	from sk_app.logins import profile_functions

	if user != "Administrator" and "Management" not in profile_functions(user):
		frappe.throw(_("Only the CEO can open the live dashboards"), frappe.PermissionError)


def _safe(fn, default=None):
	"""A page never fails because one part of ERPNext is not set up yet: that card shows "—"."""
	try:
		return fn()
	except Exception:
		frappe.log_error("SK App dashboard card")
		return default


def _has(doctype: str) -> bool:
	return bool(frappe.db.exists("DocType", doctype))


def _period(month=None):
	start = get_first_day(getdate(month) if month else getdate())
	end = get_last_day(start)
	prev = add_months(start, -1)
	return start, end, prev, get_last_day(prev)


def _sum(doctype: str, field: str, filters) -> float:
	return sum(flt(v) for v in frappe.get_all(doctype, filters=filters, pluck=field))


def _seg_filter(segment: str | None, field: str = "customer_group") -> dict:
	if segment in segments.TREE:
		return {field: ["in", segments.groups_of(segment)]}
	if segment in segments.SUB_SEGMENTS:
		return {field: segments.GROUP_OF[segment]}
	return {}


def _crm_seg(segment: str | None) -> dict:
	if segment in segments.TREE:
		return {"sk_main_segment": segment}
	if segment in segments.SUB_SEGMENTS:
		return {"sk_segment": segment}
	return {}


def _row(title, meta=None, value=None, doctype=None, name=None, c=None) -> dict:
	return {"title": str(title or name or ""), "meta": meta or "", "value": value, "doctype": doctype, "name": name, "c": c}


def _card(key, label, value, kind="count", prev=None, rows=None, c=None) -> dict:
	return {"key": key, "label": label, "value": value, "kind": kind, "prev": prev, "rows": rows, "c": c}


# ---------- shared pieces ----------

def _invoiced(start, end, segment=None) -> float:
	return _sum("Sales Invoice", "base_net_total", {"docstatus": 1, "is_return": 0, "posting_date": ["between", [start, end]],
		**_seg_filter(segment)}) + sum(r.amount for r in _tally_sales(start, end, segment))


TALLY_SALES = ("Tally Sales %", "Tally Non Cabin Sales %", "Tally Credit Note %")


def _tally_sales(start, end, segment=None) -> list:
	"""SK 26-Oct: until change list point 18 turns them into Sales Invoices, the year's sales came from Tally as Journal
	Entries ("Tally Sales 825 | party"). Their income-account amount (before GST) counts as sales; credit notes reduce it.
	Once point 18 cancels them for real invoices they drop out here by themselves (only posted entries count)."""
	jes = frappe.get_all("Journal Entry", filters={"docstatus": 1, "posting_date": ["between", [start, end]]},
		or_filters=[["user_remark", "like", w] for w in TALLY_SALES], fields=["name", "posting_date", "user_remark"], limit=0)
	if not jes:
		return []
	income = set(frappe.get_all("Account", filters={"root_type": "Income"}, pluck="name"))
	amounts = {}
	for a in frappe.get_all("Journal Entry Account", filters={"parent": ["in", [j.name for j in jes]], "account": ["in", list(income) or [""]]},
			fields=["parent", "credit", "debit"], limit=0):
		amounts[a.parent] = amounts.get(a.parent, 0) + flt(a.credit) - flt(a.debit)
	out = []
	for j in jes:
		remark = j.user_remark or ""
		main = segments.NON_CABIN if "non cabin" in remark.lower() else segments.CABIN
		if segment in segments.TREE and segment != main:
			continue
		party = remark.split("|", 1)[1].strip() if "|" in remark else remark
		out.append(frappe._dict(name=j.name, posting_date=j.posting_date, customer_name=party[:80], amount=amounts.get(j.name, 0),
			voucher=remark.split("|", 1)[0].replace("Tally", "").strip()))
	return out


def _orders(start, end, segment=None) -> list:
	# DEC-013 (SK 25-Oct): the draft Sales Orders are real orders; only cancelled ones are left out
	return frappe.get_all("Sales Order", filters={"docstatus": ["<", 2], "transaction_date": ["between", [start, end]], **_seg_filter(segment)},
		fields=["name", "customer_name", "base_net_total", "transaction_date", "customer_group", "delivery_date", "docstatus"],
		order_by="base_net_total desc", limit=500)


def _orders_card(start, end, prev_start, prev_end, segment=None, key="orders"):
	rows = _orders(start, end, segment)
	prev = sum(flt(r.base_net_total) for r in _orders(prev_start, prev_end, segment))
	return _card(key, "Orders this month", sum(flt(r.base_net_total) for r in rows), "money", prev,
		[_row(r.customer_name, f"{r.transaction_date} · {segments.SEGMENT_OF_GROUP.get(r.customer_group) or r.customer_group or ''}"
			f"{' · draft' if r.docstatus == 0 else ''}",
			r.base_net_total, "Sales Order", r.name) for r in rows[:50]])


def _sales_card(start, end, prev_start, prev_end, segment=None):
	rows = frappe.get_all("Sales Invoice", filters={"docstatus": 1, "is_return": 0, "posting_date": ["between", [start, end]], **_seg_filter(segment)},
		fields=["name", "customer_name", "base_net_total", "posting_date"], order_by="base_net_total desc", limit=50)
	tally = sorted(_tally_sales(start, end, segment), key=lambda r: -r.amount)
	return _card("sales", "Sales (invoiced, before GST)", _invoiced(start, end, segment), "money", _invoiced(prev_start, prev_end, segment),
		[_row(r.customer_name, str(r.posting_date), r.base_net_total, "Sales Invoice", r.name) for r in rows]
		+ [_row(r.customer_name, f"{r.posting_date} · Tally {r.voucher}", r.amount, "Journal Entry", r.name) for r in tally[:80]])


def _party_dues(party_type: str, segment=None) -> list:
	"""Dues per customer / supplier from the General Ledger (SK 26-Oct trial: the year's bills came from Tally as Journal
	Entries, so the invoices' outstanding showed Rs 23.6 L of the Rs 71.7 L really owed). Payments are set against the
	oldest bills first; "late" is the age of the oldest bill still unpaid. Advances (minus balances) are left out."""
	from sk_app.store import _company

	company = _company()
	accts = frappe.get_all("Account", filters={"company": company, "is_group": 0,
		"account_type": "Receivable" if party_type == "Customer" else "Payable"}, pluck="name")
	if not accts:
		return []
	sign = 1 if party_type == "Customer" else -1
	lines = frappe.db.sql("""select party, posting_date, sum(debit - credit) as amount from `tabGL Entry`
		where company = %s and is_cancelled = 0 and party_type = %s and ifnull(party, '') != '' and account in %s
		group by party, posting_date, voucher_no order by posting_date""", (company, party_type, tuple(accts)), as_dict=True)
	by = {}
	for line in lines:
		by.setdefault(line.party, []).append((line.posting_date, sign * flt(line.amount)))
	name_field = "customer_name" if party_type == "Customer" else "supplier_name"
	group_field = "customer_group" if party_type == "Customer" else "supplier_group"
	allowed = None
	if party_type == "Customer" and segment:
		allowed = set(frappe.get_all("Customer", filters=_seg_filter(segment), pluck="name"))
	today = getdate()
	out = []
	for party, items in by.items():
		if allowed is not None and party not in allowed:
			continue
		paid = sum(-a for _d, a in items if a < 0)
		open_bills = []
		for d, a in items:
			if a <= 0:
				continue
			use = min(a, paid)
			paid -= use
			if a - use > 0.5:
				open_bills.append((getdate(d), a - use))
		due = sum(a for _d, a in open_bills)
		if due <= 0.5:
			continue
		late = date_diff(today, open_bills[0][0])
		ages = {"0-30 days": 0.0, "31-60 days": 0.0, "Over 60 days": 0.0}
		for d, a in open_bills:
			days = date_diff(today, d)
			ages["0-30 days" if days <= 30 else "31-60 days" if days <= 60 else "Over 60 days"] += a
		out.append(frappe._dict(name=party, party=party, outstanding_amount=due, late=late, ages=ages))
	names = {r.name: r[name_field] for r in frappe.get_all(party_type, filters={"name": ["in", [o.name for o in out] or [""]]},
		fields=["name", name_field, group_field])}
	for o in out:
		o[name_field] = o["customer_name"] = names.get(o.name) or o.name
	out.sort(key=lambda r: -r.late)
	return out


def _receivables(segment=None):
	return _party_dues("Customer", segment)


def _receivables_card(segment=None):
	rows = _receivables(segment)
	return _card("receivables", "Receivables", sum(flt(r.outstanding_amount) for r in rows), "money", None,
		[_row(r.customer_name, f"oldest bill {r.late} days", r.outstanding_amount, "Customer", r.name,
			"red" if r.late > 60 else "amber" if r.late > 30 else None) for r in sorted(rows, key=lambda r: -r.outstanding_amount)[:60]])


def _payables_card(key="payables", label="Payables (supplier dues)"):
	rows = _party_dues("Supplier")
	return _card(key, label, sum(flt(r.outstanding_amount) for r in rows), "money", None,
		[_row(r.supplier_name, f"oldest bill {r.late} days", r.outstanding_amount, "Supplier", r.name,
			"red" if r.late > 60 else "amber" if r.late > 30 else None) for r in sorted(rows, key=lambda r: -r.outstanding_amount)[:60]])


def _cash_card():
	from erpnext.accounts.utils import get_balance_on

	from sk_app.store import _company

	company = _company()
	accounts = frappe.get_all("Account", filters={"company": company, "is_group": 0, "account_type": ["in", ["Bank", "Cash"]], "disabled": 0},
		fields=["name", "account_name"])
	rows = [_row(a.account_name, "", flt(get_balance_on(account=a.name, date=nowdate(), company=company)), "Account", a.name) for a in accounts]
	return _card("cash", "Cash & bank now", sum(r["value"] for r in rows), "money", None, rows)


def _open_deal_statuses() -> list[str]:
	return frappe.get_all("CRM Deal Status", filters={"type": ["not in", ["Won", "Lost"]]}, pluck="name")


def _pipeline_card(segment=None):
	rows = frappe.get_all("CRM Deal", filters={"status": ["in", _open_deal_statuses() or [""]], **_crm_seg(segment)},
		fields=["name", "organization", "deal_value", "status", "deal_owner", "sk_segment"], order_by="deal_value desc", limit=300)
	value = sum(flt(r.deal_value) for r in rows)
	# deals made from leads have no value until the quotation: then show how many are open instead of Rs 0
	return _card("pipeline", "Open deals (pipeline)" if value else "Open deals (no value yet)", value or len(rows), "money" if value else "count", None,
		[_row(r.organization or r.name, f"{r.status} · {_name(r.deal_owner)}{' · ' + r.sk_segment if r.sk_segment else ''}", r.deal_value,
			"CRM Deal", r.name) for r in rows[:60]])


def _leads(start, end, segment=None, extra=None) -> list:
	return frappe.get_all("CRM Lead", filters={"creation": ["between", [f"{start} 00:00:00", f"{end} 23:59:59"]], **_crm_seg(segment), **(extra or {})},
		fields=["name", "first_name", "organization", "source", "status", "lead_owner", "creation", "sk_segment", "first_responded_on"],
		order_by="creation desc", limit=500)


def _leads_card(start, end, prev_start, prev_end, segment=None, key="leads", label="New leads this month"):
	rows = _leads(start, end, segment)
	return _card(key, label, len(rows), "count", len(_leads(prev_start, prev_end, segment)),
		[_row(r.organization or r.first_name, f"{r.source or ''} · {r.status} · {_name(r.lead_owner)}", None, "CRM Lead", r.name,
			None if r.first_responded_on else "red") for r in rows[:80]])


_names = {}


def _name(user):
	if not user:
		return ""
	if user not in _names:
		_names[user] = frappe.utils.get_fullname(user)
	return _names[user]


def _not_contacted():
	"""Leads more than a day old that nobody has called / written yet."""
	if not _has("CRM Lead"):
		return []
	closed = frappe.get_all("CRM Lead Status", filters={"type": ["in", ["Won", "Lost", "Junk"]]}, pluck="name")
	return frappe.get_all("CRM Lead", filters={"first_responded_on": ["is", "not set"], "status": ["not in", closed or [""]],
		"creation": ["<", add_days(now_datetime(), -1)]}, fields=["name", "first_name", "organization", "lead_owner", "creation"],
		order_by="creation asc", limit=100)


def _late_orders(segment=None):
	return frappe.get_all("Sales Order", filters={"docstatus": ["<", 2], "delivery_date": ["<", nowdate()], "per_delivered": ["<", 100],
		"status": ["not in", ["Closed", "Completed", "On Hold"]], **_seg_filter(segment)},
		fields=["name", "customer_name", "delivery_date", "base_net_total"], order_by="delivery_date asc", limit=100)


def _targets(code="orders_value", users=None) -> dict:
	filters = {"active": 1, "kpi_code": code}
	if users is not None:
		filters["user"] = ["in", users or [""]]
	return {r.user: flt(r.monthly_target) for r in frappe.get_all("SK KPI Target", filters=filters, fields=["user", "monthly_target"])}


def _team_scorecard(start, end, users=None):
	from sk_app.kpi import _sum_orders, user_sales_orders

	targets = _targets(users=users)
	rows = []
	for user, target in sorted(targets.items(), key=lambda x: -x[1]):
		actual = _sum_orders(user_sales_orders(user, start, end))
		pct = round(actual * 100 / target) if target else 0
		rows.append(_row(_name(user), f"target {round(target / LAKH, 1)} L · {pct}%", actual, "User", user,
			"green" if pct >= 100 else "amber" if pct >= 60 else "red"))
	return rows


# ---------- month-wise charts (SK 26-Oct: "need graphical", like SK's Excel: target line vs actual, FY cumulative) ----------

def _fy_start(day=None):
	d = getdate(day)
	return getdate(f"{d.year if d.month >= 4 else d.year - 1}-04-01")


def _fy_labels(fy):
	return [f"{add_months(fy, i):%b}" for i in range(12)]


def _bucket(rows, date_field, value) -> dict:
	out = {}
	for r in rows:
		k = str(r.get(date_field))[:7]
		out[k] = out.get(k, 0.0) + flt(value(r))
	return out


def _fy_values(fy, by_month: dict) -> list:
	"""12 values Apr..Mar from {"YYYY-MM": value}; months still to come are None (no zero line into the future)."""
	this = str(getdate())[:7]
	vals = []
	for i in range(12):
		k = str(add_months(fy, i))[:7]
		vals.append(None if k > this else round(flt(by_month.get(k)) / LAKH, 1))
	return vals


def _invoice_months(fy, segment=None) -> dict:
	end = get_last_day(add_months(fy, 11))
	inv = frappe.get_all("Sales Invoice", filters={"docstatus": 1, "is_return": 0, "posting_date": ["between", [fy, end]], **_seg_filter(segment)},
		fields=["posting_date", "base_net_total"], limit=0)
	out = _bucket(inv, "posting_date", lambda r: r.base_net_total)
	for k, v in _bucket(_tally_sales(fy, end, segment), "posting_date", lambda r: r.amount).items():
		out[k] = out.get(k, 0.0) + v
	return out


def _order_months(fy, segment=None) -> dict:
	return _bucket(_orders(fy, get_last_day(add_months(fy, 11)), segment), "transaction_date", lambda r: r.base_net_total)


def _chart(key, label, fy, series, target=None, unit="L", bars=False, value=None, rows=None, c=None) -> dict:
	"""A month-wise chart card: series = [(name, colour, values)], target = monthly target line (same unit)."""
	return {"key": key, "label": label, "kind": "chart", "value": value, "unit": unit, "bars": bars, "labels": _fy_labels(fy),
		"series": [{"name": n, "c": col, "values": v} for n, col, v in series], "target": target, "rows": rows or [], "c": c, "prev": None}


def _cum(vals) -> float:
	return round(sum(v for v in vals if v), 1)


def _month_rows(fy, series) -> list:
	labels = _fy_labels(fy)
	return [_row(f"{labels[i]} {add_months(fy, i):%y}", " · ".join(f"{n} {v[i]} L" for n, _c, v in series if v[i] is not None))
		for i in range(12) if any(v[i] is not None for _n, _c, v in series)]


def _overview_charts(segment=None) -> list:
	fy = _fy_start()
	target = round(sum(_targets().values()) / LAKH, 1) or None
	total = _fy_values(fy, _invoice_months(fy, segment))
	cab = _fy_values(fy, _invoice_months(fy, segments.CABIN))
	non = _fy_values(fy, _invoice_months(fy, segments.NON_CABIN))
	book = _fy_values(fy, _order_months(fy, segment))
	inv_series = [("Invoice", "orange", total)]
	seg_series = [("Cabin", "teal", cab), ("Non-Cabin", "purple", non)]
	return [
		_chart("inv_chart", f"Invoice by month · FY so far ₹{_cum(total)} L", fy, inv_series, target, value=_cum(total), rows=_month_rows(fy, inv_series)),
		_chart("seg_chart", f"Cabin ₹{_cum(cab)} L · Non-Cabin ₹{_cum(non)} L (FY)", fy, seg_series, value=_cum(cab) + _cum(non),
			rows=_month_rows(fy, seg_series)),
		_chart("book_chart", f"Order booking by month · FY ₹{_cum(book)} L", fy, [("Orders", "blue", book)], target, value=_cum(book),
			rows=_month_rows(fy, [("Orders", "blue", book)])),
	]


def _profit_chart(user) -> dict:
	from sk_app import ledger

	fy = _fy_start()
	mw = ledger.month_wise(user or "Administrator", fy)
	by = {r["month"]: r for r in mw["rows"]}
	gross = _fy_values(fy, {k: r["gross"] for k, r in by.items()})
	net = _fy_values(fy, {k: r["net"] for k, r in by.items()})
	series = [("Gross", "green", gross), ("Net", "blue", net)]
	return _chart("profit_chart", f"Gross ₹{_cum(gross)} L · Net ₹{_cum(net)} L (FY)", fy, series, bars=True, value=_cum(net),
		rows=_month_rows(fy, series), c="red" if _cum(net) < 0 else None)


def _count_chart(key, label, doctype, date_field, filters=None, unit="") -> dict | None:
	"""A function's KPI by month as a count (1-2 per function, SK 26-Oct point 4)."""
	if not _has(doctype):
		return None
	fy = _fy_start()
	rows = frappe.get_all(doctype, filters={date_field: [">=", fy], **(filters or {})}, fields=[date_field], limit=0)
	by = _bucket(rows, date_field, lambda r: 1)
	this = str(getdate())[:7]
	vals = [None if str(add_months(fy, i))[:7] > this else int(by.get(str(add_months(fy, i))[:7], 0)) for i in range(12)]
	return _chart(key, f"{label} · FY {sum(v or 0 for v in vals)}", fy, [(label, "orange", vals)], unit=unit, value=sum(v or 0 for v in vals),
		rows=[_row(f"{_fy_labels(fy)[i]}", "", v) for i, v in enumerate(vals) if v is not None])


# ---------- pages ----------

def _overview(start, end, ps, pe, segment):
	attention = _attention()
	target = sum(_targets().values())
	orders = _orders_card(start, end, ps, pe, segment)
	cards = [*(_safe(lambda: _overview_charts(segment), []) or []), _safe(lambda: _profit_chart(None)),
		orders, _safe(lambda: _sales_card(start, end, ps, pe, segment)), _safe(lambda: _receivables_card(segment)),
		_safe(_cash_card), _safe(lambda: _pipeline_card(segment)) if _has("CRM Deal") else None,
		_safe(lambda: _leads_card(start, end, ps, pe, segment)) if _has("CRM Lead") else None]
	if target:
		cards.insert(1, _card("target", "Orders vs monthly target", round(flt(orders["value"]) * 100 / target), "pct", None,
			_team_scorecard(start, end)))
	cards.append(_safe(_sas_card))
	cards.append(_card("attention", "Needs your attention", sum(len(a["rows"]) for a in attention), "count", None,
		[r for a in attention for r in a["rows"]][:100], "red" if attention else None))
	return cards


def _sas_card():
	from sk_app import sas

	d = sas.leadership("Administrator")
	return _card("sas", f"TLC SAS score (self, target {d['target_pct']}%)", d["self_pct"], "pct", None,
		[_row(s["name"], f"{s['self_score']}/{s['out_of']} · {s['owner']}", f"{s['self_pct']}%", c="green" if s["self_pct"] >= s["target_pct"] else "amber")
			for s in d["subjects"]])


def _attention() -> list[dict]:
	"""What the CEO should act on today: old dues, POs to approve, late orders, leads nobody called, missing reports."""
	out = []
	old = [r for r in (_safe(_receivables, []) or []) if r.late > 60]
	if old:
		out.append({"label": "Dues over 60 days", "rows": [_row(r.customer_name, f"oldest bill {r.late} days", r.outstanding_amount, "Customer", r.name, "red") for r in old[:20]]})
	from sk_app.purchase import po_limit

	pos = _safe(lambda: frappe.get_all("Purchase Order", filters={"docstatus": 0, "grand_total": [">", po_limit()]},
		fields=["name", "supplier_name", "grand_total"], order_by="creation asc"), [])
	if pos:
		out.append({"label": "POs waiting for your OK", "rows": [_row(p.supplier_name, "PO to approve", p.grand_total, "Purchase Order", p.name, "amber") for p in pos]})
	late = _safe(_late_orders, [])
	if late:
		out.append({"label": "Late orders", "rows": [_row(o.customer_name, f"due {o.delivery_date}", o.base_net_total, "Sales Order", o.name, "red") for o in late[:20]]})
	nc = _safe(_not_contacted, [])
	if nc:
		out.append({"label": "Leads nobody called", "rows": [_row(r.organization or r.first_name, f"{_name(r.lead_owner)} · since {str(r.creation)[:10]}", None, "CRM Lead", r.name, "red") for r in nc[:20]]})
	from sk_app import plan

	behind = _safe(plan.behind_list, [])
	if behind:  # Target Action Plan: red flag from the 10th when the month's orders are behind
		out.append({"label": "Behind this month's target", "rows": [_row(_name(b["user"]), f"done {round(b['done'] / LAKH, 1)} L of {round(b['expected'] / LAKH, 1)} L due by today",
			b["gap"], "User", b["user"], "red") for b in behind]})
	if now_datetime().hour >= 18:
		missing = _safe(lambda: [p for p in _review(getdate())["rows"] if p["c"] == "red"], [])
		if missing:
			out.append({"label": "No day report today", "rows": missing})
	return out


def _sales(start, end, ps, pe, segment, sub=None, owner_users=None):
	seg = sub or segment
	charts = _safe(lambda: _overview_charts(seg), []) or []
	cards = [charts[2] if len(charts) > 2 else None, charts[0] if charts else None,
		_orders_card(start, end, ps, pe, seg), _safe(lambda: _sales_card(start, end, ps, pe, seg))]
	if _has("CRM Deal"):
		deals = frappe.get_all("CRM Deal", filters={"status": ["in", _open_deal_statuses() or [""]], **_crm_seg(seg)},
			fields=["status", "deal_value"], limit=1000)
		stages = {}
		for d in deals:
			s = stages.setdefault(d.status, [0, 0.0])
			s[0] += 1
			s[1] += flt(d.deal_value)
		cards.append(_safe(lambda: _pipeline_card(seg)))
		cards.append(_card("stages", "Pipeline by stage", len(deals), "count", None,
			[_row(k, f"{v[0]} deals", v[1]) for k, v in sorted(stages.items(), key=lambda x: -x[1][1])]))
	if _has("CRM Lead"):
		cards.append(_safe(lambda: _leads_card(start, end, ps, pe, seg)))
		days = {}
		for r in _leads(add_days(getdate(), -13), getdate(), seg):
			days[str(r.creation)[:10]] = days.get(str(r.creation)[:10], 0) + 1
		cards.append(_card("leads_day", "Leads per day (14 days)", sum(days.values()), "series", None,
			[_row(d[5:], "", days.get(d, 0)) for d in (str(add_days(getdate(), -n)) for n in range(13, -1, -1))]))
	quotes = _safe(lambda: frappe.get_all("Quotation", filters={"docstatus": ["<", 2], "transaction_date": ["between", [start, end]], **_seg_filter(seg)},
		fields=["name", "party_name", "customer_name", "base_net_total", "status"], order_by="base_net_total desc", limit=200), [])
	cards.append(_card("quotes", "Quotes this month", len(quotes), "count", None,
		[_row(q.customer_name or q.party_name, q.status, q.base_net_total, "Quotation", q.name) for q in quotes[:60]]))
	cards.append(_safe(lambda: _card("team", "Team vs target (orders)", None, "list", None, _team_scorecard(start, end, owner_users))))
	months = []
	for n in range(5, -1, -1):
		m = add_months(get_first_day(getdate()), -n)
		months.append(_row(f"{m:%b %y}", "", sum(flt(r.base_net_total) for r in _orders(m, get_last_day(m), seg))))
	cards.append(_card("months", "Orders by month", sum(r["value"] for r in months), "series", None, months))
	cards.append(_safe(lambda: _receivables_card(seg)))
	return cards


def _marketing(start, end, ps, pe, segment):
	if not _has("CRM Lead"):
		return [_card("crm", "Frappe CRM is not installed", None, "list", None, [])]
	from sk_app.logic import parse_lines

	rows = _leads(start, end, segment)
	by = {}
	for r in rows:
		by[r.source or "Not given"] = by.get(r.source or "Not given", 0) + 1
	digital = parse_lines(frappe.get_cached_doc("SK App Settings").get("digital_lead_sources") or "") or ["IndiaMART", "JustDial"]
	dig = [r for r in rows if r.source in digital]
	won = frappe.get_all("CRM Deal", filters={"creation": ["between", [f"{start} 00:00:00", f"{end} 23:59:59"]], **_crm_seg(segment)},
		fields=["name", "organization", "source", "deal_value", "status"], limit=300) if _has("CRM Deal") else []
	return [
		_safe(lambda: _count_chart("quote_chart", "Quotes sent", "Quotation", "transaction_date", {"docstatus": ["<", 2], **_seg_filter(segment)})),
		_safe(lambda: _count_chart("lead_chart", "New leads", "CRM Lead", "creation", _crm_seg(segment))),
		_leads_card(start, end, ps, pe, segment),
		_card("by_source", "Leads by source", len(rows), "list", None, [_row(k, "", v) for k, v in sorted(by.items(), key=lambda x: -x[1])]),
		_card("digital", "Digital leads (IndiaMART, JustDial ...)", len(dig), "count", None,
			[_row(r.organization or r.first_name, f"{r.source} · {_name(r.lead_owner)}", None, "CRM Lead", r.name) for r in dig[:80]]),
		_card("to_deals", "Leads turned into deals", len(won), "count", None,
			[_row(d.organization or d.name, f"{d.source or ''} · {d.status}", d.deal_value, "CRM Deal", d.name) for d in won[:80]]),
		_card("conversion", "Lead → deal", round(len(won) * 100 / len(rows)) if rows else 0, "pct"),
		_card("not_called", "Leads nobody called (over 1 day)", len(_not_contacted()), "count", None,
			[_row(r.organization or r.first_name, _name(r.lead_owner), None, "CRM Lead", r.name, "red") for r in _not_contacted()[:80]], "red"),
	]


def _cr100(start, end, ps, pe, segment):
	today = getdate()
	fy = today.year if today.month >= 4 else today.year - 1
	rows = []
	for y in range(fy - 3, fy + 1):
		total = _invoiced(f"{y}-04-01", f"{y + 1}-03-31", segment)
		rows.append(_row(f"FY {y}-{str(y + 1)[2:]}", f"{round(total / CRORE, 2)} Cr", total))
	this = rows[-1]["value"]
	years_left = max(GOAL_FY - fy, 1)
	last_full = rows[-2]["value"] or this
	need_growth = round(((GOAL_CR * CRORE / last_full) ** (1 / (years_left + 1)) - 1) * 100) if last_full else None
	mix = [_row(main, "", _invoiced(f"{fy}-04-01", f"{fy + 1}-03-31", main)) for main in segments.TREE]
	return [
		_card("fy", f"Sales FY {fy}-{str(fy + 1)[2:]} so far", this, "money", rows[-2]["value"], rows),
		_card("goal", f"Goal: Rs {GOAL_CR} Cr in FY {GOAL_FY}-{str(GOAL_FY + 1)[2:]}", round(this * 100 / (GOAL_CR * CRORE), 1), "pct", None,
			[_row("Growth needed every year", f"from FY {fy - 1}-{str(fy)[2:]}", need_growth)]),
		_card("mix", "Segment mix this year", this, "money", None, mix),
		_card("months", "Orders by month", None, "series", None,
			[_row(f"{m:%b %y}", "", sum(flt(r.base_net_total) for r in _orders(m, get_last_day(m), segment)))
				for m in (add_months(get_first_day(today), -n) for n in range(11, -1, -1))]),
	]


def _finance(start, end, ps, pe, segment, user=None):
	rec = _receivables(segment)
	buckets = {"0-30 days": 0.0, "31-60 days": 0.0, "Over 60 days": 0.0}
	for r in rec:
		for k, v in r.ages.items():
			buckets[k] += v
	cards = [_safe(lambda: _profit_chart(user)), _safe(_cash_card), _receivables_card(segment),
		_card("ageing", "Receivables ageing", sum(buckets.values()), "money", None, [_row(k, "", v, c="red" if k == "Over 60 days" and v else None) for k, v in buckets.items()]),
		_safe(_payables_card)]

	def pnl():
		from sk_app import ledger

		seg = ledger.segment_wise(user, start)
		return _card("pnl", "Profit by segment (this month)", seg["total"]["net"], "money", None,
			[_row(r["segment"], f"income {round(flt(r['income']) / LAKH, 1)} L", r["net"], c="red" if r["net"] < 0 else "green") for r in seg["rows"]])
	cards.append(_safe(pnl))
	return cards


def _manufacturing(start, end, ps, pe, segment):
	if not _has("Work Order"):
		return []
	wos = frappe.get_all("Work Order", filters={"docstatus": 1, "status": ["not in", ["Completed", "Stopped", "Closed", "Cancelled"]]},
		fields=["name", "item_name", "qty", "status", "sales_order", "expected_delivery_date"], order_by="expected_delivery_date asc", limit=300)
	late = [w for w in wos if w.expected_delivery_date and getdate(w.expected_delivery_date) < getdate()]
	jobs = frappe.get_all("Job Card", filters={"docstatus": 0, "status": ["in", ["Work In Progress", "Open", "Material Transferred"]]},
		fields=["name", "operation", "workstation", "status", "work_order"], limit=500)
	load = {}
	for j in jobs:
		load[j.workstation or "Not set"] = load.get(j.workstation or "Not set", 0) + 1
	done = frappe.db.count("Work Order", {"status": "Completed", "modified": [">=", f"{start} 00:00:00"]})
	return [
		_safe(lambda: _count_chart("wo_chart", "Cabins / jobs finished", "Work Order", "actual_end_date", {"status": "Completed"})),
		_safe(lambda: _count_chart("dn_chart", "Dispatches", "Delivery Note", "posting_date", {"docstatus": 1})),
		_card("in_production", "Cabins / jobs in production", len(wos), "count", None,
			[_row(w.item_name, f"{w.status} · due {w.expected_delivery_date or '?'}", w.qty, "Work Order", w.name,
				"red" if w in late else None) for w in wos[:80]]),
		_card("late", "Late in production", len(late), "count", None,
			[_row(w.item_name, f"due {w.expected_delivery_date}", w.qty, "Work Order", w.name, "red") for w in late], "red" if late else None),
		_card("load", "Workstation load (open job cards)", len(jobs), "list", None, [_row(k, "job cards", v) for k, v in sorted(load.items(), key=lambda x: -x[1])]),
		_card("done", "Finished this month", done, "count"),
		_card("late_orders", "Late customer orders", len(_late_orders(segment)), "count", None,
			[_row(o.customer_name, f"due {o.delivery_date}", o.base_net_total, "Sales Order", o.name, "red") for o in _late_orders(segment)]),
	]


def _purchase(start, end, ps, pe, segment):
	from sk_app.purchase import po_limit

	open_po = frappe.get_all("Purchase Order", filters={"docstatus": 1, "status": ["in", ["To Receive and Bill", "To Receive", "To Bill"]]},
		fields=["name", "supplier_name", "grand_total", "schedule_date", "per_received"], order_by="schedule_date asc", limit=300)
	waiting = frappe.get_all("Purchase Order", filters={"docstatus": 0}, fields=["name", "supplier_name", "grand_total", "creation"],
		order_by="creation asc", limit=200)
	late = [p for p in open_po if p.schedule_date and getdate(p.schedule_date) < getdate() and flt(p.per_received) < 100]
	reqs = frappe.get_all("Material Request", filters={"docstatus": 1, "material_request_type": "Purchase", "status": ["in", ["Pending", "Partially Ordered"]]},
		fields=["name", "schedule_date", "status"], limit=200)
	limit = po_limit()
	return [
		_safe(lambda: _count_chart("po_chart", "Purchase orders", "Purchase Order", "transaction_date", {"docstatus": 1})),
		_card("open_po", "Open POs", sum(flt(p.grand_total) for p in open_po), "money", None,
			[_row(p.supplier_name, f"needed by {p.schedule_date}", p.grand_total, "Purchase Order", p.name) for p in open_po[:60]]),
		_card("approvals", "POs waiting (draft)", len(waiting), "count", None,
			[_row(p.supplier_name, "needs your OK" if flt(p.grand_total) > limit else "draft", p.grand_total, "Purchase Order", p.name,
				"amber" if flt(p.grand_total) > limit else None) for p in waiting]),
		_card("late_po", "Late supplier deliveries", len(late), "count", None,
			[_row(p.supplier_name, f"was due {p.schedule_date}", p.grand_total, "Purchase Order", p.name, "red") for p in late], "red" if late else None),
		_safe(lambda: _payables_card("dues", "Supplier dues")),
		_card("requests", "Buy requests not ordered yet", len(reqs), "count", None,
			[_row(r.name, f"{r.status} · need by {r.schedule_date}", None, "Material Request", r.name) for r in reqs]),
	]


def _store(start, end, ps, pe, segment, user=None):
	value = sum(flt(v) for v in frappe.get_all("Bin", pluck="stock_value"))
	from sk_app.store import low_stock

	low = _safe(lambda: low_stock(user), []) or []
	today = nowdate()
	receipts = frappe.get_all("Purchase Receipt", filters={"posting_date": today, "docstatus": ["<", 2]}, fields=["name", "supplier_name", "grand_total"])
	issues = frappe.get_all("Stock Entry", filters={"posting_date": today, "docstatus": ["<", 2]}, fields=["name", "stock_entry_type", "total_outgoing_value"])
	dispatch = frappe.get_all("Delivery Note", filters={"posting_date": today, "docstatus": ["<", 2]}, fields=["name", "customer_name", "base_net_total"])
	return [
		_safe(lambda: _count_chart("rec_chart", "Receipts", "Purchase Receipt", "posting_date", {"docstatus": 1})),
		_card("stock_value", "Stock value", value, "money"),
		_card("low", "Low stock items", len(low), "count", None,
			[_row(r["item_name"] or r["item_code"], f"{r['warehouse']} · have {r['qty']} / level {r['level']}", None, "Item", r["item_code"], "red") for r in low[:80]],
			"red" if low else None),
		_card("receipts", "Received today", len(receipts), "count", None, [_row(r.supplier_name, "", r.grand_total, "Purchase Receipt", r.name) for r in receipts]),
		_card("issues", "Issued / moved today", len(issues), "count", None, [_row(r.stock_entry_type, "", r.total_outgoing_value, "Stock Entry", r.name) for r in issues]),
		_card("dispatch", "Dispatched today", len(dispatch), "count", None, [_row(r.customer_name, "", r.base_net_total, "Delivery Note", r.name) for r in dispatch]),
	]


def _quality(start, end, ps, pe, segment):
	cards = [_safe(lambda: _count_chart("qi_chart", "Inspections", "Quality Inspection", "report_date", {"docstatus": ["<", 2]})),
		_safe(lambda: _count_chart("nc_chart", "Problems found (NC)", "Non Conformance", "creation"))]
	if _has("Quality Inspection"):
		qi = frappe.get_all("Quality Inspection", filters={"report_date": ["between", [start, end]], "docstatus": ["<", 2]},
			fields=["name", "item_name", "status", "reference_name", "report_date"], order_by="report_date desc", limit=200)
		rejected = [q for q in qi if q.status == "Rejected"]
		cards.append(_card("inspections", "Inspections this month", len(qi), "count", None,
			[_row(q.item_name, f"{q.status} · {q.reference_name or ''}", None, "Quality Inspection", q.name, "red" if q.status == "Rejected" else None) for q in qi]))
		cards.append(_card("rejected", "Rejected", len(rejected), "count", None, [], "red" if rejected else None))
	if _has("Non Conformance"):
		ncs = frappe.get_all("Non Conformance", filters={"status": "Open"}, fields=["name", "subject", "creation"], order_by="creation asc", limit=200)
		late = [n for n in ncs if date_diff(nowdate(), n.creation) > 7]
		cards.append(_card("ncs", "Open problems (Non Conformance)", len(ncs), "count", None,
			[_row(n.subject, f"open since {str(n.creation)[:10]}", None, "Non Conformance", n.name, "red" if n in late else None) for n in ncs],
			"red" if late else None))
		cards.append(_card("late_fixes", "Fixes late (over 7 days)", len(late), "count"))
	if _has("Issue"):
		issues = frappe.get_all("Issue", filters={"status": ["in", ["Open", "Replied"]]}, fields=["name", "subject", "customer", "opening_date"], limit=200)
		cards.append(_card("complaints", "Customer complaints open", len(issues), "count", None,
			[_row(i.subject, i.customer or "", None, "Issue", i.name) for i in issues]))
	return cards


def _hr(start, end, ps, pe, segment):
	today = getdate()
	users = frappe.get_all("SK App User", filters={"enabled": 1}, fields=["user", "full_name"])
	last = {u.name: u.last_active for u in frappe.get_all("User", filters={"name": ["in", [u.user for u in users] or [""]]}, fields=["name", "last_active"])}
	used = [u for u in users if last.get(u.user) and getdate(last[u.user]) == today]
	cards = [_safe(lambda: _count_chart("att_chart", "Present days (Optick + thumb)", "Attendance", "attendance_date",
		{"docstatus": 1, "status": ["in", ["Present", "Half Day", "Work From Home"]]})),
		_card("app_today", "Used the app today", len(used), "count", None,
		[_row(u.full_name or u.user, f"last {str(last.get(u.user) or 'never')[:16]}", None, "User", u.user,
			None if u in used else "red") for u in sorted(users, key=lambda x: x in used)])]
	if _has("Attendance"):
		att = frappe.get_all("Attendance", filters={"attendance_date": today, "docstatus": ["<", 2]}, fields=["name", "employee_name", "status", "in_time"])
		present = [a for a in att if a.status in ("Present", "Work From Home", "Half Day")]
		cards.append(_card("attendance", "Present today (Optick + thumb)", len(present), "count", None,
			[_row(a.employee_name, a.status, None, "Attendance", a.name, None if a in present else "red") for a in att]))
	if _has("Leave Application"):
		leave = frappe.get_all("Leave Application", filters={"status": "Approved", "from_date": ["<=", today], "to_date": [">=", today], "docstatus": ["<", 2]},
			fields=["name", "employee_name", "leave_type", "to_date"])
		cards.append(_card("leave", "On leave today", len(leave), "count", None,
			[_row(l.employee_name, f"{l.leave_type} till {l.to_date}", None, "Leave Application", l.name) for l in leave]))
		waiting = frappe.get_all("Leave Application", filters={"status": "Open", "docstatus": 0}, fields=["name", "employee_name", "from_date"])
		cards.append(_card("leave_wait", "Leave requests waiting", len(waiting), "count", None,
			[_row(l.employee_name, f"from {l.from_date}", None, "Leave Application", l.name, "amber") for l in waiting]))
	cards.append(_card("employees", "Active employees", frappe.db.count("Employee", {"status": "Active"}), "count"))
	return cards


def _ai(start, end, ps, pe, segment, user=None):
	from sk_app import ai_desk

	box = ai_desk.inbox(user)
	gaps = ai_desk.erp_gaps(user)
	users = ai_desk.app_users(user)
	changes = ai_desk.change_list(user)
	states = {}
	for c in changes:
		states[c["status"] or "Not started"] = states.get(c["status"] or "Not started", 0) + 1
	return [
		_card("inbox", "Improvement inbox: new", len(box["new"]), "count", None,
			[_row(i["title"], f"{i['by']} · {i['type'] or ''}", None, i["doctype"], i["name"], "blue") for i in box["new"][:80]]),
		_card("working", "Being fixed", len(box["working"]), "count", None,
			[_row(i["title"], f"{i['category']} · due {i['due'] or ''}", None, i["doctype"], i["name"]) for i in box["working"][:80]]),
		_card("gaps", "ERP data gaps", sum(1 for g in gaps if g["kind"] == "gap" and g["count"]), "count", None,
			[_row(g["label"], f"of {g['of']}" if g["of"] is not None else "", g["count"], c="amber" if g["kind"] == "gap" and g["count"] else None) for g in gaps]),
		_card("app_use", "Used the app today", users["today"], "count", None,
			[_row(r["full_name"] or r["user"], f"{r['function'] or ''} · {r['state']}", None, "User", r["user"],
				"red" if r["state"] == "never" else None) for r in users["rows"]]),
		_card("changes", "Change list (Rev 13)", len(changes), "list", None, [_row(k, "", v) for k, v in states.items()]),
	]


def _review(day=None) -> dict:
	"""Daily Review: each person's day: report, DSI, calls and leads."""
	day = getdate(day)
	users = frappe.get_all("SK App User", filters={"enabled": 1}, fields=["user", "full_name"], order_by="full_name asc")
	rows = []
	for u in users:
		report = frappe.db.exists("SK Day Report", {"user": u.user, "date": day})
		dsi = frappe.db.count("SK DSI Entry", {"user": u.user, "date": day})
		calls = frappe.db.count("CRM Call Log", {"owner": u.user, "creation": ["between", [f"{day} 00:00:00", f"{day} 23:59:59"]]}) if _has("CRM Call Log") else 0
		leads = frappe.db.count("CRM Lead", {"lead_owner": u.user, "creation": ["between", [f"{day} 00:00:00", f"{day} 23:59:59"]]}) if _has("CRM Lead") else 0
		meta = " · ".join([("📝 report ✓" if report else "📝 no report"), f"💡 {dsi}", f"📞 {calls}", f"🎯 {leads}"])
		rows.append(_row(u.full_name or u.user, meta, None, "SK Day Report" if report else "User", report or u.user, None if report else "red"))
	return {"rows": rows}


def _daily_review(start, end, ps, pe, segment):
	today = _review(getdate())["rows"]
	yday = _review(add_days(getdate(), -1))["rows"]
	return [
		_card("today", "Today: day reports sent", sum(1 for r in today if not r["c"]), "count", None, today),
		_card("yesterday", "Yesterday", sum(1 for r in yday if not r["c"]), "count", None, yday),
	]


BUILDERS = {
	"overview": _overview, "sales": _sales, "marketing": _marketing, "cr100": _cr100, "finance": _finance,
	"manufacturing": _manufacturing, "purchase": _purchase, "store": _store, "quality": _quality, "hr": _hr, "ai": _ai,
	"daily_review": _daily_review,
}
WITH_USER = {"finance", "store", "ai"}


def page(user: str, key: str, month=None, segment=None) -> dict:
	check(user)
	if key not in PAGE_KEYS:
		frappe.throw(_("Unknown dashboard"))
	start, end, ps, pe = _period(month)
	segment = segment if segment in segments.TREE else None
	if key in ("machine_shifting", "job_work"):
		sub = "Machine Shifting" if key == "machine_shifting" else "Job Work"
		owners = [u for u in frappe.get_all("SK App User", filters={"enabled": 1}, pluck="user") if segments.user_main(u) == segments.NON_CABIN]
		cards = _sales(start, end, ps, pe, None, sub=sub, owner_users=owners)
	elif key in WITH_USER:
		cards = BUILDERS[key](start, end, ps, pe, segment, user=user)
	else:
		cards = BUILDERS[key](start, end, ps, pe, segment)
	label = next(p for p in PAGES if p[0] == key)
	return {"key": key, "title": {"English": label[1], "Marathi": label[2]}, "month": str(start), "segment": segment,
		"cards": [c for c in cards if c], "pages": [p[0] for p in PAGES], "refreshed_at": str(now_datetime())[:16]}


def badges(user: str) -> dict:
	"""Red number on each dashboard icon = items needing attention there (kept 5 minutes, so Home stays quick)."""
	key = f"sk_dash_badges:{user}"
	cached = frappe.cache.get_value(key)
	if cached is not None:
		return cached
	out = {}
	for item in _attention():
		n = len(item["rows"])
		page_key = {"Dues over 60 days": "finance", "POs waiting for your OK": "purchase", "Late orders": "manufacturing",
			"Leads nobody called": "marketing", "No day report today": "daily_review", "Behind this month's target": "sales"}.get(item["label"])
		if page_key:
			out[f"dash_{page_key}"] = {"n": n, "c": "red"}
		out["dash_overview"] = {"n": out.get("dash_overview", {}).get("n", 0) + n, "c": "red"}
	frappe.cache.set_value(key, out, expires_in_sec=300)
	return out
