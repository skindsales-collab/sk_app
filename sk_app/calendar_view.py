"""Today / My Week / My Month calendars on the phone, built from the same open work as My Day plus ERPNext Events,
company dates (SK App Settings), orders booked and DSI."""

import json

import frappe
from frappe.utils import add_days, flt, get_datetime, getdate, now_datetime, strip_html

from sk_app import guide, kpi, work
from sk_app.logic import DAY_NAMES, company_dates, item_key, month_range, parse_lines, plan_day, plan_week, rank_items


def _settings():
	return frappe.get_cached_doc("SK App Settings")


def _events(start, end) -> list[dict]:
	"""ERPNext calendar Events the user can see (own, shared or public) between two dates, with repeating ones
	(e.g. a daily reminder) placed on each day."""
	from frappe.desk.doctype.event.event import get_events

	rows = [e for e in get_events(getdate(start), getdate(end)) if e.get("status") not in ("Cancelled",)]
	rows.sort(key=lambda e: get_datetime(e.starts_on))
	return rows[:200]


def _orders_by_day(user: str, start, end) -> dict:
	names = kpi.user_sales_orders(user, start, end)
	out = {}
	for r in frappe.get_all("Sales Order", filters={"name": ["in", names or [""]]}, fields=["transaction_date", "base_net_total"]):
		day = str(r.transaction_date)
		out[day] = out.get(day, 0.0) + flt(r.base_net_total)
	return out


def _orders_target(user: str) -> float:
	return flt(frappe.db.get_value("SK KPI Target", {"user": user, "active": 1,
		"kpi_code": ["in", ["orders_value", "digital_orders_value"]]}, "monthly_target"))


def _item(i) -> dict:
	return {"kind": i.kind, "title": i.title, "doctype": i.doctype, "name": i.name, "minutes": i.minutes,
		"due": str(i.due) if i.due else None, **i.extra}


def done_today(user: str, day) -> list[dict]:
	"""What the person finished on the day: cards done, Work Book / extra work, calls (My Day "Done today")."""
	period = ["between", [f"{day} 00:00:00", f"{day} 23:59:59"]]
	done = [{"time": str(c.responded_on or c.slot_start), "title": strip_html(c.card_text or "")[:120]}
		for c in frappe.get_all("SK Guide Card", filters={"user": user, "response": "Done", "slot_start": period},
			fields=["card_text", "slot_start", "responded_on"])]
	done += [{"time": str(w.creation), "title": f"{w.entry_type}: {(w.description or '')[:100]}"}
		for w in frappe.get_all("SK Work Log", filters={"user": user, "date": day}, fields=["entry_type", "description", "creation"])]
	if frappe.db.exists("DocType", "CRM Call Log"):
		done += [{"time": str(c.creation), "title": f"Call {c.status}: {c.reference_docname or ''}"}
			for c in frappe.get_all("CRM Call Log", filters={"caller": user, "creation": period},
				fields=["status", "reference_docname", "creation"])]
	done.sort(key=lambda d: d["time"])
	return done


def today(user: str, now=None) -> dict:
	now = get_datetime(now or now_datetime())
	day = now.date()
	s = _settings()
	profile = guide.app_user(user)
	# own reminders are calendar Events, so they come in once, as fixed times
	items = [i for i in work.collect(user, profile.home if profile else None) if i.kind != "reminder"]
	events = _events(day, day)
	fixed = [(get_datetime(e.starts_on), get_datetime(e.ends_on or e.starts_on), e.subject) for e in events
		if not e.all_day and get_datetime(e.starts_on) >= now]
	slots, later = plan_day(items, now, s.work_start or "09:00", s.work_end or "18:00", s.lunch_start or "13:00",
		s.lunch_end or "14:00", fixed)
	done = done_today(user, day)
	all_day = [e.subject for e in events if e.all_day] + company_dates(s.company_dates, day.year, day.month).get(day.day, [])
	return {
		"date": str(day), "now": str(now), "work_start": str(s.work_start), "work_end": str(s.work_end),
		"all_day": all_day, "done": done,
		"slots": [{"start": str(x["start"]), "end": str(x["end"]), "title": x["title"], "kind": x["kind"],
			**({"item": _item(x["item"])} if x["item"] else {})} for x in slots],
		"later": [_item(i) for i in later],
	}


def _due_by_day(items, start, end, now) -> dict:
	out = {}
	for i in rank_items(items, now):
		if not i.due:
			continue
		d = max(getdate(i.due), getdate(now))  # overdue work shows on today
		if start <= d <= end:
			out.setdefault(str(d), []).append({**_item(i), "overdue": i.due < now})
	return out


MOVES_KEY = "sk_week_moves"


def _moves(user: str) -> dict:
	try:
		return json.loads(frappe.defaults.get_user_default(MOVES_KEY, user) or "{}")
	except ValueError:
		return {}


