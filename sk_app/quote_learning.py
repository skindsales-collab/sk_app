"""Quote correction and learning (SK 27-Nov). Rules in quote_learning_rules.py; this file reads and writes ERPNext.

Every corrected quote amount is kept in "SK Quote Correction" against the cabin's specification. It teaches (status
Teaching) only when SK approved it or the quote became a Sales Order; the next similar quote then shows a learned amount
beside the rate card. No outside AI, all data stays in ERPNext.
"""

from __future__ import annotations

import frappe
from frappe.utils import cint, flt

from sk_app import quote_learning_rules as R

DOCTYPE = "SK Quote Correction"


def _ready() -> bool:
	return bool(frappe.db.exists("DocType", DOCTYPE))


def cabin_line(p: dict) -> dict | None:
	return next((ln for ln in p.get("lines") or [] if ln["kind"] == "cabin"), None)


def learned_for(p: dict, rc: dict) -> dict | None:
	"""Learned amount for this specification from the corrections that teach (latest 50)."""
	ln = cabin_line(p)
	if not (_ready() and ln and p.get("spec_key")):
		return None
	factors = frappe.get_all(DOCTYPE, filters={"spec_key": p["spec_key"], "status": "Teaching"}, pluck="factor", order_by="creation desc", limit=50)
	out = R.learned(flt(ln["rate"]), [flt(f) for f in factors], cint(p.get("qty")) or 1, flt(rc.get("round_to")) or 1)
	if out:
		out["total"] = flt(p["total"]) - flt(ln["amount"]) + out["cabins"]  # options and transport as on the rate card
	return out


def apply(p: dict, corrected: float) -> dict:
	"""Lines with the cabin rate set so the quote total is the corrected amount; returns the back-calculation too."""
	ln = cabin_line(p)
	if not ln:
		frappe.throw(frappe._("No cabin line to correct"))
	qty = cint(ln["qty"]) or 1
	try:
		rate = R.correction_rate(p["lines"], flt(corrected), qty)
	except ValueError:
		frappe.throw(frappe._("The corrected amount must be more than the options and transport together"))
	calc = R.implied(flt(ln["rate"]), rate, flt(p.get("area")))
	calc.update({"suggested_rate": flt(ln["rate"]), "corrected_rate": rate, "suggested_total": flt(p["total"]), "corrected_total": flt(corrected)})
	return calc


def set_cabin_rate(rows: list[dict], cabin_code: str, rate: float):
	for r in rows:
		if r["item_code"] == cabin_code:
			r["rate"] = rate


def record(user: str, doc, req: dict, p: dict, calc: dict, teaches: bool, rc: dict):
	"""Keep the correction against the specification. A revision of the same quotation replaces its older correction."""
	if not _ready():
		return None
	for old in frappe.get_all(DOCTYPE, filters={"quotation": doc.name, "status": ["!=", "Not used"]}, pluck="name"):
		frappe.db.set_value(DOCTYPE, old, "status", "Not used")
	opts = ", ".join(f"{k}: {v}" for k, v in (req.get("options") or {}).items() if v)
	c = frappe.get_doc({"doctype": DOCTYPE, "spec_key": p["spec_key"], "cabin_type": req.get("type"), "title_text": req.get("title"),
		"length": flt(req.get("length")), "width": flt(req.get("width")), "height": flt(req.get("height")) or flt(rc.get("standard_height_ft")),
		"area": flt(p.get("area")), "qty": cint(p.get("qty")) or 1, "options": opts,
		"suggested_rate": calc["suggested_rate"], "corrected_rate": calc["corrected_rate"], "suggested_total": calc["suggested_total"],
		"corrected_total": calc["corrected_total"], "factor": calc["factor"], "pct": calc["pct"], "per_sqft": calc["per_sqft"],
		"status": "Teaching" if teaches and calc["teaches"] else "Waiting", "quotation": doc.name, "deal": doc.get("crm_deal") or None,
		"corrected_by": user, "rate_card": rc.get("version")})
	c.insert(ignore_permissions=True)
	return c.name


def set_status(quotation: str, status: str):
	if not _ready():
		return
	for name, factor in frappe.get_all(DOCTYPE, filters={"quotation": quotation, "status": "Waiting" if status == "Teaching" else ["!=", "Not used"]},
			fields=["name", "factor"], as_list=True):
		ok = status != "Teaching" or R.FACTOR_MIN <= flt(factor) <= R.FACTOR_MAX
		frappe.db.set_value(DOCTYPE, name, "status", status if ok else "Waiting")


def on_order_submit(doc, method=None):
	"""A quote that became an order teaches (SK 27-Nov)."""
	for q in {d.prevdoc_docname for d in doc.items if d.get("prevdoc_docname")}:
		set_status(q, "Teaching")


def corrections(quotation: str) -> list[dict]:
	if not _ready():
		return []
	return frappe.get_all(DOCTYPE, filters={"quotation": quotation}, fields=["name", "status", "corrected_total", "pct", "per_sqft"])


def ensure_field():
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	create_custom_fields({"Quotation": [{"fieldname": "sk_corrected_amount", "label": "Corrected amount (before GST)", "fieldtype": "Currency",
		"insert_after": "sk_discount_pct", "read_only": 1,
		"description": "SK 27-Nov: the amount the salesperson typed instead of the rate card; kept in SK Quote Correction"}]}, update=True)

