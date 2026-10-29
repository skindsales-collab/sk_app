"""Labour for making a cabin (SK 28/29-Oct-2026): the standard labour rate sheet in ERPNext, one service PO per job,
approved by Rushi (rate) and then the CEO, the service GRN made by itself when the job is done, and the bill payable.
Shraddha pays it in ERPNext as usual (the app never enters money).

Rate sheet: SK Labour Rate, one row per cabin size (Rev-02, signed 03/10/2025: fabrication and painter per cabin,
carpenter per cabin or per sq ft of floor). Electrical per point (SK Electrical Points of the job card) and the extras
(extra window, partition, joint at site, plumbing fittings ...) are service items SUB-* with an Item Price in the
buying Price List "Subcontract Rates"; a row with a supplier is that subcontractor's own rate.
The workstation's subcontractor is the Supplier on Workstation.sk_supplier.

Flow, all ERPNext documents, live on each step:
1. Work Order submitted → per Job Card a draft service Purchase Order (sk_job_card) at the sheet's rate, booked to the
   cabin's Project and cost centre. Electrical: when the points are entered.
2. sk_bill_stage Waiting Rushi (checks / corrects rate and qty) → Waiting CEO → Approved: the PO is submitted.
3. Job Card completed (and PO approved) → Purchase Receipt (service GRN) against the PO, submitted.
4. Quality passed the stage → Purchase Invoice from the GRN, submitted: payable to the subcontractor; Accounts get a
   ToDo to pay.
Discuss puts a question on the PO (a Comment, ToDo to the subcontractor and Production); it waits until answered.
"""

import json
import re
from contextlib import contextmanager

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, get_fullname, getdate, nowdate

from sk_app.store import _todo, _users_with_function

PRICE_LIST = "Subcontract Rates"
CHECKER, CEO, APPROVED, REJECTED = "Waiting Rushi", "Waiting CEO", "Approved", "Rejected"
STAGES = (CHECKER, CEO, APPROVED, REJECTED)
RATE_EDITORS = ("Management", "Accounts")  # SK and Shraddha change the rates
PREFIX = "SUB-"
NO_SIZE = "⚠ rate not in the sheet · "
RATE_DOCTYPE = "SK Labour Rate"
RATE_FILE = "labour_rates_rev02.json"
TRADES = (("fabricat", "fabrication"), ("carpent", "carpenter"), ("paint", "painter"))  # operation word → sheet column


def ensure_setup():
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	job = {"fieldname": "sk_job_card", "label": "Labour job card", "fieldtype": "Link", "options": "Job Card",
		"insert_after": "supplier", "read_only": 1, "in_standard_filter": 1}
	stage = {"fieldname": "sk_bill_stage", "label": "Rate approval", "fieldtype": "Select", "options": "\n" + "\n".join(STAGES),
		"insert_after": "sk_job_card", "read_only": 1, "allow_on_submit": 1, "in_list_view": 1, "in_standard_filter": 1}
	question = {"fieldname": "sk_question", "label": "Open question", "fieldtype": "Small Text", "insert_after": "sk_bill_stage",
		"read_only": 1}
	create_custom_fields({
		"Purchase Order": [job, stage, question],
		"Purchase Receipt": [dict(job)],
		"Purchase Invoice": [job, stage, question],
		"Workstation": [
			{"fieldname": "sk_supplier", "label": "Subcontractor (supplier for labour POs)", "fieldtype": "Link", "options": "Supplier",
				"insert_after": "workstation_name"},
		],
		"SK App Settings": [
			{"fieldname": "sub_bill_checker", "label": "Labour POs: rate check (Rushi)", "fieldtype": "Link",
				"options": "User", "insert_after": "lead_owner_noncabin"},
		],
	}, update=True)
	if not frappe.db.exists("Price List", PRICE_LIST):
		frappe.get_doc({"doctype": "Price List", "price_list_name": PRICE_LIST, "buying": 1, "selling": 0, "enabled": 1,
			"currency": frappe.db.get_default("currency") or "INR"}).insert(ignore_permissions=True)
	for op in frappe.get_all("Operation", pluck="name"):
		code = service_item(op)
		try:
			_per_job(code)
		except Exception:
			frappe.log_error(title=f"SK App: labour item {code} to Nos")
	load_rates()
	_sac_on_labour_items()
	backfill()


# ---------- rate sheet ----------

def _is_electrical(operation: str | None) -> bool:
	from sk_app.production import _is_electrical

	return _is_electrical(operation)


