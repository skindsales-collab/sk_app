"""Home "Decide now" data in ONE call (rebuild PR B, Path Switch Home): the 4 questions that need the person's decision,
read live from ERPNext. The phone draws the same strip as before; on the New path of Home it uses this list instead of
working it out from the KPI chart and the flow. No new screen."""

import frappe
from sk_app import store_screens
from frappe.utils import add_days, nowdate

from sk_app.core.decide_rules import keys_for, pick


def _safe(fn):
	try:
		return fn() or 0
	except Exception:
		frappe.clear_messages()
		return 0


def _leads_untouched(user: str, before) -> int:
	"""Own open leads (not cold calling) not touched since `before`; closed = lead_status.closed_lead_statuses(): Won, Junk,
	Loss and the old Converted / Unqualified (checker 7-Nov: live has Deal Loss, not Deal Lost)."""
	from sk_app.cold_calls import not_cold
	from sk_app.lead_status import closed_lead_statuses

	if not frappe.db.exists("DocType", "CRM Lead"):
		return 0
	return frappe.db.count("CRM Lead", {"lead_owner": user, "converted": 0, "modified": ["<", before],
		"status": ["not in", closed_lead_statuses() or [""]], **not_cold()})


def _quotes_waiting(user: str, before) -> int:
	"""Open submitted quotations older than `before` that are the person's: made by them, or on their CRM deal (quotes made
	by Claude / the CEO for a salesperson count for the deal owner)."""
	deal = "or q.crm_deal in (select name from `tabCRM Deal` where deal_owner = %(u)s)" \
		if frappe.get_meta("Quotation").has_field("crm_deal") and frappe.db.exists("DocType", "CRM Deal") else ""
	return frappe.db.sql(f"""select count(*) from `tabQuotation` q where q.docstatus = 1 and q.status = 'Open'
		and q.transaction_date < %(d)s and (q.owner = %(u)s {deal})""", {"u": user, "d": before})[0][0]


def _counts(user: str, keys: set) -> dict:
	from sk_app import store
	from sk_app.requisition import WAITING

	today = nowdate()
	q = {
		"approvals": lambda: frappe.db.count("Purchase Order", {"docstatus": 0, "sk_needs_ceo": 1})
			+ frappe.db.count("Material Request", {"docstatus": 0, "material_request_type": "Purchase", "sk_approval": WAITING})
			if frappe.get_meta("Purchase Order").has_field("sk_needs_ceo") else 0,
		"overdue_orders": lambda: frappe.db.count("Sales Order", {"docstatus": 1, "delivery_date": ["<", today],
			"status": ["in", ["To Deliver and Bill", "To Deliver"]]}),
		"unbilled": lambda: frappe.db.count("Sales Order", {"docstatus": 1, "per_billed": 0, "status": ["not in", ["Closed", "Completed"]]}),
		"low_stock": lambda: len(store_screens.low_stock(user)),
		"leads_untouched": lambda: _leads_untouched(user, add_days(today, -3)),
		"quotes_waiting": lambda: _quotes_waiting(user, add_days(today, -2)),
		"mr_waiting": lambda: len(store_screens.material_requests(user)),
	}
	return {k: _safe(q[k]) for k in keys if k in q}


def for_user(user: str, functions: list[str]) -> list[dict]:
	return pick(functions, _counts(user, keys_for(functions)))
