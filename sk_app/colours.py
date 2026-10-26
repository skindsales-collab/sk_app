"""Every Home icon shows its pending work in colour (change list point 15).

red = late / overdue, or a must-do not done (DSI, Day Report); amber = due today, not done yet; blue = new, not yet
opened (new lead, new drawing); green = all done for today. An icon takes the worst colour of its items. Sundays,
holidays and approved leave are never red.
"""

import frappe
from frappe.utils import get_datetime, getdate, now_datetime

from sk_app.logic import DAY_NAMES, parse_lines, to_time

ORDER = {"red": 3, "amber": 2, "blue": 1, "green": 0}
DSI_BY = "17:30"
REPORT_FROM = "17:00"
BLINK_FROM = "16:30"


def day_off(user: str, day=None) -> bool:
	"""Not a working day for the person: weekly off (SK App Settings), a holiday in the ERPNext Holiday List, or leave."""
	day = getdate(day)
	s = frappe.get_cached_doc("SK App Settings")
	working = parse_lines((s.working_days or "").replace(",", "\n")) or DAY_NAMES[:6]
	if DAY_NAMES[day.weekday()] not in working:
		return True
	emp = frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, ["name", "holiday_list", "company"], as_dict=True)
	holiday_list = (emp and emp.holiday_list) or frappe.db.get_value("Company", (emp and emp.company) or
		frappe.defaults.get_global_default("company"), "default_holiday_list")
	if holiday_list and frappe.db.exists("Holiday", {"parent": holiday_list, "holiday_date": day}):
		return True
	if emp and frappe.db.exists("DocType", "Leave Application") and frappe.db.exists("Leave Application", {
			"employee": emp.name, "status": "Approved", "docstatus": 1, "from_date": ["<=", day], "to_date": [">=", day]}):
		return True
	return False


def _mark(n, colour, blink=False):
	return {"n": n, "c": colour, **({"blink": 1} if blink else {})}


def _worst(*marks):
	marks = [m for m in marks if m]
	if not marks:
		return None
	top = max(marks, key=lambda m: ORDER[m["c"]])
	return {**top, "n": sum(m["n"] for m in marks if m["c"] == top["c"])}


def for_user(user: str, items: list, dsi_done: bool, report_sent: bool, counts: dict, now=None) -> dict:
	"""{tile: {"n": count, "c": colour, "blink": 1?}} from the person's open work and the other icons' counts."""
	now = get_datetime(now or now_datetime())
	today = now.date()
	t = now.time()
	off = day_off(user, today)
	out = {}
	if dsi_done:
		out["dsi"] = _mark(0, "green")
	elif not off:
		out["dsi"] = _mark(1, "red", blink=t >= to_time(BLINK_FROM))
	if report_sent:
		out["day_report"] = _mark(0, "green")
	elif not off and t >= to_time(REPORT_FROM):
		out["day_report"] = _mark(1, "red", blink=True)

	late = [i for i in items if i.kind not in ("dsi", "day_report") and i.due and i.due <= now]
	due_today = [i for i in items if i.kind not in ("dsi", "day_report") and i.due and now < i.due and i.due.date() == today]
	new = [i for i in items if i.kind in ("lead_new", "send_file") and i.due and i.due > now]
	day_mark = _worst(_mark(len(late), "red") if late else None, _mark(len(due_today), "amber") if due_today else None)
	if day_mark:
		out["my_day"] = day_mark
		out["calendar"] = day_mark
	lead_late = [i for i in late if i.doctype == "CRM Lead"]
	out_leads = _worst(_mark(len(lead_late), "red") if lead_late else None,
		_mark(len([i for i in new if i.kind == "lead_new"]), "blue") if any(i.kind == "lead_new" for i in new) else None)
	if out_leads:
		out["my_leads"] = out_leads
	files = [i for i in items if i.kind == "send_file"]
	if files:
		out["follow_up"] = _mark(len(files), "blue")
	for k, v in (counts or {}).items():
		if k in out or not v:
			continue
		# counts from the function icons (requests to issue, bills to post, approvals ...): waiting for me today
		out[k] = _mark(v, "blue" if k == "improvement_inbox" else "amber")
	return out
