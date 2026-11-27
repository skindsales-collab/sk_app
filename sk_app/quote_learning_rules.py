"""Quote correction and learning (SK 27-Nov), plain arithmetic, no outside AI.

The salesperson sees the rate-card (suggested) amount and may type a corrected amount. The correction is kept against the
cabin's specification; from it the rate it implies is worked back (factor against the rate card, Rs per sq ft). The next
quote for a similar cabin shows a learned amount = rate card x median factor of the corrections that teach.
Only corrections SK approved, or whose quote became an order, teach (SK 27-Nov, recommended choice 3).
"""

from __future__ import annotations

import math

# a correction outside this band against the rate card is kept for reference but never teaches (typing slip)
FACTOR_MIN, FACTOR_MAX = 0.5, 2.0


def band(area: float, slabs: list | None = None, fixed_key: str | None = None) -> str:
	"""Which cabins are 'similar': the same rate-card size slab (or the same fixed size)."""
	if fixed_key:
		return f"size {fixed_key}"
	for upto, _rate in slabs or []:
		if area <= upto:
			return f"upto {upto:g} sq ft"
	return "large"


def spec_key(typ: str, area_band: str, title: str | None = None) -> str:
	if title:  # design-priced cabins: the same written title (e.g. 'LGSF office')
		return f"{typ} | {' '.join(title.lower().split())}"
	return f"{typ} | {area_band}"


def correction_rate(lines: list[dict], corrected_total: float, qty: int) -> float:
	"""Cabin rate (per cabin) that makes the quote total equal the corrected amount; the option and transport lines stay."""
	others = sum(l["amount"] for l in lines if l["kind"] != "cabin")
	left = corrected_total - others
	if qty <= 0 or left <= 0:
		raise ValueError("The corrected amount must be more than the options and transport together")
	return round(left / qty, 2)


def implied(suggested_rate: float, corrected_rate: float, area: float) -> dict:
	"""Back-calculation: the factor against the rate card and the Rs per sq ft the correction means."""
	factor = corrected_rate / suggested_rate if suggested_rate else 0.0
	return {"factor": round(factor, 4), "pct": round((factor - 1) * 100, 2), "per_sqft": round(corrected_rate / area, 2) if area else 0.0,
		"teaches": FACTOR_MIN <= factor <= FACTOR_MAX}


def below_pct(suggested_total: float, corrected_total: float) -> float:
	"""How far below the suggestion, in % (0 when the correction is higher): checked like a discount (SK 27-Nov, choice 1)."""
	if suggested_total <= 0 or corrected_total >= suggested_total:
		return 0.0
	return round((suggested_total - corrected_total) * 100 / suggested_total, 2)


def median(xs: list[float]) -> float:
	s = sorted(xs)
	n = len(s)
	return 0.0 if not n else s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def learned(rate_card_rate: float, factors: list[float], qty: int, round_to: float = 1) -> dict | None:
	"""The learned cabin rate shown beside the rate card (never replacing it, SK 27-Nov choice 2)."""
	good = [f for f in factors if FACTOR_MIN <= f <= FACTOR_MAX]
	if not good or rate_card_rate <= 0:
		return None
	f = median(good)
	step = round_to or 1
	rate = math.ceil(rate_card_rate * f / step) * step
	return {"rate": rate, "factor": round(f, 4), "pct": round((f - 1) * 100, 1), "n": len(good), "cabins": rate * qty}
