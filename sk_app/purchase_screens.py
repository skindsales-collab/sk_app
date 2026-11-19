"""Purchase screens (reads only; the Purchase writers are writers/purchase_order.py and writers/purchase_screens.py).
Requests, last rates, suppliers, compare quotes, PO approvals, follow-up, badges.
Plan A step 3 (SK 9-Nov): split out of purchase.py; names unchanged. purchase.py keeps only the PO limit."""

from frappe.utils import add_days, flt, getdate, nowdate
from sk_app.purchase import PURCHASE, po_limit
from sk_app.store import material_pos, need
from sk_app.store_screens import material_requests
import frappe


def requests(user: str) -> list[dict]:
	need(user, PURCHASE)
	rows = material_requests(user, "purchase")
	for r in rows:
		mr = frappe.db.get_value("Material Request", r["request"], ["sk_priority", "sk_supplier"], as_dict=True) or {}
		r["supplier"] = mr.get("sk_supplier")  # material that came without PO: that supplier
		r["urgent"] = mr.get("sk_priority") == "Urgent" \
			or bool(r["needed_by"] and getdate(r["needed_by"]) <= getdate(add_days(nowdate(), 1))) or r["age_hours"] > 24
		last = last_rate(r["item_code"])
		r["last_rate"], r["last_supplier"] = (last["rate"], last["supplier"]) if last else (None, None)
	return sorted(rows, key=lambda r: (not r["urgent"], r["needed_by"] or "9999"))

def last_rate(item_code: str) -> dict | None:
	for dt, date in (("Purchase Order", "transaction_date"), ("Purchase Invoice", "posting_date")):
		rows = frappe.db.sql(f"""select p.supplier, i.rate, p.{date} as date from `tab{dt} Item` i
			join `tab{dt}` p on p.name = i.parent where p.docstatus = 1 and i.item_code = %s
			order by p.creation desc limit 1""", item_code, as_dict=True)
		if rows:
			return {**rows[0], "date": str(rows[0].date), "from": dt}
	return None

def last_rates(user: str, q: str | None = None) -> list[dict]:
	need(user, PURCHASE, "Stores")
	like = f"%{(q or '').strip()}%"
	rows = frappe.db.sql("""select i.item_code, i.item_name, p.supplier, i.rate, i.uom, p.posting_date as date
		from `tabPurchase Invoice Item` i join `tabPurchase Invoice` p on p.name = i.parent
		where p.docstatus = 1 and (i.item_name like %(q)s or i.item_code like %(q)s)
		union all
		select i.item_code, i.item_name, p.supplier, i.rate, i.uom, p.transaction_date as date
		from `tabPurchase Order Item` i join `tabPurchase Order` p on p.name = i.parent
		where p.docstatus = 1 and (i.item_name like %(q)s or i.item_code like %(q)s)
		order by date desc limit 200""", {"q": like}, as_dict=True)
	seen, out = set(), []
	for r in rows:
		key = (r.item_code, r.supplier)
		if key not in seen:
			seen.add(key)
			out.append({**r, "date": str(r.date)})
	return out[:60]

def suggest_suppliers(user: str, item_code: str) -> list[dict]:
	"""Suppliers who sold this item before (best first), then others of the same supplier group, up to 6."""
	need(user, PURCHASE)
	past = frappe.db.sql("""select supplier, count(*) n, max(d) last from (
			select p.supplier, p.posting_date d from `tabPurchase Invoice Item` i join `tabPurchase Invoice` p on p.name = i.parent
			where p.docstatus = 1 and i.item_code = %(item)s
			union all
			select p.supplier, p.transaction_date d from `tabPurchase Order Item` i join `tabPurchase Order` p on p.name = i.parent
			where p.docstatus = 1 and i.item_code = %(item)s
			union all
			select q.supplier, q.transaction_date d from `tabSupplier Quotation Item` i join `tabSupplier Quotation` q on q.name = i.parent
			where q.docstatus < 2 and i.item_code = %(item)s) x
		group by supplier order by n desc, last desc limit 6""", {"item": item_code}, as_dict=True)
	names = [r.supplier for r in past]
	groups = {g for g in frappe.get_all("Supplier", filters={"name": ["in", names or [""]]}, pluck="supplier_group") if g}
	if len(names) < 6 and groups:
		names += frappe.get_all("Supplier", filters={"supplier_group": ["in", list(groups)], "disabled": 0,
			"name": ["not in", names or [""]]}, pluck="name", limit=6 - len(names))
	return [_supplier_row(s) for s in names]

