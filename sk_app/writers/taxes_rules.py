"""Pure rule: which GST template an order or invoice gets when it was saved with no tax rows (SK 6-Nov: everyone
types the minimum, the app fills the GST). Quotes stay without tax rows on purpose (GST % in words only, SK 28-Oct)."""

FILL_ON = ("Sales Order", "Sales Invoice")


def pick_template(templates: list[dict], company: str, same_state: bool) -> str | None:
	"""templates = [{name, company, disabled, is_default}]. The company's default, else its Output GST In-state /
	Out-state template (not RCM), else None."""

	mine = [t for t in templates if t.get("company") == company and not t.get("disabled")]
	default = [t for t in mine if t.get("is_default")]
	if default:
		return default[0]["name"]
	want = "in-state" if same_state else "out-state"
	for t in mine:
		n = (t.get("name") or "").lower()
		if "output" in n and want in n and "rcm" not in n:
			return t["name"]
	return None


def needs_fill(doctype: str, tax_rows: int, template: str | None, net_total: float) -> bool:
	return doctype in FILL_ON and tax_rows == 0 and not template and float(net_total or 0) > 0


def same_state(company_gstin: str | None, party_gstin: str | None, party_state: str | None, company_state: str | None) -> bool:
	"""GST state code = first two digits of the GSTIN; without a party GSTIN the address state decides; unknown = in-state."""
	if company_gstin and party_gstin and len(company_gstin) >= 2 and len(party_gstin) >= 2:
		return company_gstin[:2] == party_gstin[:2]
	if party_state and company_state:
		return party_state.strip().lower() == company_state.strip().lower()
	return True
