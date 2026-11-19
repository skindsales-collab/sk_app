"""SK App hiring (SK 17-Nov-2026, spec SKIT/HR/HIRE/001 Rev 0 + Rev 1 bot): ERPNext setup and the reading screens.

WhatsApp (bot) or the HR tablet is only the front door. Every candidate is an ERPNext Job Applicant, Round 1 and Round 2
are Interviews, scores sit in Interview Feedback. Writers: writers/applicant.py (candidate, status taps, WorkIndia
upload), writers/interview.py (tablet / bot answers, Claude scoring, slots). Bot engine: hiring_bot.py. No salary is
read or shown anywhere; Claude never sets Rejected (Aarti or SK decides)."""

import json
import os

import frappe
from frappe import _
from frappe.utils import add_days, date_diff, flt, getdate, now_datetime, nowdate

from sk_app import hiring_rules as R

SOURCES = ("WhatsApp", "WorkIndia", "Walk In")
ROUND1, ROUND2 = "Round 1 - Tablet", "Round 2 - CEO"
APPLICANT_FIELDS = [
	{"fieldname": "sk_hiring_section", "fieldtype": "Section Break", "label": "SK App hiring", "insert_after": "notes"},
	{"fieldname": "sk_family", "fieldtype": "Select", "label": "Role family", "options": "\nS\nM\nD\nF\nT\nP\nA\nH\nE", "in_list_view": 1},
	{"fieldname": "sk_city", "fieldtype": "Data", "label": "City"},
	{"fieldname": "sk_experience_years", "fieldtype": "Float", "label": "Experience (years)"},
	{"fieldname": "sk_last_employer", "fieldtype": "Data", "label": "Last employer"},
	{"fieldname": "sk_fit", "fieldtype": "Select", "label": "Resume fit (Claude)", "options": "\nGood\nPartial\nNot matching"},
	{"fieldname": "sk_fit_reason", "fieldtype": "Small Text", "label": "Fit reason"},
	{"fieldname": "sk_claims", "fieldtype": "Small Text", "label": "Claims to verify (JSON)"},
	{"fieldname": "sk_resume_text", "fieldtype": "Long Text", "label": "Resume text (OCR)"},
	{"fieldname": "sk_col_1", "fieldtype": "Column Break"},
	{"fieldname": "sk_language", "fieldtype": "Select", "label": "Language", "options": "\nMarathi\nHindi\nEnglish"},
	{"fieldname": "sk_consent_on", "fieldtype": "Datetime", "label": "Consent given on"},
	{"fieldname": "sk_bot_state", "fieldtype": "Data", "label": "Bot state"},
	{"fieldname": "sk_bot_data", "fieldtype": "Long Text", "label": "Bot data (JSON)"},
	{"fieldname": "sk_last_message_on", "fieldtype": "Datetime", "label": "Last candidate message"},
	{"fieldname": "sk_handed_to_hr", "fieldtype": "Check", "label": "Handed to HR", "default": "0"},
	{"fieldname": "sk_sk_seen_on", "fieldtype": "Datetime", "label": "Seen by CEO on"},
	{"fieldname": "sk_workindia_id", "fieldtype": "Data", "label": "WorkIndia id"},
]
INTERVIEW_FIELDS = [
	{"fieldname": "sk_hiring_section", "fieldtype": "Section Break", "label": "SK App Round 1", "insert_after": "interview_summary"},
	{"fieldname": "sk_mode", "fieldtype": "Select", "label": "Mode", "options": "\nTablet\nWhatsApp", "in_list_view": 1},
	{"fieldname": "sk_language", "fieldtype": "Select", "label": "Language", "options": "\nMarathi\nHindi\nEnglish"},
	{"fieldname": "sk_answers", "fieldtype": "Long Text", "label": "Answers (JSON)"},
	{"fieldname": "sk_scores", "fieldtype": "Long Text", "label": "Claude scores (JSON)"},
	{"fieldname": "sk_summary", "fieldtype": "Text", "label": "Summary for SK"},
	{"fieldname": "sk_finished_on", "fieldtype": "Datetime", "label": "Finished on"},
]
SETTINGS_FIELDS = [
	{"fieldname": "hiring_section", "fieldtype": "Section Break", "label": "Hiring (WhatsApp bot)", "insert_after": "lead_owner_noncabin"},
	{"fieldname": "hr_office_address", "fieldtype": "Small Text", "label": "Office address for interview messages"},
	{"fieldname": "hr_whatsapp_number", "fieldtype": "Data", "label": "HR WhatsApp number (shown to candidates)"},
	{"fieldname": "hr_apply_link", "fieldtype": "Data", "label": "Apply page link (no salary fields)", "default": "/sk-apply/new"},
	{"fieldname": "hr_office_phone", "fieldtype": "Data", "label": "Office phone (Call office button on the tablet)"},
	{"fieldname": "whatsapp_month", "fieldtype": "Data", "label": "WhatsApp free replies: month", "read_only": 1},
	{"fieldname": "whatsapp_month_count", "fieldtype": "Int", "label": "WhatsApp free replies sent this month", "read_only": 1, "description": "The bot stops at 950 (1,000 free per month); then reply by hand in the Business app."},
	{"fieldname": "hiring_feedback_user", "fieldtype": "Link", "options": "User", "label": "User of Claude's scheduled scoring run", "description": "Listed as interviewer on every Interview so its Interview Feedback is accepted."},
	{"fieldname": "whatsapp_phone_id", "fieldtype": "Data", "label": "WhatsApp Cloud API phone number id"},
	{"fieldname": "whatsapp_bot_on", "fieldtype": "Check", "label": "WhatsApp bot on", "default": "0", "description": "The token and verify token live in site_config (whatsapp_token, whatsapp_verify_token), never here."},
	{"fieldname": "hiring_col", "fieldtype": "Column Break"},
	{"fieldname": "stt_provider", "fieldtype": "Select", "label": "Voice to text", "options": "None\nWhisper\nBhashini\nGoogle", "default": "None", "description": "Keys live in site_config (bhashini_key / google_stt_key)."},
	{"fieldname": "hr_slot_minutes", "fieldtype": "Int", "label": "Interview slot length (minutes)", "default": "30"},
]


