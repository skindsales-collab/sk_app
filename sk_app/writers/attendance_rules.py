"""Pure rules of the HR line, attendance (linear flow map, Flow 6): thumb / Optick / selfie punches (Employee Checkin)
-> one ERPNext Attendance per person per working day -> one missed-punch list to HR. Rebuild 7-Nov-2026.

Absent is never written from punches (a person at a site or on the other machine would be marked absent by mistake);
a working day with no punch and no leave goes on HR's missed-punch list instead."""

from datetime import datetime, time


def day_status(ins: datetime, outs: datetime | None, late_after: time, half_day_below: float = 0) -> tuple[str, bool]:
	"""(status, late): Present; Half Day only when SK set the hours and both punches are real; late after the settings time."""
	status = "Present"
	if half_day_below and outs and (outs - ins).total_seconds() / 3600 < half_day_below:
		status = "Half Day"
	return status, ins.time() > late_after


def first_last(punches: list[datetime]) -> tuple[datetime | None, datetime | None]:
	"""First punch = in; the last punch is the out only when it is a different, later punch."""
	if not punches:
		return None, None
	p = sorted(punches)
	return p[0], (p[-1] if len(p) > 1 and p[-1] > p[0] else None)


def plan_day(employees: list[dict], punches: dict, existing: set, on_leave: set, off: set) -> tuple[list[dict], list[dict]]:
	"""employees = [{name, employee_name, joined}] active on the day, punches = {employee: [datetime]}, existing = employees
	with an Attendance already (leave, HR fix: never changed), on_leave / off = employees on approved leave / holiday.
	Returns (attendance to make [{employee, in, out}], missed [{employee, name, what}])."""
	make, missed = [], []
	for e in employees:
		emp = e["name"]
		ins, outs = first_last(punches.get(emp) or [])
		if ins and emp not in existing:
			make.append({"employee": emp, "in": ins, "out": outs})
		if ins and not outs:
			missed.append({"employee": emp, "name": e.get("employee_name") or emp, "what": "no out-punch"})
		elif not ins and emp not in existing and emp not in on_leave and emp not in off:
			missed.append({"employee": emp, "name": e.get("employee_name") or emp, "what": "no check-in"})
	return make, missed


def attendance_problems(status: str, day, joined, today, punches: int, leave: bool) -> list:
	"""Every Attendance saved (app, ERPNext, Claude): not before joining or in the future; Present needs a punch (else HR
	writes why in a comment, as the app's Fix does); On Leave needs an approved leave application."""
	out = []
	if joined and day < joined:
		out.append(("att_before_joining", "Attendance before the joining date"))
	if day > today:
		out.append(("att_future", "Attendance for a future date"))
	if status in ("Present", "Half Day") and not punches:
		out.append(("att_no_punch", "Present without any punch (thumb / Optick / selfie): please write the reason"))
	if status == "On Leave" and not leave:
		out.append(("att_leave_not_approved", "On Leave without an approved leave application"))
	return out
