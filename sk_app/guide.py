"""Hourly 'what to do now' card for each person."""

import frappe
from frappe.utils import now_datetime

from sk_app import claude, kpi, work
from sk_app.logic import guide_prompt, is_work_slot, parse_lines, rule_card


def app_user(user: str):
	return frappe.db.get_value("SK App User", {"user": user, "enabled": 1},
		["name", "user", "full_name", "home", "language"], as_dict=True)


def make_card(user: str, use_claude: bool = True) -> dict:
	"""Build and save one guide card for the user. Claude writes it when available, else the rules do."""
	profile = app_user(user)
	if not profile:
		frappe.throw(frappe._("{0} is not set up as an SK App user").format(user))
	now = now_datetime()
	items = work.collect(user, profile.home)
	text, top = rule_card(items, now, profile.language or "English")
	source = "Rules"
	if use_claude and items:
		kpis = [k for k in kpi.scorecard(user)["kpis"] if k["live"]]
		claude_text = claude.guide_text(guide_prompt(profile.full_name or user, profile.language or "English", now, items, kpis))
		if claude_text:
			text, source = claude_text, "Claude"
	card = frappe.get_doc({
		"doctype": "SK Guide Card",
		"user": user,
		"slot_start": now,
		"minutes": top.minutes if top else 15,
		"card_text": text,
		"source": source,
		"reference_doctype": top.doctype if top and top.name else None,
		"reference_name": top.name if top and top.name else None,
	}).insert(ignore_permissions=True)
	return card.as_dict()


def hourly():
	"""Scheduler: one card per enabled SK App user during working hours (no cards in lunch, nights or Sundays)."""
	settings = frappe.get_cached_doc("SK App Settings")
	if not settings.guide_enabled:
		return
	days = parse_lines((settings.working_days or "").replace(",", "\n"))
	if not is_work_slot(now_datetime(), settings.work_start, settings.work_end, settings.lunch_start, settings.lunch_end, days):
		return
	for user in frappe.get_all("SK App User", filters={"enabled": 1}, pluck="user"):
		try:
			make_card(user)
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
			frappe.log_error(f"SK App guide card failed for {user}", "SK App Guide")
