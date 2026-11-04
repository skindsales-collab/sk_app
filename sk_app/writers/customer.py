"""Customer checks on the record (linear flow map, Flow 1 step 4). The Customer has one maker (erp_flow.make_customer),
but GSTIN and the billing address were optional, so 1,757 customers have 89 addresses and new quotes / orders stop on
customer_missing. On the New path of Sales every new customer, from any door, is checked once and its gaps logged."""

import frappe
from frappe import _

from sk_app.core.rules import report


def after_insert(doc, method=None):
	from sk_app import gates
	from sk_app.core.switch import use_new

	if not use_new("Sales", doc.owner or frappe.session.user):
		return
	report("Sales", doc, [("customer_" + k, f"Customer {doc.customer_name}: {w}") for k, w in gates.customer_missing(doc.name)],
		title=_("Customer data missing"))
