from datetime import datetime

from sk_app.logic import WorkItem, company_dates, plan_day


def test_company_dates_october_2026():
	d = company_dates(None, 2026, 10)
	assert d[1] == ["Stock closing"] and d[5] == ["Scorecard"] and d[10] == ["MAR review"]
	assert d[31] == ["Town hall"]  # last Saturday of Oct 2026


def test_company_dates_custom_and_bad_lines():
	d = company_dates("15: Pay day\nlast-Fri: Week close\n40: wrong\nnonsense", 2026, 11)
	assert d[15] == ["Pay day"] and d[27] == ["Week close"] and 40 not in d


def test_plan_day_skips_lunch_and_overflows():
	now = datetime(2026, 10, 26, 12, 30)
	items = [WorkItem("lead_new", "Call A", minutes=30, priority=1), WorkItem("task", "Long job", minutes=600, priority=3)]
	slots, later = plan_day(items, now, "09:00", "18:00", "13:00", "14:00")
	work = [s for s in slots if s["item"]]
	assert work[0]["title"] == "Call A" and work[0]["start"] == datetime(2026, 10, 26, 12, 30)
	assert [i.title for i in later] == ["Long job"]
	assert any(s["kind"] == "lunch" for s in slots)


def test_plan_day_moves_work_after_fixed_event():
	now = datetime(2026, 10, 26, 9, 0)
	fixed = [(datetime(2026, 10, 26, 9, 0), datetime(2026, 10, 26, 10, 0), "Site visit")]
	slots, _ = plan_day([WorkItem("task", "Quote", minutes=20)], now, "09:00", "18:00", "13:00", "14:00", fixed)
	work = [s for s in slots if s["item"]][0]
	assert work["start"] == datetime(2026, 10, 26, 10, 0)


def test_plan_day_after_work_end_moves_all_to_later():
	now = datetime(2026, 10, 26, 19, 0)
	slots, later = plan_day([WorkItem("task", "Quote", minutes=20)], now, "09:00", "18:00", "13:00", "14:00")
	assert slots == [] and [i.title for i in later] == ["Quote"]
