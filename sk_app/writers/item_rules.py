"""Pure rules of the one Item writer (no frappe import, so they are tested in CI)."""


def norm(name: str | None) -> str:
	"""Item names compared without case, spaces and punctuation, so 'GP Coil 0.5mm' and 'gp coil 0.5 mm' are one."""
	return "".join(ch for ch in (name or "").lower() if ch.isalnum())


def same_name(name: str, others: list[tuple[str, str]], code: str | None = None) -> list[str]:
	"""Codes of other items whose name is the same as this one. others = [(item_code, item_name), ...]."""
	key = norm(name)
	return [c for c, n in others if c != code and key and norm(n) == key]


def problems(code: str | None, name: str | None, group: str | None, uom: str | None, hsn: str | None, doubles: list[str]) -> list:
	out = []
	if not (name or "").strip():
		out.append(("item_no_name", "The item has no name"))
	if not group:
		out.append(("item_no_group", f"Item {code or name} has no item group"))
	if not uom:
		out.append(("item_no_uom", f"Item {code or name} has no unit"))
	if not hsn:
		out.append(("item_no_hsn", f"Item {code or name} has no HSN / SAC code (GST invoice will stop)"))
	if doubles:
		out.append(("item_same_name", f"Item {code or name} has the same name as {', '.join(doubles[:3])}"))
	return out
