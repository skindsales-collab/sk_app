"""SK 24-Nov (approved): the lead's stage follows its deal. Pure rules, unit tested."""

DRAWING = ("Drawing Sent", "Revision Requested", "Drawing Approved", "Quote Ready", "BOM & Quote Sent", "BOM Revision Requested", "BOM Approved")
QUOTE_WORDS = ("quot", "proposal")
NEGOTIATION_WORDS = ("negotiat", "ready to close")


def lead_stage(deal_status, deal_type, design, lead_status, order_submitted: bool, other_open_deal: bool) -> str | None:
	"""The stage the lead should have (None = leave it). A won lead and a junk lead are never changed; Deal Won only
	after the submitted Sales Order; Deal Loss only when the lead has no other open deal."""
	if lead_status in ("Deal Won", "Junk Lead"):
		return None
	low = (deal_status or "").lower()
	if deal_type == "Won":
		new = "Deal Won" if order_submitted else None
	elif deal_type == "Lost":
		new = None if other_open_deal else "Deal Loss"
	elif any(w in low for w in NEGOTIATION_WORDS):
		new = "Negotiations"
	elif any(w in low for w in QUOTE_WORDS):
		new = "Quotation"
	elif (design or "") in DRAWING:
		new = "Drawing"
	else:
		new = None
	return new if new and new != lead_status else None
