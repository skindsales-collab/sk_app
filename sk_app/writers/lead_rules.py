"""Pure rules of the one CRM Lead writer."""

from sk_app.gate_rules import lead_missing


def shape(data: dict) -> dict:
	"""The lead's fields the one way: trimmed, blanks as None, a placeholder name only when nothing is known."""
	s = lambda k: (str(data.get(k) or "")).strip() or None
	return {"first_name": s("first_name") or "Enquiry", "organization": s("organization"), "mobile_no": s("mobile_no"),
		"email": s("email"), "source": s("source"), "sk_segment": s("segment"), "sk_product": (s("product") or "")[:140] or None,
		"lead_owner": s("owner")}


def problems(shaped: dict) -> list:
	return [("lead_" + k, w) for k, w in lead_missing(shaped)]
