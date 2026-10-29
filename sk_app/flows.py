"""Live process flow on every Home (change list point 17, SK 26-Oct-2026).

"In everyone's app need two sections, one is his functional role and another common things. In function, graphical
process flow is needed ... in each section need live data for review / update, with no of days delay." · "in every
square need live data from ERP" · "after click on each section more details" · "interactive process flow to everyone".

Each function has its stages left to right. Every stage box is read live from ERPNext when Home opens: how many, the
Rs value where it means something, how many are late and the oldest delay. Tapping a box lists its records (most
late first); each row opens the record, and the box's "Work on it" button opens the app screen where that stage is
submitted / moved on. A salesperson sees their own work, a manager the team's, the CEO everything (one flow per
function).
"""

import frappe
from frappe.utils import add_days, date_diff, flt, get_first_day, getdate, now_datetime, nowdate

from sk_app import dashboards, lead_status, segments
from sk_app.dashboards import _has, _name, _row, _safe
from sk_app.production import wo_label

ROWS = 60
# SK's proposal (change list page 45): days a stage may take before it turns red
# days a lead may stay in one of SK's steps without any update before it turns red
STEP_DAYS = {"Qualified": 3, "Drawing": 2, "Quotation": 2, "Negotiations": 7}
TARGET_DAYS = {"lead": 1, "quote": 2, "Fabrication": 5, "Electrical": 2, "Carpentry": 2, "Painting": 2, "Final inspection": 1}
# factory stages in SK's order (26-Oct: carpentry after wiring); words found in the ERPNext operation names
FACTORY = [("Fabrication", "🔩", ("fabric", "weld")), ("Electrical", "💡", ("electric", "wiring")),
	("Carpentry", "🪚", ("carpen", "wood", "floor")), ("Painting", "🎨", ("paint",)), ("Final inspection", "🔍", ("inspect", "qc", "quality"))]


def _stage(key, label, icon, rows, value=None, go=None, kind="count", late_rows=None) -> dict:
	"""One box: rows are dashboard rows (c = red when late); count = len(rows) unless the rows are only an example."""
	late = [r for r in rows if r.get("c") == "red"] if late_rows is None else late_rows
	days = [r.get("days") or 0 for r in late]
	c = "red" if late else "amber" if any(r.get("c") == "amber" for r in rows) else "green" if rows else None
	return {"key": key, "label": label, "icon": icon, "count": len(rows), "value": value, "kind": kind,
		"late": len(late), "oldest": max(days) if days else 0, "c": c, "go": go,
		"rows": sorted(rows, key=lambda r: (-(r.get("days") or 0), -(r.get("pending") or 0)))[:None if frappe.flags.sk_flow_all else ROWS]}


def _late_row(title, meta, value, doctype, name, since, target, done=False, opened=None) -> dict:
	"""A row, red when it waited longer than the stage's target days (days = how long it waited).
	target 0 = since is a due date (late = days past it). Every pending row says from how many days it is pending
	(SK 27-Oct: "after open pending point, need to show from how many days it is pending"), counted from opened
	(when the record was made) or else from since."""
	days = date_diff(nowdate(), since) if since else 0
	over = (not done) and target is not None and days > target
	start = opened or (since if target != 0 else None)
	age = max(date_diff(nowdate(), start), 0) if start else None
	parts = [meta] if meta else []
	if age is not None and not done:
		parts.append(f"pending {age} days")
	if target == 0 and since and not done:
		parts.append(f"{days} days late" if days > 0 else "due today" if days == 0 else f"due in {-days} day{'s' if days < -1 else ''}")
	elif opened and since and days != age and not done:
		parts.append(f"no update {days} days")
	r = _row(title, " · ".join(parts), value, doctype, name, "red" if over else None)
	r["days"] = days if over else 0
	r["pending"] = age
	return r


# ---------- who sees what ----------

def _owners(user: str) -> list[str] | None:
	"""None = everyone (CEO / Management); otherwise the person plus their team (Rushi sees his salespeople)."""
	from sk_app.day_report import _team
	from sk_app.logins import profile_functions

	if user == "Administrator" or "Management" in profile_functions(user):
		return None
	return [user] + [p.user for p in _team(user)]


