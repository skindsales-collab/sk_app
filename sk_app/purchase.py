"""Purchase screens (SK, 26-Oct-2026 draft F02): requests to buy, get rates from 3 suppliers on WhatsApp / email,
compare quotes, Purchase Order with SK's approval above a limit, delivery follow-up, new supplier, supplier bills to
Accounts and last rates. Free only: messages go from the person's own WhatsApp / mail app.
"""

import frappe
from frappe import _
from frappe.utils import add_days, flt, fmt_money, getdate, nowdate

from sk_app.store import _company, _todo, _users_with_function, attach, material_pos, draft_reason, need, try_submit, uom
from sk_app.store_screens import material_requests
from sk_app.core.switch import use_new


PURCHASE = "Purchase"

# SK 26-Oct-2026: Rs 5,000 (draft F02 had proposed Rs 50,000); can be changed in site config "sk_po_approval_limit"
DEFAULT_PO_LIMIT = 5000

def po_limit() -> float:
	return flt(frappe.conf.get("sk_po_approval_limit") or DEFAULT_PO_LIMIT)
