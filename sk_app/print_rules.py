"""SK 22-Nov checker: internal notes written into item descriptions (Tally import notes, audit notes, instructions to
Accounts) never print on a customer document. Pure rule, unit tested; used by every SK print format (jinja method)."""

import re

# a sentence / line is internal when it starts with or contains one of these
INTERNAL = re.compile(r"^\s*(shraddha\b|from tally|sk approved|sk \d{1,2}-[a-z]{3}\b|already invoiced|submit,? then|"
	r"check amount|this is so \d)|to be amended|link to the invoice|\bshraddha\s*:|\(\d{1,2}-[a-z]{3} audit|do not mix"
	# SK 23-Nov checker: Tally / PO-sheet import notes and internal numbers (cabin no, old quote no, CRM lead, ERPNext ids)
	r"|tally\s+invoice|po data from|^\s*sales\s*:|^\s*source\s*:|\bcabin\s*no\.?\s*\d|old quote no|\bcrm-(?:lead|deal)-|\bsinv-\d|"
	r"matched by amount|\(deal won\)", re.I)
# phrases cut out of a line that stays: "(cabins 294, 295)", "Cabin 226" (a 3-digit internal cabin number, never a size)
INTERNAL_PHRASE = re.compile(r"\s*\(\s*cabins?\b[^)]*\d[^)]*\)|\s*\bcabin\s*(?:no\.?|#)?\s*\d{3}\b(?!\s*(?:x|×|\*|'|ft|feet|mm|sq|m\b))", re.I)


def clean_description(text: str | None) -> str:
	"""Drops internal lines and sentences, keeps the customer's wording and line breaks."""
	out = []
	for line in (text or "").split("\n"):
		parts = re.split(r"(?<=[.;])\s+(?=[A-Z0-9])", line.strip())
		keep = [INTERNAL_PHRASE.sub("", p).strip() for p in parts if p and not INTERNAL.search(p)]
		keep = [p for p in keep if p]
		if keep:
			out.append(" ".join(keep))
	return "\n".join(out).strip()


def sk_customer_desc(text: str | None) -> str:
	"""Jinja method for the print formats."""
	return clean_description(text)


# SK 23-Nov checker: the header (cabin or machine-shifting banner, phones, e-mail) when the customer group says nothing
# (empty, Commercial, Government, Individual, Non Profit): decided by the items. None = cannot tell (cabin header).
CABIN_WORDS = re.compile(r"cabin|toilet|kiosk|container|site office|porta|lgsf|labour camp|prefab|bunk", re.I)
NONCABIN_WORDS = re.compile(r"shift|dismantl|rigging|relocat|manpower|erection|install|commission|job work|machin|ball\s*screw|repair", re.I)


def items_noncabin(items: list[dict]) -> bool | None:
	"""items = [{item_code, item_name, hsn}]. Cabin items win (a cabin with installation is a cabin job)."""
	cabin = non = False
	for it in items or []:
		code, name, hsn = (it.get("item_code") or ""), (it.get("item_name") or ""), str(it.get("hsn") or "")
		# the item code first (an SK-JOB line may carry a cabin HSN from Tally), then the item's words, then the HSN / SAC
		if code.upper() == "SK-JOB":
			non = True
		elif code.upper().startswith(("SK-CABIN", "PROD-")) or CABIN_WORDS.search(name):
			cabin = True
		elif NONCABIN_WORDS.search(name) or hsn.startswith("99"):
			non = True
		elif hsn.startswith("9406"):
			cabin = True
	return False if cabin else (True if non else None)
