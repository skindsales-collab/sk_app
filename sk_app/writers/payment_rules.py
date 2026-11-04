"""Pure rules of the one Payment Entry writer (Flow 6 Money, Flow 5 step 5)."""

AGAINST = {"Receive": ("Sales Invoice", "Sales Order"), "Pay": ("Purchase Invoice", "Purchase Order")}


def direction(against_doctype: str) -> str | None:
	return next((k for k, v in AGAINST.items() if against_doctype in v), None)


def problems(against_doctype: str, against_name: str | None, amount: float, outstanding: float | None, mode_type: str | None,
		reference_no: str | None) -> list:
	"""Every payment is linked back to its invoice or order, has an amount not above what is due, and a bank payment
	carries its UTR / cheque number (SK 4-Nov: the same UTR is used once only, so it must be there to be checked)."""
	out = []
	if not direction(against_doctype) or not against_name:
		out.append(("payment_not_linked", "The payment is not linked to an invoice or order"))
	if amount <= 0:
		out.append(("payment_no_amount", "The payment has no amount"))
	elif outstanding is not None and outstanding > 0 and amount > outstanding + 1:
		out.append(("payment_above_due", f"The payment {amount:,.0f} is more than the amount due {outstanding:,.0f}"))
	if mode_type == "Bank" and not (reference_no or "").strip():
		out.append(("payment_no_utr", "A bank payment needs its UTR / reference number"))
	return out
