"""Essential-field gate on every function's step (SK 27-Nov, all 29 rows of the approved Excel). Rules in step_gate_rules.py.

Each hook reads the ERPNext record, asks the rule what is missing and stops the step with one plain notice: what is
missing, who fills it, why. The same stop runs from SK App, the ERPNext desk and Claude / SK Hub. missing_for() gives the
same list to the night check, so a stuck draft reaches its person on Home and in the one morning mail.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import flt

from sk_app import step_gate_rules as R


def _skip() -> bool:
	from sk_app.gates import _skip as skip

	return skip()


def _files(doctype: str, name: str | None, pdf_only: bool = False, not_quote: bool = False) -> int:
	if not name:
		return 0
	rows = frappe.get_all("File", filters={"attached_to_doctype": doctype, "attached_to_name": name, "is_folder": 0}, pluck="file_name", limit=0)
	if pdf_only:
		rows = [r for r in rows if (r or "").lower().endswith(".pdf")]
	if not_quote:
		rows = [r for r in rows if "quot" not in (r or "").lower()]
	return len(rows)


def person(function: str) -> str | None:
	try:
		from sk_app.core.night_check import _function_owner

		u = _function_owner(function)
		return frappe.db.get_value("User", u, "full_name") or u
	except Exception:
		return None


def stop(record: str, missing: list, step: str):
	if missing:
		who = R.WHO.get(step, "")
		frappe.throw(R.notice(record, missing, who, person(who) if who else None), title=_("Cannot go further"))


# ---------- the checks (doc -> missing) ----------

def _design_pdfs(deal: str) -> int:
	return _files("CRM Deal", deal, pdf_only=True, not_quote=True)


def _wo_pdfs(doc) -> int:
	return (_files("Work Order", doc.name, pdf_only=True, not_quote=True) + _files("Sales Order", doc.get("sales_order"), pdf_only=True, not_quote=True)
		+ _files("Project", doc.get("project"), pdf_only=True, not_quote=True))


def _po(doc) -> list:
	s = frappe.db.get_value("Supplier", doc.supplier, ["gst_category", "gstin"], as_dict=True) or {}
	has_addr = bool(doc.get("supplier_address")) or bool(frappe.db.exists("Dynamic Link", {"link_doctype": "Supplier", "link_name": doc.supplier,
		"parenttype": "Address"}))
	# a labour / service PO (no stock item, made by itself from the job card) does not need the contractor's address
	if not any(frappe.db.get_value("Item", i.item_code, "is_stock_item") for i in doc.items if i.get("item_code")):
		has_addr = True
	return R.purchase_order(s.get("gst_category"), s.get("gstin") or doc.get("supplier_gstin"), has_addr,
		sum(1 for i in doc.items if not i.get("schedule_date")) if not doc.get("schedule_date") else 0)


def _pinv(doc) -> list:
	unlinked = sum(1 for i in doc.items if frappe.db.get_value("Item", i.item_code, "is_stock_item") and not (i.get("purchase_receipt") or i.get("purchase_order")))
	return R.purchase_invoice(doc.get("bill_no"), doc.get("bill_date"), 0 if doc.get("update_stock") else unlinked)


def _qc_passed(doc) -> bool:
	"""A submitted (not self-check) Quality Inspection on this Delivery Note, or on any Job Card of its orders' Work Orders."""
	from sk_app.quality import qc_filter

	f = {"docstatus": 1, "status": "Accepted", **qc_filter()}
	if doc.name and frappe.db.exists("Quality Inspection", {**f, "reference_type": "Delivery Note", "reference_name": doc.name}):
		return True
	orders = {i.get("against_sales_order") for i in doc.items if i.get("against_sales_order")}
	wos = frappe.get_all("Work Order", filters={"sales_order": ["in", list(orders)], "docstatus": 1}, pluck="name") if orders else []
	cards = frappe.get_all("Job Card", filters={"work_order": ["in", wos]}, pluck="name") if wos else []
	return bool(cards and frappe.db.exists("Quality Inspection", {**f, "reference_type": "Job Card", "reference_name": ["in", cards]}))


