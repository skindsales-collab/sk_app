"""Store screens (SK, 26-Oct-2026 draft F01): stock check, receive, issue to a job, requests, dispatch, low stock,
monthly count and new item. Every record is made under the person's own login; the phone sends photos and taps,
ERPNext keeps the documents (Purchase Receipt, Stock Entry, Material Request, Delivery Note, Stock Reconciliation).

Documents that change money (receipt, dispatch, count) stay as drafts for the owner / Accounts to post; a material
issue to a job is posted at once when ERPNext allows it, otherwise it stays as a draft and the screen says so.
"""

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, nowdate

from sk_app import logins
from sk_app.core.switch import use_new


STORE = "Stores"

def need(user: str, *functions: str):
	"""Only people in the function (or the ERPNext admin) may use its screens. Records are then saved under their
	own login with ignore_permissions, because Store helpers do not carry every ERPNext stock role."""
	if "System Manager" in frappe.get_roles(user):
		return
	have = set(logins.profile_functions(user))
	if not have & set(functions):
		frappe.throw(_("This screen is for {0}").format(" / ".join(functions)), frappe.PermissionError)

def attach(file_url: str | None, doctype: str, name: str, user: str):
	"""Attach a photo the person uploaded from the phone to the ERPNext record."""
	if not file_url:
		return
	file_name = frappe.db.get_value("File", {"file_url": file_url, "owner": user, "attached_to_name": ["is", "not set"]})
	if file_name:
		frappe.db.set_value("File", file_name, {"attached_to_doctype": doctype, "attached_to_name": name})

def insert_for(doc, user: str):
	"""Insert as the system, kept in the person's name. ERPNext fills the supplier's payable account while saving and
	refuses when the person (Store) may not read accounts (SK 27-Oct, Yogesh: "User don't have permissions to
	select/read this account")."""
	current = frappe.session.user
	frappe.set_user("Administrator")
	try:
		doc.flags.ignore_permissions = True
		doc.insert()
	finally:
		frappe.set_user(current)
	frappe.db.set_value(doc.doctype, doc.name, {"owner": user, "modified_by": user}, update_modified=False)
	doc.owner = doc.modified_by = user
	return doc

def submit_for(doc, user: str) -> bool:
	"""Post by the document's owner in the app (Store posts its receipt): ERPNext's own submit and checks, run by the
	system because posting writes accounts the store login may not read (SK 27-Oct: receipt stuck in draft)."""
	current = frappe.session.user
	frappe.set_user("Administrator")
	try:
		posted = try_submit(doc)
	finally:
		frappe.set_user(current)
	if posted:
		frappe.db.set_value(doc.doctype, doc.name, "modified_by", user, update_modified=False)
	return posted

def try_submit(doc) -> bool:
	"""Post the document if ERPNext accepts it (stock available, accounts set); else keep the draft.
	SK 4-Nov rebuild (F2): ERPNext's reason is kept for the screen too (draft_reason), not only in a comment."""
	frappe.flags.sk_draft_reason = None
	frappe.db.savepoint("sk_submit")
	try:
		doc.flags.ignore_permissions = True
		doc.submit()
		return True
	except Exception as e:
		frappe.db.rollback(save_point="sk_submit")
		frappe.clear_messages()
		doc.reload()
		reason = frappe.utils.strip_html(str(e) or type(e).__name__)[:200]
		frappe.flags.sk_draft_reason = reason
		doc.add_comment("Comment", _("Kept as draft by SK App: {0}").format(reason))
		return False

def draft_reason() -> str | None:
	"""Why the last try_submit kept its draft (None when it posted)."""
	return frappe.flags.get("sk_draft_reason")

def uom(item_code: str) -> dict:
	"""Unit fields ERPNext wants on every item row (rows made by hand, not mapped from another document)."""
	u = frappe.db.get_value("Item", item_code, "stock_uom")
	return {"uom": u, "stock_uom": u, "conversion_factor": 1}

def _company():
	# SK 28-Oct (Rev 1 point 5): a dashboard set to one company reads that company; entries use the person's company
	return frappe.flags.get("sk_company") or frappe.defaults.get_user_default("Company") \
		or frappe.db.get_single_value("Global Defaults", "default_company") or frappe.db.get_value("Company", {}, "name")

def material_pos(doctype: str = "Purchase Order") -> dict:
	"""Filter for the POs / receipts of material: a labour PO (sk_job_card) runs its own chain, its GRN and bill made by
	themselves when the job is done and passed (SK 29-Oct), so purchase, store, quality and accounts lists leave it out."""
	return {"sk_job_card": ["is", "not set"]} if frappe.get_meta(doctype).has_field("sk_job_card") else {}

def _users_with_function(function: str) -> list[str]:
	main = frappe.get_all("SK App User", filters={"home": function, "enabled": 1}, pluck="user")
	other = frappe.get_all("SK App User Function", filters={"function": function, "parenttype": "SK App User"}, pluck="parent")
	other = frappe.get_all("SK App User", filters={"name": ["in", other or [""]], "enabled": 1}, pluck="user")
	from sk_app.logins import profile_functions  # SK 9-Nov: a job doer with a workstation is not the Machine Shifting owner

	return [u for u in dict.fromkeys(main + other) if function in profile_functions(u)]

def users_or_ceo(function: str) -> list[str]:
	"""People of a function, else the CEO (SK 1-Nov logic check A1/A2: a QC check or "make the PO" task that found nobody
	with the function went to nobody; now it reaches the CEO, who sees the gap)."""
	return _users_with_function(function) or _users_with_function("Management")

def _todo(user: str, doctype: str, name: str, text: str):
	frappe.get_doc({"doctype": "ToDo", "allocated_to": user, "reference_type": doctype, "reference_name": name,
		"description": text, "priority": "High", "date": nowdate()}).insert(ignore_permissions=True)