def _has_gstin() -> bool:
	return frappe.get_meta("Supplier").has_field("gstin")  # India Compliance app adds it

def _supplier_row(name: str) -> dict:
	fields = ["name", "supplier_name", "supplier_group", "mobile_no", "email_id"] + (["gstin"] if _has_gstin() else [])
	s = frappe.db.get_value("Supplier", name, fields, as_dict=True) or {}
	last = frappe.get_all("Purchase Invoice", filters={"supplier": name, "docstatus": 1}, pluck="posting_date",
		order_by="posting_date desc", limit=1)
	last = last[0] if last else None
	return {**s, "last_bill": str(last) if last else None}

def suppliers(user: str, q: str | None = None) -> list[dict]:
	need(user, PURCHASE, "Stores", "Accounts")
	like = f"%{(q or '').strip()}%"
	gst = _has_gstin()
	return frappe.get_all("Supplier", filters={"disabled": 0},
		or_filters=[["supplier_name", "like", like]] + ([["gstin", "like", like]] if gst else []),
		fields=["name", "supplier_name", "supplier_group", "mobile_no"] + (["gstin"] if gst else []), order_by="supplier_name asc", limit=30)

def compare(user: str, item_code: str) -> dict:
	need(user, PURCHASE)
	quotes = frappe.db.sql("""select q.name, q.supplier, i.rate, i.qty, i.lead_time_days, q.transaction_date, q.valid_till, q.docstatus
		from `tabSupplier Quotation Item` i join `tabSupplier Quotation` q on q.name = i.parent
		where q.docstatus < 2 and i.item_code = %s and q.transaction_date >= %s order by i.rate asc""",
		(item_code, add_days(nowdate(), -30)), as_dict=True)
	last = last_rate(item_code)
	best = quotes[0] if quotes else None
	return {"item_code": item_code, "item_name": frappe.db.get_value("Item", item_code, "item_name"),
		"quotes": [{**q, "transaction_date": str(q.transaction_date), "valid_till": str(q.valid_till or "")} for q in quotes],
		"last": last, "saving": (flt(last["rate"]) - flt(best.rate)) * flt(best.qty) if (last and best) else None, "limit": po_limit()}

def approvals(user: str) -> list[dict]:
	"""Purchase Orders waiting for the CEO (over 10% above the approved requisition)."""
	need(user, "Management")
	rows = frappe.get_all("Purchase Order", filters={"docstatus": 0, "sk_needs_ceo": 1},
		fields=["name", "supplier_name", "grand_total", "schedule_date", "owner", "creation"], order_by="creation asc")
	for r in rows:
		r["why"] = frappe.db.get_value("Comment", {"reference_doctype": "Purchase Order", "reference_name": r.name,
			"content": ["like", "Waits for CEO%"]}, "content", order_by="creation desc")
	return rows

def follow_up(user: str) -> list[dict]:
	"""Orders due today or late, with the supplier's phone."""
	need(user, PURCHASE)
	pos = frappe.get_all("Purchase Order", filters={"docstatus": 1, "status": ["in", ["To Receive and Bill", "To Receive"]],
		"schedule_date": ["<=", nowdate()], **material_pos()}, fields=["name", "supplier", "supplier_name", "schedule_date", "grand_total"],
		order_by="schedule_date asc")
	for p in pos:
		p["days_late"] = (getdate() - getdate(p.schedule_date)).days
		p["mobile"] = frappe.db.get_value("Supplier", p.supplier, "mobile_no")
		p["items"] = ", ".join(frappe.get_all("Purchase Order Item", filters={"parent": p.name}, pluck="item_name", limit=3))
		p["schedule_date"] = str(p.schedule_date)
	return pos

def badges(user: str, functions: list[str]) -> dict:
	out = {}
	if PURCHASE in functions:
		out["buy_requests"] = len(material_requests(user, "purchase"))
		out["po_follow_up"] = frappe.db.count("Purchase Order", {"docstatus": 1, "status": ["in", ["To Receive and Bill", "To Receive"]],
			"schedule_date": ["<=", nowdate()], **material_pos()})
	if "Management" in functions:
		from sk_app.purchase_screens import req_badges

		out["po_approvals"] = frappe.db.count("Purchase Order", {"docstatus": 0, "sk_needs_ceo": 1}) \
			+ req_badges(user, functions).get("po_approvals", 0)
	return {k: v for k, v in out.items() if v}


# ---------- Plan A (SK 9-Nov): moved here unchanged from purchase_screens.py ----------
from frappe import _
from frappe.utils import add_days, flt, getdate, now_datetime, nowdate
from sk_app.requisition import APPROVED, MANAGEMENT, RAISERS, REJECTED, WAITING
from sk_app.store import need
import frappe