def _is_inspection(operation: str | None) -> bool:
	return "inspection" in (operation or "").lower()  # Quality is in-house: no labour PO


def _trade(operation: str | None) -> str | None:
	op = (operation or "").lower()
	return next((col for word, col in TRADES if word in op), None)


def service_item(operation: str) -> str:
	"""SUB-<Operation>: the non-stock item the job is ordered on (per cabin, electrical per point)."""
	code = (PREFIX + operation)[:140]
	if not frappe.db.exists("Item", code):
		_new_item(code, _("{0} (labour)").format(operation), "Nos",
			_("Labour: {0}, rate per {1}").format(operation, "point" if _is_electrical(operation) else "cabin"))
	return code


def _new_item(code: str, name: str, uom: str, description: str):
	group = "Services" if frappe.db.exists("Item Group", "Services") else frappe.db.get_value("Item Group", {"is_group": 0}, "name")
	frappe.get_doc({"doctype": "Item", "item_code": code, "item_name": name[:140], "item_group": group, "stock_uom": uom,
		"is_stock_item": 0, "is_purchase_item": 1, "is_sales_item": 0, "description": description}).insert(ignore_permissions=True)


def _per_job(code: str):
	"""SK 29-Oct: the sheet is per cabin, so the job items are counted in Nos (they were per sq ft before any bill)."""
	if frappe.db.get_value("Item", code, "stock_uom") == "Nos":
		return
	if any(frappe.db.exists(dt, {"item_code": code}) for dt in ("Purchase Order Item", "Purchase Invoice Item", "Purchase Receipt Item")):
		return
	item = frappe.get_doc("Item", code)
	item.stock_uom = "Nos"
	item.uoms = []
	item.flags.ignore_permissions = True
	item.save()


SAC = "9988"  # manufacturing services on goods owned by others (labour job work); Accounts can change it per item


def _sac_on_labour_items():
	"""GST needs an HSN / SAC code on each PO / bill row (India Compliance): labour items without one get 9988."""
	if not frappe.get_meta("Item").has_field("gst_hsn_code") or not frappe.db.exists("GST HSN Code", SAC):
		return
	for code in frappe.get_all("Item", filters={"item_code": ["like", PREFIX + "%"], "gst_hsn_code": ["in", ["", None]]}, pluck="name"):
		frappe.db.set_value("Item", code, "gst_hsn_code", SAC)


def _sqft_uom() -> str:
	for u in ("Square Foot", "Sq Ft", "SqFt"):
		if frappe.db.exists("UOM", u):
			return u
	return frappe.get_doc({"doctype": "UOM", "uom_name": "Square Foot"}).insert(ignore_permissions=True).name


def _set_standard_price(item_code: str, value: float, uom: str):
	"""Standard (no supplier) rate, only when none is there yet: a rate the CEO / Accounts changed stays."""
	if not value or frappe.db.exists("Item Price", {"price_list": PRICE_LIST, "item_code": item_code, "supplier": ["in", ["", None]]}):
		return
	frappe.get_doc({"doctype": "Item Price", "price_list": PRICE_LIST, "item_code": item_code, "price_list_rate": value,
		"uom": uom}).insert(ignore_permissions=True)


def load_rates():
	"""SK's signed labour rate sheet (data/labour_rates_rev02.json) → SK Labour Rate rows, electrical per point and the
	extras as SUB-X-* service items with their Item Price. A row already on this revision is left as it is."""
	if not frappe.db.exists("DocType", RATE_DOCTYPE):
		return
	data = json.loads(frappe.read_file(frappe.get_app_path("sk_app", "data", RATE_FILE)))
	rev = data["revision"]
	for r in data["sizes"]:
		name = f"LR-{r['sr_no']}"
		if frappe.db.exists(RATE_DOCTYPE, name):
			if frappe.db.get_value(RATE_DOCTYPE, name, "revision") == rev:
				continue
			doc = frappe.get_doc(RATE_DOCTYPE, name)
		else:
			doc = frappe.new_doc(RATE_DOCTYPE)
		doc.update({"enabled": 1, "remark": None, **r, "revision": rev})
		doc.flags.ignore_permissions = True
		doc.save()
	for op in frappe.get_all("Operation", pluck="name"):
		if _is_electrical(op):
			_set_standard_price(service_item(op), flt(data.get("electrical_per_point")), "Nos")
	for x in data["extras"]:
		code = f"{PREFIX}X-{x['code']}"
		uom = _sqft_uom() if x["uom"] == "Square Foot" else x["uom"]
		if not frappe.db.exists("Item", code):
			_new_item(code, x["name"], uom, _("Labour extra ({0}): {1}, rate per {2}. {3}").format(x["trade"], x["name"],
				"sq ft" if uom != "Nos" else "no.", x.get("remark") or rev))
		_set_standard_price(code, flt(x["rate"]), uom)


