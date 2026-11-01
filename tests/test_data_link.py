"""SK 1-Nov 13:03 "check for proper data update": portal notices are not leads; SK's status flow decides open / closed."""

import sys
import types

from sk_app.gate_rules import is_portal_enquiry

sys.modules.setdefault("frappe", types.ModuleType("frappe"))
from sk_app.lead_status import is_closed  # noqa: E402


def test_portal_notices_are_not_leads():
	empty = {"first_name": "Enquiry", "mobile_no": None, "email": None, "organization": ""}
	assert not is_portal_enquiry(empty, "10 India BuyLeads allocated successfully!")
	assert not is_portal_enquiry(empty, 'Confirmed "Automatic Wc Flushing System"  Deal ?')
	assert not is_portal_enquiry({**empty, "mobile_no": "9876543210"}, "See how Sk Ind Tech performed last week")
	assert not is_portal_enquiry(empty, "Enquiry for Portable Cabin")  # no buyer contact at all


def test_real_buyer_enquiries_are_leads():
	assert is_portal_enquiry({"first_name": "Ramesh Patil", "mobile_no": "98220 12345"}, "Enquiry for Portable Cabin from Ramesh")
	assert is_portal_enquiry({"first_name": "Ramesh Patil", "mobile_no": None, "email": "ramesh@patil.in"}, "Buyer enquiry")
	assert not is_portal_enquiry({"first_name": "Enquiry", "mobile_no": None, "email": "x@y.in"}, "Buyer enquiry")


def test_sk_flow_decides_closed_statuses():
	assert not is_closed("Qualified", "Won")  # old Frappe CRM type Won, SK: open work
	assert is_closed("Junk Lead", "Open")  # CRM has no Junk type, so it was saved as Open
	assert is_closed("Deal Won", "Won") and is_closed("Deal Loss", "Lost")
	assert not is_closed("New", "Open") and not is_closed("Negotiations", "Ongoing")
	assert is_closed("Converted", "Won") and is_closed("Unqualified", "Lost") and is_closed("Junk", "Lost")
	assert not is_closed("Contacted", "Ongoing")