# SK 2-Nov: Accounts receives material; without a PO it raises the urgent requisition, the CEO approves, a PO is made

def req_last_rate(item_code: str) -> dict | None:
	from sk_app.purchase_screens import last_rate as last

	return last(item_code)

def estimate_rate(item_code: str) -> float:
	last = req_last_rate(item_code)
	return flt(last["rate"]) if last else flt(frappe.db.get_value("Item", item_code, "valuation_rate"))

def item_info(user: str, item_code: str) -> dict:
	"""What the form shows under the item: stock now, minimum order qty, re-order level, last rate, already asked."""
	need(user, *RAISERS)
	item = frappe.db.get_value("Item", item_code, ["item_name", "stock_uom", "min_order_qty", "safety_stock"], as_dict=True)
	if not item:
		frappe.throw(_("Item {0} not found").format(item_code))
	stock = sum(flt(x) for x in frappe.get_all("Bin", filters={"item_code": item_code}, pluck="actual_qty"))
	reorder = sum(flt(x) for x in frappe.get_all("Item Reorder", filters={"parent": item_code, "parenttype": "Item"},
		pluck="warehouse_reorder_level"))
	asked = frappe.db.sql("""select coalesce(sum(i.qty - i.ordered_qty), 0) from `tabMaterial Request Item` i
		join `tabMaterial Request` m on m.name = i.parent where i.item_code = %s and m.material_request_type = 'Purchase'
		and m.docstatus < 2 and coalesce(m.sk_approval, '') != %s and m.status not in ('Stopped', 'Cancelled', 'Ordered', 'Received')""",
		(item_code, REJECTED))[0][0]
	last = req_last_rate(item_code)
	return {"item_code": item_code, "item_name": item.item_name, "uom": item.stock_uom, "stock": stock,
		"min_order_qty": flt(item.min_order_qty), "reorder_level": reorder or flt(item.safety_stock),
		"already_asked": flt(asked), "last_rate": last and last["rate"], "last_supplier": last and last["supplier"],
		"last_date": last and str(last.get("date") or "")}

def cabins(user: str) -> list[dict]:
	"""Project / cabin codes to pick: open cabin orders (Sales Order) and open Projects."""
	need(user, *RAISERS)
	return cabin_codes()

def cabin_codes() -> list[dict]:
	out = []
	for so in frappe.get_all("Sales Order", filters={"docstatus": 1, "status": ["not in", ["Completed", "Closed", "Cancelled"]]},
			fields=["name", "customer_name"], order_by="delivery_date asc", limit=60):
		item = frappe.db.get_value("Sales Order Item", {"parent": so.name}, "item_name", order_by="idx asc")
		out.append({"code": so.name, "label": " · ".join(x for x in (so.name, so.customer_name, item) if x)})
	if frappe.db.exists("DocType", "Project"):
		for p in frappe.get_all("Project", filters={"status": "Open"}, fields=["name", "project_name"], limit=40):
			out.append({"code": p.name, "label": " · ".join(x for x in (p.name, p.project_name) if x and x != p.name) or p.name})
	return out

def _value(mr) -> float:
	return sum(flt(i.qty) * flt(i.rate) for i in mr.items)

def from_store_request(user: str, rows: list[dict], reason: str, priority: str = "Planned"):

	from sk_app.writers.requisition import raise_request
	"""Short / low stock found by Store: the same requisition route (waits for the CEO)."""
	r = raise_request(user, [{"item_code": x["item_code"], "qty": flt(x.get("short") or x.get("qty")), "warehouse": x.get("warehouse")}
		for x in rows], priority, need_by=max((getdate(x["needed_by"]) for x in rows if x.get("needed_by")), default=None),
		note=reason or _("Short in store"))
	return frappe.get_doc("Material Request", r["name"])

def quotes(item_code: str, limit: int = 2) -> list[dict]:
	"""Best recent supplier quotes for the item, one per supplier."""
	rows = frappe.db.sql("""select q.supplier, q.name, i.rate, q.transaction_date from `tabSupplier Quotation Item` i
		join `tabSupplier Quotation` q on q.name = i.parent where q.docstatus < 2 and i.item_code = %s and q.transaction_date >= %s
		order by i.rate asc""", (item_code, add_days(nowdate(), -60)), as_dict=True)
	out, seen = [], set()
	for r in rows:
		if r.supplier in seen:
			continue
		seen.add(r.supplier)
		out.append({"supplier": frappe.db.get_value("Supplier", r.supplier, "supplier_name") or r.supplier, "quote": r.name,
			"rate": flt(r.rate), "date": str(r.transaction_date)})
		if len(out) >= limit:
			break
	return out

