"""Flow 6 HR: punches -> attendance, missed punches, leave (1 per 20 days after 6 months, HR then CEO), new joiner."""

from datetime import date, datetime, time

from sk_app.writers.attendance_rules import attendance_problems, day_status, first_last, plan_day
from sk_app.writers.employee_rules import joiner_errors, joiner_warnings
from sk_app.writers.leave_rules import earned, eligible_from, holiday_problems, leave_problems, next_step


def keys(found):
	return [k for k, _w in found]


def dt(h, m=0):
	return datetime(2026, 11, 5, h, m)


def test_day_status_late_and_half_day():
	assert day_status(dt(9, 2), dt(18), time(9, 15)) == ("Present", False)
	assert day_status(dt(9, 30), None, time(9, 15)) == ("Present", True)
	assert day_status(dt(9), dt(12), time(9, 15), 4) == ("Half Day", False)
	assert day_status(dt(9), None, time(9, 15), 4) == ("Present", False)  # no out-punch: never half day


def test_first_and_last_punch():
	assert first_last([]) == (None, None)
	assert first_last([dt(9)]) == (dt(9), None)
	assert first_last([dt(18), dt(9), dt(13)]) == (dt(9), dt(18))


def test_plan_day_makes_attendance_and_one_missed_list():
	emps = [{"name": e, "employee_name": e} for e in ("A", "B", "C", "D", "E", "F")]
	punches = {"A": [dt(9), dt(18)], "B": [dt(9, 40)], "F": [dt(9), dt(18)]}
	make, missed = plan_day(emps, punches, existing={"F"}, on_leave={"D"}, off={"E"})
	assert [m["employee"] for m in make] == ["A", "B"]  # F already has attendance (HR fix / leave): never changed
	assert [(m["employee"], m["what"]) for m in missed] == [("B", "no out-punch"), ("C", "no check-in")]


def test_attendance_rules():
	d, today = date(2026, 11, 5), date(2026, 11, 7)
	assert attendance_problems("Present", d, date(2026, 1, 1), today, 2, False) == []
	assert keys(attendance_problems("Present", d, date(2026, 11, 6), today, 0, False)) == ["att_before_joining", "att_no_punch"]
	assert keys(attendance_problems("On Leave", date(2026, 11, 9), None, today, 0, False)) == ["att_future", "att_leave_not_approved"]
	assert attendance_problems("Absent", d, None, today, 0, False) == []


def test_paid_leave_after_6_months_one_per_20_days():
	assert eligible_from(date(2026, 4, 1)) == date(2026, 10, 1)
	assert eligible_from(date(2026, 8, 31)) == date(2027, 2, 28)
	assert earned(19) == 0 and earned(20) == 1 and earned(45.5) == 2
	joined = date(2026, 4, 1)
	assert leave_problems(False, 3, None, date(2026, 5, 1), 0, 0) == []  # leave without pay: always
	assert keys(leave_problems(True, 1, joined, date(2026, 9, 30), 100, 0)) == ["leave_before_6_months"]
	assert leave_problems(True, 1, joined, date(2026, 11, 10), 22, 0) == []
	assert keys(leave_problems(True, 2, joined, date(2026, 11, 10), 22, 0)) == ["leave_not_earned"]
	assert keys(leave_problems(True, 1, joined, date(2026, 11, 10), 40, 2)) == ["leave_not_earned"]
	assert keys(leave_problems(True, 1, None, date(2026, 11, 10), 40, 0)) == ["leave_no_joining"]


def test_holiday_list_has_sk_paid_holidays():
	full = [(date(2027, 1, 26), "Republic Day"), (date(2026, 5, 1), "Maharashtra Day"), (date(2026, 8, 15), "Independence Day"),
		(date(2026, 9, 14), "Ganesh Chaturthi"), (date(2026, 10, 20), "Dussehra"), (date(2026, 11, 8), "Diwali (Laxmi Pujan)"),
		(date(2026, 11, 10), "Diwali Padwa")]
	assert holiday_problems(full, 2026) == []
	found = holiday_problems(full[:2] + full[4:6], 2026)
	assert [w for _k, w in found] == ["Independence Day 2026-08-15 is not in the holiday list",
		"Ganesh Chaturthi (1 day) is not in the holiday list", "Diwali (2 days) is not in the holiday list"]


def test_leave_approval_hr_then_ceo():
	assert next_step(True, by_hr=True, by_ceo=False, hr_done=False) == "to_ceo"
	assert next_step(False, by_hr=True, by_ceo=False, hr_done=False) == "reject"
	assert next_step(True, by_hr=True, by_ceo=False, hr_done=True) == "not_allowed"  # HR cannot approve twice
	assert next_step(True, by_hr=False, by_ceo=True, hr_done=True) == "approve"
	assert next_step(True, by_hr=False, by_ceo=True, hr_done=False) == "approve"  # the CEO may decide at once
	assert next_step(True, by_hr=False, by_ceo=False, hr_done=True) == "not_allowed"


def test_new_joiner_errors_and_warnings():
	ok = {"name": "Ram  Patil", "gender": "Male", "dob": "01-01-1995", "aadhaar": "1234 5678 9012", "pan": "abcde1234f"}
	assert joiner_errors(ok) == []
	assert keys(joiner_errors({"name": " ", "gender": "", "aadhaar": "123", "pan": "X1"})) == ["emp_no_name", "emp_no_gender",
		"emp_no_dob", "emp_aadhaar", "emp_pan"]
	assert joiner_warnings("+91 98220 12345", 2, date(2026, 11, 1)) == []
	assert keys(joiner_warnings("", 1, None)) == ["emp_no_mobile", "emp_no_papers", "emp_no_joining"]
