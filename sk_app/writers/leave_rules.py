"""Pure rules of the HR line, leave (Flow 6), SK's rules (Framework IT 7-Nov): 1 paid leave per 20 days worked once the
person has completed 6 months; the fixed paid holidays; approval by HR first, then the CEO. Nothing salary-related."""

from datetime import date

DAYS_PER_LEAVE = 20
MONTHS_BEFORE_LEAVE = 6
# paid holidays SK fixed; the dated ones by month-day, the festivals by name (their date changes every year)
FIXED = {(1, 26): "Republic Day", (5, 1): "Maharashtra Day", (8, 15): "Independence Day"}
FESTIVALS = {"Ganesh Chaturthi": 1, "Dussehra": 1, "Diwali": 2}


def eligible_from(joined: date) -> date:
	"""The day 6 months after joining (end of month when that day does not exist)."""
	m = joined.month - 1 + MONTHS_BEFORE_LEAVE
	y, m = joined.year + m // 12, m % 12 + 1
	for d in (joined.day, 30, 29, 28):
		try:
			return date(y, m, d)
		except ValueError:
			continue
	return date(y, m, 28)


def earned(days_worked: float) -> int:
	"""Paid leave earned by the days worked (present = 1, half day = 0.5), counted from joining (or the 6-month day)."""
	return int(float(days_worked or 0) // DAYS_PER_LEAVE)


def leave_problems(paid: bool, days: float, joined: date | None, from_date: date, worked: float, used: float) -> list:
	"""A paid leave needs 6 months done on its first day and enough earned leave; leave without pay is always allowed."""
	if not paid:
		return []
	if not joined:
		return [("leave_no_joining", "The joining date is missing on the Employee: HR must fill it")]
	if from_date < eligible_from(joined):
		return [("leave_before_6_months", f"Paid leave starts after 6 months ({eligible_from(joined)}); take Leave Without Pay")]
	left = earned(worked) - float(used or 0)
	if float(days or 0) > left:
		return [("leave_not_earned", f"Only {max(left, 0):g} paid leave earned (1 per {DAYS_PER_LEAVE} days worked); take Leave Without Pay")]
	return []


def holiday_problems(holidays: list[tuple], fy_start_year: int) -> list:
	"""holidays = [(date, description)] of the company list for the financial year starting April fy_start_year."""
	out = []
	days = {d: (t or "") for d, t in holidays}
	for (m, d), name in FIXED.items():
		day = date(fy_start_year + (1 if m < 4 else 0), m, d)
		if day not in days:
			out.append(("holiday_missing", f"{name} {day} is not in the holiday list"))
	for name, count in FESTIVALS.items():
		found = sum(1 for t in days.values() if name.lower() in t.lower())
		if found < count:
			out.append(("holiday_missing", f"{name} ({count} day{'s' if count > 1 else ''}) is not in the holiday list"))
	return out


def next_step(ok: bool, by_hr: bool, by_ceo: bool, hr_done: bool) -> str:
	"""Approval order HR, then CEO. Returns reject / to_ceo / approve / not_allowed."""
	if by_ceo and (hr_done or not by_hr):
		return "approve" if ok else "reject"
	if by_hr and not hr_done:
		return "to_ceo" if ok else "reject"
	return "not_allowed"
