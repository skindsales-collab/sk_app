"""Known facts (SK 4-Nov-2026): "many times you ask something, then I inform that it is already available".

One place in ERPNext (SK Known Fact) for every master, rule and decision already given. The rule for every Claude
project, thread and app helper: CHECK BEFORE ASK.
1. find(): search here (and say where you looked: SK Known Fact, ERPNext records, project memory, sk-* skills, files).
2. Ask only what is not found.
3. save(): every answer is saved at once; a changed answer replaces the old one (kept, marked Replaced).
4. If SK says "already given", save(..., asked_again=True): it counts on the scorecard ("Repeat questions to SK").
"""

import frappe
from frappe.utils import now_datetime, nowdate

DOCTYPE = "SK Known Fact"
FIELDS = ["name", "topic", "area", "fact", "given_by", "given_on", "source", "times_asked_again"]


def find(query: str, area: str | None = None, limit: int = 20) -> list[dict]:
	"""Active facts that match the query best first (see fact_rules.score)."""
	from sk_app.core.fact_rules import score, words

	q = words(query)
	filters = {"status": "Active"}
	if area:
		filters["area"] = area
	scored = []
	for r in frappe.get_all(DOCTYPE, filters=filters, fields=FIELDS + ["keywords"], limit=0):
		n = score(q, r.topic, f"{r.fact} {r.keywords or ''}")
		if n:
			scored.append((n, r))
	scored.sort(key=lambda x: -x[0])
	return [{**{k: r.get(k) for k in FIELDS}, "open": frappe.utils.get_url_to_form(DOCTYPE, r.name)} for _n, r in scored[:limit]]


def save(topic: str, fact: str, area: str = "Company", given_by: str = "SK", source: str | None = None,
		replaces: str | None = None, asked_again: bool = False) -> dict:
	topic, fact = (topic or "").strip()[:140], (fact or "").strip()
	if not topic or not fact:
		frappe.throw("topic and fact are both needed")
	same = frappe.db.get_value(DOCTYPE, {"topic": topic, "status": "Active"}, ["name", "fact"], as_dict=True)
	if asked_again and (same or replaces):
		name = replaces or same.name
		doc = frappe.get_doc(DOCTYPE, name)
		doc.times_asked_again = (doc.times_asked_again or 0) + 1
		doc.last_asked_again = now_datetime()
		doc.save(ignore_permissions=True)
		return {"name": doc.name, "asked_again": doc.times_asked_again, "open": frappe.utils.get_url_to_form(DOCTYPE, doc.name)}
	if same and not replaces and same.fact.strip() != fact:
		# SK 4-Nov input read-back: a new answer that differs from the one already saved is never swapped quietly
		return {"conflict": same.name, "saved_fact": same.fact, "new_fact": fact, "open": frappe.utils.get_url_to_form(DOCTYPE, same.name),
			"next": "Read both back to SK ('Understood: … expected result: …'). If SK confirms the new one, call again with replaces="
				+ same.name}
	old = replaces
	if old and frappe.db.get_value(DOCTYPE, old, "given_by") == "SK":
		from sk_app.core.people import is_ceo

		if not is_ceo(frappe.session.user):
			frappe.throw(f"{old} is SK's own rule; only SK / the CEO can change it. Ask SK, then save SK's answer.")
	if same and not old:
		return {"name": same.name, "unchanged": True, "open": frappe.utils.get_url_to_form(DOCTYPE, same.name)}
	doc = frappe.get_doc({"doctype": DOCTYPE, "topic": topic, "fact": fact, "area": area or "Company", "given_by": given_by or "SK",
		"given_on": nowdate(), "source": (source or "")[:140]}).insert(ignore_permissions=True)
	if asked_again:
		doc.db_set({"times_asked_again": 1, "last_asked_again": now_datetime()})
	if old:
		frappe.db.set_value(DOCTYPE, old, {"status": "Replaced", "replaced_by": doc.name})
	return {"name": doc.name, "replaced": old, "open": frappe.utils.get_url_to_form(DOCTYPE, doc.name)}


def asked_again_on(day) -> int:
	"""Scorecard: how many times on this day someone asked SK / staff something already given."""
	if not frappe.db.table_exists("SK Hub Log"):
		return 0
	return frappe.db.count("SK Hub Log", {"action": "asked again", "creation": ["between", [f"{day} 00:00:00", f"{day} 23:59:59.999999"]]})