def _in(field: str, owners) -> dict:
	return {} if owners is None else {field: ["in", owners or [""]]}


# ---------- flows ----------

def sales(user: str, segment=None, only_self=False) -> list[dict]:
	"""only_self: the person's own work only (one member's arrows on the sales manager's team screen)."""
	owners = [user] if only_self else _owners(user)
	seg = dashboards._crm_seg(segment)
	start = get_first_day(getdate())
	stages = []
	# SK 27-Oct: arrows follow his steps New → Qualified → Drawing → Quotation → Negotiations (→ won = orders)
	by = {step: [] for step in lead_status.STEPS}
	if _has("CRM Lead"):
		closed = frappe.get_all("CRM Lead Status", filters={"type": ["in", ["Won", "Lost", "Junk"]]}, pluck="name")
		from sk_app.cold_calls import not_cold

		leads = frappe.get_all("CRM Lead", filters={"converted": 0, "status": ["not in", closed or [""]], **seg, **_in("lead_owner", owners), **not_cold()},
			fields=["name", "first_name", "organization", "status", "lead_owner", "creation", "modified", "first_responded_on", "sk_segment"],
			order_by="creation asc", limit=0)
		for l in leads:
			step = lead_status.step_of(l.status)
			not_called = step == "New" and not l.first_responded_on
			by[step].append(_late_row(l.organization or l.first_name or l.name, f"{l.status} · {_name(l.lead_owner)}" + (" · not called" if not_called else ""),
				None, "CRM Lead", l.name, l.creation if step == "New" else l.modified,
				(TARGET_DAYS["lead"] if not_called else None) if step == "New" else STEP_DAYS[step], opened=l.creation))
	deals = []
	if _has("CRM Deal"):
		open_st = dashboards._open_deal_statuses()
		deals = frappe.get_all("CRM Deal", filters={"status": ["in", open_st or [""]], **seg, **_in("deal_owner", owners)},
			fields=["name", "organization", "status", "deal_value", "deal_owner", "creation", "modified", "sk_customer_name"],
			order_by="modified asc", limit=0)
		for d in deals:
			step = lead_status.step_of(d.status, deal=True)
			r = _late_row(d.get("sk_customer_name") or d.organization or d.name, f"{d.status} · {_name(d.deal_owner)}", d.deal_value,
				"CRM Deal", d.name, d.modified, STEP_DAYS.get(step), opened=d.creation)
			by[step].append(r)
	icons = {"New": "🎯", "Qualified": "✅", "Drawing": "📐", "Quotation": "📄", "Negotiations": "🤝"}
	go = {"New": "my_leads", "Qualified": "my_leads", "Drawing": "my_deals", "Quotation": "my_deals", "Negotiations": "my_deals"}
	# the 8 arrows always show, 0 when empty (SK 27-Oct: arrows missing looked like a fault)
	for step in lead_status.STEPS:
		rows = by[step]
		value = sum(flt(r["value"]) for r in rows if r.get("value"))
		stages.append(_stage(step.lower(), step, icons[step], rows, value or None, go=go[step]))
	# SK 27-Oct "All status shows in flow chart": the three closing steps too, closed this month
	done = {"Deal Won": [], "Junk Lead": [], "Deal Loss": []}
	if _has("CRM Lead"):
		for l in frappe.get_all("CRM Lead", filters={"status": ["in", list(done)], "modified": [">=", start], **seg, **_in("lead_owner", owners)},
				fields=["name", "first_name", "organization", "status", "lead_owner", "modified"], limit=0):
			done[l.status].append(_row(l.organization or l.first_name or l.name, f"{str(l.modified)[:10]} · {_name(l.lead_owner)}", None, "CRM Lead", l.name))
	if _has("CRM Deal"):
		kinds = {r.name: r.type for r in frappe.get_all("CRM Deal Status", fields=["name", "type"])}
		closed_st = [k for k, v in kinds.items() if v in ("Won", "Lost")]
		for d in frappe.get_all("CRM Deal", filters={"status": ["in", closed_st or [""]], "modified": [">=", start], **seg, **_in("deal_owner", owners)},
				fields=["name", "organization", "status", "deal_value", "deal_owner", "modified", "sk_customer_name"], limit=0):
			done["Deal Won" if kinds.get(d.status) == "Won" else "Deal Loss"].append(_row(d.get("sk_customer_name") or d.organization or d.name,
				f"{str(d.modified)[:10]} · {_name(d.deal_owner)}", d.deal_value, "CRM Deal", d.name))
	for key, icon in (("Deal Won", "🏆"), ("Junk Lead", "🗑️"), ("Deal Loss", "❌")):
		rows = done[key]
		value = sum(flt(r["value"]) for r in rows if r.get("value"))
		stages.append(_stage(key.lower().replace(" ", "_"), f"{key} (month)", icon, rows, value or None, go="my_leads", late_rows=[]))
	if segment == segments.NON_CABIN:
		# SK 28-Oct (Rev 1 point 9): the Non-Cabin jobs (Rothe Erde etc.) taken off the factory board are Aditya's to run
		jobs = frappe.get_all("Sales Order", filters={"docstatus": ["<", 2], "per_delivered": ["<", 100], "status": ["not in", ["Closed", "Completed"]],
			"customer_group": ["in", segments.groups_of(segments.NON_CABIN)]}, fields=["name", "customer_name", "delivery_date", "base_net_total",
			"transaction_date", "docstatus"], order_by="delivery_date asc", limit=0)
		stages.append(_stage("non_cabin_jobs", "Non-Cabin jobs open", "🛠️", [_late_row(s.customer_name, f"due {s.delivery_date or '?'}"
			+ (" · draft order" if s.docstatus == 0 else ""), s.base_net_total, "Sales Order", s.name, s.delivery_date, 0, opened=s.transaction_date)
			for s in jobs], sum(flt(s.base_net_total) for s in jobs), kind="money"))
	return stages


