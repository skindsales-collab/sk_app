"""Bank match from the payment side uses the statement's own matching rule (one rule for both directions)."""

from sk_app.statement_rules import pick_match


def test_payment_finds_its_bank_line():
	pay = {"reference_number": "IMPS628900000001", "party_hint": "Neo Curtains"}
	lines = [{"name": "BT-1", "reference_no": "IMPS628900000001", "party": "Neo curt"},
		{"name": "BT-2", "reference_no": "IMPS628900000002", "party": "Technomech"}]
	assert pick_match(pay, lines)[0]["name"] == "BT-1"
	assert pick_match({"reference_number": None, "party_hint": "Technomech Solutions"}, lines)[0]["name"] == "BT-2"
	assert pick_match({"reference_number": None, "party_hint": None}, lines) == (None, "several payments of this amount")
	assert pick_match({"reference_number": None, "party_hint": None}, []) == (None, "not in ERPNext")