# ---------- setup (idempotent, runs at migrate) ----------

def ensure_setup():
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	if not frappe.db.exists("DocType", "Job Applicant"):
		return
	for name in SOURCES:
		if not frappe.db.exists("Job Applicant Source", name):
			frappe.get_doc({"doctype": "Job Applicant Source", "source_name": name}).insert(ignore_permissions=True)
	for skill in R.SKILLS:
		if not frappe.db.exists("Skill", skill):
			frappe.get_doc({"doctype": "Skill", "skill_name": skill}).insert(ignore_permissions=True)
	for name, desc in ((ROUND1, "SK App Round 1 (tablet or WhatsApp bot): 6 common + 6 role questions, scored by Claude, Aarti decides"),
			(ROUND2, "SK's Round 2 in person")):
		if frappe.db.exists("DocType", "Interview Type") and not frappe.db.exists("Interview Type", name):
			doc = frappe.get_doc({"doctype": "Interview Type", "interview_type_name": name, "description": desc, "expected_average_rating": 0.6})
			for skill in R.SKILLS:
				doc.append("expected_skill_set", {"skill": skill})
			doc.insert(ignore_permissions=True)
	create_custom_fields({"Job Applicant": APPLICANT_FIELDS, "Interview": INTERVIEW_FIELDS}, update=True)
	if frappe.db.exists("DocType", "SK App Settings"):
		create_custom_fields({"SK App Settings": SETTINGS_FIELDS}, update=True)
	load_questions()


