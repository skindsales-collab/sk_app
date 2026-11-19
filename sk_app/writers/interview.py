"""The one Interview writer (SK hiring, 17-Nov-2026): Round 1 on the tablet or by the WhatsApp bot (start, each answer,
finish), Claude's scoring into Interview Feedback, slot booking for Round 1 / Round 2, reminders. Claude never sets
Rejected; the band Hold leaves the feedback unsubmitted for Aarti."""

import json
import re

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, get_datetime, getdate, now_datetime, nowdate

from sk_app import hiring_rules as R

ROUND1, ROUND2 = "Round 1 - Tablet", "Round 2 - CEO"


def _applicant(name: str):
	return frappe.get_doc("Job Applicant", name)


def _open_round1(applicant: str) -> str | None:
	return frappe.db.get_value("Interview", {"job_applicant": applicant, "interview_type": ROUND1, "docstatus": ["<", 2], "status": ["!=", "Cancelled"]}, "name")


def ensure_round1(applicant: str, mode: str, language: str | None = None, when=None, time=None) -> str:
	"""The applicant's Round 1 Interview (one per candidate), Pending until it is finished."""
	name = _open_round1(applicant)
	a = _applicant(applicant)
	if name:
		doc = frappe.get_doc("Interview", name)
	else:
		doc = frappe.new_doc("Interview")
		doc.update({"interview_type": ROUND1, "job_applicant": applicant, "job_opening": a.job_title, "designation": a.designation, "status": "Pending"})
	doc.sk_mode = mode
	if language:
		doc.sk_language = language
	_interviewers(doc)
	doc.scheduled_on = getdate(when) if when else (doc.scheduled_on or nowdate())
	if time:
		doc.from_time = time
	doc.flags.ignore_permissions = True
	doc.flags.ignore_mandatory = True
	doc.save()
	return doc.name


def _interviewers(doc):
	"""HRMS lets only a listed interviewer write Interview Feedback: HR (Aarti), the CEO and the user Claude's scheduled run
	signs in as (SK App Settings 'hiring_feedback_user', else Administrator) are on every Round 1 / Round 2 Interview."""
	from sk_app.core.people import ceo_users
	from sk_app.hiring import hr_users

	have = {r.interviewer for r in doc.get("interview_details") or []}
	extra = frappe.get_cached_doc("SK App Settings").get("hiring_feedback_user") if frappe.db.exists("DocType", "SK App Settings") else None
	for u in list(hr_users()) + list(ceo_users()) + [extra or "Administrator"]:
		if u and u not in have and frappe.db.exists("User", u):
			doc.append("interview_details", {"interviewer": u})
			have.add(u)


def start(user: str, applicant: str, language: str, consent: bool, mode: str = "Tablet", adult: bool = True, spoken: str | None = None, consent_url: str | None = None) -> dict:
	"""Tablet (self-service, R10): the candidate picked the language, ticked 18+ and I agree, and said 'I agree' (recorded).
	Returns the question list, the consent text and the interviewer name for the screen."""
	from sk_app import hiring

	hiring._check(user)
	if not consent or not adult:
		frappe.throw(_("The candidate must tick 18 or older and I agree first"))
	a = _applicant(applicant)
	frappe.db.set_value("Job Applicant", applicant, {"sk_consent_on": now_datetime(), "sk_language": language}, update_modified=False)
	name = ensure_round1(applicant, mode, language)
	doc = frappe.get_doc("Interview", name)
	doc.add_comment("Comment", _("Consent {0}: ticked 18+ and I agree{1} ({2})").format(str(now_datetime())[:16], ", said: " + spoken[:80] if spoken else "", language))
	if consent_url and not frappe.db.exists("File", {"file_url": consent_url, "attached_to_doctype": "Interview", "attached_to_name": name}):
		frappe.get_doc({"doctype": "File", "file_url": consent_url, "file_name": "consent_i_agree.webm", "is_private": 1, "attached_to_doctype": "Interview", "attached_to_name": name}).insert(ignore_permissions=True)
	qs = hiring.questions(a.get("sk_family"))
	settings = frappe.get_cached_doc("SK App Settings")
	return {"interview": name, "questions": qs, "teach_back": hiring.teach_back(), "language": language, "family": a.get("sk_family"),
		"consent": R.CONSENT, "disclosure": R.DISCLOSURE, "interviewer": R.INTERVIEWER_NAME, "office_phone": settings.get("hr_office_phone"), "keep_days": R.VIDEO_KEEP_DAYS}