SIZE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:ft|')?\s*[x×*]\s*(\d+(?:\.\d+)?)(?:\s*(?:ft|')?\s*[x×*]\s*(\d+(?:\.\d+)?))?", re.I)


def size_of(text: str | None) -> tuple | None:
	"""'Cabin 314 · HD · 12ft x 10ft x 8.6ft' → (12, 10, 8.6); height None when not written."""
	m = SIZE_RE.search(text or "")
	return (flt(m.group(1)), flt(m.group(2)), flt(m.group(3)) or None) if m else None


def sqft(text: str | None) -> float:
	s = size_of(text)
	return s[0] * s[1] if s else 0


def sheet_row(text: str | None):
	"""The sheet's row for the cabin size (10 x 8 and 8 x 10 are the same); the nearest height when two match."""
	s = size_of(text)
	if not s or not frappe.db.exists("DocType", RATE_DOCTYPE):
		return None
	key = sorted(s[:2])
	rows = [r for r in frappe.get_all(RATE_DOCTYPE, filters={"enabled": 1}, fields=["name", "cabin_size", "length", "width", "height",
		"fabrication", "carpenter", "carpenter_per_sqft", "painter"], order_by="sr_no asc") if sorted((flt(r.length), flt(r.width))) == key]
	return min(rows, key=lambda r: abs(flt(r.height) - (s[2] or 8.6))) if rows else None


def _price(item_code: str, supplier: str | None) -> float:
	if supplier is None:
		filters = {"price_list": PRICE_LIST, "item_code": item_code, "supplier": ["in", ["", None]]}
	else:
		filters = {"price_list": PRICE_LIST, "item_code": item_code, "supplier": supplier}
	return flt(frappe.db.get_value("Item Price", filters, "price_list_rate", order_by="valid_from desc"))


def rate(item_code: str, supplier: str | None) -> float:
	"""The subcontractor's own rate, else the standard rate of the price list."""
	return (_price(item_code, supplier) if supplier else 0) or _price(item_code, None)


def check_rate_edit(doc, method=None):
	"""Item Price / SK Labour Rate: only SK (Management) and Accounts change the labour rates."""
	if doc.doctype == "Item Price" and doc.price_list != PRICE_LIST:
		return
	if frappe.session.user == "Administrator" or frappe.flags.in_install or frappe.flags.in_migrate or frappe.flags.in_test:
		return
	from sk_app.logins import profile_functions

	if not set(RATE_EDITORS) & set(profile_functions(frappe.session.user)) and "System Manager" not in frappe.get_roles():
		frappe.throw(_("Only the CEO and Accounts can change labour rates"), frappe.PermissionError)


@contextmanager
def _as_system():
	"""ERPNext fills accounts / item details while saving and posting, which Production, Rushi (Sales) or the CEO login
	may not read (as for Store receipts, store.insert_for); the checks of who may do what stay in this module."""
	current = frappe.session.user
	frappe.set_user("Administrator")
	try:
		yield
	finally:
		frappe.set_user(current)


def _post(doc, savepoint: str) -> bool:
	"""Submit if ERPNext accepts it, else keep the draft with the reason (own savepoint: this runs inside the Job Card's
	or PO's own posting, which has its savepoint too)."""
	frappe.db.savepoint(savepoint)
	try:
		doc.flags.ignore_permissions = True
		doc.submit()
		return True
	except Exception as e:
		frappe.db.rollback(save_point=savepoint)
		frappe.clear_messages()
		doc.reload()
		doc.add_comment("Comment", _("Kept as draft by SK App: {0}").format((str(e) or type(e).__name__)[:200]))
		return False


# ---------- the service PO per job ----------

def supplier_of(workstation: str | None) -> str | None:
	"""Workstation's subcontractor as a Supplier; made once from the subcontractor's login name when not yet set."""
	if not workstation:
		return None
	sup = frappe.db.get_value("Workstation", workstation, "sk_supplier")
	if sup:
		return sup
	user = frappe.db.get_value("SK App User", {"workstation": workstation, "enabled": 1}, "user")
	if not user:
		return None
	if frappe.db.exists("Employee", {"user_id": user, "status": "Active"}):
		return None  # SK 28-Oct: a full-time employee on the workstation (Satish) is paid salary, never billed
	name = get_fullname(user)
	sup = frappe.db.get_value("Supplier", {"supplier_name": name})
	if not sup:
		group = frappe.db.get_value("Supplier Group", {"is_group": 0}, "name")
		sup = frappe.get_doc({"doctype": "Supplier", "supplier_name": name, "supplier_group": group,
			"supplier_type": "Individual"}).insert(ignore_permissions=True).name
	frappe.db.set_value("Workstation", workstation, "sk_supplier", sup)
	return sup