def load_questions(replace: bool = False) -> int:
	"""The 60 questions of SK_Interview_Question_Bank_17Nov2026.json into SK Interview Question (HR edits them there)."""
	if not frappe.db.table_exists("SK Interview Question"):
		return 0
	path = os.path.join(os.path.dirname(__file__), "data", "interview_questions.json")
	bank = json.load(open(path, encoding="utf-8"))
	n = 0
	for i, q in enumerate(bank["questions"], 1):
		is_test = q["code"].endswith("T")
		trait = {"Learning": "Learning", "Learning (teach-back)": "Learning"}.get(q.get("trait"), q.get("trait"))
		if trait not in ("Background", "Flexibility", "Attitude", "Learning", "Reliability", "Role Skill", "Communication"):
			trait = "Role Skill"
		values = {"family": q["family"], "trait": trait, "seq": i, "is_test": int(is_test), "look_for": q.get("look_for"), "en": q["en"], "mr": q.get("mr"), "hi": q.get("hi"), "active": 1}
		if frappe.db.exists("SK Interview Question", q["code"]):
			if replace:
				frappe.db.set_value("SK Interview Question", q["code"], values, update_modified=False)
			continue
		frappe.get_doc({"doctype": "SK Interview Question", "code": q["code"], **values}).insert(ignore_permissions=True)
		n += 1
	return n


def bank() -> dict:
	path = os.path.join(os.path.dirname(__file__), "data", "interview_questions.json")
	return json.load(open(path, encoding="utf-8"))


def designation_family() -> dict:
	return bank().get("designation_family") or {}


def questions(family: str | None) -> list[dict]:
	rows = frappe.get_all("SK Interview Question", filters={"active": 1}, fields=["code", "family", "trait", "seq", "is_test", "look_for", "en", "mr", "hi"], limit=0) \
		if frappe.db.table_exists("SK Interview Question") else []
	return R.questions_for(family, [dict(r) for r in rows])


def teach_back() -> dict:
	return bank().get("teach_back") or {}


# ---------- who ----------

def whatsapp_month_count() -> int:
	from sk_app import whatsapp

	return whatsapp.month_count()


def hr_users() -> list[str]:
	"""The HR owners = the enabled logins with the HR function (SK 17-Nov: no separate HR person; SK and Samir carry the
	HR function in SK App User), never a name in code."""
	from sk_app.core.people import users_with_function

	return [u for u in users_with_function("HR") if u != "Administrator" and frappe.db.exists("SK App User", {"user": u, "enabled": 1})]


def hr_user() -> str | None:
	"""Who signs Round 1 feedback and gets the HR ToDos: the settings' feedback user (SK), else the first HR owner, else the CEO."""
	from sk_app.core.people import ceo_users

	fixed = frappe.get_cached_doc("SK App Settings").get("hiring_feedback_user") if frappe.db.exists("DocType", "SK App Settings") else None
	if fixed and frappe.db.exists("User", fixed):
		return fixed
	users = hr_users() or [u for u in ceo_users() if u != "Administrator"]
	return users[0] if users else None


def is_hr(user: str) -> bool:
	from sk_app.core.people import is_ceo

	return user in hr_users() or is_ceo(user)


def _check(user: str):
	if not is_hr(user):
		frappe.throw(_("Only HR or the CEO opens hiring"), frappe.PermissionError)


# ---------- reads ----------

def _applicant_row(a) -> dict:
	return {"name": a.name, "applicant_name": a.applicant_name, "mobile": a.phone_number, "job": a.job_title, "designation": a.designation,
		"status": a.status, "source": a.source, "family": a.get("sk_family"), "city": a.get("sk_city"), "fit": a.get("sk_fit"),
		"fit_reason": a.get("sk_fit_reason"), "rating": flt(a.get("applicant_rating")) * 5 if a.get("applicant_rating") else None,
		"applied": str(a.creation)[:10], "days": date_diff(nowdate(), getdate(a.creation)), "handed": bool(a.get("sk_handed_to_hr")),
		"bot_state": a.get("sk_bot_state"), "language": a.get("sk_language"), "link": f"/app/job-applicant/{a.name}"}


