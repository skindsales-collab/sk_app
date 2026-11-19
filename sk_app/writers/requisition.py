"""requisition screens (reads only). Plan A (SK 9-Nov): split out of purchase_screens.py, names unchanged."""

from frappe import _
from frappe.utils import add_days, cint, flt, getdate, nowdate
from sk_app.purchase_screens import _value, estimate_rate
from sk_app.requisition import APPROVED, MANAGEMENT, MAX_ITEMS, PRIORITIES, RAISERS, REJECTED, WAITING, _ceos, _is_ceo
from sk_app.store import _company, _todo, attach, need, uom, users_or_ceo
from sk_app.store_screens import _default_store
import frappe
from sk_app import purchase_screens


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
	from sk_app.store import material_pos

	# only the POs made before the 28-Oct rule (SK 1-Nov logic check B2: run on every migrate it re-flagged new POs
	# from approved requisitions, which need the CEO only when over 10% above the approved value)
	for name in frappe.get_all("Purchase Order", filters={"docstatus": 0, "grand_total": [">", po_limit()], "creation": ["<", "2026-10-28"],
			**material_pos()}, pluck="name"):
		frappe.db.set_value("Purchase Order", name, "sk_needs_ceo", 1, update_modified=False)

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
	for who in users_or_ceo("Purchase"):  # SK 1-Nov: never to nobody
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
	from sk_app.writers.purchase_order import place_po

	return place_po(po, user)