def _cabin_text(jc) -> str:
	from sk_app.store import job_card_cabin

	wo = frappe.db.get_value("Work Order", jc.work_order, ["item_name", "production_item"], as_dict=True) or {}
	for text in (jc.get("sk_cabin"), wo.get("item_name"), wo.get("production_item"), job_card_cabin(jc.work_order)):
		if size_of(text):
			return text
	return jc.get("sk_cabin") or wo.get("item_name") or ""


def points(job_card: str) -> float:
	return flt(frappe.db.get_value("SK Electrical Points", {"job_card": job_card}, "total_points"))


def job_rate(jc, supplier: str | None) -> tuple[float, float, str]:
	"""(qty, rate, how) for the job: the subcontractor's own rate, else the sheet's row for the cabin size, else the
	standard price; electrical per point. Rate 0 = not found, Rushi puts it."""
	item = service_item(jc.operation)
	cabins = flt(jc.for_quantity) or 1
	if _is_electrical(jc.operation) or _is_electrical(jc.workstation):
		n = points(jc.name)
		r = rate(item, supplier)
		return n, r, _("{0} points × Rs {1}").format(n, r)
	own = _price(item, supplier) if supplier else 0
	if own:
		return cabins, own, _("{0}'s own rate").format(supplier)
	trade = _trade(jc.operation)
	row = sheet_row(_cabin_text(jc)) if trade else None
	if row and flt(row[trade]):
		r, how = flt(row[trade]), _("Rate sheet {0} ({1} ft)").format(row.name, row.cabin_size)
		if trade == "carpenter" and row.carpenter_per_sqft:
			area = flt(row.length) * flt(row.width)
			how += _(": {0} sq ft × Rs {1}").format(area, r)
			r = r * area
		return cabins, r, how
	r = _price(item, None)
	return cabins, r, _("Standard rate") if r else ""


def po_of(job_card: str) -> str | None:
	return frappe.db.get_value("Purchase Order", {"sk_job_card": job_card, "docstatus": ["<", 2]}, "name")


def make_po(job_card: str) -> str | None:
	"""Service PO for the job, once per job card: the workstation's subcontractor at the sheet's rate, waiting for Rushi."""
	if not frappe.get_meta("Purchase Order").has_field("sk_job_card"):
		return None
	if po_of(job_card):
		return po_of(job_card)
	jc = frappe.get_doc("Job Card", job_card)
	if _is_inspection(jc.operation):
		return None
	supplier = supplier_of(jc.workstation)
	if not supplier:
		return None  # in-house work (salary): nothing to order
	qty, r, how = job_rate(jc, supplier)
	if not qty:
		return None  # electrical: the PO comes when the points are entered
	item = service_item(jc.operation)
	company = frappe.db.get_value("Work Order", jc.work_order, "company") or jc.company
	due = getdate(jc.get("expected_end_date") or add_days(nowdate(), 7))
	due = max(due, getdate(nowdate()))
	cabin = jc.get("sk_cabin") or jc.production_item or ""
	po = frappe.new_doc("Purchase Order")
	po.update({"supplier": supplier, "company": company, "transaction_date": nowdate(), "schedule_date": due,
		"sk_job_card": jc.name, "sk_bill_stage": CHECKER, "buying_price_list": PRICE_LIST})
	po.append("items", {"item_code": item, "qty": qty, "rate": r, "price_list_rate": r, "uom": "Nos", "conversion_factor": 1,
		"schedule_date": due, "description": ("" if r else NO_SIZE) + _("{0} · {1} · {2}").format(jc.operation, cabin, jc.name)})
	po.flags.ignore_permissions = True
	po.set_missing_values()
	po.items[0].rate = po.items[0].price_list_rate = r
	po.items[0].uom, po.items[0].conversion_factor = "Nos", 1
	po.insert()
	po.add_comment("Comment", how or _("Rate not found in the rate sheet: Rushi, please put the rate."))
	who = checker()
	if who:
		_todo(who, "Purchase Order", po.name, _("Labour PO to check (rate): {0} · {1} · {2} · {3}").format(po.supplier_name,
			jc.operation, cabin, frappe.format(po.grand_total, "Currency")))
	return po.name


