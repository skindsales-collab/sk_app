"""Daily Day Report: every person reports their day's work in the app; managers review it for monitoring and improvement.

The app also captures what it already knows about the day (guide cards done, calls, CRM notes, new leads, Work Book,
DSI, KPI score), so the person only writes what was done, the problems and tomorrow's plan.
"""

import frappe
from frappe import _
from frappe.utils import add_to_date, cint, get_datetime, getdate, now_datetime, strip_html

from sk_app import guide, kpi
from sk_app.logic import WorkItem, to_time

REMIND_BEFORE_END_MINUTES = 60
RATINGS = ("Good", "OK", "Needs improvement")


def due_at(day=None):
	"""Report is due at the Work End time of SK App Settings (default 6 pm)."""
	end = to_time(frappe.get_cached_doc("SK App Settings").work_end or "18:00:00")
	return get_datetime(f"{getdate(day)} {end.strftime('%H:%M:%S')}")


def _count(doctype: str, filters: dict) -> int:
	if not frappe.db.exists("DocType", doctype):
		return 0
	return frappe.db.count(doctype, filters)


def captured(user: str, day=None) -> dict:
	"""What the app recorded for the user on the day."""
	day = getdate(day)
	period = ["between", [f"{day} 00:00:00", f"{day} 23:59:59"]]
	from sk_app.comms import call_totals

	calls = call_totals(user, day)
	facts = {
		"cards_done": _count("SK Guide Card", {"user": user, "response": "Done", "slot_start": period}),
		"calls_made": calls["calls"],
		"talk_minutes": round(calls["talk_seconds"] / 60),
		"missed_calls": calls["missed"],
		"notes_added": _count("FCRM Note", {"owner": user, "creation": period}),
		"leads_created": _count("CRM Lead", {"owner": user, "creation": period}),
		"work_entries": _count("SK Work Log", {"user": user, "date": day}),
		"dsi_done": 1 if _count("SK DSI Entry", {"user": user, "date": day}) else 0,
		"kpi_score": kpi.scorecard(user, day)["total_score"],
	}
	lines = []
	for card in frappe.get_all("SK Guide Card", filters={"user": user, "response": "Done", "slot_start": period},
			fields=["card_text"], order_by="slot_start asc", limit=20):
		lines.append("✓ " + strip_html(card.card_text or "").split("\n")[0][:120])
	for w in frappe.get_all("SK Work Log", filters={"user": user, "date": day}, fields=["entry_type", "description"],
			order_by="creation asc", limit=20):
		lines.append(f"• {w.entry_type}: {(w.description or '')[:120]}")
	facts["auto_summary"] = "\n".join(lines)
	return facts


def _find(user: str, day) -> str | None:
	return frappe.db.get_value("SK Day Report", {"user": user, "date": getdate(day)}, "name")


def get(user: str, day=None) -> dict:
	"""Today's report if already sent (the person can still edit it), plus what the app captured."""
	day = getdate(day)
	name = _find(user, day)
	report = frappe.get_doc("SK Day Report", name).as_dict() if name else None
	return {"date": str(day), "due_at": str(due_at(day)), "report": report, "captured": captured(user, day)}


def submit(user: str, work_done: str, problems: str | None = None, plan_tomorrow: str | None = None,
		photo: str | None = None) -> str:
	"""Save the user's report for today (one per person per day; sending again updates it)."""
	if not (work_done or "").strip():
		frappe.throw(_("Please write the work you did today"))
	profile = guide.app_user(user)
	day = getdate()
	name = _find(user, day)
	doc = frappe.get_doc("SK Day Report", name) if name else frappe.new_doc("SK Day Report")
	now = now_datetime()
	doc.update({"user": user, "date": day, "function": profile.home if profile else None,
		"manager": frappe.db.get_value("SK App User", {"user": user}, "manager"),
		"work_done": work_done.strip(), "problems": (problems or "").strip(), "plan_tomorrow": (plan_tomorrow or "").strip(),
		**captured(user, day)})
	if photo:
		doc.photo = photo
	if not doc.submitted_on:
		doc.submitted_on = now
		doc.on_time = 1 if now <= due_at(day) else 0
	doc.save(ignore_permissions=True) if name else doc.insert(ignore_permissions=True)
	return doc.name


def reminder(user: str, now=None) -> list[WorkItem]:
	"""My Day / hourly card item from one hour before Work End until the report is sent."""
	now = get_datetime(now or now_datetime())
	due = due_at(now)
	if now < add_to_date(due, minutes=-REMIND_BEFORE_END_MINUTES) or _find(user, now):
		return []
	# always the last job of the day: other work comes first, so no due time (never "overdue") and lowest priority
	return [WorkItem("day_report", "Send today's Day Report", "SK Day Report", "", minutes=5, priority=9, extra={"due_at": str(due)})]


def _team(manager: str) -> list[dict]:
	"""Everyone under `manager`, down the whole chain (a CEO sees the managers and their people too). The CEO /
	Management function sees everyone in the app."""
	from sk_app.logins import profile_functions

	people = frappe.get_all("SK App User", filters={"enabled": 1}, fields=["user", "full_name", "home", "manager"],
		order_by="full_name asc")
	# SK 26-Oct: decided by the app function only, not by ERPNext roles (an old HR / admin role gave Samir and Rahul
	# everyone's reports)
	if manager == "Administrator" or "Management" in profile_functions(manager):
		return [p for p in people if p.user != manager]
	under, todo = set(), [manager]
	while todo:
		boss = todo.pop()
		for p in people:
			if p.manager == boss and p.user not in under and p.user != manager:
				under.add(p.user)
				todo.append(p.user)
	return [p for p in people if p.user in under]


def team(manager: str, day=None) -> dict:
	"""Who has reported on the day, who has not, and each report, for the manager's review."""
	day = getdate(day)
	people = _team(manager)
	rows = {r.user: r for r in frappe.get_all("SK Day Report", filters={"date": day, "user": ["in", [p.user for p in people] or [""]]},
		fields=["name", "user", "work_done", "problems", "plan_tomorrow", "photo", "submitted_on", "on_time", "cards_done",
			"calls_made", "talk_minutes", "missed_calls", "notes_added", "leads_created", "work_entries", "dsi_done", "kpi_score", "manager_rating",
			"manager_comment"])}
	out = []
	for p in people:
		r = rows.get(p.user)
		out.append({"user": p.user, "full_name": p.full_name, "function": p.home, "reported": bool(r), "report": r})
	sent = sum(1 for o in out if o["reported"])
	return {"date": str(day), "total": len(out), "sent": sent, "missing": len(out) - sent, "people": out}


def review(manager: str, report: str, rating: str | None = None, comment: str | None = None) -> str:
	doc = frappe.get_doc("SK Day Report", report)
	if doc.user not in {p.user for p in _team(manager)}:
		frappe.throw(_("This report is not from your team"), frappe.PermissionError)
	if rating and rating not in RATINGS:
		frappe.throw(_("Unknown rating"))
	doc.update({"manager_rating": rating or doc.manager_rating, "manager_comment": (comment or "").strip() or doc.manager_comment,
		"reviewed_by": manager, "reviewed_on": now_datetime()})
	doc.save(ignore_permissions=True)
	return doc.name


def my_history(user: str, days: int = 14) -> list[dict]:
	return frappe.get_all("SK Day Report", filters={"user": user, "date": [">=", add_to_date(getdate(), days=-cint(days))]},
		fields=["name", "date", "work_done", "on_time", "manager_rating", "manager_comment"], order_by="date desc")
