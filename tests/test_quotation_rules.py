from sk_app.writers.quotation_rules import gst_terms, problems, ref_kind, revision


def test_gst_line_always_there():
	assert gst_terms("") == "GST @ 18% extra as applicable."
	assert gst_terms("Payment 50% advance") == "Payment 50% advance<br>GST @ 18% extra as applicable."
	assert gst_terms("GST @ 18% is charged extra.") == "GST @ 18% is charged extra."


def test_ref_kind():
	assert ref_kind("BLD", "Cabin") == "BLD"
	assert ref_kind(None, "Non-Cabin") == "JOB"
	assert ref_kind(None, None) == "CAB"


def test_revision():
	assert revision(None, "C1") == {"mode": "new", "ref": None, "rev": 0}
	assert revision({"party_name": "C2"}, "C1")["mode"] == "refuse"
	assert revision({"party_name": "C1", "docstatus": 0, "sk_quote_ref": "R", "sk_rev": 1}, "C1") == {"mode": "in_place", "ref": "R", "rev": 2}
	assert revision({"party_name": "C1", "docstatus": 1, "sk_quote_ref": "R", "sk_rev": 0}, "C1") == {"mode": "new", "ref": "R", "rev": 1}


def test_problems():
	assert problems("C1", "D1", [{"item_code": "X", "qty": 1, "rate": 5}]) == []
	keys = [k for k, _w in problems(None, None, [{"item_code": "X", "qty": 0, "rate": 5}])]
	assert keys == ["quote_no_customer", "quote_without_deal", "quote_item_zero"]
	assert [k for k, _w in problems("C1", "D1", [])] == ["quote_no_items"]
