from sk_app.gate_rules import (
	count_missing,
	customer_missing,
	deal_step_needs,
	is_placeholder_name,
	lead_may_become_deal,
	lead_missing,
	old_order_data_pending,
	order_missing,
	quotation_missing,
	request_missing,
)


def keys(missing):
	return {k for k, _t in missing}


def test_placeholder_names():
	for name in ["Enquiry", "enquiry from IndiaMART", "  ", None, "9876543210", "Lead 12", "New Enquiry", "Cabin enquiry", "Sir"]:
		assert is_placeholder_name(name), name
	for name in ["Godrej Properties", "Rushi Patil", "Lead Engineering Pvt Ltd", "Bharat Forge"]:
		assert not is_placeholder_name(name), name


def test_lead_needs_name_mobile_segment_source():
	full = {"first_name": "Amit Shah", "organization": "ABC Infra", "mobile_no": "+91 98220 12345", "sk_segment": "Office Cabin",
		"source": "IndiaMART", "lead_owner": "rushi@x"}
	assert lead_missing(full) == []
	bad = {"first_name": "Enquiry", "organization": "", "mobile_no": "12345", "sk_segment": None, "source": "", "lead_owner": ""}
	assert keys(lead_missing(bad)) == {"organization", "first_name", "mobile_no", "sk_segment", "source", "lead_owner"}
	# a deal carries deal_owner instead of lead_owner
	assert lead_missing({**full, "lead_owner": None, "deal_owner": "rushi@x"}) == []
	# no mobile but a way to reach: JustDial (number only inside JustDial) or a mail enquiry with the sender's e-mail
	assert lead_missing({**full, "mobile_no": None, "source": "JustDial"}) == []
	assert lead_missing({**full, "mobile_no": None, "source": "Email", "email": "a@b.com"}) == []
	assert keys(lead_missing({**full, "mobile_no": None, "source": "Email"})) == {"mobile_no"}
	assert keys(lead_missing({**full, "mobile_no": None, "source": "IndiaMART", "email": "a@b.com"})) == {"mobile_no"}


def test_customer_gstin_or_unregistered_with_reason():
	base = {"customer_name": "ABC Infra", "address_state": "Maharashtra", "address_pincode": "411014", "mobile_no": "9822012345"}
	assert customer_missing({**base, "gst_category": "Registered Regular", "gstin": "27AAACA1234A1Z5"}) == []
	assert keys(customer_missing({**base, "gst_category": "Registered Regular", "gstin": "27AAAC"})) == {"gstin"}
	assert keys(customer_missing({**base, "gst_category": "Unregistered"})) == {"gstin"}
	assert customer_missing({**base, "gst_category": "Unregistered", "sk_gst_note": "Individual, no GST"}) == []
	assert keys(customer_missing({**base, "gst_category": "Unregistered", "sk_gst_note": "x", "address_state": ""})) == {"address"}


def test_non_gst_person_needs_no_gstin():
	"""SK 4-Nov: a person (non-GST, unregistered) customer is complete with no GSTIN and no reason."""
	base = {"customer_name": "Nishant Vinayak Jamdade", "address_state": "Maharashtra", "address_pincode": "411014", "mobile_no": "8329307905"}
	assert customer_missing({**base, "customer_type": "Individual", "gst_category": "Unregistered"}) == []
	assert customer_missing({**base, "customer_type": "Individual"}) == []  # no category yet = unregistered
	# a company still says it has no GSTIN (the app's tick leaves the note), so a company GSTIN is not skipped by mistake
	assert keys(customer_missing({**base, "customer_type": "Company", "gst_category": "Unregistered"})) == {"gstin"}
	# a person who gave a GSTIN must give a valid one
	assert keys(customer_missing({**base, "customer_type": "Individual", "gstin": "27AAAC"})) == {"gstin"}


def test_lead_becomes_deal_only_after_qualifying():
	"""SK 4-Nov (Swati / Nishant): call not connected, the lead must not turn into a deal."""
	assert not lead_may_become_deal("New")
	assert not lead_may_become_deal(None)  # junk / lost
	for step in ("Qualified", "Drawing", "Quotation", "Negotiations", "Won"):
		assert lead_may_become_deal(step), step
	assert lead_may_become_deal("New", "Won")  # the customer's order was submitted: the won deal is made


def test_quotation_needs_items_rate_gst_valid_till():
	ok = {"party_name": "ABC", "valid_till": "2026-11-12", "items": [{"qty": 1, "rate": 250000}], "taxes": 2}
	assert quotation_missing(ok) == []
	assert keys(quotation_missing({**ok, "taxes": 0, "total_taxes_and_charges": 0})) == {"taxes"}
	# SK 28-Oct: no GST rows, the terms say GST is extra
	assert quotation_missing({**ok, "taxes": 0, "terms": "GST @ 18% extra as applicable."}) == []
	assert keys(quotation_missing({**ok, "items": [{"qty": 1, "rate": 0}]})) == {"items"}
	assert keys(quotation_missing({"items": []})) == {"party_name", "items", "taxes", "valid_till"}


def test_order_needs_po_or_copy_delivery_value():
	ok = {"transaction_date": "2026-10-28", "delivery_date": "2026-11-20", "po_no": "PO-77", "items": [{"qty": 1, "rate": 5}], "grand_total": 5}
	assert order_missing(ok) == []
	assert order_missing({**ok, "po_no": "", "po_file": True}) == []
	assert keys(order_missing({**ok, "po_no": "", "delivery_date": None, "grand_total": 0})) == {"po_no", "delivery_date", "grand_total"}


def test_request_and_count():
	assert request_missing({"items": [{"item_code": "GI-SHEET", "qty": 4}], "schedule_date": "2026-11-01", "reason": "Cabin 12"}) == []
	assert keys(request_missing({"items": [{"item_code": "GI-SHEET", "qty": 0}], "schedule_date": None, "reason": " "})) == {"items", "schedule_date", "reason"}
	assert count_missing("Stores - SK", ["A", "B"], {"A": "3", "B": 0}) == []
	assert keys(count_missing("Stores - SK", ["A", "B"], {"A": "3"})) == {"counts"}


def test_deal_steps():
	assert deal_step_needs("Qualified", [], []) == []
	assert keys(deal_step_needs("Quotation", [], [])) == {"quotation"}
	assert deal_step_needs("Quotation", [{"docstatus": 0}], []) == []
	assert keys(deal_step_needs("Negotiations", [{"docstatus": 0}], [])) == {"quotation"}
	assert keys(deal_step_needs("Won", [{"docstatus": 1}], [{"docstatus": 0}])) == {"sales_order"}
	assert deal_step_needs("Won", [{"docstatus": 1}], [{"docstatus": 1}]) == []


def test_ceo_may_submit_old_order_with_customer_data_pending():
	assert old_order_data_pending("2026-07-20", True)
	assert old_order_data_pending("2026-10-31", True)
	assert not old_order_data_pending("2026-11-01", True)  # new orders: full gate
	assert not old_order_data_pending("2026-07-20", False)  # only the CEO
	assert not old_order_data_pending(None, True)


def test_placeholder_po_numbers():
	from sk_app.gate_rules import is_placeholder_po

	for po in ["From CRM-LEAD-2026-00012", "NA", "N/A", "-", "PO awaited", "Pending", "TBA", "0", "crm-deal-2026-00001"]:
		assert is_placeholder_po(po), po
	for po in ["4500123456", "25940227", "PO/2026/118", "Verbal / WhatsApp order", "", None]:
		assert not is_placeholder_po(po), po