def purge_videos() -> int:
	"""Daily (R9.4): answer videos and voice files older than 7 days are deleted; the Interview gets 'video deleted on <date>'."""
	cutoff = add_days(nowdate(), -R.VIDEO_KEEP_DAYS)
	n = 0
	for f in frappe.get_all("File", filters={"attached_to_doctype": "Interview", "creation": ["<", cutoff], "file_name": ["like", "%.webm"]}, fields=["name", "attached_to_name"], limit=500):
		frappe.delete_doc("File", f.name, ignore_permissions=True, force=True)
		n += 1
		try:
			iv = frappe.get_doc("Interview", f.attached_to_name)
			answers = json.loads(iv.get("sk_answers") or "[]")
			for a in answers:
				for k in ("video", "voice"):
					if a.get(k):
						a[k] = None
			frappe.db.set_value("Interview", iv.name, "sk_answers", json.dumps(answers, ensure_ascii=False), update_modified=False)
			iv.add_comment("Comment", _("video deleted on {0} (kept {1} days)").format(nowdate(), R.VIDEO_KEEP_DAYS))
		except Exception:
			frappe.log_error("SK hiring purge note")
	return n


def save_answer(interview: str, code: str, text: str | None, voice_url: str | None = None, photo_url: str | None = None, language: str | None = None,
		steps_right: int | None = None, video_url: str | None = None, measures: dict | None = None) -> dict:
	"""One answer onto the interview: the text from speech, the voice / video file (private, deleted after 7 days), the
	practical-test photo, and the speech measures (start delay, length, pace, pauses: information only, never a score)."""
	doc = frappe.get_doc("Interview", interview)
	answers = json.loads(doc.get("sk_answers") or "[]")
	answers = [x for x in answers if x.get("code") != code]
	row = {"code": code, "text": (text or "").strip()[:4000], "voice": voice_url, "video": video_url, "photo": photo_url, "language": language or doc.get("sk_language"), "at": str(now_datetime())[:19]}
	if steps_right is not None:
		row["steps_right"] = cint(steps_right)
	if measures:
		m = measures if isinstance(measures, dict) else json.loads(measures)
		row.update(R.speech_measures(len((text or "").split()), m.get("start_delay_s"), m.get("duration_s"), m.get("long_pauses")))
	answers.append(row)
	frappe.db.set_value("Interview", interview, {"sk_answers": json.dumps(answers, ensure_ascii=False), "status": "Under Review"}, update_modified=False)
	for url in (voice_url, photo_url, video_url):
		if url and not frappe.db.exists("File", {"file_url": url, "attached_to_doctype": "Interview", "attached_to_name": interview}):
			src = frappe.db.get_value("File", {"file_url": url}, ["file_name", "is_private"], as_dict=True)
			if src:
				frappe.get_doc({"doctype": "File", "file_url": url, "file_name": src.file_name, "is_private": 1, "attached_to_doctype": "Interview", "attached_to_name": interview}).insert(ignore_permissions=True)
	return {"saved": code, "answers": len(answers)}


LANG_CODE = {"Marathi": "mr", "Hindi": "hi", "English": "en"}


def answers_json(answers: list[dict]) -> str:
	"""The handshake text (R7, free mode): 'ANSWERS_JSON: [{code, lang, answer}]' in interview_summary; the scheduled Claude
	run reads it, writes the Interview Feedback draft and the 'Claude Round 1:' comment."""
	rows = [{"code": x.get("code"), "lang": LANG_CODE.get(x.get("language") or "", "mr"), "answer": x.get("text") or ("(voice only, not transcribed)" if x.get("voice") else "(no answer)")}
		for x in answers]
	for x, r in zip(answers, rows):
		if x.get("steps_right") is not None:
			r["steps_right"] = x["steps_right"]
		for k in ("photo", "video", "start_delay_s", "duration_s", "wpm", "long_pauses"):
			if x.get(k) is not None:
				r[k] = x[k]
	return "ANSWERS_JSON: " + json.dumps(rows, ensure_ascii=False)


