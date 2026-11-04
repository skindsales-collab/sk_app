"""Pure rules of the one Quotation writer (no frappe import, so they are tested in CI).

SK 4-Nov: making a quote is one flow for every user (cabin sales, Design, Aditya for non-cabin, SK), each with their
own login; the record keeps who made it.
"""

GST_TERMS = "GST @ 18% extra as applicable."
NON_CABIN = "Non-Cabin"


def gst_terms(terms: str | None) -> str:
	"""Quotes show no GST amount, only the rate (SK 28-Oct): the terms always say GST is extra."""
	terms = (terms or "").strip()
	return terms if "gst" in terms.lower() else (terms + "<br>" if terms else "") + GST_TERMS


def ref_kind(kind: str | None, segment: str | None) -> str:
	"""Quote number series: the caller's kind (CAB, BLD, JOB) or, when not given, from the deal's main segment."""
	if kind:
		return kind
	return "JOB" if segment == NON_CABIN else "CAB"


def revision(old: dict | None, customer: str) -> dict:
	"""How a revise is made. old = {party_name, docstatus, sk_quote_ref, sk_rev} or None.
	A draft is changed in place (rev + 1); a submitted quote stays as sent and a new one is made with the same number,
	rev + 1; a quote of another customer is refused."""
	if not old:
		return {"mode": "new", "ref": None, "rev": 0}
	if old.get("party_name") != customer:
		return {"mode": "refuse", "why": "That quotation is for another customer"}
	rev = int(old.get("sk_rev") or 0) + 1
	if int(old.get("docstatus") or 0) == 0:
		return {"mode": "in_place", "ref": old.get("sk_quote_ref"), "rev": rev}
	return {"mode": "new", "ref": old.get("sk_quote_ref"), "rev": rev}


def problems(customer: str | None, deal: str | None, items: list) -> list:
	"""What the linear flow needs on every quote: a customer, a link back to its deal, items with qty and rate."""
	out = []
	if not customer:
		out.append(("quote_no_customer", "The quotation has no customer"))
	if not deal:
		out.append(("quote_without_deal", "The quotation is not linked to a deal (it will not count on the deal or the graph)"))
	if not items:
		out.append(("quote_no_items", "The quotation has no items"))
	for i, it in enumerate(items or [], 1):
		if float(it.get("qty") or 0) <= 0 or float(it.get("rate") or 0) <= 0:
			out.append(("quote_item_zero", f"Item row {i} ({it.get('item_code')}) has no qty or rate"))
	return out
