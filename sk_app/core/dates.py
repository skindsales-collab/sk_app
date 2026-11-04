"""Pure date rules (no frappe), tested in CI."""

from datetime import date


def fy_start(d: date) -> date:
	"""Indian financial year start: 1 April of this year, or of last year before April."""
	return date(d.year if d.month >= 4 else d.year - 1, 4, 1)


def month_key(d: date) -> str:
	return f"{d:%b %y}"


def by_month(items: list, day_of, value_of) -> list:
	"""[{month, count, value}] in date order for the graph. items are any rows; day_of / value_of read them."""
	out = {}
	for it in items:
		d = day_of(it)
		out.setdefault((d.year, d.month), {"month": month_key(d), "count": 0, "value": 0.0})
		out[(d.year, d.month)]["count"] += 1
		out[(d.year, d.month)]["value"] += float(value_of(it) or 0)
	return [out[k] for k in sorted(out)]
