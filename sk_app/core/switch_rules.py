"""Pure decisions for the path switch (no Frappe imports, unit tested in tests/test_core_switch.py)."""

MODULES = ("Finance", "Sales", "Store", "Purchase", "Production", "HR", "Home")
WARN, ENFORCE = "Warn only", "Enforce"


def pilot_list(text) -> list[str]:
	"""One e-mail per line (commas and spaces also fine), lower case, no blanks."""
	parts = str(text or "").replace(",", "\n").replace(";", "\n").split()
	return list(dict.fromkeys(p.strip().lower() for p in parts if p.strip()))


def uses_new(row, user: str) -> bool:
	"""row = the module's SK Path Switch ({path, pilot_users}) or None. No row or Old = old path for everyone."""
	if not row or (row.get("path") or "Old") != "New":
		return False
	pilots = pilot_list(row.get("pilot_users"))
	return not pilots or (user or "").lower() in pilots


def rule_mode(row) -> str:
	"""How the new shared rules act for a module: Warn only until SK sets Enforce."""
	return ENFORCE if row and row.get("rules") == ENFORCE else WARN
