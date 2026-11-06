"""Import completeness (SK 6-Nov, KF-04328: the Oct Biziverse import left 1,383 leads behind and nobody flagged it).
Every load records an SK Import row (source, rows in source, rows loaded, the ERPNext filter that finds its records).
Nightly check(): rows in ERPNext behind that filter vs rows in source → gap on the record, one scorecard line
"Import gaps" (target 0) and a ToDo to the CEO when any gap is open."""

import json

import frappe
from frappe import _
from frappe.utils import now_datetime, nowdate

DOCTYPE = "SK Import"
OWNER_FIELD = {"CRM Lead": "lead_owner", "CRM Deal": "deal_owner", "Quotation": "owner", "Sales Order": "owner", "Sales Invoice": "owner",
	"Purchase Invoice": "owner", "Payment Entry": "owner"}


def record(source: str, erp_doctype: str, rows_in_source: int, rows_loaded: int, erp_filters: dict, *, file_name=None, record_type=None,
		by_salesperson: dict | None = None, note=None) -> str | None:
	"""Called by every loader after its load. Returns the SK Import name."""
	if not frappe.db.table_exists(DOCTYPE):
		return None
	doc = frappe.get_doc({"doctype": DOCTYPE, "source": source[:140], "file_name": file_name, "record_type": record_type, "erp_doctype": erp_doctype,
		"rows_in_source": int(rows_in_source), "rows_loaded": int(rows_loaded), "erp_filters": json.dumps(erp_filters),
		"by_salesperson": json.dumps(by_salesperson) if by_salesperson else None, "note": note}).insert(ignore_permissions=True)
	_check_one(doc)
	return doc.name


def gap_of(rows_in_source: int, rows_in_erp: int) -> int:
	return max(int(rows_in_source or 0) - int(rows_in_erp or 0), 0)


def _check_one(doc) -> int:
	try:
		filters = json.loads(doc.erp_filters or "{}")
	except ValueError:
		filters = {}
	n = frappe.db.count(doc.erp_doctype, filters) if filters else 0
	gap = gap_of(doc.rows_in_source, n)
	detail = None
	if doc.by_salesperson and OWNER_FIELD.get(doc.erp_doctype):
		try:
			want = json.loads(doc.by_salesperson)
		except ValueError:
			want = {}
		have = {r[0] or "": r[1] for r in frappe.get_all(doc.erp_doctype, filters=filters, fields=[OWNER_FIELD[doc.erp_doctype], "count(name) as n"],
			group_by=OWNER_FIELD[doc.erp_doctype], as_list=True)}
		diff = {k: int(v) - int(have.get(k, 0)) for k, v in want.items() if int(v) != int(have.get(k, 0))}
		if diff:
			detail = json.dumps(diff)
	frappe.db.set_value(DOCTYPE, doc.name, {"rows_in_erp": n, "gap": gap, "checked_on": now_datetime(),
		**({"note": (f"Per salesperson source-ERPNext: {detail}")[:1000]} if detail else {})}, update_modified=False)
	return gap


def check() -> dict:
	"""Nightly: every SK Import re-counted; gaps to the CEO."""
	if not frappe.db.table_exists(DOCTYPE):
		return {}
	gaps = {}
	for name in frappe.get_all(DOCTYPE, pluck="name"):
		doc = frappe.get_doc(DOCTYPE, name)
		g = _check_one(doc)
		if g:
			gaps[name] = {"source": doc.source, "gap": g}
	if gaps:
		from sk_app.core.people import ceo_users

		text = _("Import gaps (source rows not in ERPNext): ") + "; ".join(f"{v['source']}: {v['gap']}" for v in gaps.values()) + \
			" <a href='/app/sk-import?gap=%5B%22%3E%22%2C0%5D'>SK Import</a>"
		for u in ceo_users():
			if not frappe.db.exists("ToDo", {"allocated_to": u, "status": "Open", "date": nowdate(), "description": ["like", "Import gaps%"]}):
				frappe.get_doc({"doctype": "ToDo", "allocated_to": u, "description": text, "priority": "High", "date": nowdate(),
					"reference_type": DOCTYPE}).insert(ignore_permissions=True)
	return gaps


def total_gap() -> int:
	if not frappe.db.table_exists(DOCTYPE):
		return 0
	return int(frappe.db.sql("select coalesce(sum(gap), 0) from `tabSK Import`")[0][0] or 0)