_A_FIELDS = ["name", "applicant_name", "phone_number", "job_title", "designation", "status", "source", "sk_family", "sk_city", "sk_fit", "sk_fit_reason",
	"applicant_rating", "creation", "sk_handed_to_hr", "sk_bot_state", "sk_language", "sk_sk_seen_on", "sk_last_message_on"]


def home(user: str) -> dict:
	"""HR's Hiring screen: new candidates, today's interviews, waiting for SK, jobs open."""
	_check(user)
	today = nowdate()
	new = [_applicant_row(a) for a in frappe.get_all("Job Applicant", filters={"status": ["in", ["Open", "Replied"]]}, fields=_A_FIELDS, order_by="creation desc", limit=0)]
	ivs = frappe.get_all("Interview", filters={"scheduled_on": today, "status": ["in", ["Pending", "Under Review"]], "docstatus": ["<", 2]},
		fields=["name", "job_applicant", "interview_type", "from_time", "status", "sk_mode"], order_by="from_time asc", limit=0)
	names = {a.name: a for a in frappe.get_all("Job Applicant", filters={"name": ["in", [i.job_applicant for i in ivs] or [""]]}, fields=_A_FIELDS)}
	todays = [{"interview": i.name, "applicant": i.job_applicant, "applicant_name": names[i.job_applicant].applicant_name if i.job_applicant in names else i.job_applicant,
		"job": names[i.job_applicant].job_title if i.job_applicant in names else None, "round": i.interview_type, "time": str(i.from_time or "")[:5], "status": i.status,
		"mode": i.sk_mode} for i in ivs]
	waiting = [_applicant_row(a) for a in frappe.get_all("Job Applicant", filters={"status": "Shortlisted"}, fields=_A_FIELDS, order_by="modified desc", limit=0)]
	handed = [_applicant_row(a) for a in frappe.get_all("Job Applicant", filters={"sk_handed_to_hr": 1, "status": ["not in", ["Accepted", "Rejected"]]}, fields=_A_FIELDS, limit=0)]
	jobs = frappe.get_all("Job Opening", filters={"status": "Open"}, fields=["name", "job_title", "designation"], order_by="job_title asc", limit=0)
	settings = frappe.get_cached_doc("SK App Settings")
	apply = settings.get("hr_apply_link") or "/sk-apply/new"
	for j in jobs:
		j["apply_link"] = f"{apply}?job_title={j.name}"  # the web form has no job pick: the link carries the opening
	return {"new": new, "today": todays, "waiting": waiting, "handed": handed, "jobs": [dict(j) for j in jobs], "office_phone": settings.get("hr_office_phone"),
		"bot_on": bool(settings.get("whatsapp_bot_on")), "hr_number": settings.get("hr_whatsapp_number"), "today_date": today,
		"apply_link": settings.get("hr_apply_link") or "/sk-apply/new",
		"free_replies": {"sent": whatsapp_month_count(), "cap": R.FREE_REPLIES_PER_MONTH},
		"families": R.FAMILIES, "families_mr": R.FAMILIES_MR, "slots": slots(user)}


def badges(user: str, functions: list[str]) -> dict:
	out = {}
	if "HR" in functions and frappe.db.exists("DocType", "Job Applicant"):
		n = frappe.db.count("Job Applicant", {"status": ["in", ["Open", "Replied"]]}) + frappe.db.count("Job Applicant", {"sk_handed_to_hr": 1, "status": ["not in", ["Accepted", "Rejected"]]})
		if n:
			out["hiring"] = {"n": n, "c": "amber"}
	if "Management" in functions and frappe.db.exists("DocType", "Job Applicant"):
		n = frappe.db.count("Job Applicant", {"status": "Shortlisted"})
		if n:
			out["round2"] = {"n": n, "c": "red"}
	return out


