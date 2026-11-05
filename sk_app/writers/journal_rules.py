"""Pure rules of the one Journal Entry writer (Flow 6 Money: petty cash voucher, expense payment, bank charges)."""


def voucher_type(account_type: str | None) -> str:
	"""Money from a Cash ledger is a Cash Entry; from a Bank ledger a Bank Entry; anything else a plain Journal Entry."""
	return {"Cash": "Cash Entry", "Bank": "Bank Entry"}.get(account_type or "", "Journal Entry")


def rows(expense_account: str, money_account: str, amount: float, cost_center: str | None = None) -> list[dict]:
	"""The two lines of a voucher: the expense debited, the cash / bank ledger credited, both on the cabin's cost centre."""
	return [{"account": expense_account, "debit_in_account_currency": amount, "credit_in_account_currency": 0, "cost_center": cost_center},
		{"account": money_account, "debit_in_account_currency": 0, "credit_in_account_currency": amount, "cost_center": cost_center}]


def problems(total_debit: float, total_credit: float, narration: str | None, has_bank_row: bool, reference_no: str | None) -> list:
	"""Every journal says what it was for, moves money, balances, and a bank entry carries the bank's reference."""
	out = []
	if not (narration or "").strip():
		out.append(("journal_no_narration", "The journal entry does not say what the money was for"))
	if (total_debit or 0) <= 0:
		out.append(("journal_no_amount", "The journal entry has no amount"))
	elif abs((total_debit or 0) - (total_credit or 0)) > 0.5:
		out.append(("journal_unbalanced", f"Debit {total_debit:,.2f} and credit {total_credit:,.2f} differ"))
	if has_bank_row and not (reference_no or "").strip():
		out.append(("journal_bank_no_reference", "A bank entry needs the bank's reference (UTR / cheque number)"))
	return out
