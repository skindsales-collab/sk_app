"""Purchase requisition (SK 27-Oct-2026): every purchase starts as a requisition, the CEO approves it, a PO is made
only from an approved requisition (same ERP item codes) and Store receives only against that PO. All of it is the
ERPNext chain Material Request → Purchase Order → Purchase Receipt → Purchase Invoice.

- One form with Planned / Urgent; project / cabin code; the form shows stock, minimum order qty, re-order level and
  last rate. Raised by Store (Yogesh) or Purchase (Aarti).
- Material that came without a PO: Store raises an urgent requisition with the challan photo; same route.
- The CEO's approval screen shows the estimated value; for Urgent also the last rate and the best two quotes.
"""

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, getdate, now_datetime, nowdate

from sk_app.store import STORE, _company, _default_store, _todo, _users_with_function, attach, need, uom

MANAGEMENT = "Management"
MAX_ITEMS = 20
RAISERS = (STORE, "Purchase", MANAGEMENT, "HR")  # SK 28-Oct: Aarti (HR, acting purchase manager)
WAITING, APPROVED, REJECTED = "Waiting CEO", "Approved", "Rejected"
PRIORITIES = ("Planned", "Urgent")


def ensure_setup():
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	create_custom_fields({
		"Material Request": [
			{"fieldname": "sk_priority", "label": "Planned / Urgent", "fieldtype": "Select", "options": "Planned\nUrgent",
				"default": "Planned", "insert_after": "material_request_type", "in_list_view": 1, "in_standard_filter": 1},
			{"fieldname": "sk_approval", "label": "CEO approval", "fieldtype": "Select", "options": f"\n{WAITING}\n{APPROVED}\n{REJECTED}",
				"insert_after": "sk_priority", "read_only": 1, "in_list_view": 1, "in_standard_filter": 1, "allow_on_submit": 1},
			{"fieldname": "sk_cabin", "label": "Project / cabin code", "fieldtype": "Data", "insert_after": "sk_approval"},
			{"fieldname": "sk_without_po", "label": "Material came without PO", "fieldtype": "Check", "insert_after": "sk_cabin"},
			{"fieldname": "sk_supplier", "label": "Supplier (came without PO)", "fieldtype": "Link", "options": "Supplier",
				"insert_after": "sk_without_po", "depends_on": "sk_without_po"},
			{"fieldname": "sk_approved_value", "label": "Approved value (estimate)", "fieldtype": "Currency",
				"insert_after": "sk_supplier", "read_only": 1, "allow_on_submit": 1},
			{"fieldname": "sk_approved_by", "label": "Approved / rejected by", "fieldtype": "Link", "options": "User",
				"insert_after": "sk_approved_value", "read_only": 1, "allow_on_submit": 1},
		],
		"Purchase Order": [
			{"fieldname": "sk_needs_ceo", "label": "Waits for CEO approval", "fieldtype": "Check", "insert_after": "supplier",
				"read_only": 1, "in_standard_filter": 1},
		],
	}, update=True)
	# draft POs that waited for SK under the old Rs limit stay in the CEO's list
	from sk_app.purchase import po_limit

	for name in frappe.get_all("Purchase Order", filters={"docstatus": 0, "grand_total": [">", po_limit()]}, pluck="name"):
		frappe.db.set_value("Purchase Order", name, "sk_needs_ceo", 1, update_modified=False)


def _is_ceo(user: str) -> bool:
	from sk_app.logins import profile_functions

	return user == "Administrator" or MANAGEMENT in profile_functions(user)


# ---------- the form ----------

def last_rate(item_code: str) -> dict | None:
	from sk_app.purchase import last_rate as last

	return last(item_code)


def estimate_rate(item_code: str) -> float:
	last = last_rate(item_code)
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
	last = last_rate(item_code)
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