def to_approve(user: str) -> list[dict]:
	need(user, MANAGEMENT)
	out = []
	for mr in frappe.get_all("Material Request", filters={"docstatus": 0, "material_request_type": "Purchase", "sk_approval": WAITING},
			fields=["name", "sk_priority", "sk_cabin", "sk_without_po", "sk_supplier", "schedule_date", "owner", "creation"],
			order_by="creation asc"):
		urgent = mr.sk_priority == "Urgent"
		items = []
		for i in frappe.get_all("Material Request Item", filters={"parent": mr.name},
				fields=["item_code", "item_name", "qty", "uom", "rate"], order_by="idx asc"):
			stock = sum(flt(x) for x in frappe.get_all("Bin", filters={"item_code": i.item_code}, pluck="actual_qty"))
			last = req_last_rate(i.item_code)
			items.append({**i, "amount": flt(i.qty) * flt(i.rate), "stock": stock,
				"min_order_qty": flt(frappe.db.get_value("Item", i.item_code, "min_order_qty")),
				"last_rate": last and last["rate"], "last_supplier": last and last["supplier"],
				"quotes": quotes(i.item_code) if urgent else []})
		comment = frappe.db.get_value("Comment", {"reference_doctype": "Material Request", "reference_name": mr.name,
			"comment_type": "Comment"}, "content", order_by="creation asc")
		out.append({**mr, "schedule_date": str(mr.schedule_date), "creation": str(mr.creation), "by": frappe.utils.get_fullname(mr.owner),
			"supplier_name": mr.sk_supplier and frappe.db.get_value("Supplier", mr.sk_supplier, "supplier_name"),
			"items": items, "value": sum(x["amount"] for x in items), "note": comment,
			"photos": frappe.get_all("File", filters={"attached_to_doctype": "Material Request", "attached_to_name": mr.name}, pluck="file_url"),
			"age_days": (now_datetime() - mr.creation).days})
	return sorted(out, key=lambda r: (r["sk_priority"] != "Urgent", r["creation"]))

def track(user: str, days: int = 60) -> list[dict]:
	"""Every requisition with its stage: Waiting CEO → Approved → PO made → Material in (or Rejected), days pending."""
	need(user, *RAISERS)
	since = add_days(nowdate(), -int(days))
	out = []
	for mr in frappe.get_all("Material Request", filters={"material_request_type": "Purchase", "docstatus": ["<", 2],
			"creation": [">=", since]}, fields=["name", "docstatus", "sk_priority", "sk_approval", "sk_cabin", "sk_without_po",
			"per_ordered", "per_received", "status", "owner", "creation", "schedule_date"], order_by="creation desc", limit=200):
		pos = frappe.db.sql("""select distinct p.name, p.docstatus, p.supplier_name, p.sk_needs_ceo from `tabPurchase Order Item` i
			join `tabPurchase Order` p on p.name = i.parent where i.material_request = %s and p.docstatus < 2""", mr.name, as_dict=True)
		if mr.sk_approval == REJECTED:
			stage = "rejected"
		elif mr.docstatus == 0:
			stage = "waiting_ceo"
		elif flt(mr.per_received) >= 100 or mr.status == "Received":
			stage = "material_in"
		elif any(p.docstatus == 1 for p in pos):
			stage = "po_made"
		elif pos:
			stage = "po_waiting_ceo" if any(p.sk_needs_ceo for p in pos) else "po_draft"
		else:
			stage = "approved"
		items = frappe.get_all("Material Request Item", filters={"parent": mr.name}, fields=["item_name", "qty", "uom"], order_by="idx asc")
		out.append({"name": mr.name, "stage": stage, "priority": mr.sk_priority or "Planned", "cabin": mr.sk_cabin,
			"without_po": mr.sk_without_po, "by": frappe.utils.get_fullname(mr.owner), "need_by": str(mr.schedule_date or ""),
			"days": (now_datetime() - mr.creation).days, "items": items, "pos": [{"name": p.name, "supplier": p.supplier_name} for p in pos],
			"received_pct": flt(mr.per_received)})
	return out

def req_badges(user: str, functions: list[str]) -> dict:
	out = {}
	if MANAGEMENT in functions:
		out["po_approvals"] = frappe.db.count("Material Request", {"docstatus": 0, "material_request_type": "Purchase", "sk_approval": WAITING})
	return {k: v for k, v in out.items() if v}
