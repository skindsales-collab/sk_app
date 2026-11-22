"""SK 22-Nov checker: internal notes written into item descriptions (Tally import notes, audit notes, instructions to
Accounts) never print on a customer document. Pure rule, unit tested; used by every SK print format (jinja method)."""

import re

# a sentence / line is internal when it starts with or contains one of these
INTERNAL = re.compile(r"^\s*(shraddha\b|from tally|sk approved|sk \d{1,2}-[a-z]{3}\b|already invoiced|submit,? then|"
	r"check amount|this is so \d)|to be amended|link to the invoice|\bshraddha\s*:|\(\d{1,2}-[a-z]{3} audit|do not mix", re.I)


def clean_description(text: str | None) -> str:
	"""Drops internal lines and sentences, keeps the customer's wording and line breaks."""
	out = []
	for line in (text or "").split("\n"):
		parts = re.split(r"(?<=[.;])\s+(?=[A-Z0-9])", line.strip())
		keep = [p for p in parts if p and not INTERNAL.search(p)]
		if keep:
			out.append(" ".join(keep))
	return "\n".join(out).strip()


def sk_customer_desc(text: str | None) -> str:
	"""Jinja method for the print formats."""
	return clean_description(text)