def raise_request(user: str, items: list[dict], priority: str = "Planned", need_by=None, cabin=None, note=None,
		photo=None, goods_photo=None, without_po=0, supplier=None, bill_no=None) -> dict:
	"""Save the requisition as a draft Material Request (Purchase) waiting for the CEO."""
	need(user, *RAISERS)
	if priority not in PRIORITIES:
		frappe.throw(_("Pick Planned or Urgent"))
	rows = [i for i in items or [] if i.get("item_code") and flt(i.get("qty")) > 0]
	if not rows:
		frappe.throw(_("Please pick the item and quantity"))
	if not (note or "").strip() and not (cint(without_po) and bill_no):
		frappe.throw(_("Please say why it is needed (reason)"))  # SK 28-Oct mandatory gate
	if len(rows) > MAX_ITEMS:  # SK 28-Oct (Rev 1 point 12): up to 20 items on one requisition
		frappe.throw(_("Up to {0} items on one requisition; please send the rest on a second one").format(MAX_ITEMS))
	if cint(without_po):
		priority = "Urgent"
		if not supplier or not frappe.db.exists("Supplier", supplier):
			frappe.throw(_("Material came without PO: please pick the supplier"))
	need_by = getdate(need_by or (nowdate() if priority == "Urgent" else add_days(nowdate(), 7)))
	if need_by < getdate():
		need_by = getdate()
	cabin = (cabin or "").strip()
	link = {}
	if cabin and frappe.db.exists("Sales Order", cabin):
		link = {"sales_order": cabin}
	elif cabin and frappe.db.exists("DocType", "Project") and frappe.db.exists("Project", cabin):
		link = {"project": cabin}
	mr = frappe.new_doc("Material Request")
	mr.update({"material_request_type": "Purchase", "company": _company(), "transaction_date": nowdate(), "schedule_date": need_by,
		"sk_priority": priority, "sk_approval": WAITING, "sk_cabin": cabin or None, "sk_without_po": cint(without_po),
		"sk_supplier": supplier if cint(without_po) else None})
	if mr.meta.has_field("sk_reason"):
		mr.sk_reason = (note or "").strip() or _("Material came without PO, bill / challan {0}").format(bill_no)
	for i in rows:
		rate = estimate_rate(i["item_code"])
		mr.append("items", {"item_code": i["item_code"], "qty": flt(i["qty"]), "schedule_date": need_by,
			"warehouse": i.get("warehouse") or _default_store(i["item_code"], mr.company), "rate": rate,
			"amount": rate * flt(i["qty"]), **uom(i["item_code"]), **link})
	mr.flags.ignore_permissions = True
	mr.insert()
	text = [x for x in ((note or "").strip(), bill_no and _("Supplier bill / challan no: {0}").format(bill_no),
		cint(without_po) and _("Material came without PO from {0}").format(frappe.db.get_value("Supplier", supplier, "supplier_name")))
		if x]
	if text:
		mr.add_comment("Comment", "\n".join(text))
	attach(photo, "Material Request", mr.name, user)
	attach(goods_photo, "Material Request", mr.name, user)
	who = frappe.utils.get_fullname(user)
	for ceo in _ceos():
		if ceo != user:
			_todo(ceo, "Material Request", mr.name, _("{0} purchase requisition {1} from {2}: please approve").format(
				_(priority), mr.name, who))
	return {"name": mr.name, "value": _value(mr), "priority": priority}


def _ceos() -> list[str]:
	return _users_with_function(MANAGEMENT) or [u for u in frappe.get_all("Has Role",
		filters={"role": "System Manager", "parenttype": "User"}, pluck="parent") if u != "Administrator"]


def _value(mr) -> float:
	return sum(flt(i.qty) * flt(i.rate) for i in mr.items)


def from_store_request(user: str, rows: list[dict], reason: str, priority: str = "Planned"):
	"""Short / low stock found by Store: the same requisition route (waits for the CEO)."""
	r = raise_request(user, [{"item_code": x["item_code"], "qty": flt(x.get("short") or x.get("qty")), "warehouse": x.get("warehouse")}
		for x in rows], priority, need_by=max((getdate(x["needed_by"]) for x in rows if x.get("needed_by")), default=None),
		note=reason or _("Short in store"))
	return frappe.get_doc("Material Request", r["name"])


# ---------- the CEO ----------

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
			last = last_rate(i.item_code)
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


def decide(user: str, name: str, approve, note=None) -> dict:
	need(user, MANAGEMENT)
	mr = frappe.get_doc("Material Request", name)
	if mr.docstatus != 0 or mr.sk_approval != WAITING:
		frappe.throw(_("{0} is already decided").format(name))
	frappe.db.set_value("ToDo", {"reference_type": "Material Request", "reference_name": name, "status": "Open"}, "status", "Closed")
	if not cint(approve):
		if not (note or "").strip():
			frappe.throw(_("Please give the reason"))
		frappe.db.set_value("Material Request", name, {"sk_approval": REJECTED, "sk_approved_by": user})
		mr.add_comment("Comment", _("Rejected by CEO: {0}").format(note.strip()))
		_todo(mr.owner, "Material Request", name, _("Requisition {0} rejected: {1}").format(name, note.strip()))
		return {"name": name, "status": REJECTED}
	mr.sk_approval = APPROVED
	mr.sk_approved_by = user
	mr.sk_approved_value = _value(mr)
	mr.flags.ignore_permissions = True
	mr.flags.sk_ceo_ok = True
	mr.save()
	mr.submit()
	mr.add_comment("Comment", _("Approved by CEO") + (f": {note.strip()}" if (note or "").strip() else ""))
	for who in _users_with_function("Purchase"):
		_todo(who, "Material Request", name, _("Approved requisition {0}: make the PO").format(name))
	if mr.owner != user:
		_todo(mr.owner, "Material Request", name, _("Requisition {0} approved by CEO").format(name))
	return {"name": name, "status": APPROVED}


