"""Subcontractor bills (SK 28-Oct-2026): a rate sheet per subcontractor / vendor in ERPNext, the bill made by itself
when a job is finished and passed by Quality, checked by Rushi (rate + job card), approved by the CEO, then posted so
it shows as payable. Shraddha pays it in ERPNext as usual (the app never enters money).

Rate sheet: Price List "Subcontract Rates" (buying), one Item Price per job type (service item SUB-<Operation>) and
supplier; a row with no supplier is the standard rate for everyone. Rates are per sq ft of the cabin, electrical per
point (SK Electrical Points of the job card). The workstation's subcontractor is the Supplier on Workstation.sk_supplier.

Bill: draft Purchase Invoice with sk_job_card; sk_bill_stage Waiting Rushi → Waiting CEO → Approved (posted) or
Rejected. Discuss puts a question on the bill (a Comment, ToDo to the subcontractor and Production) and the bill waits
until it is answered.
"""

import re
from contextlib import contextmanager

import frappe
from frappe import _
from frappe.utils import cint, flt, get_fullname, nowdate

from sk_app.store import _todo, _users_with_function, submit_for

PRICE_LIST = "Subcontract Rates"
CHECKER, CEO, APPROVED, REJECTED = "Waiting Rushi", "Waiting CEO", "Approved", "Rejected"
STAGES = (CHECKER, CEO, APPROVED, REJECTED)
RATE_EDITORS = ("Management", "Accounts")  # SK and Shraddha change the rates
PREFIX = "SUB-"
NO_SIZE = "⚠ size not found · "


def ensure_setup():
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	create_custom_fields({
		"Purchase Invoice": [
			{"fieldname": "sk_job_card", "label": "Subcontract job card", "fieldtype": "Link", "options": "Job Card",
				"insert_after": "supplier", "read_only": 1, "in_standard_filter": 1},
			{"fieldname": "sk_bill_stage", "label": "Bill approval", "fieldtype": "Select", "options": "\n" + "\n".join(STAGES),
				"insert_after": "sk_job_card", "read_only": 1, "allow_on_submit": 1, "in_list_view": 1, "in_standard_filter": 1},
			{"fieldname": "sk_question", "label": "Open question", "fieldtype": "Small Text", "insert_after": "sk_bill_stage",
				"read_only": 1},
		],
		"Workstation": [
			{"fieldname": "sk_supplier", "label": "Subcontractor (supplier for bills)", "fieldtype": "Link", "options": "Supplier",
				"insert_after": "workstation_name"},
		],
		"SK App Settings": [
			{"fieldname": "sub_bill_checker", "label": "Subcontractor bills: first check (Rushi)", "fieldtype": "Link",
				"options": "User", "insert_after": "lead_owner_noncabin"},
		],
	}, update=True)
	if not frappe.db.exists("Price List", PRICE_LIST):
		frappe.get_doc({"doctype": "Price List", "price_list_name": PRICE_LIST, "buying": 1, "selling": 0, "enabled": 1,
			"currency": frappe.db.get_default("currency") or "INR"}).insert(ignore_permissions=True)
	for op in frappe.get_all("Operation", pluck="name"):
		service_item(op)


# ---------- rate sheet ----------

def _is_electrical(operation: str | None) -> bool:
	from sk_app.production import _is_electrical

	return _is_electrical(operation)


def service_item(operation: str) -> str:
	"""SUB-<Operation>: the non-stock item the job type is billed on (per sq ft, electrical per point)."""
	code = (PREFIX + operation)[:140]
	if not frappe.db.exists("Item", code):
		uom = "Nos" if _is_electrical(operation) else _sqft_uom()
		group = "Services" if frappe.db.exists("Item Group", "Services") else frappe.db.get_value("Item Group", {"is_group": 0}, "name")
		frappe.get_doc({"doctype": "Item", "item_code": code, "item_name": _("{0} (subcontract)").format(operation), "item_group": group,
			"stock_uom": uom, "is_stock_item": 0, "is_purchase_item": 1, "is_sales_item": 0,
			"description": _("Subcontract labour: {0}, rate per {1}").format(operation, "point" if uom == "Nos" else "sq ft")}).insert(ignore_permissions=True)
	return code


def _sqft_uom() -> str:
	for u in ("Square Foot", "Sq Ft", "SqFt"):
		if frappe.db.exists("UOM", u):
			return u
	return frappe.get_doc({"doctype": "UOM", "uom_name": "Square Foot"}).insert(ignore_permissions=True).name


def rate(item_code: str, supplier: str | None) -> float:
	"""The subcontractor's own rate, else the standard rate of the sheet."""
	for sup in (supplier, None):
		if sup is None:
			filters = {"price_list": PRICE_LIST, "item_code": item_code, "supplier": ["in", ["", None]]}
		else:
			filters = {"price_list": PRICE_LIST, "item_code": item_code, "supplier": sup}
		r = frappe.db.get_value("Item Price", filters, "price_list_rate", order_by="valid_from desc")
		if r:
			return flt(r)
	return 0


