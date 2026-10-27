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
	"""Save the user's report for today (one per person per day; sending again updates it). SK 26-Oct: the report
	is made from the day's ERPNext activity by itself, so typing is optional (a remark only)."""
	profile = guide.app_user(user)
	day = getdate()
	name = _find(user, day)
	doc = frappe.get_doc("SK Day Report", name) if name else frappe.new_doc("SK Day Report")
	now = now_datetime()
	facts = captured(user, day)
	doc.update({"user": user, "date": day, "function": profile.home if profile else None,
		"manager": frappe.db.get_value("SK App User", {"user": user}, "manager"),
		"work_done": (work_done or "").strip() or auto_text(facts), "problems": (problems or "").strip(), "plan_tomorrow": (plan_tomorrow or "").strip(),
		**facts})
	if photo:
		doc.photo = photo
	if not doc.submitted_on:
		doc.submitted_on = now
		doc.on_time = 1 if now <= due_at(day) else 0
	doc.save(ignore_permissions=True) if name else doc.insert(ignore_permissions=True)
	return doc.name


def auto_text(facts: dict) -> str:
	"""The day's work in words, from what the app recorded (calls, leads, notes, jobs done, Work Book, DSI)."""
	parts = [f"{facts.get('calls_made', 0)} calls ({facts.get('talk_minutes', 0)} min)" if facts.get("calls_made") else "",
		f"{facts['leads_created']} new leads" if facts.get("leads_created") else "", f"{facts['notes_added']} CRM notes" if facts.get("notes_added") else "",
		f"{facts['cards_done']} jobs done" if facts.get("cards_done") else "", "DSI done" if facts.get("dsi_done") else ""]
	head = ", ".join(p for p in parts if p) or "No activity recorded in the app"
	return f"Auto: {head}" + (f"\n{facts['auto_summary']}" if facts.get("auto_summary") else "")


def auto_reports(now=None):
	"""Hourly: after Work End, everyone who has not sent a report gets one made from the day's activity (SK 26-Oct:
	"team report should be automatic"). Sending later still adds the person's remark to the same report."""
	now = get_datetime(now or now_datetime())
	if now < due_at(now):
		return
	for user in frappe.get_all("SK App User", filters={"enabled": 1}, pluck="user"):
		if _find(user, now.date()):
			continue
		try:
			submit(user, "")
		except Exception:
			frappe.log_error(f"SK App auto day report {user}")


def reminder(user: str, now=None) -> list[WorkItem]:
	"""My Day / hourly card item from one hour before Work End until the report is sent."""
	now = get_datetime(now or now_datetime())
	due = due_at(now)
	if now < add_to_date(due, minutes=-REMIND_BEFORE_END_MINUTES) or _find(user, now):
		return []
	# always the last job of the day: other work comes first, so no due time (never "overdue") and lowest priority
	return [WorkItem("day_report", "Day Report (made by itself): add a remark if needed", "SK Day Report", "", minutes=5, priority=9, extra={"due_at": str(due)})]


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


def team_screen(manager: str, people: list[dict]) -> dict:
	"""SK 27-Oct point 7: the sales manager's team screen in the standard format ("in arrow way"): each person's
	arrows (New → ... → Negotiations), month-to-date sale against their target, calls today and overdue, and the
	team's "Decide now": leads not called after 24 hours, quotations waiting over 7 days, the person most behind."""
	from frappe.utils import add_to_date, now_datetime, nowdate

	from sk_app import activities, comms, flows, home_kpi, lead_status
	from sk_app.dashboards import _has, _safe

	members = []
	for p in people:
		steps = _safe(lambda p=p: flows.sales(p["user"], only_self=True), []) or []
		card = _safe(lambda p=p: home_kpi.sales(p["user"], only_self=True), None)
		actual = due = target = 0
		if card:
			pts = card["week"]["lines"][0]["points"]
			actual, due, target = (pts[-1] if pts else 0), (card["week"]["target"][-1] if card["week"]["target"] else 0), card["target"]
		members.append({"user": p["user"], "full_name": p["full_name"],
			"steps": [{"key": s["key"], "label": s["label"], "count": s["count"], "late": s["late"], "c": s["c"]} for s in steps],
			"actual": actual, "due": due, "target": target, "pct": round(actual * 100 / due) if due else None,
			"calls_today": _safe(lambda p=p: comms.call_totals(p["user"], nowdate())["calls"], 0) or 0,
			"acts": _safe(lambda p=p: {k: v for k, v in activities.today(p["user"]).items() if k in ("hit", "total")}, None)})
	users = [p["user"] for p in people]
	decide = {"not_called": 0, "quotes_waiting": 0, "behind": None}
	if _has("CRM Lead"):
		closed = frappe.get_all("CRM Lead Status", filters={"type": ["in", ["Won", "Lost", "Junk"]]}, pluck="name")
		from sk_app.cold_calls import not_cold

		decide["not_called"] = frappe.db.count("CRM Lead", {"lead_owner": ["in", users], "converted": 0, "first_responded_on": ["is", "not set"], **not_cold(),
			"status": ["not in", closed or [""]], "creation": ["<", add_to_date(now_datetime(), hours=-24)]})
		decide["quotes_waiting"] = frappe.db.count("CRM Lead", {"lead_owner": ["in", users], "status": "Quotation",
			"modified": ["<", add_to_date(now_datetime(), days=-7)]})
	if _has("CRM Deal"):
		quote_st = [s for s in frappe.get_all("CRM Deal Status", pluck="name") if lead_status.step_of(s, deal=True) == "Quotation"]
		if quote_st:
			decide["quotes_waiting"] += frappe.db.count("CRM Deal", {"deal_owner": ["in", users], "status": ["in", quote_st],
				"modified": ["<", add_to_date(now_datetime(), days=-7)]})
	ranked = sorted([m for m in members if m["pct"] is not None and m["target"]], key=lambda m: m["pct"])
	if ranked and ranked[0]["pct"] < 100:
		decide["behind"] = {"user": ranked[0]["user"], "full_name": ranked[0]["full_name"], "pct": ranked[0]["pct"]}
	return {"members": members, "decide": decide}