def missing_for(doctype: str, name: str) -> list:
	"""For the night check: what a draft still lacks (same rules as the stop)."""
	try:
		doc = frappe.get_doc(doctype, name)
		fn = {"Purchase Order": _po, "Purchase Invoice": _pinv,
			"Purchase Receipt": lambda d: R.purchase_receipt(d.get("supplier_delivery_note"), _files(d.doctype, d.name)),
			"Stock Entry": lambda d: R.stock_issue(d.get("purpose"), d.get("work_order"), d.get("project")),
			"Delivery Note": lambda d: R.delivery_note(d.get("vehicle_no"), d.get("transporter") or d.get("transporter_name") or d.get("driver_name"), _qc_passed(d)),
			"Payment Entry": lambda d: R.payment(d.payment_type, d.party_type, len(d.get("references") or [])),
			"Expense Claim": lambda d: R.expense_claim(d.get("employee"), _files(d.doctype, d.name), d.get("sk_no_bill")),
			"Work Order": lambda d: R.work_order(_wo_pdfs(d))}.get(doctype)
		return fn(doc) if fn else []
	except Exception:
		return []


# ---------- hooks ----------

def check_deal_design(doc, method=None):
	"""CRM Deal validate (rows 8-9)."""
	if _skip() or doc.is_new() or not doc.meta.has_field("custom_design_status") or not doc.has_value_changed("custom_design_status"):
		return
	stop(_("Deal {0}: Design status '{1}'").format(doc.name, doc.custom_design_status),
		R.design_status(doc.custom_design_status, _design_pdfs(doc.name), doc.get("custom_design_quote_value")), "design_status")


def check_send_to_design(lead: str):
	"""Row 3: called by Send to design."""
	d = frappe.db.get_value("CRM Lead", lead, ["sk_product"] if frappe.get_meta("CRM Lead").has_field("sk_product") else ["name"], as_dict=True) or {}
	notes = " ".join(frappe.get_all("FCRM Note", filters={"reference_doctype": "CRM Lead", "reference_docname": lead}, pluck="content", limit=20)) \
		if frappe.db.exists("DocType", "FCRM Note") else ""
	text = " ".join(x for x in (d.get("sk_product"), frappe.utils.strip_html(notes or "")) if x)
	stop(_("Lead {0}: Send to design").format(lead), R.send_to_design(text), "send_to_design")


def _submit(step: str, fn):
	def hook(doc, method=None):
		if not _skip():
			stop(f"{_(doc.doctype)} {doc.name}", fn(doc), step)
	return hook


check_work_order = _submit("work_order", lambda d: R.work_order(_wo_pdfs(d)))
check_purchase_order = _submit("purchase_order", _po)
check_purchase_invoice = _submit("purchase_invoice", _pinv)
check_purchase_receipt = _submit("purchase_receipt", lambda d: R.purchase_receipt(d.get("supplier_delivery_note"), _files(d.doctype, d.name)))
check_stock_entry = _submit("stock_issue", lambda d: R.stock_issue(d.get("purpose"), d.get("work_order"), d.get("project")))
check_delivery_note = _submit("delivery_note", lambda d: R.delivery_note(d.get("vehicle_no"),
	d.get("transporter") or d.get("transporter_name") or d.get("driver_name"), _qc_passed(d)))
check_payment = _submit("payment", lambda d: R.payment(d.payment_type, d.party_type, len(d.get("references") or [])))
check_expense_claim = _submit("expense_claim", lambda d: R.expense_claim(d.get("employee"), _files(d.doctype, d.name), d.get("sk_no_bill")))


def check_project(doc, method=None):
	"""Project validate (row 22): closed only with the handover proof."""
	if _skip() or doc.is_new() or not doc.has_value_changed("status"):
		return
	stop(f"{_('Project')} {doc.name}", R.project_close(doc.status, _files("Project", doc.name)), "project_close")


def check_employee_login(employee: str, mobile: str | None = None):
	"""Row 28: the app login is made only for a complete Employee."""
	d = frappe.db.get_value("Employee", employee, ["cell_number", "date_of_joining", "department", "designation"], as_dict=True) or {}
	d["cell_number"] = d.get("cell_number") or mobile
	stop(f"{_('Employee')} {employee}: {_('app login')}", R.employee_login(d), "employee_login")