def _quietly(fn, job_card: str, what: str):
	"""A labour PO / GRN / bill must never stop the job card or the Work Order itself; a failure is logged."""
	try:
		with _as_system():
			return fn(job_card)
	except Exception:
		frappe.log_error(title=f"SK App: labour {what} for {job_card}")


def wo_submitting(doc, method=None):
	frappe.flags.sk_wo_submitting = doc.name


def on_work_order_submit(doc, method=None):
	"""Work Order on_submit (after the stages done before ERPNext are closed): a service PO for each open job."""
	frappe.flags.sk_wo_submitting = None
	for card in frappe.get_all("Job Card", filters={"work_order": doc.name, "docstatus": 0, "status": ["!=", "Completed"]}, pluck="name"):
		_quietly(make_po, card, "PO")


def on_job_card_insert(doc, method=None):
	"""A job card added later to a running Work Order gets its PO at once (those of the Work Order's submit wait for it)."""
	if frappe.flags.get("sk_wo_submitting") or frappe.db.get_value("Work Order", doc.work_order, "docstatus") != 1:
		return
	_quietly(make_po, doc.name, "PO")


def on_points(job_card: str):
	"""Electrical: the PO is made, or its qty set, when the points are entered."""
	po = po_of(job_card)
	if not po:
		return _quietly(make_po, job_card, "PO")
	jc = frappe.db.get_value("Job Card", job_card, ["operation", "workstation"], as_dict=True) or {}
	if not (_is_electrical(jc.get("operation")) or _is_electrical(jc.get("workstation"))):
		return
	doc = frappe.get_doc("Purchase Order", po)
	n = points(job_card)
	if doc.docstatus == 0 and n and flt(doc.items[0].qty) != n:
		doc.items[0].qty = n
		doc.flags.ignore_permissions = True
		with _as_system():
			doc.save()
		doc.add_comment("Comment", _("Points entered: {0}").format(n))


# ---------- service GRN and bill ----------

def receipt_of(job_card: str, docstatus=1) -> str | None:
	return frappe.db.get_value("Purchase Receipt", {"sk_job_card": job_card, "docstatus": docstatus}, "name")


def bill_of(job_card: str) -> str | None:
	return frappe.db.get_value("Purchase Invoice", {"sk_job_card": job_card, "docstatus": ["<", 2]}, "name")


def passed(job_card: str) -> bool:
	return bool(frappe.db.exists("Quality Inspection", {"reference_type": "Job Card", "reference_name": job_card, "docstatus": 1,
		"status": "Accepted"}))


def _completed(job_card: str) -> bool:
	return frappe.db.get_value("Job Card", job_card, "status") == "Completed"


def receive(job_card: str) -> str | None:
	"""Job done and PO approved → service GRN (Purchase Receipt) against the PO, posted; the bill too if Quality passed."""
	po = frappe.db.get_value("Purchase Order", {"sk_job_card": job_card, "docstatus": 1}, "name")
	if not po or not _completed(job_card):
		return None
	name = receipt_of(job_card)
	if not name:
		draft = receipt_of(job_card, 0)
		if draft:
			pr = frappe.get_doc("Purchase Receipt", draft)
		else:
			from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt

			pr = make_purchase_receipt(po)
			pr.update({"sk_job_card": job_card, "posting_date": nowdate(), "supplier_delivery_note": job_card[:140]})
			pr.flags.ignore_permissions = True
			pr.insert()
		if not _post(pr, "sk_grn"):
			return None
		name = pr.name
		frappe.db.set_value("ToDo", {"reference_type": "Purchase Order", "reference_name": po, "status": "Open"}, "status", "Closed")
	if passed(job_card):
		post_bill(job_card)
	return name


def post_bill(job_card: str) -> str | None:
	"""Quality passed and GRN posted → Purchase Invoice from the GRN, posted: payable to the subcontractor."""
	pr = receipt_of(job_card)
	if not pr or not frappe.get_meta("Purchase Invoice").has_field("sk_job_card"):
		return None
	name = bill_of(job_card)
	if name and frappe.db.get_value("Purchase Invoice", name, "docstatus") == 1:
		return name
	if name:
		pi = frappe.get_doc("Purchase Invoice", name)
	else:
		from erpnext.stock.doctype.purchase_receipt.purchase_receipt import make_purchase_invoice

		pi = make_purchase_invoice(pr)
		pi.update({"sk_job_card": job_card, "sk_bill_stage": APPROVED, "bill_no": job_card[:140], "bill_date": nowdate(),
			"posting_date": nowdate(), "set_posting_time": 1})
		pi.flags.ignore_permissions = True
		pi.insert()
	pi.flags.sk_bill_ok = True
	if not _post(pi, "sk_bill"):
		return pi.name
	for who in _users_with_function("Accounts"):
		_todo(who, "Purchase Invoice", pi.name, _("Labour bill payable: {0} · {1} (PO approved, job done, Quality passed)").format(
			pi.supplier_name, frappe.format(pi.grand_total, "Currency")))
	return pi.name


