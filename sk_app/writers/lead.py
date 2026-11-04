"""The one CRM Lead writer (linear flow map, Flow 1 step 1). The app lead form and the mail scan (IndiaMART, JustDial,
GeM) each made a lead their own way; the mail scan skipped the mandatory fields silently. On the New path of Sales both
come through here: the same fields, owner, segment, first status, requirement note and photo, and the mandatory gate
reported the one way (the app still stops; a mail lead is saved and its gaps go to SK Rule Log so someone completes it).
Same inputs and outputs for the user (SK 4-Nov)."""

import frappe
from frappe import _

from sk_app.core.rules import report
from sk_app.writers.lead_rules import problems, shape


def write(user: str | None, data: dict, *, stop_on_missing: bool, requirement: str | None = None, photo: str | None = None,
		no_gstin=0):
	"""data: first_name, organization, mobile_no, email, source, segment, product, owner, status. Returns the saved lead."""
	from sk_app import crm, gates

	d = shape(data)
	if d["source"] and not frappe.db.exists("CRM Lead Source", d["source"]):
		from sk_app.lead_sources import _ensure_source

		_ensure_source(d["source"])
	found = problems(d)
	if found and stop_on_missing:
		gates.stop(_("Lead cannot be saved"), [(k[5:], w) for k, w in found])
	status = data.get("status")
	status = [status] if status and frappe.db.exists("CRM Lead Status", status) \
		else frappe.get_all("CRM Lead Status", order_by="position asc", pluck="name", limit=1)
	doc = frappe.new_doc("CRM Lead")
	doc.update({k: v for k, v in d.items() if v is not None and (k in ("first_name", "organization", "mobile_no", "email", "source", "lead_owner")
		or doc.meta.has_field(k))})
	doc.status = status[0] if status else "New"
	if frappe.utils.cint(no_gstin) and doc.meta.has_field(gates.NO_GSTIN):
		doc.set(gates.NO_GSTIN, 1)
	if not stop_on_missing:
		doc.flags.ignore_permissions = True
		doc.flags.ignore_mandatory = True
	doc.insert()
	report("Sales", doc, found, title=_("Lead data missing"))
	if (requirement or "").strip():
		frappe.get_doc({"doctype": "FCRM Note", "title": _("Requirement"), "content": requirement.strip(),
			"reference_doctype": "CRM Lead", "reference_docname": doc.name}).insert(ignore_permissions=True)
	if photo and user:
		crm._attach(photo, "CRM Lead", doc.name, user)
	return doc