def finish(user: str | None, interview: str, note: str | None = None) -> dict:
	"""Aarti taps Finish (or the bot's last answer came): the answers go onto the Interview as ANSWERS_JSON and the status
	turns Under Review; Claude's scheduled run (9:47, 13:47, 17:47 IST, Mon-Sat) scores it. No API key is used."""
	doc = frappe.get_doc("Interview", interview)
	answers = json.loads(doc.get("sk_answers") or "[]")
	frappe.db.set_value("Interview", interview, {"status": "Under Review", "sk_finished_on": now_datetime(), "interview_summary": answers_json(answers)}, update_modified=False)
	if note:
		doc.add_comment("Comment", _("HR note: {0}").format(note))
	return {"interview": interview, "answers": len(answers), "scored": False, "band": None, "note": "answers sent; Claude scores at 9:47, 13:47 or 17:47"}


# ---------- scores, as Claude's scheduled run leaves them (R7): Interview Feedback draft + 'Claude Round 1:' comment ----------

def scores_of(interview: str) -> dict | None:
	"""Read back what the scheduled Claude run wrote: the 5 skill ratings (stored score/5), the feedback text and the band."""
	fb = frappe.get_all("Interview Feedback", filters={"interview": interview, "docstatus": ["<", 2]}, fields=["name", "feedback", "result", "average_rating"],
		order_by="modified desc", limit=1)
	if not fb:
		return None
	traits = []
	for row in frappe.get_all("Skill Assessment", filters={"parent": fb[0].name, "parenttype": "Interview Feedback"}, fields=["skill", "rating"]):
		traits.append({"skill": row.skill, "score": int(round(flt(row.rating) * 5)) or None, "evidence": "", "note": ""})
	overall = R.overall([{"skill": t["skill"], "score": t["score"], "evidence": "x"} for t in traits if t["score"]])
	return {"traits": traits, "overall": overall, "band": R.band(overall), "feedback": fb[0].feedback or "", "result": fb[0].result, "name": fb[0].name}


# ---------- slots (R5 item 11) ----------

def book(user: str | None, applicant: str, round_type: str, date, time, mode: str = "Tablet") -> dict:
	"""A Round 1 or Round 2 slot for the candidate. Round 2 waits until the applicant is Shortlisted."""
	a = _applicant(applicant)
	if round_type == ROUND2 and a.status not in (R.STATUS_SHORTLISTED, R.STATUS_SELECTED, R.STATUS_HOLD):
		frappe.throw(_("Round 2 is booked after HR sends the candidate to SK"))
	if round_type == ROUND1:
		name = ensure_round1(applicant, mode, a.get("sk_language"), date, time)
	else:
		name = frappe.db.get_value("Interview", {"job_applicant": applicant, "interview_type": ROUND2, "docstatus": ["<", 2], "status": ["!=", "Cancelled"]}, "name")
		doc = frappe.get_doc("Interview", name) if name else frappe.new_doc("Interview")
		if not name:
			doc.update({"interview_type": ROUND2, "job_applicant": applicant, "job_opening": a.job_title, "designation": a.designation, "status": "Pending"})
		doc.scheduled_on, doc.from_time = getdate(date), time
		minutes = int(frappe.get_cached_doc("SK App Settings").get("hr_slot_minutes") or 30)
		h, m = [int(x) for x in str(time)[:5].split(":")]
		doc.to_time = f"{(h * 60 + m + minutes) // 60 % 24:02d}:{(h * 60 + m + minutes) % 60:02d}:00"
		_interviewers(doc)
		doc.flags.ignore_permissions = True
		doc.flags.ignore_mandatory = True
		doc.save()
		name = doc.name
	key = "W3" if round_type == ROUND1 else "W5"
	from sk_app.writers.applicant import message_for

	return {"interview": name, "date": str(date), "time": time, "message": message_for(applicant, key, date=frappe.utils.formatdate(date, "dd-MMM"), time=time)}


SLOT = re.compile(r"^\s*slot\s*:\s*(\d{1,2}[-/ ][A-Za-z]{3}(?:[-/ ]\d{2,4})?|\d{4}-\d{2}-\d{2})\s+(\d{1,2}:\d{2})", re.I)