def candidate(user: str, name: str) -> dict:
	"""One candidate: resume fit, Round 1 answers, Claude summary, Round 2 slot, actions by role."""
	_check(user)
	from sk_app.core.people import is_ceo

	a = frappe.get_doc("Job Applicant", name)
	row = _applicant_row(a)
	ivs = frappe.get_all("Interview", filters={"job_applicant": name, "docstatus": ["<", 2]}, fields=["name", "interview_type", "status", "scheduled_on", "from_time",
		"sk_mode", "sk_scores", "sk_summary", "sk_answers", "sk_finished_on", "interview_summary"], order_by="creation asc", limit=0)
	round1 = next((i for i in ivs if i.interview_type == ROUND1), None)
	round2 = next((i for i in ivs if i.interview_type == ROUND2), None)
	from sk_app.writers.applicant import claude_notes
	from sk_app.writers.interview import scores_of

	scores = scores_of(round1.name) if round1 else None  # written by Claude's scheduled run (R7)
	answers = json.loads(round1.sk_answers) if round1 and round1.sk_answers else []
	ranked = ranked_for_job(a.job_title) if a.job_title else []
	mine = next((r for r in ranked if r["name"] == name), None)
	files = frappe.get_all("File", filters={"attached_to_doctype": "Job Applicant", "attached_to_name": name}, fields=["file_name", "file_url"], limit=20)
	if is_ceo(user) and a.status == "Shortlisted" and not a.get("sk_sk_seen_on"):
		frappe.db.set_value("Job Applicant", name, "sk_sk_seen_on", now_datetime(), update_modified=False)
	return {**row, "email": a.email_id, "claims": json.loads(a.get("sk_claims") or "[]"), "experience": a.get("sk_experience_years"), "last_employer": a.get("sk_last_employer"),
		"round1": dict(round1) if round1 else None, "round2": dict(round2) if round2 else None, "scores": scores, "answers": answers,
		"summary": (scores or {}).get("feedback") or (round1.sk_summary if round1 else None), "claude_notes": claude_notes(name),
		"waiting_claude": bool(round1 and round1.status == "Under Review" and not scores), "rank": mine and mine.get("rank"), "of": mine and mine.get("of"), "files": [dict(f) for f in files],
		"is_ceo": is_ceo(user), "stars": {t["skill"]: R.stars(t.get("score")) for t in (scores or {}).get("traits", [])} if scores else {},
		"questions": questions(a.get("sk_family")), "teach_back": teach_back(), "resume_text": (a.get("sk_resume_text") or "")[:3000]}


def ranked_for_job(job: str) -> list[dict]:
	rows = []
	for a in frappe.get_all("Job Applicant", filters={"job_title": job, "status": ["not in", ["Rejected"]]}, fields=_A_FIELDS, limit=0):
		from sk_app.writers.interview import scores_of

		iv = frappe.get_all("Interview", filters={"job_applicant": a.name, "interview_type": ROUND1, "docstatus": ["<", 2]}, pluck="name", limit=1)
		scores = (scores_of(iv[0]) if iv else None) or {}
		rows.append({**_applicant_row(a), "overall": scores.get("overall"), "band": scores.get("band"), "one_line": (scores.get("feedback") or "")[:160]})
	return R.rank(rows)


def round2(user: str) -> dict:
	"""SK's screen: Round 2 today, waiting for his decision, and a ranked list for each open job."""
	_check(user)
	today = nowdate()
	ivs = frappe.get_all("Interview", filters={"interview_type": ROUND2, "scheduled_on": today, "docstatus": ["<", 2], "status": ["in", ["Pending", "Under Review"]]},
		fields=["name", "job_applicant", "from_time"], order_by="from_time asc", limit=0)
	names = {a.name: a for a in frappe.get_all("Job Applicant", filters={"name": ["in", [i.job_applicant for i in ivs] or [""]]}, fields=_A_FIELDS)}
	todays = [{"interview": i.name, "time": str(i.from_time or "")[:5], **(_applicant_row(names[i.job_applicant]) if i.job_applicant in names else {"name": i.job_applicant})} for i in ivs]
	waiting = [_applicant_row(a) for a in frappe.get_all("Job Applicant", filters={"status": "Shortlisted"}, fields=_A_FIELDS, order_by="modified asc", limit=0)]
	jobs = [{"job": j.name, "title": j.job_title, "rows": ranked_for_job(j.name)} for j in frappe.get_all("Job Opening", filters={"status": "Open"}, fields=["name", "job_title"], limit=0)]
	return {"today": todays, "waiting": waiting, "jobs": [j for j in jobs if j["rows"]], "today_date": today}