def check_rate_edit(doc, method=None):
	"""Item Price hook: only SK (Management) and Accounts change the subcontract rates."""
	if doc.price_list != PRICE_LIST or frappe.session.user == "Administrator" or frappe.flags.in_install or frappe.flags.in_test:
		return
	from sk_app.logins import profile_functions

	if not set(RATE_EDITORS) & set(profile_functions(frappe.session.user)) and "System Manager" not in frappe.get_roles():
		frappe.throw(_("Only the CEO and Accounts can change subcontract rates"), frappe.PermissionError)


@contextmanager
def _as_system():
	"""ERPNext fills accounts / item details while saving and posting, which Quality, Rushi (Sales) or the CEO login
	may not read (as for Store receipts, store.insert_for); the checks of who may do what stay in this module."""
	current = frappe.session.user
	frappe.set_user("Administrator")
	try:
		yield
	finally:
		frappe.set_user(current)


# ---------- making the bill ----------

def sqft(text: str | None) -> float:
	"""'12ft x 10ft x 8.6ft' (or 12 x 10) → 120 sq ft."""
	m = re.search(r"(\d+(?:\.\d+)?)\s*(?:ft|')?\s*[x×*]\s*(\d+(?:\.\d+)?)", text or "", re.I)
	return flt(m.group(1)) * flt(m.group(2)) if m else 0


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


def quantity(jc) -> float:
	if _is_electrical(jc.operation) or _is_electrical(jc.workstation):
		return flt(frappe.db.get_value("SK Electrical Points", {"job_card": jc.name}, "total_points"))
	from sk_app.store import job_card_cabin

	wo = frappe.db.get_value("Work Order", jc.work_order, ["item_name", "production_item"], as_dict=True) or {}
	size = sqft(jc.get("sk_cabin")) or sqft(wo.get("item_name")) or sqft(wo.get("production_item")) or sqft(job_card_cabin(jc.work_order))
	return size * (flt(jc.for_quantity) or 1)


def bill_of(job_card: str) -> str | None:
	return frappe.db.get_value("Purchase Invoice", {"sk_job_card": job_card, "docstatus": ["<", 2]}, "name")


def make_bill(job_card: str) -> str | None:
	"""After Quality passes the job: draft bill for the workstation's subcontractor, once per job card."""
	if not frappe.get_meta("Purchase Invoice").has_field("sk_job_card"):
		return None
	if bill_of(job_card):
		return bill_of(job_card)
	jc = frappe.get_doc("Job Card", job_card)
	supplier = supplier_of(jc.workstation)
	if not supplier:
		return None  # in-house work: nothing to bill
	qty = quantity(jc)
	if _is_electrical(jc.operation) or _is_electrical(jc.workstation):
		if not qty:
			return None  # bill comes when the points are entered
	item = service_item(jc.operation)
	company = frappe.db.get_value("Work Order", jc.work_order, "company") or jc.company
	pi = frappe.new_doc("Purchase Invoice")
	pi.update({"supplier": supplier, "company": company, "posting_date": nowdate(), "sk_job_card": jc.name, "sk_bill_stage": CHECKER,
		"bill_no": jc.name, "bill_date": nowdate(),
		"remarks": _("Subcontract bill for {0} · {1} · {2}").format(jc.name, jc.operation, jc.get("sk_cabin") or jc.production_item or "")})
	pi.append("items", {"item_code": item, "qty": qty or 1, "rate": rate(item, supplier), "price_list_rate": rate(item, supplier),
		"description": ("" if qty else NO_SIZE) + _("{0} · {1} · {2}").format(jc.operation, jc.get("sk_cabin") or "", jc.name)})
	pi.buying_price_list = PRICE_LIST
	pi.flags.ignore_permissions = True
	pi.set_missing_values()
	pi.items[0].rate = rate(item, supplier)
	pi.insert()
	if not qty:
		pi.add_comment("Comment", _("Cabin size not found: Rushi, please put the sq ft."))
	for who in [checker()]:
		if who:
			_todo(who, "Purchase Invoice", pi.name, _("Subcontractor bill to check: {0} · {1} · {2}").format(pi.supplier_name, jc.operation, jc.get("sk_cabin") or ""))
	return pi.name


def on_qc_pass(job_card: str):
	try:
		with _as_system():
			make_bill(job_card)
	except Exception:
		frappe.log_error(title=f"SK App: subcontractor bill for {job_card}")


def on_points(job_card: str):
	"""Electrical: the bill waits for the points; passed by Quality already → make it now."""
	if frappe.db.exists("Quality Inspection", {"reference_type": "Job Card", "reference_name": job_card, "docstatus": 1, "status": "Accepted"}):
		on_qc_pass(job_card)


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