def on_comment(doc, method=None):
	"""R12 (SK 17-Nov): the HR owner writes 'Slot: 18-Nov 10:30' as a comment on the Job Applicant and the Round 1 Interview
	draft is made for that slot (tablet). The ready WhatsApp text is added as a reply comment with the wa.me link."""
	if doc.get("reference_doctype") != "Job Applicant" or doc.get("comment_type") != "Comment" or not doc.get("reference_name"):
		return
	m = SLOT.match(frappe.utils.strip_html(doc.get("content") or ""))
	if not m:
		return
	from frappe.utils import getdate

	day = m.group(1)
	if not re.match(r"\d{4}-\d{2}-\d{2}", day):
		parts = re.split(r"[-/ ]", day)
		if len(parts) == 2:
			parts.append(str(getdate(nowdate()).year))
		day = f"{parts[2] if len(parts[2]) == 4 else '20' + parts[2]}-{frappe.utils.formatdate(frappe.utils.getdate(parts[0] + ' ' + parts[1] + ' ' + (parts[2] if len(parts[2]) == 4 else '20' + parts[2])), 'MM')}-{int(parts[0]):02d}"
	try:
		out = book(doc.owner, doc.reference_name, ROUND1, getdate(day), m.group(2) + ":00", "Tablet")
	except Exception:
		frappe.log_error(f"SK hiring slot comment {doc.reference_name}")
		return
	frappe.get_doc("Job Applicant", doc.reference_name).add_comment("Comment", f"Round 1 booked {out['date']} {out['time']} ({out['interview']}). "
		f"Send by WhatsApp: <a href='{out['message']['wa_link']}' target='_blank'>open chat</a>")


def send_reminders() -> int:
	"""The day before an interview: W4 by the bot (when on), else a ToDo line for HR."""
	return _reminders()


def _reminders() -> int:
	from sk_app import hiring_bot

	tomorrow = add_days(nowdate(), 1)
	n = 0
	for iv in frappe.get_all("Interview", filters={"scheduled_on": tomorrow, "docstatus": ["<", 2], "status": "Pending", "reminded": 0}, fields=["name", "job_applicant", "from_time"], limit=0):
		if hiring_bot.remind(iv.job_applicant, str(iv.from_time or "")[:5]):
			frappe.db.set_value("Interview", iv.name, "reminded", 1, update_modified=False)
			n += 1
	return n


# ---------- SK's Round 2 on the tablet (R8, SK 17-Nov) ----------

def round2_start(user: str, applicant: str) -> dict:
	"""CEO only: the Round 2 Interview (today if none booked), the question list (Claude's 3 + 5 standard) and the Round 1 evidence."""
	from sk_app import hiring
	from sk_app.core.people import is_ceo
	from sk_app.writers.applicant import claude_notes

	if not is_ceo(user):
		frappe.throw(_("Round 2 on the tablet is the CEO's screen"), frappe.PermissionError)
	a = _applicant(applicant)
	name = frappe.db.get_value("Interview", {"job_applicant": applicant, "interview_type": ROUND2, "docstatus": ["<", 2], "status": ["!=", "Cancelled"]}, "name")
	if not name:
		name = book(user, applicant, ROUND2, nowdate(), str(now_datetime())[11:16], "Tablet")["interview"]
	r1 = _open_round1(applicant)
	scores = scores_of(r1) if r1 else None
	notes = claude_notes(applicant)
	claude_q = []
	for n in notes:
		claude_q = R.claude_questions_from(n["text"])
		if claude_q:
			break
	if not claude_q and scores:
		claude_q = R.claude_questions_from(scores.get("feedback"))
	done = json.loads(frappe.db.get_value("Interview", name, "sk_answers") or "[]")
	r1_answers = json.loads(frappe.db.get_value("Interview", r1, "sk_answers") or "[]") if r1 else []
	return {"interview": name, "questions": R.r2_questions(claude_q), "tags": R.R2_TAGS, "tags_mr": R.R2_TAGS_MR, "round1": scores, "claude_notes": notes,
		"round1_answers": r1_answers, "speech": R.speech_line(r1_answers),
		"answers": done, "applicant_name": a.applicant_name, "job": frappe.db.get_value("Job Opening", a.job_title, "job_title") if a.job_title else (a.designation or "")}