def _job_cards(workstation=None) -> list:
	filters = {"docstatus": 0, "status": ["not in", ["Completed", "Cancelled"]]}
	if workstation:
		filters["workstation"] = workstation
	return frappe.get_all("Job Card", filters=filters, fields=["name", "operation", "workstation", "status", "work_order",
		"expected_end_date", "expected_start_date", "creation", "for_quantity"], order_by="creation asc", limit=0)


def _factory_stage(operation: str) -> str | None:
	low = (operation or "").lower()
	return next((name for name, _icon, words in FACTORY if any(w in low for w in words)), None)


def factory(user: str, go="job_cards", workstation=None) -> list[dict]:
	"""Orders → Fabrication → Electrical → Carpentry → Painting → Final inspection → Dispatch (SK 26-Oct)."""
	stages = []
	if not workstation:
		from sk_app.production import non_cabin_orders

		non_cabin = non_cabin_orders()  # SK 28-Oct: the factory board shows cabins only; Non-Cabin jobs are on Aditya's arrows
		# SK 29-Oct: only submitted orders wait for the factory (drafts are still with sales), and a cabin whose Project
		# already has a Work Order is started even when the Work Order is not linked to the order
		with_wo = set(frappe.get_all("Work Order", filters={"docstatus": ["<", 2], "sales_order": ["is", "set"]}, pluck="sales_order"))
		wo_projects = set(frappe.get_all("Work Order", filters={"docstatus": ["<", 2], "project": ["is", "set"]}, pluck="project"))
		waiting = [s for s in frappe.get_all("Sales Order", filters={"docstatus": 1, "per_delivered": ["<", 100],
			"status": ["not in", ["Closed", "Completed", "On Hold"]]}, fields=["name", "customer_name", "delivery_date", "base_net_total",
			"transaction_date", "docstatus", "project"], order_by="delivery_date asc", limit=0)
			if s.name not in with_wo and s.name not in non_cabin and not (s.project and s.project in wo_projects)]
		stages.append(_stage("orders", "Orders to start", "🧾", [_late_row(s.customer_name, f"due {s.delivery_date or '?'}"
			+ (" · draft order" if s.docstatus == 0 else ""), s.base_net_total, "Sales Order", s.name, s.delivery_date, 0, opened=s.transaction_date)
			for s in waiting], sum(flt(s.base_net_total) for s in waiting), go="order_board", kind="money"))
	jobs = _job_cards(workstation)
	by = {name: [] for name, _i, _w in FACTORY}
	for j in jobs:
		stage = _factory_stage(j.operation)
		if stage:
			by[stage].append(j)
	for name, icon, _w in FACTORY:
		rows = []
		for j in by[name]:
			since = j.expected_end_date or j.creation
			r = _late_row(wo_label(j.work_order, j.name), f"{j.work_order or j.name} · {j.operation} · {j.status} · {j.workstation or ''}", None, "Job Card", j.name,
				since, 0 if j.expected_end_date else TARGET_DAYS.get(name), opened=j.creation)
			if j.status == "Work In Progress" and r["c"] != "red":
				r["c"] = "amber"
			rows.append(r)
		stages.append(_stage(name.lower().replace(" ", "_"), name, icon, rows, go=go))
	if not workstation:
		done = frappe.get_all("Work Order", filters={"docstatus": 1, "status": "Completed"}, fields=["name", "item_name", "sales_order", "modified"], limit=0)
		delivered = set(frappe.get_all("Delivery Note Item", filters={"docstatus": 1, "against_sales_order": ["in", [w.sales_order for w in done if w.sales_order] or [""]]},
			pluck="against_sales_order"))
		ready = [w for w in done if not w.sales_order or w.sales_order not in delivered]
		stages.append(_stage("dispatch", "Ready to dispatch", "🚚", [_late_row(wo_label(w.name, w.item_name), f"{w.name} · {w.sales_order or ''}", None, "Work Order", w.name,
			w.modified, 2) for w in ready], go="ready_dispatch"))
	return stages


