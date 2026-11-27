"""SK 27-Nov "keep 850, no change" (Rothe): runs once on deploy, and only if 850, 856 and 857 are all cancelled
(Accounts cancels 857 first). The three become -CXL, the counter goes back to 855, a draft SK/IND/1126/850 is made
for Accounts to submit. Nothing happens otherwise."""

import frappe


def execute():
	from sk_app.invoice_naming import keep_number

	names = ["SK/IND/1126/850", "SK/IND/1126/856", "SK/IND/1126/857"]
	if not all(frappe.db.exists("Sales Invoice", n) for n in names):
		return
	made = keep_number("SK/IND/1126/850", names, "SK/IND/1126/857", 855)
	frappe.log_error(title="SK App keep invoice 850", message=f"made: {made}") if not made else None
