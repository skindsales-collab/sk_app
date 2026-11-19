"""File rules on every attach path (PR H, SK 16-Nov KF-05549): one hook on File, so the SK App, the Hub (design push),
the ERPNext desk and Frappe CRM all follow it."""

import frappe
from frappe import _

from sk_app.file_rules import CUSTOMER_FACING, allowed_on, customer_file_name


def check_file(doc, method=None):
	"""before_insert of File: a non-PDF / internal file on a customer-facing record is refused with the reason; a
	customer file name loses the internal cabin number."""
	if doc.get("is_folder") or not doc.get("attached_to_doctype"):
		return
	ok, why = allowed_on(doc.attached_to_doctype, doc.file_name)
	if not ok:
		frappe.throw(_(why), title=_("Not for the customer's record"))
	if doc.attached_to_doctype in CUSTOMER_FACING:
		clean = customer_file_name(doc.file_name)
		if clean != doc.file_name:
			doc.file_name = clean
