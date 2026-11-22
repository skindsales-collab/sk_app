"""SK 21-Nov: the quote sent to the customer is the ERPNext Quotation's own print (SK Cabin Quotation format). On submit
its PDF is saved on the Quotation and on its CRM Deal, so the app's PDF / WhatsApp buttons and the deal show the same
file; no separate quote PDF is made."""

import frappe


def attach_on_submit(doc, method=None):
	try:
		fmt = frappe.get_meta("Quotation").default_print_format or "SK Cabin Quotation"
		pdf = frappe.attach_print("Quotation", doc.name, print_format=fmt, doc=doc)
		name = f"{(doc.get('sk_quote_ref') or doc.name).replace('/', '-')}_{doc.name}.pdf"
		for dt, dn in (("Quotation", doc.name), ("CRM Deal", doc.get("crm_deal"))):
			if dn and frappe.db.exists(dt, dn) and not frappe.db.exists("File", {"attached_to_doctype": dt, "attached_to_name": dn, "file_name": name}):
				frappe.get_doc({"doctype": "File", "file_name": name, "content": pdf["fcontent"], "is_private": 1,
					"attached_to_doctype": dt, "attached_to_name": dn}).insert(ignore_permissions=True)
	except Exception:
		frappe.log_error(f"SK App quote PDF on submit {doc.name}")  # never stops the submit