def subcontractor(user: str) -> list[dict]:
	ws = frappe.db.get_value("SK App User", {"user": user}, "workstation")
	if not ws:
		return []
	jobs = frappe.get_all("Job Card", filters={"workstation": ws, "docstatus": ["<", 2]},
		fields=["name", "operation", "status", "work_order", "expected_end_date", "creation", "modified", "docstatus"], order_by="creation asc", limit=0)
	start = get_first_day(getdate())

	def rows(items, target=None):
		out = []
		for j in items:
			r = _late_row(wo_label(j.work_order, j.name), f"{j.work_order or j.name} · {j.operation or ''}", None, None, None, j.expected_end_date or j.creation, 0 if j.expected_end_date else target, opened=j.creation)
			out.append(r)
		return out

	waiting = [j for j in jobs if j.docstatus == 0 and j.status in ("Open", "Material Transferred")]
	working = [j for j in jobs if j.docstatus == 0 and j.status in ("Work In Progress", "On Hold")]
	done = [j for j in jobs if (j.docstatus == 1 or j.status == "Completed") and getdate(j.modified) >= start]
	return [_stage("waiting", "My jobs waiting", "⏳", rows(waiting, 2), go="my_jobs"),
		_stage("working", "In progress", "🛠️", rows(working, 3), go="my_jobs"),
		_stage("done", "Done this month (photo)", "✅", [_row(wo_label(j.work_order, j.name), f"{j.work_order or j.name} · {j.operation or ''}") for j in done], go="my_jobs")]