def move_item(user: str, key: str, day) -> dict:
	"""'Move to Tue': the person puts one open item on another day of the week (kept until the item is done)."""
	moves = {k: v for k, v in _moves(user).items() if getdate(v) >= add_days(getdate(), -7)}
	if day:
		moves[str(key)[:200]] = str(getdate(day))
	else:
		moves.pop(key, None)
	frappe.defaults.set_user_default(MOVES_KEY, json.dumps(moves), user)
	return {"ok": True}


def _routine(user: str) -> list[tuple]:
	from sk_app.functions import ROUTINE
	from sk_app.logins import profile_functions

	out = []
	for f in profile_functions(user):
		out += [r for r in ROUTINE.get(f, []) if r not in out]
	return out + [("daily", "17:30", 15, "DSI + Day Report")]


def _event_minutes(events) -> dict:
	out = {}
	for e in events:
		if e.all_day:
			continue
		start, end = get_datetime(e.starts_on), get_datetime(e.ends_on or e.starts_on)
		out[start.date()] = out.get(start.date(), 0) + max(0, int((end - start).total_seconds() // 60))
	return out


def week(user: str, day=None) -> dict:
	"""A real weekly plan (change list point 9c): fixed weekly routine of the person's functions first, then open
	work spread over the working days by free hours, most urgent first. Overloaded days come back amber."""
	day = getdate(day)
	start = add_days(day, -day.weekday())
	end = add_days(start, 6)
	now = now_datetime()
	s = _settings()
	profile = guide.app_user(user)
	items = [i for i in work.collect(user, profile.home if profile else None) if i.kind != "reminder"]
	orders = _orders_by_day(user, start, end)
	events = _events(start, end)
	working = parse_lines((s.working_days or "").replace(",", "\n")) or DAY_NAMES[:6]
	dates = [add_days(start, n) for n in range(7)]
	plan = plan_week(items, dates, now, s.work_start or "09:00", s.work_end or "18:00", s.lunch_start or "13:00",
		s.lunch_end or "14:00", working, busy=_event_minutes(events), routine=_routine(user), moves=_moves(user))
	dsi = set(str(d) for d in frappe.get_all("SK DSI Entry", filters={"user": user, "date": ["between", [start, end]]}, pluck="date"))
	days = []
	for d in dates:
		key = str(d)
		p = plan[d]
		labels = company_dates(s.company_dates, d.year, d.month).get(d.day, [])
		days.append({"date": key, "day": DAY_NAMES[d.weekday()], "working": DAY_NAMES[d.weekday()] in working,
			"today": d == getdate(now), "company": labels,
			"events": [{"title": e.subject, "time": None if e.all_day else str(e.starts_on)[11:16]} for e in events if str(e.starts_on)[:10] == key],
			"routine": p["routine"],
			"due": [{**_item(i), "key": item_key(i), "overdue": flag == "overdue", "moved": flag == "moved"} for i, flag in p["items"]],
			"load": p["load"], "capacity": p["capacity"], "over": p["load"] > p["capacity"] and p["capacity"] > 0,
			"orders": orders.get(key, 0.0), "dsi": key in dsi})
	m_start, m_end = month_range(day)
	month_days = sum(1 for n in range((m_end - m_start).days + 1) if DAY_NAMES[add_days(m_start, n).weekday()] in working)
	week_days = sum(1 for x in days if x["working"])
	target = _orders_target(user)
	return {"start": str(start), "end": str(end), "week_no": start.isocalendar()[1], "days": days,
		"orders": sum(orders.values()), "orders_target": round(target * week_days / month_days, 2) if month_days else 0,
		"open_items": sum(len(x["due"]) for x in days)}


def month(user: str, year=None, month_no=None) -> dict:
	today_ = getdate()
	year, month_no = int(year or today_.year), int(month_no or today_.month)
	start, end = month_range(getdate(f"{year}-{month_no:02d}-01"))
	now = now_datetime()
	s = _settings()
	profile = guide.app_user(user)
	due = _due_by_day([i for i in work.collect(user, profile.home if profile else None) if i.kind != "reminder"], start, end, now)
	orders = _orders_by_day(user, start, end)
	labels = company_dates(s.company_dates, year, month_no)
	dsi = set(str(d) for d in frappe.get_all("SK DSI Entry", filters={"user": user, "date": ["between", [start, end]]}, pluck="date"))
	events = _events(start, end)
	days = []
	for n in range((end - start).days + 1):
		d = add_days(start, n)
		key = str(d)
		days.append({"date": key, "day": d.day, "weekday": d.weekday(), "today": d == today_, "company": labels.get(d.day, []),
			"events": [e.subject for e in events if str(e.starts_on)[:10] == key],
			"due": len(due.get(key, [])), "overdue": any(x["overdue"] for x in due.get(key, [])),
			"orders": orders.get(key, 0.0), "dsi": key in dsi})
	card = kpi.scorecard(user, end if end < today_ else today_)
	return {"year": year, "month": month_no, "label": f"{start:%B %Y}", "days": days, "score": card["total_score"],
		"orders": sum(orders.values()), "orders_target": _orders_target(user), "dsi": len(dsi)}
