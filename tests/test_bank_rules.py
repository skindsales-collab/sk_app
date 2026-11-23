from datetime import date

from sk_app.bank_rules import date_gap_warning, reversal_rows


def test_date_gap():
	assert date_gap_warning(date(2026, 11, 23), date(2026, 11, 20)) is None
	w = date_gap_warning(date(2026, 11, 23), date(2026, 10, 23))
	assert w and "31 days" in w
	assert date_gap_warning(date(2026, 11, 23), None) is None


def test_reversal_undoes_receive_and_pay():
	r = reversal_rows("Receive", "Debtors - SK", "SBI - SK", 1000, 1000, "Customer", "C1")
	assert r[0] == {"account": "SBI - SK", "credit_in_account_currency": 1000}
	assert r[1]["account"] == "Debtors - SK" and r[1]["debit_in_account_currency"] == 1000 and r[1]["party"] == "C1"
	p = reversal_rows("Pay", "SBI - SK", "Creditors - SK", 500, 500, "Supplier", "S1")
	assert p[0] == {"account": "SBI - SK", "debit_in_account_currency": 500} and p[1]["credit_in_account_currency"] == 500
