"""GST filled by the app (SK 6-Nov, KF-04410: one entry, the app fills the rest). A Sales Order or Sales Invoice saved
with no tax rows and no template gets the company's Output GST template (in-state / out-state by GSTIN), on the New path
of Sales; the save goes on either way and the fill is written on the timeline. Quotations are left as they are."""

import frappe
from frappe import _

from sk_app.writers.taxes_rules import needs_fill, pick_template, same_state


def _gstin(doctype: str, name: str | None) -> str | None:
	if not name:
		return None
	meta = frappe.get_meta(doctype)
	for f in ("gstin", "gst_in", "tax_id"):
		if meta.has_field(f):
			v = frappe.db.get_value(doctype, name, f)
			if v:
				return v
	return None


def fill(doc) -> str | None:
	"""Sets taxes_and_charges and the tax rows on an unsaved / draft doc; returns the template used or None."""
	company = doc.company
	templates = frappe.get_all("Sales Taxes and Charges Template", fields=["name", "company", "disabled", "is_default"])
	party_state = doc.get("place_of_supply")  # India Compliance: "27-Maharashtra"
	company_state = frappe.db.get_value("Company", company, "state") if frappe.get_meta("Company").has_field("state") else None
	company_gstin = doc.get("company_gstin") or _gstin("Company", company)
	party_gstin = doc.get("billing_address_gstin") or _gstin("Customer", doc.get("customer"))
	template = pick_template(templates, company, same_state(company_gstin, party_gstin, party_state and party_state[3:], company_state))
	if not template:
		return None
	doc.taxes_and_charges = template
	doc.set("taxes", [])
	from erpnext.controllers.accounts_controller import get_taxes_and_charges

	for row in get_taxes_and_charges("Sales Taxes and Charges Template", template) or []:
		doc.append("taxes", row)
	doc.calculate_taxes_and_totals()
	return template


def on_validate(doc, method=None):
	"""Every Sales Order / Sales Invoice on the New path of Sales, from the app, ERPNext or SK Hub."""
	from sk_app.core.switch import use_new

	if doc.docstatus != 0 or frappe.flags.in_import or not use_new("Sales", doc.owner or frappe.session.user):
		return
	if not needs_fill(doc.doctype, len(doc.get("taxes") or []), doc.get("taxes_and_charges"), doc.net_total):
		return
	template = fill(doc)
	if template:
		doc.flags.sk_gst_filled = template


def after_save(doc, method=None):
	if doc.flags.get("sk_gst_filled"):
		doc.add_comment("Comment", _("GST filled by SK App: {0}").format(doc.flags.sk_gst_filled))
		doc.flags.sk_gst_filled = None
