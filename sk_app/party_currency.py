"""SK 23-Nov (Swati / Pranali: "User don't have permissions to select/read this account" when they save or submit a
quotation in ERPNext): on every save ERPNext works out the party's account currency for the payment schedule, and to do
that it reads the party's receivable / payable Account, which Sales (and Purchase) users may not read. Before the
document is checked, the currency (only the currency, never the account) is worked out once as the system for this
request, so ERPNext uses that answer and the person needs no Account permission. Who may save / submit is unchanged:
ERPNext still checks the person's own Quotation / Sales Order / Purchase Order rights."""

import frappe

PARTY = {"Quotation": ("Customer", "party_name"), "Sales Order": ("Customer", "customer"), "Delivery Note": ("Customer", "customer"),
	"Sales Invoice": ("Customer", "customer"), "Purchase Order": ("Supplier", "supplier"), "Purchase Receipt": ("Supplier", "supplier"),
	"Purchase Invoice": ("Supplier", "supplier")}


def warm(doc, method=None):
	if doc.doctype not in PARTY or not doc.get("company") or frappe.session.user == "Administrator":
		return
	if doc.doctype == "Quotation" and doc.get("quotation_to") != "Customer":
		return
	party_type, field = PARTY[doc.doctype]
	party = doc.get(field)
	if not party or frappe.has_permission("Account", "select") or frappe.has_permission("Account", "read"):
		return
	from erpnext.accounts.party import get_party_account_currency

	from sk_app.store_screens import as_system

	try:
		with as_system():
			currency = get_party_account_currency(party_type, party, doc.company)
		# switching the user back empties the request cache, so the answer is put in it after the switch
		frappe.local.cache.setdefault("party_account_currency", {})[(party_type, party, doc.company)] = currency
	except Exception:
		frappe.log_error(f"SK App party currency {doc.doctype} {doc.name}")
