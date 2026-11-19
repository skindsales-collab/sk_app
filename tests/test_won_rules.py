"""SK 14-Nov (KF-05180): a deal is Won only when its Sales Order exists."""

from sk_app.writers.lead_rules import deal_won_gap


def test_won_by_hand_without_order_is_a_gap():
	assert deal_won_gap(was_won=False, is_won=True, from_order=False, has_order=False)[0][0] == "deal_won_without_order"


def test_won_from_the_order_or_with_an_order_is_fine():
	assert deal_won_gap(False, True, from_order=True, has_order=False) == []
	assert deal_won_gap(False, True, from_order=False, has_order=True) == []


def test_other_saves_of_a_won_deal_or_open_deals_are_quiet():
	assert deal_won_gap(was_won=True, is_won=True, from_order=False, has_order=False) == []
	assert deal_won_gap(False, False, False, False) == []


# ---- New Lead for an existing customer (SK 14-Nov) ----
from sk_app.writers.lead_rules import fill_from_existing, rank_matches


def test_rank_puts_the_name_that_starts_with_the_text_first():
	names = ["Mittal brothers Pvt Ltd, Mittal Group", "Rothe Erde India Private Limited", "Thyssenkrupp Rothe Erde"]
	assert rank_matches("rothe", names) == ["Rothe Erde India Private Limited", "Thyssenkrupp Rothe Erde", "Mittal brothers Pvt Ltd, Mittal Group"]
	assert rank_matches("r", names) == [] and rank_matches("xyz", names) == []


def test_pick_fills_erpnext_data_and_keeps_what_was_typed():
	pick = {"customer_name": "Rothe Erde India Private Limited", "contact": "Mr Patil", "mobile": "9876500011", "email": None,
		"gstin": "27AAAAA0000A1Z5", "segment": "Machine Shifting"}
	got = fill_from_existing({"first_name": ""}, pick)
	assert got == {"organization": "Rothe Erde India Private Limited", "first_name": "Mr Patil", "mobile_no": "9876500011",
		"segment": "Machine Shifting", "no_gstin": 0, "source": "Existing Customer"}
	# no contact in ERPNext and nothing typed: the company name stands in; no GSTIN -> the unregistered tick
	got = fill_from_existing({"first_name": ""}, {"customer_name": "Sujal Enterprises", "gstin": None})
	assert got["first_name"] == "Sujal Enterprises" and got["no_gstin"] == 1
	# a typed person stays when ERPNext has no contact
	assert "first_name" not in fill_from_existing({"first_name": "Ramesh"}, {"customer_name": "Sujal Enterprises"})


from sk_app.writers.lead_rules import customer_match_keys


def test_incoming_lead_matches_a_customer_by_mobile_or_company_domain():
	assert customer_match_keys("+91 98765 00011", "sales@rotheerde.com") == {"mobile10": "9876500011", "domain": "rotheerde.com"}
	assert customer_match_keys("98220", "someone@gmail.com") == {"mobile10": "", "domain": ""}
	assert customer_match_keys(None, "bad-address") == {"mobile10": "", "domain": ""}