def on_job_card_change(doc, method=None):
	"""Job Card on_update / on_submit: completed → its service GRN at once."""
	if doc.status == "Completed" and frappe.db.exists("Purchase Order", {"sk_job_card": doc.name, "docstatus": 1}) and not receipt_of(doc.name):
		_quietly(receive, doc.name, "GRN")


def on_po_submit(doc, method=None):
	"""Service PO approved after the job was already done → GRN now."""
	if doc.get("sk_job_card"):
		_quietly(receive, doc.sk_job_card, "GRN")


def on_qc_pass(job_card: str):
	_quietly(post_bill, job_card, "bill")


def backfill():
	"""Jobs already running when the labour PO flow came (29-Oct): one PO each, the same as from the Work Order submit."""
	if not frappe.get_meta("Purchase Order").has_field("sk_job_card"):
		return
	wos = frappe.get_all("Work Order", filters={"docstatus": 1, "status": ["not in", ["Completed", "Stopped", "Closed", "Cancelled"]]}, pluck="name")
	for card in frappe.get_all("Job Card", filters={"work_order": ["in", wos or [""]], "docstatus": 0, "status": ["!=", "Completed"]}, pluck="name"):
		if not po_of(card):
			_quietly(make_po, card, "PO")


# ---------- approval ----------

def checker() -> str | None:
	user = frappe.db.get_single_value("SK App Settings", "sub_bill_checker") if frappe.get_meta("SK App Settings").has_field("sub_bill_checker") else None
	if user:
		return user
	for name in ("Rishikesh", "Rushi"):
		u = frappe.db.get_value("User", {"full_name": ["like", f"{name}%"], "enabled": 1}, "name")
		if u:
			return u
	return None


def _ceos() -> list[str]:
	from sk_app.requisition import _ceos

	return _ceos()


def _is_ceo(user: str) -> bool:
	from sk_app.requisition import _is_ceo

	return _is_ceo(user)


def _sub_users(po) -> list[str]:
	ws = frappe.db.get_value("Job Card", po.sk_job_card, "workstation")
	return frappe.get_all("SK App User", filters={"workstation": ws, "enabled": 1}, pluck="user") if ws else []


def can_see(user: str) -> bool:
	return user == checker() or _is_ceo(user)


def _row(po) -> dict:
	jc = frappe.db.get_value("Job Card", po.sk_job_card, ["name", "operation", "workstation", "sk_cabin", "work_order", "status",
		"total_time_in_mins", "for_quantity", "project"], as_dict=True) or {}
	it = frappe.get_all("Purchase Order Item", filters={"parent": po.name}, fields=["item_code", "qty", "uom", "rate", "amount", "description"], limit=1)
	qc = frappe.get_all("Quality Inspection", filters={"reference_type": "Job Card", "reference_name": po.sk_job_card, "docstatus": 1},
		fields=["name", "status", "inspected_by"], order_by="creation desc", limit=1)
	talk = frappe.get_all("Comment", filters={"reference_doctype": "Purchase Order", "reference_name": po.name, "comment_type": "Comment"},
		fields=["content", "comment_email", "creation"], order_by="creation asc")
	bill = bill_of(po.sk_job_card)
	bill = frappe.db.get_value("Purchase Invoice", bill, ["name", "docstatus", "outstanding_amount", "status"], as_dict=True) if bill else None
	return {"name": po.name, "supplier": po.supplier_name, "stage": po.sk_bill_stage, "total": flt(po.grand_total), "question": po.sk_question,
		"job": jc, "line": it[0] if it else None, "no_size": bool(it and (it[0].description or "").startswith(NO_SIZE)), "qc": qc[0] if qc else None,
		"date": str(po.transaction_date), "docstatus": po.docstatus, "grn": receipt_of(po.sk_job_card), "bill": bill,
		"photos": frappe.get_all("File", filters={"attached_to_doctype": "Job Card", "attached_to_name": po.sk_job_card}, pluck="file_url"),
		"talk": [{"by": get_fullname(c.comment_email), "text": frappe.utils.strip_html(c.content or ""), "when": str(c.creation)} for c in talk]}


