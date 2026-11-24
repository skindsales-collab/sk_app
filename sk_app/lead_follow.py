"""SK 24-Nov (approved): the linked lead's stage follows its deal (rules: lead_follow_rules). Runs on every deal save
(app, CRM screen, desk, Claude), where the app writes a deal directly, and hourly for deals changed in the last 2 hours.
Only the lead is written, without its save hooks, so nothing can come back and reset the deal. Old pairs that already
differ are not changed in bulk: a lead follows from the next change of its deal."""

import frappe
from frappe import _
from frappe.utils import add_to_date, now_datetime

from sk_app.lead_follow_rules import lead_stage


def _order_submitted(deal: str) -> bool:
	"""A submitted Sales Order, found as the Won gate finds it (gates.erp_docs: the customer's, the quotation's, or by PO)."""
	from sk_app import gates

	frappe.local.sk_gate_docs = None
	return any(o.get("docstatus") == 1 for o in gates.erp_docs(deal)[1])


def follow(deal: str) -> str | None:
	d = frappe.db.get_value("CRM Deal", deal, "*", as_dict=True)
	if not d or not d.get("lead"):
		return None
	lead = frappe.db.get_value("CRM Lead", d.lead, ["status", "lost_reason", "lost_notes"], as_dict=True)
	if not lead:
		return None
	types = dict(frappe.get_all("CRM Deal Status", fields=["name", "type"], as_list=True))
	typ = types.get(d.status)
	closed = [s for s, t in types.items() if t in ("Won", "Lost")]
	other = bool(frappe.db.exists("CRM Deal", {"lead": d.lead, "name": ["!=", deal], "status": ["not in", closed]})) if typ == "Lost" else False
	new = lead_stage(d.status, typ, d.get("custom_design_status"), lead.status, typ == "Won" and _order_submitted(deal), other)
	if not new or not frappe.db.exists("CRM Lead Status", new):
		return None
	values = {"status": new}
	if new == "Deal Loss":  # the CRM asks for the reason on the lead's next save
		values.update({f: d.get(f) for f in ("lost_reason", "lost_notes") if d.get(f) and not lead.get(f)})
	frappe.db.set_value("CRM Lead", d.lead, values, update_modified=False)
	frappe.get_doc({"doctype": "Comment", "comment_type": "Info", "reference_doctype": "CRM Lead", "reference_name": d.lead,
		"content": _("Stage {0} > {1}: follows deal {2}").format(lead.status, new, deal)}).insert(ignore_permissions=True)
	return new


def safe_follow(deal: str):
	try:
		return follow(deal)
	except Exception:
		frappe.log_error(f"SK App lead follows deal {deal}")  # never stops the deal's save


def on_deal_update(doc, method=None):
	if frappe.flags.in_import or frappe.flags.in_migrate or frappe.flags.in_patch:
		return
	before = doc.get_doc_before_save()
	if before and all(before.get(f) == doc.get(f) for f in ("status", "custom_design_status", "lead")):
		return
	safe_follow(doc.name)


def on_order_submit(doc, method=None):
	"""Sales Order on_submit, after the deal is marked Won: its lead becomes Deal Won."""
	names = {r.get("prevdoc_docname") for r in doc.items if r.get("prevdoc_docname")}
	if names and frappe.get_meta("Quotation").has_field("crm_deal"):
		for deal in set(frappe.get_all("Quotation", filters={"name": ["in", list(names)], "crm_deal": ["is", "set"]}, pluck="crm_deal")):
			safe_follow(deal)


def hourly():
	for deal in frappe.get_all("CRM Deal", filters={"modified": [">=", add_to_date(now_datetime(), hours=-2)], "lead": ["is", "set"]}, pluck="name", limit=0):
		safe_follow(deal)
