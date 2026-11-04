"""Bank statement reading (SK 4-Nov-2026: "why put the UTR by hand, can it be filled from the statement"), free of
ERPNext so it can be tested. sk_app.bank_statement uses it.

Reads the text of an SBI account statement PDF (one line per transaction: txn date, value date, description, ref, branch,
debit or credit, balance; the next lines carry the rest of the description, e.g. IMPS/628918804996/UTIB-/Neo curt-).
Debit or credit is decided from the running balance, so a wrong reading stops instead of booking a wrong side.
"""

import re

_START = re.compile(r"^\s*(\d{2}/\d{2}/\d{4})\s+(\d{2}/\d{2}/\d{4})\s+(.*)$")
_AMOUNT = re.compile(r"([\d,]+\.\d{2})")
_OPENING = re.compile(r"Opening Balance[^:]*:\s*([\d,]+\.\d{2})", re.I)
_SKIP = ("Txn Date", "No.", "**This", "Page ")
# the bank's own reference, most specific first
_REFS = (
	(r"IMPS/(\d{10,})", "IMPS"),
	(r"\b([A-Z]{4}[RN]\d{12,})", ""),  # RTGS / NEFT UTR, e.g. ICICR22026102819679695
	(r"NEFT\*[A-Z0-9]+\*([A-Z0-9]+)", ""),
	(r"UPI/(\d{10,})", "UPI"),
	(r"\b(CT[0-9A-Z]{6,})", ""),
	(r"Chq (\d{6})", "CHQ"),
	(r"INB-? ?([0-9A-Za-z]{14,})", ""),
	(r"crn(\w{12,})", ""),
)


class StatementError(ValueError):
	pass


def _num(s: str) -> float:
	return float(s.replace(",", ""))


def reference(text: str) -> str | None:
	for pat, prefix in _REFS:
		m = re.search(pat, text)
		if m:
			return prefix + m.group(1)
	return None


def party_hint(text: str) -> str:
	"""The payee / payer name the bank shows (cut short by the bank), e.g. "Neo curt" from xx644-/Neo curt-."""
	m = re.search(r"xx\d+-/([^-/]+)", text) or re.search(r"\*([A-Z][A-Z .&]{3,})$", text)
	return m.group(1).strip() if m else ""


def parse_text(text: str) -> dict:
	"""{opening, closing, rows: [{date (YYYY-MM-DD), withdrawal, deposit, description, reference_number, party_hint, balance}]}"""
	om = _OPENING.search(text)
	if not om:
		raise StatementError("Opening balance not found: is this an SBI account statement?")
	opening = bal = _num(om.group(1))
	tx, cur = [], None
	for line in text.splitlines():
		m = _START.match(line)
		if m:
			cur = {"date": m.group(1), "first": m.group(3), "more": []}
			tx.append(cur)
		elif cur is not None and line.strip() and not line.strip().startswith(_SKIP):
			cur["more"].append(line.strip())
	if not tx:
		raise StatementError("No transactions found in the statement")
	rows = []
	for t in tx:
		nums = _AMOUNT.findall(t["first"])
		if len(nums) < 2:
			raise StatementError(f"Could not read the amounts on {t['date']}: {t['first'][:80]}")
		amount, balance = _num(nums[-2]), _num(nums[-1])
		if abs(round(bal - amount, 2) - balance) < 0.01:
			withdrawal, deposit = amount, 0.0
		elif abs(round(bal + amount, 2) - balance) < 0.01:
			withdrawal, deposit = 0.0, amount
		else:
			raise StatementError(f"Balance does not follow on {t['date']} ({amount:,.2f}): the statement was not read correctly")
		bal = balance
		desc = re.sub(r"\s{2,}", " ", (_AMOUNT.sub("", t["first"]) + " " + " ".join(t["more"])).strip())
		d, mth, y = t["date"].split("/")
		rows.append({"date": f"{y}-{mth}-{d}", "withdrawal": withdrawal, "deposit": deposit, "description": desc[:500],
			"reference_number": reference(desc), "party_hint": party_hint(desc), "balance": balance})
	return {"opening": opening, "closing": bal, "rows": rows}


def pick_match(row: dict, candidates: list[dict]) -> tuple[dict | None, str]:
	"""Which ERPNext payment is this bank line. candidates: same side, same amount, near date, not yet cleared.
	Same reference first; else the only candidate; else the one whose party starts like the bank's name; else none."""
	ref = re.sub(r"[^A-Z0-9]", "", (row.get("reference_number") or "").upper())
	if ref:
		same = [c for c in candidates if re.sub(r"[^A-Z0-9]", "", (c.get("reference_no") or "").upper()) == ref]
		if len(same) == 1:
			return same[0], "same UTR"
	if len(candidates) == 1:
		return candidates[0], "same amount and date"
	hint = (row.get("party_hint") or "").lower()[:6]
	if hint:
		named = [c for c in candidates if (c.get("party") or "").lower().replace("ms. ", "").startswith(hint)]
		if len(named) == 1:
			return named[0], "same amount, date and party"
	return None, "several payments of this amount" if candidates else "not in ERPNext"