def check_submit(doc, method=None):
	"""Material Request (Purchase) is submitted only after the CEO's approval, in the app or in ERPNext."""
	if doc.material_request_type != "Purchase" or doc.flags.sk_ceo_ok or frappe.flags.in_install or frappe.flags.in_migrate:
		return
	if doc.sk_approval == APPROVED:
		return
	if _is_ceo(frappe.session.user):  # the CEO submitting it in ERPNext is the approval
		doc.sk_approval = APPROVED
		doc.sk_approved_by = frappe.session.user
		doc.sk_approved_value = _value(doc)
		return
	frappe.throw(_("A purchase requisition needs the CEO's approval (SK App → PO Approvals) before it is submitted"))


def check_po(doc, method=None):
	"""Purchase Order only from an approved requisition (SK 27-Oct), unless the CEO makes it."""
	if frappe.flags.in_install or frappe.flags.in_migrate or _is_ceo(frappe.session.user):
		return
	missing = [i.item_code for i in doc.items if not i.material_request
		or frappe.db.get_value("Material Request", i.material_request, "sk_approval") != APPROVED]
	if missing:
		frappe.throw(_("No CEO-approved purchase requisition for: {0}. Raise a requisition first.").format(", ".join(sorted(set(missing)))))


def check_receipt(doc, method=None):
	"""Store receives only against a PO; material without a PO goes through an urgent requisition first."""
	if doc.is_return or frappe.flags.in_install or frappe.flags.in_migrate or _is_ceo(frappe.session.user):
		return
	if any(not i.purchase_order for i in doc.items):
		frappe.throw(_("Receive only against a Purchase Order. Material without PO: SK App → Receive → Came without PO."))


# ---------- the PO ----------

def link_requests(po) -> None:
	"""PO rows without a requisition get the oldest approved, not yet ordered requisition row of the same item."""
	for row in po.items:
		if row.material_request:
			continue
		hit = frappe.db.sql("""select i.parent, i.name from `tabMaterial Request Item` i join `tabMaterial Request` m on m.name = i.parent
			where i.item_code = %s and m.docstatus = 1 and m.material_request_type = 'Purchase' and m.sk_approval = %s
			and i.qty > i.ordered_qty and m.status not in ('Stopped', 'Cancelled') order by m.creation asc limit 1""",
			(row.item_code, APPROVED), as_dict=True)
		if hit:
			row.material_request, row.material_request_item = hit[0].parent, hit[0].name


def approved_value(po) -> float:
	total = 0.0
	for row in po.items:
		if row.material_request_item:
			total += flt(row.qty) * flt(frappe.db.get_value("Material Request Item", row.material_request_item, "rate"))
	return total


def needs_ceo(po) -> str | None:
	"""Why this PO goes back to the CEO, else None (SK 28-Oct option 1: only when over 10% above the approved value)."""
	from sk_app.purchase import po_limit

	if any(not r.material_request for r in po.items):
		return _("no approved requisition for some items")
	ok = approved_value(po)
	if ok <= 0:
		return _("no estimate on the requisition") if flt(po.grand_total) > po_limit() else None
	if flt(po.net_total) > ok * 1.10:
		return _("{0}% above the approved value").format(round((flt(po.net_total) / ok - 1) * 100))
	return None


def po_from_request(user: str, request: str, supplier: str, rates: dict | None = None, schedule_date=None) -> dict:
	"""Purchase makes the PO straight from an approved requisition (e.g. material that came without PO)."""
	need(user, "Purchase", MANAGEMENT)
	from erpnext.stock.doctype.material_request.material_request import make_purchase_order

	mr = frappe.get_doc("Material Request", request)
	if mr.docstatus != 1 or mr.sk_approval != APPROVED:
		frappe.throw(_("{0} is not approved by the CEO yet").format(request))
	supplier = supplier or mr.sk_supplier
	if not supplier:
		frappe.throw(_("Please pick the supplier"))
	po = make_purchase_order(request)
	po.supplier = supplier
	po.schedule_date = getdate(schedule_date or max(getdate(mr.schedule_date), getdate()))
	for row in po.items:
		row.schedule_date = po.schedule_date
		if rates and flt(rates.get(row.item_code)) > 0:
			row.rate = flt(rates[row.item_code])
	po.set_missing_values()
	from sk_app.purchase import place_po

	return place_po(po, user)


# ---------- Store's tracking ----------

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


def badges(user: str, functions: list[str]) -> dict:
	out = {}
	if MANAGEMENT in functions:
		out["po_approvals"] = frappe.db.count("Material Request", {"docstatus": 0, "material_request_type": "Purchase", "sk_approval": WAITING})
	return {k: v for k, v in out.items() if v}
