from sk_app.writers.journal_rules import problems, rows, voucher_type


def test_voucher_type_and_rows():
	assert (voucher_type("Cash"), voucher_type("Bank"), voucher_type(None)) == ("Cash Entry", "Bank Entry", "Journal Entry")
	r = rows("Tea Expenses", "Cash", 250, "Portable Cabin")
	assert [x["account"] for x in r] == ["Tea Expenses", "Cash"]
	assert sum(x["debit_in_account_currency"] for x in r) == sum(x["credit_in_account_currency"] for x in r) == 250
	assert all(x["cost_center"] == "Portable Cabin" for x in r)


def test_problems():
	assert problems(250, 250, "tea for site", False, None) == []
	assert problems(250, 250, "bank charges", True, "SBI CHG 123") == []
	keys = lambda *a: [k for k, _w in problems(*a)]
	assert keys(0, 0, " ", True, None) == ["journal_no_narration", "journal_no_amount", "journal_bank_no_reference"]
	assert keys(250, 200, "x", False, None) == ["journal_unbalanced"]