def stores(user: str) -> list[dict]:
	from sk_app.store import low_stock

	issue = frappe.get_all("Material Request", filters={"docstatus": 1, "material_request_type": "Material Issue", "status": ["in", ["Pending", "Partially Ordered"]]},
		fields=["name", "schedule_date", "transaction_date", "owner"], order_by="schedule_date asc", limit=0)
	from sk_app.store import material_pos

	to_receive = frappe.get_all("Purchase Order", filters={"docstatus": 1, "status": ["in", ["To Receive and Bill", "To Receive"]], **material_pos()},
		fields=["name", "supplier_name", "schedule_date", "grand_total", "transaction_date"], order_by="schedule_date asc", limit=0)
	moved = frappe.get_all("Stock Entry", filters={"posting_date": nowdate(), "docstatus": ["<", 2]}, fields=["name", "stock_entry_type", "total_outgoing_value"])
	low = _safe(lambda: low_stock(user), []) or []
	reorder = frappe.get_all("Material Request", filters={"docstatus": ["<", 2], "material_request_type": "Purchase", "status": ["in", ["Draft", "Pending", "Partially Ordered"]]},
		fields=["name", "schedule_date", "transaction_date"], order_by="transaction_date asc", limit=0)
	dispatch = frappe.get_all("Sales Order", filters={"docstatus": 1, "status": ["in", ["To Deliver and Bill", "To Deliver"]]},
		fields=["name", "customer_name", "delivery_date", "base_net_total", "transaction_date"], order_by="delivery_date asc", limit=0)
	return [
		_stage("requests", "Requests to issue", "📋", [_late_row(m.name, _name(m.owner), None, "Material Request", m.name, m.schedule_date, 0, opened=m.transaction_date) for m in issue], go="store_requests"),
		_stage("receive", "To receive", "🚚", [_late_row(p.supplier_name, f"due {p.schedule_date}", p.grand_total, "Purchase Order", p.name, p.schedule_date, 0, opened=p.transaction_date)
			for p in to_receive], sum(flt(p.grand_total) for p in to_receive), go="receive"),
		_stage("issued", "Issued / moved today", "📤", [_row(m.stock_entry_type, "", m.total_outgoing_value, "Stock Entry", m.name) for m in moved], go="issue"),
		_stage("low", "Low stock", "⚠️", [_row(r["item_name"] or r["item_code"], f"{r['warehouse']} · have {r['qty']} / level {r['level']}", None,
			"Item", r["item_code"], "red") for r in low], go="low_stock"),
		_stage("reorder", "Sent to Purchase", "🛒", [_late_row(m.name, str(m.schedule_date or ""), None, "Material Request", m.name, m.transaction_date, 2)
			for m in reorder], go="store_requests"),
		_stage("dispatch", "To dispatch", "🚛", [_late_row(s.customer_name, f"due {s.delivery_date}", s.base_net_total, "Sales Order", s.name, s.delivery_date, 0, opened=s.transaction_date)
			for s in dispatch], go="dispatch"),
	]


def purchase(user: str) -> list[dict]:
	from sk_app.logins import profile_functions
	from sk_app.purchase import po_limit

	reqs = frappe.get_all("Material Request", filters={"docstatus": 1, "material_request_type": "Purchase", "status": ["in", ["Pending", "Partially Ordered"]]},
		fields=["name", "schedule_date", "transaction_date"], order_by="transaction_date asc", limit=0)
	rfq = frappe.get_all("Supplier Quotation", filters={"docstatus": ["<", 2], "transaction_date": [">=", add_days(nowdate(), -30)]},
		fields=["name", "supplier_name", "grand_total", "transaction_date", "status"], limit=0) if _has("Supplier Quotation") else []
	from sk_app.store import material_pos

	mat = material_pos()  # labour POs: own chain (Rushi → CEO → GRN when the job is done)
	draft = frappe.get_all("Purchase Order", filters={"docstatus": 0, **mat}, fields=["name", "supplier_name", "grand_total", "creation"], order_by="creation asc", limit=0)
	sent = frappe.get_all("Purchase Order", filters={"docstatus": 1, "status": ["in", ["To Receive and Bill", "To Receive"]], **mat},
		fields=["name", "supplier_name", "grand_total", "schedule_date", "transaction_date"], order_by="schedule_date asc", limit=0)
	got = frappe.get_all("Purchase Receipt", filters={"docstatus": ["<", 2], "posting_date": [">=", get_first_day(getdate())], **material_pos("Purchase Receipt")},
		fields=["name", "supplier_name", "grand_total", "posting_date", "per_billed"], limit=0)
	bills = frappe.get_all("Purchase Invoice", filters={"docstatus": 0}, fields=["name", "supplier_name", "grand_total", "creation"], limit=0)
	limit = po_limit()
	ceo = user == "Administrator" or "Management" in profile_functions(user)
	return [
		_stage("requests", "Buy requests", "📋", [_late_row(m.name, f"need by {m.schedule_date}", None, "Material Request", m.name, m.transaction_date, 2) for m in reqs], go="buy_requests"),
		_stage("rates", "Rates (30 days)", "💬", [_row(q.supplier_name, f"{q.status} · {q.transaction_date}", q.grand_total, "Supplier Quotation", q.name) for q in rfq], go="compare"),
		_stage("approval", "PO to approve", "✅", [_late_row(p.supplier_name, "needs CEO OK" if flt(p.grand_total) > limit else "draft", p.grand_total,
			"Purchase Order", p.name, p.creation, 1) for p in draft], sum(flt(p.grand_total) for p in draft), go="po_approvals" if ceo else "po_follow_up", kind="money"),
		_stage("sent", "PO sent, to come", "📦", [_late_row(p.supplier_name, f"due {p.schedule_date}", p.grand_total, "Purchase Order", p.name, p.schedule_date, 0, opened=p.transaction_date)
			for p in sent], sum(flt(p.grand_total) for p in sent), go="po_follow_up", kind="money"),
		_stage("received", "Received this month", "🚚", [_row(r.supplier_name, f"{r.posting_date} · billed {round(flt(r.per_billed))}%", r.grand_total,
			"Purchase Receipt", r.name, None if flt(r.per_billed) >= 100 else "amber") for r in got], go="bills"),
		_stage("bills", "Bills to match", "🧾", [_late_row(b.supplier_name, "draft bill", b.grand_total, "Purchase Invoice", b.name, b.creation, 2) for b in bills], go="bills"),
	]


