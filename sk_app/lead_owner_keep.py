"""SK 23-Nov (approved, low-orders review): cancelling a task (ToDo) on a lead or deal no longer empties its owner.
Frappe CRM clears lead_owner / deal_owner whenever any ToDo on the record is cancelled, so closing a "Customer mail" or
quote task left leads with no owner. The owner before the cancel is kept. Clean-up on migrate: duplicate open
"Customer mail" tasks (one per lead / deal per person is kept, the newest) and tasks made from salary / PF / password /
our own mails are closed (status Cancelled, can be reopened)."""

import frappe

FIELD = {"CRM Lead": "lead_owner", "CRM Deal": "deal_owner"}


def remember_owner(doc, method=None):
	"""ToDo validate: the record's owner just before a cancel."""
	field = FIELD.get(doc.get("reference_type"))
	if not field or not doc.get("reference_name") or doc.is_new() or doc.status != "Cancelled":
		return
	before = doc.get_doc_before_save()
	if before and before.status != "Cancelled":
		doc.flags.sk_owner_before = frappe.db.get_value(doc.reference_type, doc.reference_name, field)


def keep_owner(doc, method=None):
	"""ToDo on_update (runs after Frappe CRM's): the owner is put back when the cancel emptied it."""
	owner = doc.flags.get("sk_owner_before")
	field = FIELD.get(doc.get("reference_type"))
	if not owner or not field or not frappe.db.exists(doc.reference_type, doc.reference_name):
		return
	if not frappe.db.get_value(doc.reference_type, doc.reference_name, field):
		frappe.db.set_value(doc.reference_type, doc.reference_name, field, owner, update_modified=False)


def clean_mail_todos() -> dict:
	from sk_app.lead_mail_rules import private_or_internal
	from sk_app.mailbox import MAIL_TODO

	rows = frappe.get_all("ToDo", filters={"status": "Open", "description": ["like", MAIL_TODO + "%"]},
		fields=["name", "allocated_to", "reference_type", "reference_name", "description"], order_by="creation desc", limit=0)
	seen, closed_dup, closed_private = set(), 0, 0
	for t in rows:
		subject = (t.description or "")[len(MAIL_TODO):]
		if private_or_internal("x@customer.example", subject):
			frappe.db.set_value("ToDo", t.name, "status", "Cancelled", update_modified=False)
			closed_private += 1
			continue
		k = (t.allocated_to, t.reference_type, t.reference_name)
		if k in seen:
			frappe.db.set_value("ToDo", t.name, "status", "Cancelled", update_modified=False)
			closed_dup += 1
		seen.add(k)
	return {"duplicates_closed": closed_dup, "private_closed": closed_private}
