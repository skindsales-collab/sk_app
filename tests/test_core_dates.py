from datetime import date

from sk_app.core.dates import by_month, fy_start


def test_fy_start():
	assert fy_start(date(2026, 11, 4)) == date(2026, 4, 1)
	assert fy_start(date(2026, 2, 1)) == date(2025, 4, 1)


def test_by_month():
	rows = [{"d": date(2026, 5, 3), "v": 10}, {"d": date(2026, 4, 9), "v": 5}, {"d": date(2026, 5, 20), "v": None}]
	assert by_month(rows, lambda r: r["d"], lambda r: r["v"]) == [
		{"month": "Apr 26", "count": 1, "value": 5.0}, {"month": "May 26", "count": 2, "value": 10.0}]