def quality(user: str) -> list[dict]:
	inspect = [j for j in _job_cards() if _factory_stage(j.operation) == "Final inspection"]
	stages = [_stage("inspect", "Inspection due", "🔍", [_late_row(wo_label(j.work_order, j.name), f"{j.work_order or j.name} · {j.status}", None, "Job Card", j.name,
		j.expected_end_date or j.creation, 0 if j.expected_end_date else 1, opened=j.creation) for j in inspect], go="final_check")]
	if _has("Non Conformance"):
		ncs = frappe.get_all("Non Conformance", filters={"status": "Open"}, fields=["name", "subject", "creation"], order_by="creation asc", limit=0)
		stages.append(_stage("nc", "Problems to fix", "❗", [_late_row(n.subject, "Non Conformance", None, "Non Conformance", n.name, n.creation, 7) for n in ncs], go="non_conformance"))
	if _has("Issue"):
		issues = frappe.get_all("Issue", filters={"status": ["in", ["Open", "Replied"]]}, fields=["name", "subject", "customer", "opening_date"], limit=0)
		stages.append(_stage("complaints", "Customer complaints", "🛠️", [_late_row(i.subject, i.customer or "", None, "Issue", i.name, i.opening_date, 3) for i in issues], go="complaints"))
	return stages