def slots(user: str, days: int = 7) -> list[dict]:
	"""Free interview slots from tomorrow: HR's working hours 10:00-17:00 minus booked interviews (data, no code: HR edits the hours in settings later)."""
	settings = frappe.get_cached_doc("SK App Settings")
	step = int(settings.get("hr_slot_minutes") or 30)
	booked = {(str(i.scheduled_on), str(i.from_time or "")[:5]) for i in frappe.get_all("Interview", filters={"scheduled_on": [">=", nowdate()], "docstatus": ["<", 2],
		"status": ["!=", "Cancelled"]}, fields=["scheduled_on", "from_time"], limit=0)}
	out = []
	for d in range(1, days + 1):
		day = add_days(nowdate(), d)
		if getdate(day).weekday() == 6:
			continue
		minutes = 10 * 60
		while minutes + step <= 17 * 60 and len(out) < 40:
			t = f"{minutes // 60:02d}:{minutes % 60:02d}"
			if (str(day), t) not in booked:
				out.append({"date": str(day), "time": t})
			minutes += step
	return out


HR_GMAIL = "skindtech.hr@gmail.com"  # SK 17-Nov (R14): candidates mail the resume here; WhatsApp resumes are forwarded here by the HR owner
FORWARD_REMINDER = (f"Forward WhatsApp resumes to {HR_GMAIL} (label 'Resume to forward').",
	f"WhatsApp वरील बायोडाटा {HR_GMAIL} वर फॉरवर्ड करा ('Resume to forward' लेबल).")


def resume_forward_reminder() -> int:
	"""10 AM and 4 PM, Mon-Sat (SK 17-Nov 'some notification is needed to identify that this needs to forward'): the HR
	owners (Samir, SK) get the reminder in the app (notification + today's to-do). Resume intake moves to the HR Gmail."""
	from sk_app.mailbox import _notify

	users = hr_users()
	if not users:
		return 0
	text = FORWARD_REMINDER[0] + " · " + FORWARD_REMINDER[1]
	_notify(users, "📨 " + text)
	for u in users:
		if not frappe.db.exists("ToDo", {"allocated_to": u, "status": "Open", "date": nowdate(), "description": ["like", "📨 Resume to forward%"]}):
			frappe.get_doc({"doctype": "ToDo", "allocated_to": u, "description": "📨 Resume to forward: " + text, "priority": "Medium", "date": nowdate()}).insert(ignore_permissions=True)
	return len(users)


# ---------- hourly: resume reads, timers, reminders ----------

def hourly():
	"""Every hour: 48 h without a reply hands the bot chat to HR; reminders the day before; the 6-month clean-up.
	Resume reading and scoring are Claude's scheduled run (R7), not here."""
	from sk_app.writers import applicant as aw
	from sk_app.writers import interview as iw

	cutoff = frappe.utils.add_to_date(now_datetime(), hours=-48)
	for a in frappe.get_all("Job Applicant", filters={"sk_bot_state": ["not in", ["", None, "done", "hr"]], "sk_last_message_on": ["<", cutoff], "sk_handed_to_hr": 0}, pluck="name", limit=100):
		aw.hand_to_hr(a, "no reply for 48 hours")
	frappe.db.commit()
	iw.send_reminders()
	aw.purge_old()
	if now_datetime().hour == 3:
		iw.purge_videos()  # R9.4: answer videos older than 7 days
	frappe.db.commit()
