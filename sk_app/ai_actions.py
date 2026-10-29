"""AI actions to lift the graph, every morning (SK 27-Oct-2026, improvement list points 3 and 6: "input expected from
AI" on the 🎯 Actions screen, and many graphs empty).

Free and rule-based, from live ERPNext data. Each person gets, in 🎯 Actions (and so in My Day, as ToDos):
- the stages of their own work flow that are late (most late first), short term, due today;
- the gap to today's share of the target on their graph, short term;
- a graph month that missed its target, long term (a week);
- "Start here": the first ERPNext entries that make an empty graph fill, long term;
- salespeople: yesterday's activity counters that missed their targets.
Each action says why (the data behind it). An action whose reason is gone the next morning is cancelled; one still
true is kept (not made twice). Only the person closes their action, with proof, as before.
"""

import re

import frappe
from frappe.utils import add_days, flt, getdate, nowdate

from sk_app.dashboards import _safe
from sk_app.home_kpi import ACTION_MARK, chart_for

AI = "🤖 AI"
KEY = re.compile(r"\s*\[ai:([^\]]+)\]\s*$")


def _money(v) -> str:
	v = flt(v)
	return f"Rs {v / 1e5:.1f} L" if abs(v) >= 1e5 else f"Rs {round(v):,}"


def rules(user: str, functions: list[str]) -> list[dict]:
	"""[{key, text, why, priority, term, days}] for the person today."""
	from sk_app import flows

	out = []
	# 1. late stages of the person's own flow
	data = _safe(lambda: flows.for_user(user, functions), {"flows": []}) or {"flows": []}
	late = sorted([(f, st) for f in data["flows"] for st in f["stages"] if st.get("late")], key=lambda x: (-x[1]["late"], -x[1]["oldest"]))
	for f, st in late[:3]:
		where = f" ({f['label']})" if f.get("label") else ""
		out.append({"key": f"late:{f.get('src') or f['function']}:{st['key']}", "term": "short", "days": 0,
			"priority": "High" if st["oldest"] > 7 else "Medium",
			"text": f"Clear the {st['late']} late in {st['label']}{where}",
			"why": f"{st['late']} of {st['count']} waiting longer than the target days, oldest {st['oldest']} days"})
	# 2-4. the graph
	card = _safe(lambda: chart_for(user, functions), None)
	if card and card["kind"] == "money":
		pts, due = card["week"]["lines"][0]["points"], card["week"]["target"]
		actual, owed = (pts[-1] if pts else 0), (due[-1] if due else 0)
		if card.get("target") and owed > actual:
			out.append({"key": "gap", "term": "short", "days": 0, "priority": "High",
				"text": f"Close the {_money(owed - actual)} gap to today's target: follow up Negotiations and Quotation first",
				"why": f"This month {_money(actual)} booked against {_money(owed)} due by today (month target {_money(card['target'])})"})
	elif card and card["kind"] == "trend":
		last = next((p for p in reversed(card["points"]) if p.get("v") is not None), None)
		if last:
			off = last["v"] > card["target"] if card.get("good_low") else last["v"] < card["target"]
			if off:
				out.append({"key": "trend", "term": "long", "days": 7, "priority": "Medium",
					"text": f"Bring {card['title']} to the target {card['target']}{card['unit']}",
					"why": f"{last['m']}: {last['v']}{card['unit']}"})
	elif card and card["kind"] == "projects" and card["invoiced"] and card["correct"] < card["invoiced"]:
		# SK 29-Oct: P&L applies after the invoice; an invoiced project's P&L is only right once its cost is posted too
		gaps = [r for r in card["projects"] if r["invoiced"] and r["missing"]]
		out.append({"key": "projects", "term": "short", "days": 1, "priority": "High",
			"text": f"Post the material / bills of {len(gaps)} invoiced projects, first {', '.join(r['label'] for r in gaps[:3])}",
			"why": f"{card['correct']} of {card['invoiced']} invoiced projects have their cost posted (target {card['target']}%)"})
	if card and card.get("need"):
		out.append({"key": "start", "term": "long", "days": 7, "priority": "Medium", "text": f"Start here: {card['need']}",
			"why": "Your graph has no data in ERPNext yet"})
	# 5. yesterday's sales activities
	if {"Sales", "Marketing"} & set(functions):
		from sk_app import activities

		y = _safe(lambda: activities.today(user, add_days(nowdate(), -1)), None)
		if y and getdate(add_days(nowdate(), -1)).weekday() < 6 and y["hit"] < y["total"]:
			missed = [r["label"] for r in y["rows"] if r["done"] < r["target"]][:3]
			out.append({"key": "acts", "term": "short", "days": 0, "priority": "Medium",
				"text": f"Hit today's activity targets, first: {', '.join(missed)}",
				"why": f"Yesterday {y['hit']} of {y['total']} activities reached their target"})
	return out


def _ai_open(user: str) -> dict:
	rows = frappe.get_all("ToDo", filters={"allocated_to": user, "status": "Open", "description": ["like", f"{ACTION_MARK}{AI}%"]},
		fields=["name", "description"], limit=0)
	out = {}
	for r in rows:
		m = KEY.search(r.description or "")
		if m:
			out[m.group(1)] = r.name
	return out


def refresh(user: str) -> int:
	"""Make today's AI actions for one person; cancel the ones whose reason is gone. Returns how many are open."""
	from sk_app.logins import profile_functions

	functions = profile_functions(user)
	if not functions:
		return 0
	want = {r["key"]: r for r in rules(user, functions)}
	have = _ai_open(user)
	for key, name in have.items():
		if key not in want:
			frappe.db.set_value("ToDo", name, "status", "Cancelled")
	for key, r in want.items():
		desc = f"{ACTION_MARK}{AI} · {'Short term' if r['term'] == 'short' else 'Long term'} · {r['text']} — Why: {r['why']} [ai:{key}]"
		due = add_days(nowdate(), r["days"])
		if key in have:
			frappe.db.set_value("ToDo", have[key], {"description": desc, "priority": r["priority"]})
		else:
			frappe.get_doc({"doctype": "ToDo", "allocated_to": user, "assigned_by": "Administrator", "description": desc,
				"priority": r["priority"], "date": due, "status": "Open"}).insert(ignore_permissions=True)
	frappe.cache.set_value(f"sk_ai_actions:{user}", nowdate(), expires_in_sec=26 * 3600)
	return len(want)


def refresh_if_stale(user: str):
	if frappe.cache.get_value(f"sk_ai_actions:{user}") != nowdate():
		_safe(lambda: refresh(user), 0)


def morning():
	"""Scheduler, every morning: everyone's AI actions."""
	for user in frappe.get_all("SK App User", filters={"enabled": 1}, pluck="user"):
		try:
			refresh(user)
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
			frappe.log_error(f"SK AI actions {user}")


def split(text: str) -> dict:
	"""For the screen: an AI action's term, text and reason without the key."""
	text = KEY.sub("", text or "")
	if not text.startswith(AI):
		return {"ai": False, "text": text}
	parts = text.split(" · ", 2)
	body = parts[2] if len(parts) == 3 else text
	what, _sep, why = body.partition(" — Why: ")
	return {"ai": True, "term": parts[1] if len(parts) == 3 else "", "text": what, "why": why}
