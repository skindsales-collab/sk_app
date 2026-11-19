"""Purchase requisition (SK 27-Oct-2026): every purchase starts as a requisition, the CEO approves it, a PO is made
only from an approved requisition (same ERP item codes) and Store receives only against that PO. All of it is the
ERPNext chain Material Request → Purchase Order → Purchase Receipt → Purchase Invoice.

- One form with Planned / Urgent; project / cabin code; the form shows stock, minimum order qty, re-order level and
  last rate. Raised by Store (Yogesh) or Purchase (Aarti).
- Material that came without a PO: Store raises an urgent requisition with the challan photo; same route.
- The CEO's approval screen shows the estimated value; for Urgent also the last rate and the best two quotes.
"""

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, getdate, now_datetime, nowdate

from sk_app.store import STORE, _company, _todo, _users_with_function, attach, need, uom, users_or_ceo
from sk_app.store_screens import _default_store


MANAGEMENT = "Management"

MAX_ITEMS = 20

RAISERS = (STORE, "Purchase", MANAGEMENT, "HR", "Accounts")  # SK 28-Oct: Aarti (HR, acting purchase manager)
# SK 2-Nov: Accounts receives material; without a PO it raises the urgent requisition, the CEO approves, a PO is made
WAITING, APPROVED, REJECTED = "Waiting CEO", "Approved", "Rejected"

PRIORITIES = ("Planned", "Urgent")

def _is_ceo(user: str) -> bool:
	from sk_app.core.people import is_ceo  # one shared check (rebuild Phase 0)

	return is_ceo(user)

def _ceos() -> list[str]:
	from sk_app.core.people import ceo_users

	return ceo_users()
