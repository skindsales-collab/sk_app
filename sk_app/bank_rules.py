"""SK 23-Nov (approved): bank entry checks. Pure rules, unit tested."""

from datetime import date

GAP_DAYS = 7  # payment posting date this far from the bank reference date is probably a typing mistake


def date_gap_warning(posting_date: date | None, reference_date: date | None, limit: int = GAP_DAYS) -> str | None:
	"""A warning when the entry's date and the bank reference (UTR / cheque) date are far apart (None = fine)."""
	if not posting_date or not reference_date:
		return None
	gap = abs((posting_date - reference_date).days)
	if gap <= limit:
		return None
	return (f"The posting date {posting_date:%d-%m-%Y} is {gap} days from the bank reference date {reference_date:%d-%m-%Y}. "
		"Please check both dates against the bank statement.")


def reversal_rows(payment_type: str, paid_from: str, paid_to: str, amount_from: float, amount_to: float,
		party_type: str | None, party: str | None) -> list[dict]:
	"""Journal rows that undo a Payment Entry (a payment that failed or came back): every account the payment debited is
	credited and the other way round, with the party on the party account."""
	if payment_type == "Receive":  # bank was debited, the customer's account credited
		return [{"account": paid_to, "credit_in_account_currency": amount_to},
			{"account": paid_from, "debit_in_account_currency": amount_from, "party_type": party_type, "party": party}]
	if payment_type == "Pay":  # bank credited, the supplier's account debited
		return [{"account": paid_from, "debit_in_account_currency": amount_from},
			{"account": paid_to, "credit_in_account_currency": amount_to, "party_type": party_type, "party": party}]
	# Internal Transfer
	return [{"account": paid_from, "debit_in_account_currency": amount_from}, {"account": paid_to, "credit_in_account_currency": amount_to}]
