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


# SK 23-Nov (Curesense quote 00067 went out with design's own PDF and another header): a PDF made outside SK App is
# never the quote. The scope and specification lines are on the Quotation itself, so every quote prints in the final
# SK format (patch 102), whatever made it (app, ERPNext desk, Claude / SK Hub, a quote file on a deal).
import re as _re

ATTACHED_NOT_QUOTE = ("A PDF made outside SK App is not the quote. Write the scope and specification lines on the quotation "
	"(Make quotation in the app), so it prints in the SK format")
CABIN_SCREEN = ("Make the cabin quote in the app cabin quote screen (type, size, options), so the specification prints on it, "
	"or write the full specification on the line")
_PLACEHOLDER = _re.compile(r"as\s+per\s+(?:the\s+)?(?:attached|enclosed)|as\s+per\s+(?:our\s+|the\s+)?quot", _re.I)
CABIN_ITEM = "SK-CABIN"
SPEC_MIN = 60  # characters of specification text a hand-written cabin line needs


def _text(html) -> str:
	return " ".join(_re.sub(r"<[^>]+>", " ", str(html or "")).replace("&nbsp;", " ").split())


def scope_problem(items: list[dict], cabin_request: bool) -> str | None:
	"""Why the quotation may not be sent (None = it may). items = [{item_code, item_name, description}]."""
	for it in items or []:
		text = _text(it.get("description")) or _text(it.get("item_name"))
		if _PLACEHOLDER.search(text):
			return ATTACHED_NOT_QUOTE
		if it.get("item_code") == CABIN_ITEM and not cabin_request and len(text) < SPEC_MIN:
			return CABIN_SCREEN
	return None


# SK 17-Nov sales list (approved 23-Nov "maximum possible coding for correction"): a lead never goes back to New once it
# was Qualified or later (ADVANTEK 00518 went Qualified > Drawing > New on 2-Nov and dropped out of the follow-up).
BACK_TO_NEW = "This lead was already {0}. It cannot go back to New: keep it at its stage, or mark it Lost / Junk with the reason"


def back_to_new(old_status: str | None, new_status: str | None) -> bool:
	return bool(old_status) and old_status != "New" and new_status == "New"