def _sub_users(pi) -> list[str]:
	ws = frappe.db.get_value("Job Card", pi.sk_job_card, "workstation")
	return frappe.get_all("SK App User", filters={"workstation": ws, "enabled": 1}, pluck="user") if ws else []


def can_see(user: str) -> bool:
	return user == checker() or _is_ceo(user)


def _row(pi) -> dict:
	jc = frappe.db.get_value("Job Card", pi.sk_job_card, ["name", "operation", "workstation", "sk_cabin", "work_order", "status",
		"total_time_in_mins", "for_quantity"], as_dict=True) or {}
	it = frappe.get_all("Purchase Invoice Item", filters={"parent": pi.name}, fields=["item_code", "qty", "uom", "rate", "amount", "description"], limit=1)
	qc = frappe.get_all("Quality Inspection", filters={"reference_type": "Job Card", "reference_name": pi.sk_job_card, "docstatus": 1},
		fields=["name", "status", "inspected_by"], order_by="creation desc", limit=1)
	talk = frappe.get_all("Comment", filters={"reference_doctype": "Purchase Invoice", "reference_name": pi.name, "comment_type": "Comment"},
		fields=["content", "comment_email", "creation"], order_by="creation asc")
	return {"name": pi.name, "supplier": pi.supplier_name, "stage": pi.sk_bill_stage, "total": flt(pi.grand_total), "question": pi.sk_question,
		"job": jc, "line": it[0] if it else None, "no_size": bool(it and (it[0].description or "").startswith(NO_SIZE)), "qc": qc[0] if qc else None, "date": str(pi.posting_date), "docstatus": pi.docstatus,
		"photos": frappe.get_all("File", filters={"attached_to_doctype": "Job Card", "attached_to_name": pi.sk_job_card}, pluck="file_url"),
		"talk": [{"by": get_fullname(c.comment_email), "text": frappe.utils.strip_html(c.content or ""), "when": str(c.creation)} for c in talk]}


FIELDS = ["name", "supplier_name", "sk_bill_stage", "grand_total", "sk_question", "sk_job_card", "posting_date", "docstatus"]


def to_approve(user: str) -> list[dict]:
	"""Rushi: bills waiting for his check; CEO: bills waiting for the CEO (and Rushi's, to see what comes)."""
	stages = ([CHECKER] if user == checker() else []) + ([CEO, CHECKER] if _is_ceo(user) else [])
	if not stages:
		frappe.throw(_("Only Rushi and the CEO approve subcontractor bills"), frappe.PermissionError)
	rows = frappe.get_all("Purchase Invoice", filters={"docstatus": 0, "sk_bill_stage": ["in", list(set(stages))]}, fields=FIELDS,
		order_by="posting_date asc", limit=100)
	out = [_row(r) for r in rows]
	mine = set(([CHECKER] if user == checker() else []) + ([CEO] if _is_ceo(user) else []))
	for r in out:
		r["mine"] = r["stage"] in mine
	out.sort(key=lambda r: not r["mine"])
	return out


def my_bills(user: str) -> list[dict]:
	"""The subcontractor's own bills, newest first, with the stage and any question waiting for him."""
	from sk_app.production import my_workstation

	ws = my_workstation(user)
	jcs = frappe.get_all("Job Card", filters={"workstation": ws}, pluck="name", limit=0) if ws else []
	rows = frappe.get_all("Purchase Invoice", filters={"sk_job_card": ["in", jcs or [""]], "docstatus": ["<", 2]}, fields=FIELDS,
		order_by="posting_date desc", limit=50)
	return [_row(r) for r in rows]


