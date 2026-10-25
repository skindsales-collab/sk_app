from datetime import date, datetime, timedelta

from sk_app.logic import (
	WorkItem,
	expected_by_today,
	guide_prompt,
	is_work_slot,
	kpi_colour,
	kpi_score,
	month_range,
	rank_items,
	rule_card,
	to_time,
)

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]


def test_month_range():
	assert month_range(date(2026, 2, 14)) == (date(2026, 2, 1), date(2026, 2, 28))
	assert month_range(date(2026, 12, 31)) == (date(2026, 12, 1), date(2026, 12, 31))


def test_kpi_score_caps_and_zero_target():
	assert kpi_score(45, 45, 30) == 30
	assert kpi_score(90, 45, 30) == 36  # capped at 120%
	assert kpi_score(-5, 45, 30) == 0
	assert kpi_score(10, 0, 30) == 0


def test_kpi_colour():
	assert kpi_colour(100, 100) == "green"
	assert kpi_colour(85, 100) == "yellow"
	assert kpi_colour(50, 100) == "red"
	assert kpi_colour(5, 0) == "grey"


def test_expected_by_today_counts_working_days_only():
	# Oct 2026 has 27 Mon-Sat days; by Sat 31-Oct the full target is expected
	assert expected_by_today(26, date(2026, 10, 31), DAYS) == 26
	assert expected_by_today(27, date(2026, 10, 1), DAYS) == 1


def test_to_time_accepts_frappe_timedelta():
	assert to_time(timedelta(hours=9, minutes=30)).strftime("%H:%M") == "09:30"
	assert to_time("13:40:00").strftime("%H:%M") == "13:40"


def test_is_work_slot():
	args = ("09:00:00", "18:00:00", "13:00:00", "13:40:00", DAYS)
	assert is_work_slot(datetime(2026, 10, 26, 10, 0), *args)  # Monday 10:00
	assert not is_work_slot(datetime(2026, 10, 26, 13, 10), *args)  # lunch
	assert not is_work_slot(datetime(2026, 10, 26, 18, 0), *args)  # after hours
	assert not is_work_slot(datetime(2026, 10, 25, 10, 0), *args)  # Sunday


def test_rank_overdue_then_new_leads():
	now = datetime(2026, 10, 26, 10, 0)
	items = [
		WorkItem("task", "Old task", due=now + timedelta(days=2)),
		WorkItem("lead_followup", "Late follow-up", due=now - timedelta(hours=1)),
		WorkItem("lead_new", "Fresh lead", due=now + timedelta(minutes=5), priority=1),
	]
	ranked = [i.title for i in rank_items(items, now)]
	assert ranked == ["Late follow-up", "Fresh lead", "Old task"]


def test_rule_card_languages_and_empty():
	now = datetime(2026, 10, 26, 10, 0)
	text, item = rule_card([WorkItem("lead_new", "ABC Infra", priority=1)], now)
	assert text.startswith("Now: call new lead ABC Infra") and item.title == "ABC Infra"
	text, _ = rule_card([WorkItem("dsi", "DSI")], now, "Marathi")
	assert text.startswith("आता:")
	text, item = rule_card([], now)
	assert item is None and "DSI" in text


def test_guide_prompt_lists_items_and_kpis():
	now = datetime(2026, 10, 26, 10, 0)
	p = guide_prompt("Rahul", "English", now, [WorkItem("task", "Send quote")],
		[{"kpi_label": "Orders booked", "actual": 2.5e5, "monthly_target": 1.25e6, "unit": "Rs"}])
	assert "Send quote" in p and "Orders booked: 250000 / 1.25e+06 Rs" in p
