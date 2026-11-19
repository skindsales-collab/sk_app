"""Double entry rules (SK 4-Nov-2026), kept free of ERPNext so they can be tested on their own. sk_app.doubles uses
them on every save (live) and in the morning list for Shraddha and SK.

On 4-Nov these doubles were found: Oxford Rs 17,46,400 paid twice (ACC-PAY-00012 / 00206), Ai Portable Rs 3,32,500
twice (00198 / 00204), Plylam bill PINV-26-00369 / 00371 (a Tally double) and two Catalyst deals saved 17 seconds apart.
"""

import re
from datetime import date, datetime

DAYS = 7  # same party and same amount within 7 days is a possible double
CROSS_DAYS = 10  # a Tally voucher and a bank transfer for the same money can be days apart (checker 7-Nov: Babasaheb, 8 days)
BANK_DAYS = 1  # on the bank's own dates the same transfer is one day at most apart (checker 9-Nov: PE bank date = JE date)
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


_TALLY_REF = re.compile(r"Tally\s+(?:invoice|voucher|bill|receipt|payment|journal|sales|purchase)?\s*(?:no\.?\s*)?([A-Z]{1,6}[A-Z0-9/\-]*\d[A-Z0-9/\-]*)", re.I)


def tally_ref(text) -> str | None:
	"""The Tally voucher number written in a migrated record's remarks ("Tally invoice SK/IND/0926/812 ..."), else None.
	Sales Invoices from Tally have no bill-number field, so this is their reference (checker 7-Nov: 13 false pairs)."""
	m = _TALLY_REF.search(str(text or ""))
	return m.group(1).strip("/-") if m else None


def day_window(d) -> tuple:
	"""SK 7-Nov (KF-04801): the same mobile / company on the SAME DATE is a duplicate lead, on another date a new lead.
	Returns the day's start and end as strings for a creation filter."""
	day = str(d)[:10]
	return (f"{day} 00:00:00", f"{day} 23:59:59")


def different_refs(a, b) -> bool:
	"""Both have a real number (bill no, PO no) and the numbers differ: two separate entries, not a double."""
	ka, kb = norm_ref(a), norm_ref(b)
	return bool(ka and kb and ka != kb)


# a Tally voucher number: PAY/586/25-26, REC/12, J329, SK/IND/0926/812, PUR/NC/066/25-26 (not an ERPNext name like JE-01769)
_TALLY_NO = re.compile(r"^(PAY|PMT|REC|RCT|RCPT|JV|J|JRN|CNTR|CON|SAL|PUR|SK|CN|DN)(?=[/\-\s]?\d|/)[A-Z0-9/\-\s]*$", re.I)
# a bank's own transfer number: a long UTR / IMPS number, or a bank code in front (ICICR2202261)
_BANK_NO = re.compile(r"\d{9,}|(ICIC|HDFC|SBIN|UTIB|KKBK|PUNB|BARB|CNRB|IDIB|YESB|INDB|IDFB|AXIS)[A-Z0-9]*\d{5,}")


def ref_kind(ref) -> str | None:
	"""What a payment / journal number is: "bank" (UTR, IMPS, NEFT, cheque), "tally" (a Tally voucher number) or "bill"."""
	s = norm_ref(ref)
	if not s:
		return None
	raw = str(ref).strip()
	if looks_bank_ref(raw) or _BANK_NO.fullmatch(s):
		return "bank"
	return "tally" if _TALLY_NO.match(raw) else "bill"


def plain_no(ref) -> str | None:
	"""A plain Tally serial written on a migrated receipt / payment (329, 330): a voucher number too, though short."""
	s = str(ref or "").strip()
	return s if s.isdigit() and 2 <= len(s) <= 8 and set(s) != {"0"} else None


def different_vouchers(a, b) -> bool:
	"""Two payments / journals are two real entries only when both have their own number OF THE SAME KIND: two Tally voucher
	numbers (PAY/526 and PAY/527) or two bill numbers (305 and 306). Checker 7-Nov: a bank number never clears a pair, not
	against a Tally number (Babasaheb: JE-01769 PAY/586/25-26 vs PE-00202 IMPS62991715402) and not against another bank
	number (Oxford Rs 17,46,400: PE-00012 ICICR2202261 vs PE-00206 469833504408, the same money booked twice).
	Checker 9-Nov: 8 of 9 pairs left were Tally receipts with plain serials (329 vs 330): two numbers, two entries."""
	pa, pb = plain_no(a), plain_no(b)
	if pa and pb:
		return pa != pb
	ka, kb = ref_kind(a), ref_kind(b)
	return bool(ka and ka == kb and ka != "bank" and norm_ref(a) != norm_ref(b))


def pair_days(a, b) -> int:
	"""Days apart two entries may be and still be one payment: a Tally voucher against a bank number gets CROSS_DAYS."""
	return CROSS_DAYS if {ref_kind(a), ref_kind(b)} == {"tally", "bank"} else DAYS


def voucher_double(a_ref, a_date, b_ref, b_date) -> bool:
	"""Same party and amount already matched: is this a possible double (numbers do not clear it, dates close enough)?"""
	return not different_vouchers(a_ref, b_ref) and near(a_date, b_date, pair_days(a_ref, b_ref))


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


def payee_fits(a: dict, b: dict) -> bool:
	"""Bank-side rows: two named payees must be the same; a row without a party (a Tally journal on an advance ledger) fits
	a named payee when the payee's name is in its remark ("Tally Payment PAY/586 | BABASAHEB SIR (ADVANCE)")."""
	pa, pb = a.get("payee"), b.get("payee")
	if pa and pb:
		return pa == pb
	named, other = (a, b) if pa else (b, a) if pb else (None, None)
	if named and other.get("hint"):
		word = next((w for w in re.split(r"[^A-Z0-9]+", str(named["payee"]).upper()) if len(w) >= 4), None)
		return not word or word in str(other["hint"]).upper()
	return True


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
				if not near(a.get("date"), b.get("date"), max(days, CROSS_DAYS)):
					break
				gap = pair_days(a.get("ref"), b.get("ref")) if days == DAYS else days
				# bank-side rows (checker 9-Nov, Babasaheb PE-00202 = JE-01769): the same bank account, direction, amount and
				# bank date (within BANK_DAYS) across doctypes is a pair unless both name different payees
				if str(a.get("kind", "")).startswith("bank"):
					gap = BANK_DAYS
					if not payee_fits(a, b):
						continue
				if (same_amount(a["amount"], b["amount"]) and near(a.get("date"), b.get("date"), gap)
						and not different_vouchers(a.get("ref"), b.get("ref"))):
					# two entries with their own numbers of the same kind (Tally PAY/526 and PAY/527, bills 305 and 306) are two
					# real entries (SK 7-Nov); a bank number never clears a pair (checker 7-Nov)
					add(a, b, "same party and amount within {} days".format(gap))
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