def round2_save(user: str, interview: str, entry: dict) -> dict:
	"""One question's taps: q, quality, confidence, attitude, flexibility (1-5), tags, note, voice."""
	from sk_app.core.people import is_ceo

	if not is_ceo(user):
		frappe.throw(_("Round 2 on the tablet is the CEO's screen"), frappe.PermissionError)
	doc = frappe.get_doc("Interview", interview)
	rows = json.loads(doc.get("sk_answers") or "[]")
	rows = [r for r in rows if r.get("q") != entry.get("q")]
	clean = {"q": str(entry.get("q") or "")[:500], "tags": [t for t in (entry.get("tags") or []) if t in R.R2_TAGS], "note": str(entry.get("note") or "")[:2000], "voice": entry.get("voice"),
		"at": str(now_datetime())[:19]}
	for k in R.R2_RATINGS:
		v = entry.get(k)
		clean[k] = min(5, max(1, cint(v))) if v not in (None, "", 0) else None
	rows.append(clean)
	frappe.db.set_value("Interview", interview, {"sk_answers": json.dumps(rows, ensure_ascii=False), "status": "Under Review", "sk_mode": "Tablet"}, update_modified=False)
	if clean["voice"] and not frappe.db.exists("File", {"file_url": clean["voice"], "attached_to_doctype": "Interview", "attached_to_name": interview}):
		src = frappe.db.get_value("File", {"file_url": clean["voice"]}, ["file_name"], as_dict=True)
		if src:
			frappe.get_doc({"doctype": "File", "file_url": clean["voice"], "file_name": src.file_name, "is_private": 1, "attached_to_doctype": "Interview", "attached_to_name": interview}).insert(ignore_permissions=True)
	return {"saved": len(rows)}


def round2_finish(user: str, interview: str, feel, decision: str, note: str | None = None, voice: str | None = None) -> dict:
	"""SK's end screen: overall feel 1-5 and Selected / Hold / Not selected (his decision is final). Saves R2_JSON on the
	Interview, an Interview Feedback with SK as interviewer, and applies the decision (W5-W7 message ready)."""
	from sk_app.core.people import is_ceo
	from sk_app.writers import applicant as aw

	if not is_ceo(user):
		frappe.throw(_("Round 2 on the tablet is the CEO's screen"), frappe.PermissionError)
	doc = frappe.get_doc("Interview", interview)
	rows = json.loads(doc.get("sk_answers") or "[]")
	feel = cint(feel) or None
	payload = {"feel": feel, "decision": decision, "note": (note or "")[:2000], "voice": voice, "r2_average": R.r2_average(rows), "answers": rows}
	r1 = _open_round1(doc.job_applicant)
	r1_scores = scores_of(r1) if r1 else None
	payload["combined"] = R.combined(r1_scores and r1_scores.get("overall"), payload["r2_average"])
	frappe.db.set_value("Interview", interview, {"interview_summary": "R2_JSON: " + json.dumps(payload, ensure_ascii=False), "status": "Under Review", "sk_finished_on": now_datetime(),
		"average_rating": (payload["r2_average"] or 0) / 5}, update_modified=False)
	existing = frappe.db.get_value("Interview Feedback", {"interview": interview, "docstatus": 0}, "name")
	fb = frappe.get_doc("Interview Feedback", existing) if existing else frappe.new_doc("Interview Feedback")
	fb.update({"interview": interview, "interview_type": ROUND2, "job_applicant": doc.job_applicant, "interviewer": user,
		"feedback": f"SK Round 2: feel {feel or '-'} / 5 · taps average {payload['r2_average'] or '-'} · combined {payload['combined'] or '-'} · {decision}" + (f"\n{note}" if note else "")})
	fb.set("skill_assessment", [])
	r1_learning = next((t["score"] for t in (r1_scores or {}).get("traits", []) if t["skill"] == "Learning Ability"), None)
	for t in R.r2_feedback_scores(rows, r1_learning):
		if t.get("score"):
			fb.append("skill_assessment", {"skill": t["skill"], "rating": t["score"] / 5})
	# checker 17-Nov: Cleared = Selected, Rejected = Not selected, set and submitted only by SK's tap; Hold = no result,
	# the Interview stays Under Review and the Job Applicant goes to Hold
	fb.result = {"selected": "Cleared", "not_selected": "Rejected"}.get(decision)
	fb.flags.ignore_permissions = True
	fb.flags.ignore_mandatory = True
	fb.save()
	if fb.result:
		fb.submit()
		frappe.db.set_value("Interview", interview, "status", fb.result, update_modified=False)
	out = aw.decide(user, doc.job_applicant, decision, note)
	key = {"selected": "W9", "hold": "W6b", "not_selected": "W7"}[decision]
	out["message"] = aw.message_for(doc.job_applicant, key)
	return {"interview": interview, "combined": payload["combined"], "r2_average": payload["r2_average"], **out}
