"""Pure rule of the Home "Decide now" strip (rebuild PR B, SK 26-Oct: data needed to decide comes first on every main
screen). Each function has its fixed questions in order; only the ones with something waiting are shown, at most 4."""

MAX = 4
# function -> [(key, words, view the cell opens)] in the order SK reads them
ITEMS = {
	"Management": [("approvals", "approvals waiting", "po_approvals"), ("overdue_orders", "orders past delivery date", "dispatch"),
		("unbilled", "orders not billed", "invoices"), ("low_stock", "items below reorder level", "low_stock")],
	"Sales": [("leads_untouched", "leads not touched for 3 days", "follow_up"), ("quotes_waiting", "quotations waiting", "follow_up")],
	"Stores": [("mr_waiting", "material requests waiting", "store_requests"), ("low_stock", "items below reorder level", "low_stock")],
}
ITEMS["Store"] = ITEMS["Stores"]


def pick(functions: list[str], counts: dict) -> list[dict]:
	"""counts = {key: number}; returns [{key, n, label, go}] for the person's functions, first function first, no repeats."""
	out, seen = [], set()
	for fn in functions or []:
		for key, words, go in ITEMS.get(fn, []):
			n = int(counts.get(key) or 0)
			if n > 0 and key not in seen:
				seen.add(key)
				out.append({"key": key, "n": n, "label": words, "go": go})
	return out[:MAX]


def keys_for(functions: list[str]) -> set:
	"""Which counts to read for this person (only those, so a sales login never runs the CEO's queries)."""
	return {k for fn in functions or [] for k, _w, _g in ITEMS.get(fn, [])}
