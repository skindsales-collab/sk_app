"""Pure rule: which bill(s) a payment pays (SK 6-Nov, KF-04447). One payment often covers 3-4 invoices together.
Order: bill numbers written in the narration; else the one open invoice with the exact amount; else the set of open
invoices (oldest first) adding up to the amount, then any exact combination; else None (Accounts choose)."""

import re
from itertools import combinations

TOL = 1.0  # rupee rounding


def _norm(text) -> str:
	return re.sub(r"[^A-Z0-9]", "", str(text or "").upper())


def by_narration(narration: str, invoices: list[dict]) -> list[dict]:
	"""Invoices whose number (or the party's bill number) is written in the narration."""
	text = _norm(narration)
	if not text:
		return []
	out = []
	for inv in invoices:
		keys = [k for k in (inv.get("name"), inv.get("bill_no")) if k and len(_norm(k)) >= 4]
		if any(_norm(k) in text for k in keys):
			out.append(inv)
	return out


def allocate(amount: float, invoices: list[dict], narration: str | None = None) -> tuple[list[dict], str]:
	"""invoices = [{name, outstanding, date, bill_no?}] of one party, open. Returns ([{name, amount}], why) or ([], why).
	Allocation never exceeds an invoice's outstanding; the last invoice in a set may be part-paid only when the
	narration named it or it is the single match."""
	amount = float(amount or 0)
	if amount <= 0 or not invoices:
		return [], "nothing to allocate" if amount <= 0 else "no open invoice"
	named = by_narration(narration or "", invoices)
	if named:
		rows, left = [], amount
		for inv in sorted(named, key=lambda i: str(i.get("date") or "")):
			take = min(float(inv["outstanding"]), left)
			if take > 0:
				rows.append({"name": inv["name"], "amount": round(take, 2)})
				left -= take
		return rows, "bill number in narration"
	exact = [i for i in invoices if abs(float(i["outstanding"]) - amount) <= TOL]
	if len(exact) == 1:
		return [{"name": exact[0]["name"], "amount": round(amount, 2)}], "same amount"
	if len(exact) > 1:
		return [], "several invoices of this amount"
	ordered = sorted(invoices, key=lambda i: (str(i.get("date") or ""), i["name"]))
	run, total = [], 0.0
	for inv in ordered:
		run.append(inv)
		total += float(inv["outstanding"])
		if abs(total - amount) <= TOL:
			return [{"name": i["name"], "amount": round(float(i["outstanding"]), 2)} for i in run], "oldest invoices add up"
		if total > amount + TOL:
			break
	fits = []
	for n in range(2, min(len(invoices), 6) + 1):
		for combo in combinations(invoices, n):
			if abs(sum(float(i["outstanding"]) for i in combo) - amount) <= TOL:
				fits.append(combo)
				if len(fits) > 1:
					break
		if len(fits) > 1:
			break
	if len(fits) == 1:
		return [{"name": i["name"], "amount": round(float(i["outstanding"]), 2)} for i in fits[0]], "invoices add up"
	if len(fits) > 1:
		return [], "more than one set of invoices adds up"
	if len(invoices) == 1 and float(invoices[0]["outstanding"]) > amount:
		return [{"name": invoices[0]["name"], "amount": round(amount, 2)}], "part payment of the only open invoice"
	return [], "no invoice or set of invoices matches"
