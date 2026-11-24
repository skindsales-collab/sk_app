from sk_app.lead_follow_rules import lead_stage as s


def test_lead_follows_deal():
	assert s("Qualification", "Open", "Drawing Sent", "Qualified", False, False) == "Drawing"
	assert s("Proposal/Quotation", "Ongoing", "Drawing Sent", "Drawing", False, False) == "Quotation"
	assert s("Negotiation", "Ongoing", "Quote Ready", "Quotation", False, False) == "Negotiations"
	assert s("Won", "Won", "Not Required", "Negotiations", True, False) == "Deal Won"
	assert s("Lost", "Lost", "On Hold", "Qualified", False, False) == "Deal Loss"


def test_what_is_left_alone():
	assert s("Won", "Won", None, "Quotation", False, False) is None  # no submitted order yet
	assert s("Lost", "Lost", None, "Quotation", False, True) is None  # another deal is still open
	assert s("Lost", "Lost", None, "Deal Won", False, False) is None and s("Negotiation", "Ongoing", None, "Junk Lead", False, False) is None
	assert s("Qualification", "Open", "Not Required", "Qualified", False, False) is None
	assert s("Proposal/Quotation", "Ongoing", None, "Quotation", False, False) is None  # already there: nothing written


def test_design_alone_never_pulls_a_lead_back():
	assert s("Demo/Making", "Ongoing", "BOM & Quote Sent", "Quotation", False, False) is None
	assert s("Qualification", "Open", "Drawing Sent", "Negotiations", False, False) is None
	assert s("Qualification", "Open", "Drawing Sent", "Deal Loss", False, False) is None
	assert s("Proposal/Quotation", "Ongoing", "Drawing Sent", "Negotiations", False, False) == "Quotation"  # the deal itself moved
