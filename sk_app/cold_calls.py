"""Cold Calling list (SK 27-Oct-2026, Pranali: "all leads, including cold-calling data, are displayed under My Leads; a
separate option for Cold Calling Leads will make it easier to call cold leads without mixing them with current leads").

A cold lead is a CRM Lead with sk_cold = 1. It stays a normal ERPNext / CRM lead (same owner, Call / WhatsApp / Mail
logged and counted), but it is kept out of My Leads, the New count, the status arrows and Decide Now. When the customer
shows interest the salesperson taps "Interested → My Leads" and it joins the normal lead flow.

SK 28-Oct (Rev 1 point 7, Pranali, approved): "cold calling data must move to Marketing, it is not a lead". Every cold
lead now moves to the Marketing list (an ERPNext Contact in the same person's name, its calls and notes moved with it)
and the lead is removed. A call list uploaded as "Cold calling" goes straight to the Marketing list. When someone is
interested, "Make lead" on the Marketing list makes the lead.
"""

import frappe
from frappe import _
from frappe.utils import add_days, now_datetime

FIELD = "sk_cold"
COLD_SOURCE = "Cold calling"


def has_field() -> bool:
	return bool(frappe.db.exists("DocType", "CRM Lead")) and frappe.get_meta("CRM Lead").has_field(FIELD)


def not_cold() -> dict:
	"""Filter for the normal lead lists."""
	return {FIELD: ["!=", 1]} if has_field() else {}


def ensure_field():
	if not frappe.db.exists("DocType", "CRM Lead"):
		return
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	create_custom_fields({"CRM Lead": [{"fieldname": FIELD, "label": "Cold calling lead", "fieldtype": "Check", "insert_after": "status",
		"in_standard_filter": 1, "description": "Call-list data: shown in the app's Cold Calling list, not in My Leads"}]}, update=True)
	frappe.clear_cache(doctype="CRM Lead")
	if not frappe.db.get_default("sk_cold_backfill"):
		backfill()
		frappe.db.set_default("sk_cold_backfill", "1")


def backfill(days: int = 3) -> int:
	"""Existing call-list data: leads still New, never called, more than `days` old (SK 27-Oct option 1)."""
	first = frappe.get_all("CRM Lead Status", order_by="position asc", pluck="name", limit=1)
	names = frappe.get_all("CRM Lead", filters={"converted": 0, "status": first[0] if first else "New", "first_responded_on": ["is", "not set"],
		"creation": ["<", add_days(now_datetime(), -days)], FIELD: ["!=", 1]}, pluck="name", limit=0)
	names += frappe.get_all("CRM Lead", filters={"source": COLD_SOURCE, FIELD: ["!=", 1]}, pluck="name", limit=0)
	for n in set(names):
		frappe.db.set_value("CRM Lead", n, FIELD, 1, update_modified=False)
	return len(set(names))


def cold_list(user: str, q: str | None = None) -> list[dict]:
	"""The person's cold leads: never called first, then the ones called longest ago."""
	if not has_field():
		return []
	filters = {"lead_owner": user, "converted": 0, FIELD: 1}
	or_filters = None
	if (q or "").strip():
		like = f"%{q.strip()}%"
		or_filters = [["lead_name", "like", like], ["organization", "like", like], ["mobile_no", "like", like]]
	rows = frappe.get_all("CRM Lead", filters=filters, or_filters=or_filters, fields=["name", "lead_name", "organization", "mobile_no",
		"phone", "email", "source", "status", "creation"], order_by="creation desc", limit=0)
	calls = {}
	if rows and frappe.db.exists("DocType", "CRM Call Log"):
		for c in frappe.get_all("CRM Call Log", filters={"reference_doctype": "CRM Lead", "reference_docname": ["in", [r.name for r in rows]]},
				fields=["reference_docname", "status", "duration", "creation"], order_by="creation asc", limit=0):
			x = calls.setdefault(c.reference_docname, {"n": 0, "last": None, "last_status": None})
			x["n"] += 1
			x["last"], x["last_status"] = str(c.creation), c.status
	out = []
	for r in rows:
		c = calls.get(r.name, {"n": 0, "last": None, "last_status": None})
		out.append({"doctype": "CRM Lead", "name": r.name, "title": r.organization or r.lead_name or r.name, "person": r.lead_name,
			"mobile": r.mobile_no or r.phone, "email": r.email, "source": r.source, "calls": c["n"], "last": c["last"],
			"last_status": c["last_status"], "created": str(r.creation)})
	out.sort(key=lambda r: (r["calls"] > 0, r["last"] or ""))
	return out


def set_cold(user: str, lead: str, cold: int) -> dict:
	"""'Interested → My Leads' (cold = 0) or 'Move to Cold Calling' (cold = 1), by the lead's owner or their manager."""
	from sk_app.crm import _check

	_check("CRM Lead", lead, "write")
	if int(cold):
		return {"name": lead, "cold": 1, "contact": move_to_marketing(lead)}
	frappe.db.set_value("CRM Lead", lead, FIELD, 0)
	return {"name": lead, "cold": 0}


def move_to_marketing(lead: str) -> str | None:
	"""One cold lead → the Marketing list. Its calls and notes move to the Contact; the lead is then removed."""
	from sk_app.marketing_list import put_on_list

	l = frappe.db.get_value("CRM Lead", lead, ["name", "first_name", "last_name", "lead_name", "organization", "mobile_no", "phone",
		"email", "lead_owner", "owner", "source", "status"], as_dict=True)
	if not l:
		return None
	person = l.lead_name or " ".join(filter(None, [l.first_name, l.last_name])) or l.organization or l.mobile_no or l.email or lead
	mobile = l.mobile_no or l.phone
	if not mobile and not l.email:
		return None
	contact = put_on_list(l.lead_owner or l.owner, person, mobile, l.organization, None, l.email)["name"]
	calls = 0
	for doctype in ("CRM Call Log", "FCRM Note", "Comment", "Communication"):
		if not frappe.db.exists("DocType", doctype):
			continue
		ref, refname = ("reference_doctype", "reference_name") if doctype in ("Comment", "Communication") else ("reference_doctype", "reference_docname")
		rows = frappe.get_all(doctype, filters={ref: "CRM Lead", refname: lead}, pluck="name", limit=0)
		for n in rows:
			frappe.db.set_value(doctype, n, {ref: "Contact", refname: contact}, update_modified=False)
		if doctype == "CRM Call Log":
			calls = len(rows)
	frappe.get_doc({"doctype": "Comment", "comment_type": "Info", "reference_doctype": "Contact", "reference_name": contact,
		"content": f"Moved from cold-calling lead {lead} ({l.source or 'no source'}, {l.status}, {calls} calls) by SK App"}).insert(ignore_permissions=True)
	try:
		frappe.delete_doc("CRM Lead", lead, ignore_permissions=True, force=True)
	except Exception:
		# a lead ERPNext will not remove (linked elsewhere) stays a cold lead, out of every lead list
		frappe.log_error(f"SK App cold lead {lead} not removed")
	return contact


def move_all(user: str | None = None) -> int:
	n = 0
	if not has_field():
		return n
	for lead in frappe.get_all("CRM Lead", filters={FIELD: 1, "converted": 0}, pluck="name", limit=0):
		if move_to_marketing(lead):
			n += 1
	return n


def move_all_once():
	"""On deploy: every cold lead, called or not (SK's default for point 7), moves to the Marketing list once."""
	if frappe.db.get_default("sk_cold_to_marketing"):
		return
	move_all()
	frappe.db.set_default("sk_cold_to_marketing", "1")
