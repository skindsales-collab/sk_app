"""The WhatsApp hiring bot engine (Rev 1, R5 items 8-11): one incoming message -> bot_rules.step -> replies + ERPNext
effects (applicant, resume, interview answers, slot booking, hand-over to HR). Transport: whatsapp.py (Meta Cloud API)
or the test console (rebuild test, 10 dummy candidates). State per candidate lives on the Job Applicant (sk_bot_state,
sk_bot_data), so a chat can pause and continue within 48 hours."""

import json

import frappe
from frappe.utils import now_datetime

from sk_app import bot_rules as B

ROUND1 = "Round 1 - Tablet"


def _applicant_for(mobile: str) -> str:
	from sk_app.writers import applicant as aw

	name = aw.find_by_mobile(mobile)
	if name:
		return name
	return aw.write(None, {"mobile": mobile}, source="WhatsApp", note="WhatsApp bot").name


def _ctx(applicant: str) -> dict:
	from sk_app import hiring

	a = frappe.db.get_value("Job Applicant", applicant, ["applicant_name", "sk_family", "job_title"], as_dict=True)
	settings = frappe.get_cached_doc("SK App Settings")
	jobs = frappe.get_all("Job Opening", filters={"status": "Open"}, fields=["name", "job_title"], order_by="job_title asc", limit=12)
	return {"name": None if (a.applicant_name or "").startswith("Candidate ") else a.applicant_name, "jobs": [j.job_title for j in jobs], "job_names": {j.job_title: j.name for j in jobs},
		"questions": hiring.questions(a.sk_family), "teach_back": hiring.teach_back(), "slots": hiring.slots(None), "address": settings.get("hr_office_address")}


def handle(mobile: str, incoming: dict, send) -> list[str]:
	"""One message from a candidate. send(mobile, text) delivers each reply. Returns the replies (for the console / test)."""
	from sk_app.writers import applicant as aw
	from sk_app.writers import interview as iw

	applicant = _applicant_for(mobile)
	a = frappe.get_doc("Job Applicant", applicant)
	state, data = a.get("sk_bot_state") or None, json.loads(a.get("sk_bot_data") or "{}")
	ctx = _ctx(applicant)
	replies, state, data, effects = B.step(state, data, incoming, ctx)
	for e in effects:
		kind = e["kind"]
		if kind == "consent":
			frappe.db.set_value("Job Applicant", applicant, {"sk_consent_on": now_datetime(), "sk_language": data.get("language")}, update_modified=False)
		elif kind == "resume":
			aw.attach(applicant, e["url"])
			aw.write(None, {"mobile": mobile, "language": data.get("language"), "consent": True}, source="WhatsApp")
			frappe.enqueue("sk_app.writers.applicant.read_resume", name=applicant, queue="short", enqueue_after_commit=True)
		elif kind == "applicant":
			d = e["data"]
			aw.write(None, {"mobile": mobile, "applicant_name": d.get("name"), "job": ctx["job_names"].get(d.get("job")), "experience": d.get("experience"),
				"city": d.get("city"), "last_employer": d.get("last_employer"), "language": d.get("language"), "consent": True}, source="WhatsApp")
			ctx = _ctx(applicant)
		elif kind == "hand_to_hr":
			aw.hand_to_hr(applicant, e.get("why") or "candidate asked for HR")
		elif kind == "delete":
			aw.delete_request(applicant)
	frappe.db.set_value("Job Applicant", applicant, {"sk_bot_state": state, "sk_bot_data": json.dumps(data, ensure_ascii=False), "sk_last_message_on": now_datetime()}, update_modified=False)
	_log(applicant, "in", incoming.get("text") or incoming.get("transcript") or (incoming.get("media") or {}).get("kind") or "")
	for r in replies:
		send(mobile, r, applicant) if send is _send_free else send(mobile, r)
		_log(applicant, "out", r)
	return replies


def _send_free(mobile: str, text: str, applicant: str | None = None) -> bool:
	from sk_app import whatsapp

	return whatsapp.send_text(mobile, text, applicant)


def _transcribe(media: dict, language: str | None) -> str | None:
	from sk_app import speech

	try:
		content = media.get("content")
		if not content and media.get("url"):
			f = frappe.get_doc("File", {"file_url": media["url"]})
			content = f.get_content()
		return speech.transcribe(content, language, media.get("media_type") or "audio/ogg") if content else None
	except Exception:
		frappe.log_error("SK hiring bot transcript")
		return None


def _log(applicant: str, direction: str, text: str):
	"""Every bot line as a comment on the Job Applicant (HR reads the chat in ERPNext; 6-month clean-up removes it with the row's files)."""
	try:
		frappe.get_doc("Job Applicant", applicant).add_comment("Comment", ("📥 " if direction == "in" else "🤖 ") + (text or "")[:1000])
	except Exception:
		pass


def push(applicant: str, key: str, **values) -> dict:
	"""R11 (free only): a message the company starts (W0, W4, W5, W6, W7, W9) is never sent by the bot. The HR owner gets a
	'Send by WhatsApp' link (wa.me) and a ToDo with it."""
	from sk_app.hiring import hr_users
	from sk_app.writers.applicant import message_for

	m = message_for(applicant, key, **values)
	for u in hr_users():
		frappe.get_doc({"doctype": "ToDo", "allocated_to": u, "reference_type": "Job Applicant", "reference_name": applicant, "priority": "Medium", "date": frappe.utils.nowdate(),
			"description": f"Send by WhatsApp ({key}): <a href='{m['wa_link']}' target='_blank'>open chat</a><br>{frappe.utils.escape_html(m['text'][:300])}"}).insert(ignore_permissions=True)
	return m


def remind(applicant: str, time: str) -> bool:
	"""Reminder the day before (W4): a wa.me link to the HR owner, never a template (R11)."""
	push(applicant, "W4", time=time)
	return True


def offer_round2(applicant: str, send=None) -> list[str]:
	"""R13: no slots by bot. After Send to SK the HR owner gets the Round 2 call (W5) as a 'Send by WhatsApp' link."""
	push(applicant, "W5", date="", time="")
	return []