def accounts(user: str) -> list[dict]:
	start = get_first_day(getdate())
	orders = dashboards._orders(start, getdate())
	tally = dashboards._tally_sales(start, getdate())
	sis = frappe.get_all("Sales Invoice", filters={"docstatus": 1, "is_return": 0, "is_opening": ["!=", "Yes"], "posting_date": [">=", start]}, fields=["name", "customer_name", "base_net_total", "posting_date"])
	dues = dashboards._receivables()
	old = [d for d in dues if d.ages["Over 60 days"] > 0.5]
	got = frappe.get_all("Payment Entry", filters={"payment_type": "Receive", "docstatus": 1, "posting_date": [">=", start]}, fields=["name", "party_name", "paid_amount", "posting_date"])
	tally_in = frappe.get_all("Journal Entry", filters={"docstatus": 1, "posting_date": [">=", start], "user_remark": ["like", "Tally Receipt%"]},
		fields=["name", "user_remark", "total_debit", "posting_date"])
	pay = dashboards._party_dues("Supplier")
	invoiced = [_row(s.customer_name, str(s.posting_date), s.base_net_total, "Sales Invoice", s.name) for s in sis] + \
		[_row(t.customer_name, f"{t.posting_date} · Tally {t.voucher}", t.amount, "Journal Entry", t.name) for t in tally]
	return [
		_stage("orders", "Orders this month", "🧾", [_row(o.customer_name, str(o.transaction_date), o.base_net_total, o.doctype, o.name) for o in orders],
			sum(flt(o.base_net_total) for o in orders), go="invoices", kind="money"),
		_stage("invoiced", "Invoiced this month", "🧮", invoiced, sum(flt(r["value"]) for r in invoiced), go="invoices", kind="money"),
		_stage("dues", "Receivables", "📥", [_row(d.customer_name, f"oldest bill {d.late} days", d.outstanding_amount, "Customer", d.name,
			"amber" if d.late > 30 else None) for d in dues], sum(flt(d.outstanding_amount) for d in dues), go="to_collect", kind="money", late_rows=[]),
		_stage("over60", "Over 60 days", "⏰", [{**_row(d.customer_name, f"oldest bill {d.late} days", d.ages["Over 60 days"], "Customer", d.name, "red"), "days": d.late}
			for d in old], sum(d.ages["Over 60 days"] for d in old), go="to_collect", kind="money"),
		_stage("collected", "Collected this month", "💰", [_row(p.party_name, str(p.posting_date), p.paid_amount, "Payment Entry", p.name) for p in got]
			+ [_row((j.user_remark or "").split("|", 1)[-1].strip(), f"{j.posting_date} · Tally receipt", j.total_debit, "Journal Entry", j.name) for j in tally_in],
			sum(flt(p.paid_amount) for p in got) + sum(flt(j.total_debit) for j in tally_in), go="cash_today", kind="money"),
		_stage("to_pay", "Bills to pay", "📤", [_row(p.supplier_name, f"oldest bill {p.late} days", p.outstanding_amount, "Supplier", p.name,
			"amber" if p.late > 30 else None) for p in pay], sum(flt(p.outstanding_amount) for p in pay), go="to_pay", kind="money", late_rows=[]),
	]


def hr(user: str) -> list[dict]:
	from sk_app import hr as hr_mod

	day = _safe(lambda: hr_mod.today(user), None) or {"groups": {}}
	g = day.get("groups") or {}

	def people(key, c=None):
		return [_row(x.get("name") or x.get("employee"), x.get("in") or x.get("leave_type") or "", None, "Employee", x.get("employee"), c) for x in g.get(key) or []]

	leave = frappe.get_all("Leave Application", filters={"status": "Open", "docstatus": 0}, fields=["name", "employee_name", "from_date", "creation"]) if _has("Leave Application") else []
	claims = frappe.get_all("Expense Claim", filters={"approval_status": "Draft", "docstatus": 0}, fields=["name", "employee_name", "total_claimed_amount", "creation"]) if _has("Expense Claim") else []
	fixes = _safe(lambda: hr_mod.fix_requests(user), []) or []
	return [
		_stage("present", "Present today", "🕘", people("present"), go="attendance"),
		_stage("late", "Late today", "⏰", people("late", "amber"), go="attendance"),
		_stage("absent", "No check-in yet", "❔", people("no_checkin", "red"), go="attendance"),
		_stage("leave", "Leave to approve", "🌴", [_late_row(l.employee_name, f"from {l.from_date}", None, "Leave Application", l.name, l.creation, 1) for l in leave], go="leave_expense"),
		_stage("claims", "Expense claims", "🧾", [_late_row(c.employee_name, "claim", c.total_claimed_amount, "Expense Claim", c.name, c.creation, 2) for c in claims],
			sum(flt(c.total_claimed_amount) for c in claims), go="leave_expense"),
		_stage("fixes", "Attendance fixes asked", "🔧", [_row(f.get("text") or "", str(f.get("date") or ""), None, "Employee", f.get("employee"), "amber") for f in fixes], go="attendance"),
	]