FIELDS = ["name", "supplier_name", "sk_bill_stage", "grand_total", "sk_question", "sk_job_card", "transaction_date", "docstatus"]


def _my_stages(user: str) -> list[str]:
	"""Rushi checks the rate first, then the CEO; the CEO does Rushi's check only when no checker is set."""
	rushi = checker()
	return ([CHECKER] if user == rushi or (not rushi and _is_ceo(user)) else []) + ([CEO] if _is_ceo(user) else [])


def to_approve(user: str) -> list[dict]:
	"""Rushi: labour POs waiting for his rate check; CEO: those waiting for the CEO (and Rushi's, to see what comes)."""
	if not can_see(user):
		frappe.throw(_("Only Rushi and the CEO approve labour POs"), frappe.PermissionError)
	mine = set(_my_stages(user))
	stages = mine | ({CHECKER} if _is_ceo(user) else set())
	rows = frappe.get_all("Purchase Order", filters={"docstatus": 0, "sk_job_card": ["is", "set"], "sk_bill_stage": ["in", list(stages)]},
		fields=FIELDS, order_by="transaction_date asc", limit=100)
	out = [_row(r) for r in rows]
	for r in out:
		r["mine"] = r["stage"] in mine
	out.sort(key=lambda r: not r["mine"])
	return out


def my_bills(user: str) -> list[dict]:
	"""The subcontractor's own labour POs, newest first: rate stage, GRN, bill, and any question waiting for him."""
	from sk_app.production import my_workstation

	ws = my_workstation(user)
	jcs = frappe.get_all("Job Card", filters={"workstation": ws}, pluck="name", limit=0) if ws else []
	rows = frappe.get_all("Purchase Order", filters={"sk_job_card": ["in", jcs or [""]], "docstatus": ["<", 2]}, fields=FIELDS,
		order_by="transaction_date desc", limit=50)
	return [_row(r) for r in rows]


def decide(user: str, name: str, approve, note=None, qty=None, rate=None) -> dict:
	po = frappe.get_doc("Purchase Order", name)
	if not po.get("sk_job_card") or po.docstatus != 0:
		frappe.throw(_("PO {0} is not waiting").format(name))
	stage = po.sk_bill_stage
	if stage not in _my_stages(user):
		frappe.throw(_("This PO is not waiting for you") if stage != CHECKER else _("Rushi checks the rate first"), frappe.PermissionError)
	if not cint(approve):
		if not (note or "").strip():
			frappe.throw(_("Please say why it is rejected"))
		back = stage == CEO  # the CEO sends it back to Rushi for the rate; Rushi's reject stops the PO
		po.db_set("sk_bill_stage", CHECKER if back else REJECTED)
		po.add_comment("Comment", _("{0} by {1}: {2}").format(_("Sent back") if back else _("Rejected"), get_fullname(user), note))
		for who in ([checker()] if back else set(_sub_users(po) + _users_with_function("Production"))):
			if who:
				_todo(who, "Purchase Order", po.name, _("Labour PO {0}: {1}").format(_("sent back") if back else _("rejected"), note))
		return {"name": po.name, "stage": CHECKER if back else REJECTED}
	if po.get("sk_question"):
		frappe.throw(_("Question still open: {0}").format(po.sk_question))
	row = po.items[0]
	if stage == CHECKER:
		changes = []
		if qty not in (None, "") and flt(qty) > 0 and flt(qty) != flt(row.qty):
			changes.append(_("qty {0} → {1}").format(row.qty, flt(qty)))
			row.qty = flt(qty)
		if rate not in (None, "") and flt(rate) > 0 and flt(rate) != flt(row.rate):
			changes.append(_("rate {0} → {1}").format(row.rate, flt(rate)))
			row.rate = row.price_list_rate = flt(rate)
		if changes:
			row.description = (row.description or "").removeprefix(NO_SIZE)
			po.flags.ignore_permissions = True
			with _as_system():
				po.save()
			po.add_comment("Comment", _("Corrected by {0}: {1}").format(get_fullname(user), ", ".join(changes)))
	if not flt(row.rate) or (row.description or "").startswith(NO_SIZE):
		frappe.throw(_("Please put the rate (not in the rate sheet for this cabin size)"))
	if note:
		po.add_comment("Comment", note)
	frappe.db.set_value("ToDo", {"reference_type": "Purchase Order", "reference_name": po.name, "status": "Open",
		"allocated_to": user}, "status", "Closed")
	if stage == CHECKER:
		po.db_set("sk_bill_stage", CEO)
		po.add_comment("Comment", _("Rate checked by {0}").format(get_fullname(user)))
		for who in _ceos():
			_todo(who, "Purchase Order", po.name, _("Labour PO to approve: {0} · {1}").format(po.supplier_name, frappe.format(po.grand_total, "Currency")))
		if not _is_ceo(user):
			return {"name": po.name, "stage": CEO}
	po.db_set("sk_bill_stage", APPROVED)
	po.add_comment("Comment", _("Approved by {0}").format(get_fullname(user)))
	po.flags.sk_bill_ok = True
	with _as_system():
		posted = _post(po, "sk_po")
	if not posted:
		po.db_set("sk_bill_stage", CEO)
		return {"name": po.name, "stage": CEO, "posted": False}
	frappe.db.set_value("Purchase Order", po.name, "modified_by", user, update_modified=False)
	frappe.db.set_value("ToDo", {"reference_type": "Purchase Order", "reference_name": po.name, "status": "Open"}, "status", "Closed")
	for who in _sub_users(po):
		_todo(who, "Purchase Order", po.name, _("Your labour PO is approved: {0} · {1}").format(po.items[0].description, frappe.format(po.grand_total, "Currency")))
	return {"name": po.name, "stage": APPROVED, "posted": True, "grn": receipt_of(po.sk_job_card)}


