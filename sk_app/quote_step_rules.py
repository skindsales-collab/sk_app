"""SK 21-Nov (Swati's trial: a new lead went straight to a quote, two quotes on one deal): the sales steps, in order,
each reached only from the one before. All records stay in ERPNext (CRM Lead, CRM Call Log, CRM Deal, Quotation).

lead (New) -> call logged -> Qualified -> (cabin) Send to design -> drawing approved -> Quotation (by hand) -> submit
                                        -> (Non-Cabin) Send for quote ---------------------> Quotation (by hand) -> submit
"""

# design statuses on the CRM Deal from which a cabin quotation may be made (the drawing was approved, or later)
DRAWING_OK = ("Drawing Approved", "BOM & Quote Sent", "BOM Revision Requested", "BOM Approved", "Order Received", "Stock Checked")
CALL_FIRST = "Call the customer first: log the call (Talked) on the lead, then mark it Qualified"
DRAWING_FIRST = "The drawing must be approved before the quote. Send the deal to design, get the drawing checked, then make the quote"
QUALIFY_FIRST_QUOTE = "Qualify the lead first (call logged, marked Qualified), then make the quote from its deal"


def may_qualify(calls_completed: int) -> bool:
	"""A lead becomes Qualified only after at least one call where the customer was spoken to."""
	return calls_completed > 0


def quote_problem(segment_main: str | None, design_status: str | None, has_deal: bool) -> str | None:
	"""Why a quotation may not be made yet (None = it may). Cabin: drawing approved. Non-Cabin: a deal (qualified lead)."""
	if not has_deal:
		return QUALIFY_FIRST_QUOTE
	if segment_main == "Cabin" and (design_status or "") not in DRAWING_OK:
		return DRAWING_FIRST
	return None