def ai(user: str) -> list[dict]:
	from sk_app import ai_desk

	box = _safe(lambda: ai_desk.inbox(user), None) or {"new": [], "working": []}
	tasks = frappe.get_all("Task", filters={"status": ["not in", ["Cancelled"]], "project": ["is", "set"]}, fields=["name", "subject", "status", "exp_end_date", "modified", "creation"], limit=0)
	planned = [t for t in tasks if t.status in ("Open", "Template")]
	working = [t for t in tasks if t.status in ("Working", "Pending Review", "Overdue")]
	done = [t for t in tasks if t.status == "Completed" and getdate(t.modified) >= get_first_day(getdate())]
	task_row = lambda t: _late_row(t.subject, t.status, None, "Task", t.name, t.exp_end_date, 0, opened=t.creation)  # noqa: E731
	return [
		_stage("ideas", "New ideas / problems", "📥", [_row(i["title"], i["by"], None, i["doctype"], i["name"], "amber") for i in box["new"]], go="improvement_inbox"),
		_stage("sorted", "Being fixed", "🔧", [_row(i["title"], i.get("category") or "", None, i["doctype"], i["name"]) for i in box["working"]], go="improvement_inbox"),
		_stage("planned", "ERP tasks planned", "🗂️", [task_row(t) for t in planned], go="projects"),
		_stage("in_work", "ERP tasks in work", "⚙️", [task_row(t) for t in working], go="projects"),
		_stage("live", "Done this month", "✅", [_row(t.subject, "Completed", None, "Task", t.name) for t in done], go="projects"),
	]


BUILDERS = {"Sales": sales, "Marketing": sales, "Machine Shifting": lambda u: sales(u, segments.NON_CABIN), "Production": factory,
	"Subcontractor": subcontractor, "Stores": stores, "Purchase": purchase, "Quality": quality, "Accounts": accounts, "HR": hr, "AI": ai}
CEO_ORDER = [("Sales", "Sales"), ("Machine Shifting", "Non-Cabin (Aditya)"), ("Production", "Factory"), ("Stores", "Stores"),
	("Purchase", "Purchase"), ("Quality", "Quality"), ("Accounts", "Accounts"), ("HR", "HR"), ("AI", "AI & ERP")]


def _flow(function: str, user: str, label=None) -> dict | None:
	build = BUILDERS.get(function)
	if not build:
		return None
	try:
		stages = build(user) or []
	except Exception as e:
		# 27-Oct: an error used to leave the arrows blank; now the screen says so (and the log keeps it)
		frappe.log_error(f"SK App flow {function}")
		return {"function": function, "src": function, "label": label, "stages": [], "error": str(e)[:200]}
	if not stages:
		return None
	return {"function": function, "src": function, "label": label, "stages": stages}


def for_user(user: str, functions: list[str]) -> dict:
	"""Every flow of the person's functions (point 17). The CEO gets one flow per function."""
	out = []
	if "Management" in functions:
		out = [f for f in (_flow(fn, user, label) for fn, label in CEO_ORDER) if f]
		for f in out:
			f["function"] = "Management"
	seen = set()
	for fn in functions:
		if fn == "Management" or fn in seen or fn not in BUILDERS:
			continue
		if fn == "Marketing" and "Sales" in functions:
			continue  # same CRM flow once
		seen.add(fn)
		f = _flow(fn, user)
		if f:
			out.append(f)
	return {"flows": out, "at": str(now_datetime())[:16]}


def stage_rows(user: str, functions: list[str], src: str, key: str) -> dict:
	"""Every record of one box (Home sends only the first ROWS; SK 27-Oct: "total leads 260 but showing 60 only")."""
	if src not in BUILDERS or not ("Management" in functions or src in functions or (src == "Marketing" and "Sales" in functions)):
		frappe.throw("Not your flow", frappe.PermissionError)
	frappe.flags.sk_flow_all = True
	try:
		stages = BUILDERS[src](user) or []
	finally:
		frappe.flags.sk_flow_all = False
	st = next((s for s in stages if s["key"] == key), None)
	return {"rows": st["rows"] if st else [], "count": st["count"] if st else 0}