def discuss(user: str, name: str, text: str) -> dict:
	"""Rushi / CEO ask a question: the PO waits until the subcontractor or Production answers."""
	po = frappe.get_doc("Purchase Order", name)
	if not can_see(user):
		frappe.throw(_("Only Rushi and the CEO discuss labour POs"), frappe.PermissionError)
	if not (text or "").strip():
		frappe.throw(_("Please say your question"))
	po.db_set("sk_question", text.strip()[:500])
	po.add_comment("Comment", _("Question from {0}: {1}").format(get_fullname(user), text))
	for who in set(_sub_users(po) + _users_with_function("Production")) - {user}:
		_todo(who, "Purchase Order", po.name, _("Question on your labour PO: {0}").format(text))
	return {"name": po.name, "question": po.sk_question}


def reply(user: str, name: str, text: str) -> dict:
	po = frappe.get_doc("Purchase Order", name)
	from sk_app.logins import profile_functions

	if user not in _sub_users(po) and "Production" not in profile_functions(user) and not can_see(user):
		frappe.throw(_("This is not your PO"), frappe.PermissionError)
	if not (text or "").strip():
		frappe.throw(_("Please say your answer"))
	po.add_comment("Comment", _("Answer from {0}: {1}").format(get_fullname(user), text))
	po.db_set("sk_question", None)
	frappe.db.set_value("ToDo", {"reference_type": "Purchase Order", "reference_name": po.name, "status": "Open",
		"description": ["like", "%Question on your labour PO%"]}, "status", "Closed")
	waiting = checker() if po.sk_bill_stage == CHECKER else None
	for who in ([waiting] if waiting else _ceos()):
		_todo(who, "Purchase Order", po.name, _("Answer on labour PO {0}: {1}").format(po.name, text))
	return {"name": po.name}


def check_submit(doc, method=None):
	"""Purchase Order / Invoice hook, also in ERPNext itself: a labour PO is submitted only after Rushi's rate check and
	the CEO (the CEO submitting a PO Rushi checked is the approval); its bill only from the GRN of that PO."""
	if not doc.get("sk_job_card") or doc.flags.sk_bill_ok:
		return
	if doc.doctype == "Purchase Invoice":
		if doc.get("sk_bill_stage") == APPROVED or all(i.get("purchase_receipt") for i in doc.items):
			return
		frappe.throw(_("A labour bill comes from the service GRN of its approved PO ({0})").format(doc.sk_job_card))
	if doc.get("sk_bill_stage") == CEO and _is_ceo(frappe.session.user):
		doc.sk_bill_stage = APPROVED
		return
	if doc.get("sk_bill_stage") != APPROVED:
		frappe.throw(_("Labour PO {0} needs Rushi's rate check and then the CEO's approval").format(doc.name))


def badges(user: str) -> dict:
	if not frappe.get_meta("Purchase Order").has_field("sk_bill_stage"):
		return {}
	stages = _my_stages(user)
	n = frappe.db.count("Purchase Order", {"docstatus": 0, "sk_job_card": ["is", "set"], "sk_bill_stage": ["in", stages]}) if stages else 0
	return {"sub_bills": n} if n else {}