def decide(user: str, name: str, approve, note=None, qty=None) -> dict:
	pi = frappe.get_doc("Purchase Invoice", name)
	if not pi.get("sk_job_card") or pi.docstatus != 0:
		frappe.throw(_("Bill {0} is not waiting").format(name))
	stage = pi.sk_bill_stage
	if not ((stage == CHECKER and (user == checker() or _is_ceo(user))) or (stage == CEO and _is_ceo(user))):
		frappe.throw(_("This bill is not waiting for you"), frappe.PermissionError)
	if not cint(approve):
		if not (note or "").strip():
			frappe.throw(_("Please say why it is rejected"))
		pi.db_set("sk_bill_stage", REJECTED)
		pi.add_comment("Comment", _("Rejected by {0}: {1}").format(get_fullname(user), note))
		for who in set(_sub_users(pi) + _users_with_function("Production")):
			_todo(who, "Purchase Invoice", pi.name, _("Bill rejected: {0}").format(note))
		return {"name": pi.name, "stage": REJECTED}
	if pi.get("sk_question"):
		frappe.throw(_("Question still open: {0}").format(pi.sk_question))
	if stage == CHECKER and qty not in (None, "") and flt(qty) > 0 and flt(qty) != flt(pi.items[0].qty):
		old = pi.items[0].qty
		pi.items[0].qty = flt(qty)
		pi.items[0].description = (pi.items[0].description or "").removeprefix(NO_SIZE)
		pi.flags.ignore_permissions = True
		with _as_system():
			pi.save()
		pi.add_comment("Comment", _("Qty corrected by {0}: {1} → {2}").format(get_fullname(user), old, flt(qty)))
	if not flt(pi.items[0].rate):
		frappe.throw(_("No rate for {0} in the rate sheet ({1}). Please ask the CEO / Accounts to add it.").format(pi.items[0].item_code, PRICE_LIST))
	if (pi.items[0].description or "").startswith(NO_SIZE):
		frappe.throw(_("Please put the sq ft / points"))
	if note:
		pi.add_comment("Comment", note)
	if stage == CHECKER and not _is_ceo(user):
		pi.db_set("sk_bill_stage", CEO)
		pi.add_comment("Comment", _("Rate and job card checked by {0}").format(get_fullname(user)))
		for who in _ceos():
			_todo(who, "Purchase Invoice", pi.name, _("Subcontractor bill to approve: {0} · {1}").format(pi.supplier_name, frappe.format(pi.grand_total, "Currency")))
		return {"name": pi.name, "stage": CEO}
	pi.db_set("sk_bill_stage", APPROVED)
	pi.add_comment("Comment", _("Approved by {0}").format(get_fullname(user)))
	pi.flags.sk_bill_ok = True
	posted = submit_for(pi, user)
	frappe.db.set_value("ToDo", {"reference_type": "Purchase Invoice", "reference_name": pi.name, "status": "Open"}, "status", "Closed")
	for who in _users_with_function("Accounts"):
		_todo(who, "Purchase Invoice", pi.name, _("Approved subcontractor bill to pay: {0} · {1}").format(pi.supplier_name,
			frappe.format(pi.grand_total, "Currency")))
	return {"name": pi.name, "stage": APPROVED, "posted": posted}


def discuss(user: str, name: str, text: str) -> dict:
	"""Rushi / CEO ask a question: the bill waits until the subcontractor or Production answers."""
	pi = frappe.get_doc("Purchase Invoice", name)
	if not can_see(user):
		frappe.throw(_("Only Rushi and the CEO discuss bills"), frappe.PermissionError)
	if not (text or "").strip():
		frappe.throw(_("Please say your question"))
	pi.db_set("sk_question", text.strip()[:500])
	pi.add_comment("Comment", _("Question from {0}: {1}").format(get_fullname(user), text))
	for who in set(_sub_users(pi) + _users_with_function("Production")) - {user}:
		_todo(who, "Purchase Invoice", pi.name, _("Question on your bill: {0}").format(text))
	return {"name": pi.name, "question": pi.sk_question}


def reply(user: str, name: str, text: str) -> dict:
	pi = frappe.get_doc("Purchase Invoice", name)
	from sk_app.logins import profile_functions

	if user not in _sub_users(pi) and "Production" not in profile_functions(user) and not can_see(user):
		frappe.throw(_("This is not your bill"), frappe.PermissionError)
	if not (text or "").strip():
		frappe.throw(_("Please say your answer"))
	pi.add_comment("Comment", _("Answer from {0}: {1}").format(get_fullname(user), text))
	pi.db_set("sk_question", None)
	frappe.db.set_value("ToDo", {"reference_type": "Purchase Invoice", "reference_name": pi.name, "status": "Open",
		"description": ["like", "%Question on your bill%"]}, "status", "Closed")
	waiting = checker() if pi.sk_bill_stage == CHECKER else None
	for who in ([waiting] if waiting else _ceos()):
		_todo(who, "Purchase Invoice", pi.name, _("Answer on bill {0}: {1}").format(pi.name, text))
	return {"name": pi.name}


def check_submit(doc, method=None):
	"""Purchase Invoice hook: a subcontract bill is posted only after Rushi and the CEO approved it."""
	if not doc.get("sk_job_card") or doc.flags.sk_bill_ok:
		return
	if doc.get("sk_bill_stage") != APPROVED and not _is_ceo(frappe.session.user):
		frappe.throw(_("Subcontractor bill {0} needs Rushi's check and the CEO's approval first").format(doc.name))


def badges(user: str) -> dict:
	if not frappe.get_meta("Purchase Invoice").has_field("sk_bill_stage"):
		return {}
	stages = ([CHECKER] if user == checker() else []) + ([CEO] if _is_ceo(user) else [])
	n = frappe.db.count("Purchase Invoice", {"docstatus": 0, "sk_bill_stage": ["in", stages]}) if stages else 0
	return {"sub_bills": n} if n else {}
