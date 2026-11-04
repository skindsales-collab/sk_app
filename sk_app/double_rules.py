"""Double entry rules (SK 4-Nov-2026), kept free of ERPNext so they can be tested on their own. sk_app.doubles uses
them on every save (live) and in the morning list for Shraddha and SK.

On 4-Nov these doubles were found: Oxford Rs 17,46,400 paid twice (ACC-PAY-00012 / 00206), Ai Portable Rs 3,32,500
twice (00198 / 00204), Plylam bill PINV-26-00369 / 00371 (a Tally double) and two Catalyst deals saved 17 seconds apart.
"""

import re
from datetime import date, datetime

DAYS = 7  # same party and same amount within 7 days is a possible double
AMOUNT_GAP = 0.5  # rupees: a rounding difference is still the same amount

# words that are not a real reference number
_PLACEHOLDER = {"", "NA", "N/A", "NIL", "NONE", "NULL", "-", "0", "00", "000", "CASH", "TEST", "REF", "TBA", "NOREF"}
# a bank transfer reference: such a payment must go through a bank account, never Cash
_BANK_REF = re.compile(r"^(IMPS|NEFT|RTGS|UTR|UPI|CHQ|CHEQUE|INB|MOBT|BIL/|ACH)", re.I)


def norm_ref(ref) -> str | None:
	"""A reference number to compare: upper case, letters and digits only; placeholders are None."""
	s = re.sub(r"[^A-Z0-9]", "", str(ref or "").upper())
	# "SK App 2026-10-28": the date the app wrote when no UTR was typed (before 4-Nov), the same on every payment of a day
	if s in {re.sub(r"[^A-Z0-9]", "", p) for p in _PLACEHOLDER} or len(s) < 4 or set(s) == {"0"} or re.fullmatch(r"(SKAPP|CASH)\d*", s):
		return None
	return s


def looks_bank_ref(ref) -> bool:
	"""IMPS / NEFT / RTGS / UTR / UPI / cheque reference: the money went through the bank."""
	return bool(_BANK_REF.match(str(ref or "").strip()))


def different_refs(a, b) -> bool:
	"""Both have a real number (bill no, PO no) and the numbers differ: two separate entries, not a double."""
	ka, kb = norm_ref(a), norm_ref(b)
	return bool(ka and kb and ka != kb)


def same_amount(a, b) -> bool:
	try:
		return abs(float(a or 0) - float(b or 0)) <= AMOUNT_GAP
	except (TypeError, ValueError):
		return False


def _day(d) -> date | None:
	if isinstance(d, datetime):
		return d.date()
	if isinstance(d, date):
		return d
	try:
		return date.fromisoformat(str(d)[:10])
	except (TypeError, ValueError):
		return None


def days_apart(a, b) -> int | None:
	da, db = _day(a), _day(b)
	return abs((da - db).days) if da and db else None


def near(a, b, days: int = DAYS) -> bool:
	gap = days_apart(a, b)
	return gap is not None and gap <= days


def mobile_key(mobile) -> str | None:
	"""Last 10 digits of a mobile number (+91 98220 12345 and 9822012345 are the same person)."""
	digits = re.sub(r"\D", "", str(mobile or ""))
	return digits[-10:] if len(digits) >= 10 else None


def bank_mode_to_cash(mode_type: str | None, account_type: str | None, reference_no=None) -> bool:
	"""Shraddha 4-Nov (Neo Curtains Rs 15,600 and Rs 3,900): a Net Banking payment was booked from Cash, so it showed in
	the ledger but never in Bank Reconciliation. A bank mode of payment or a bank reference must use a Bank account."""
	if account_type != "Cash":
		return False
	return mode_type == "Bank" or looks_bank_ref(reference_no)


def find_pairs(rows: list[dict], days: int = DAYS) -> list[dict]:
	"""Possible doubles in a list of entries for the morning check.

	Each row: kind (e.g. "Payment Entry" or a direction like "Pay"), doctype, name, party, amount, date, ref, ok (ticked
	"Not a double"). Two rows are a pair when they have the same kind, party and amount within `days`, or the same reference
	number (any party: one bank transfer cannot pay two suppliers; give a bill number as "supplier bill-no" so it is
	compared within its supplier only). Every pair is given once; a pair where either row was ticked "Not a double" is left out.
	"""
	pairs, seen = [], set()

	def add(a, b, why):
		key = tuple(sorted([(a["doctype"], a["name"]), (b["doctype"], b["name"])]))
		if key in seen or a.get("ok") or b.get("ok") or key[0] == key[1]:
			return
		seen.add(key)
		first, second = sorted([a, b], key=lambda r: (str(r.get("date") or ""), r["name"]))
		pairs.append({"first": first, "second": second, "why": why})

	groups: dict = {}
	for r in rows:
		if r.get("party") and r.get("amount"):
			groups.setdefault((r.get("kind"), r["party"], round(float(r["amount"]))), []).append(r)
	for g in groups.values():
		g.sort(key=lambda r: str(r.get("date") or ""))
		for i, a in enumerate(g):
			for b in g[i + 1:]:
				if not near(a.get("date"), b.get("date"), days):
					break
				if same_amount(a["amount"], b["amount"]):
					add(a, b, "same party and amount within {} days".format(days))
	refs: dict = {}
	for r in rows:
		key = norm_ref(r.get("ref"))
		if key:
			refs.setdefault(key, []).append(r)
	for g in refs.values():
		for i, a in enumerate(g):
			for b in g[i + 1:]:
				add(a, b, "same reference number")
	pairs.sort(key=lambda p: str(p["second"].get("date") or ""), reverse=True)
	return pairs
