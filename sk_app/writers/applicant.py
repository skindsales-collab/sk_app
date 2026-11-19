"""The one Job Applicant writer (SK hiring, 17-Nov-2026): a candidate from WhatsApp, WorkIndia or HR's tablet; Claude's
resume read; HR / SK status taps; WorkIndia Excel upload; the 6-month clean-up. No salary field is ever read or written."""

import json
import re

import frappe
from frappe import _
from frappe.utils import add_months, cint, flt, now_datetime, nowdate

from sk_app import hiring_rules as R

NO_AGE_GENDER = ("age", "gender", "sex", "dob", "date of birth", "marital", "religion", "caste")


def _mobile(v) -> str | None:
	d = re.sub(r"\D", "", str(v or ""))[-10:]
	return d if len(d) == 10 and d[0] in "6789" else None


def find_by_mobile(mobile: str | None) -> str | None:
	m = _mobile(mobile)
	return frappe.db.get_value("Job Applicant", {"phone_number": ["like", f"%{m}"]}, "name") if m else None


def write(user: str | None, data: dict, *, source: str, resume_url: str | None = None, note: str | None = None) -> "frappe.Document":
	"""data: applicant_name, mobile, email, job (Job Opening), designation, city, language. Returns the saved applicant
	(the existing one of the same mobile, updated, so nobody is entered twice)."""
	from sk_app import hiring

	mobile = _mobile(data.get("mobile"))
	name = data.get("applicant_name") or (f"Candidate {mobile[-4:]}" if mobile else "Candidate")
	existing = find_by_mobile(mobile)
	doc = frappe.get_doc("Job Applicant", existing) if existing else frappe.new_doc("Job Applicant")
	if not existing:
		doc.applicant_name = name[:140]
		doc.status = R.STATUS_NEW
		doc.source = source if frappe.db.exists("Job Applicant Source", source) else None
	elif name and not doc.applicant_name.startswith("Candidate "):
		pass
	else:
		doc.applicant_name = name[:140]
	if mobile:
		doc.phone_number = mobile
	doc.email_id = R.applicant_email(data.get("email") or doc.email_id, mobile) or doc.email_id
	if not doc.email_id:
		frappe.throw(_("A 10-digit mobile or an e-mail is needed"))
	job = data.get("job")
	if job and frappe.db.exists("Job Opening", job):
		doc.job_title = job
		doc.designation = frappe.db.get_value("Job Opening", job, "designation") or doc.designation
	if data.get("designation") and frappe.db.exists("Designation", data["designation"]):
		doc.designation = data["designation"]
	fam = data.get("family") or R.family_of(doc.designation, hiring.designation_family())
	if fam:
		doc.sk_family = fam
	for k, f in (("city", "sk_city"), ("language", "sk_language"), ("last_employer", "sk_last_employer"), ("workindia_id", "sk_workindia_id")):
		if data.get(k):
			doc.set(f, str(data[k])[:140])
	if data.get("experience") not in (None, ""):
		doc.sk_experience_years = flt(data["experience"])
	if data.get("consent"):
		doc.sk_consent_on = now_datetime()
	if note:
		doc.notes = ((doc.notes or "") + " | " + note)[:140]
	doc.flags.ignore_permissions = True
	doc.flags.ignore_mandatory = True
	doc.save()
	if resume_url:
		attach(doc.name, resume_url, user)
	return doc


def before_insert(doc, method=None):
	"""Every Job Applicant, from the staff apply form or the desk too (R12): the e-mail is <mobile>@applicant.skind.local
	when blank, the mobile is kept as 10 digits, and the role family follows the designation."""
	from sk_app import hiring

	m = _mobile(doc.get("phone_number"))
	if m:
		doc.phone_number = m
	doc.email_id = R.applicant_email(doc.get("email_id"), m) or doc.get("email_id")
	if not doc.get("sk_family") and doc.get("designation"):
		fam = R.family_of(doc.designation, hiring.designation_family())
		if fam:
			doc.sk_family = fam
	if not doc.get("source") and frappe.db.exists("Job Applicant Source", "WhatsApp"):
		doc.source = "WhatsApp"


def attach(name: str, file_url: str, user: str | None = None):
	"""The resume (photo / PDF / Word) onto the applicant; the OCR text goes to sk_resume_text."""
	if frappe.db.exists("File", {"file_url": file_url, "attached_to_doctype": "Job Applicant", "attached_to_name": name}):
		return
	src = frappe.db.get_value("File", {"file_url": file_url}, ["file_name", "is_private"], as_dict=True)
	frappe.get_doc({"doctype": "File", "file_url": file_url, "file_name": (src and src.file_name) or "resume", "is_private": 1,
		"attached_to_doctype": "Job Applicant", "attached_to_name": name}).insert(ignore_permissions=True)
	frappe.db.set_value("Job Applicant", name, "resume_attachment", file_url, update_modified=False)


def claude_notes(name: str) -> list[dict]:
	"""The scheduled Claude run's comments on the applicant ('Claude screen:' fit, 'Claude Round 1:' band + Round 2 questions)."""
	rows = frappe.get_all("Comment", filters={"reference_doctype": "Job Applicant", "reference_name": name, "comment_type": "Comment",
		"content": ["like", "%Claude %"]}, fields=["content", "creation"], order_by="creation desc", limit=10)
	out = []
	for r in rows:
		text = frappe.utils.strip_html(r.content or "")
		if text.startswith("Claude screen:") or text.startswith("Claude Round 1:"):
			out.append({"text": text, "on": str(r.creation)[:16]})
	return out


def read_resume(name: str) -> dict | None:
	"""Free mode (R7): the scheduled Claude run reads resumes and leaves a 'Claude screen:' comment; nothing to do here."""
	return None


# ---------- taps ----------

def decide(user: str, name: str, action: str, note: str | None = None) -> dict:
	"""HR: send_to_sk / hold. SK: selected / hold / not_selected. Claude never calls this."""
	from sk_app import hiring
	from sk_app.core.people import is_ceo

	hiring._check(user)
	doc = frappe.get_doc("Job Applicant", name)
	actions = {"send_to_sk": R.STATUS_SHORTLISTED, "hold": R.STATUS_HOLD, "selected": R.STATUS_SELECTED, "not_selected": R.STATUS_NOT, "reopen": R.STATUS_REPLIED}
	if action not in actions:
		frappe.throw(_("Unknown action"))
	if action in ("selected", "not_selected") and not is_ceo(user):
		frappe.throw(_("Only the CEO decides after Round 2"), frappe.PermissionError)
	doc.status = actions[action]
	doc.flags.ignore_permissions = True
	doc.save()
	doc.add_comment("Comment", _("{0} by {1}").format(action.replace("_", " "), frappe.utils.get_fullname(user)) + (f": {note}" if note else ""))
	msg_key = {"hold": "W6", "not_selected": "W7", "selected": "W9", "send_to_sk": "W5"}.get(action)
	return {"status": doc.status, "message": message_for(name, msg_key) if msg_key else None}


def hand_to_hr(name: str, why: str):
	frappe.db.set_value("Job Applicant", name, {"sk_handed_to_hr": 1, "sk_bot_state": "hr"}, update_modified=False)
	for u in _hr_users():
		frappe.get_doc({"doctype": "ToDo", "allocated_to": u, "reference_type": "Job Applicant", "reference_name": name, "priority": "Medium", "date": nowdate(),
			"description": _("Candidate needs HR: {0}").format(why)}).insert(ignore_permissions=True)


def _hr_users() -> list[str]:
	from sk_app.hiring import hr_users

	return hr_users()


def message_for(name: str, key: str, **extra) -> dict:
	"""The WhatsApp text (EN + MR) for a candidate and the wa.me link HR taps in Phase 1."""
	a = frappe.db.get_value("Job Applicant", name, ["applicant_name", "phone_number", "job_title"], as_dict=True)
	job = frappe.db.get_value("Job Opening", a.job_title, "job_title") if a.job_title else ""
	settings = frappe.get_cached_doc("SK App Settings")
	text = R.message(key, name=a.applicant_name, job=job, address=settings.get("hr_office_address"), **extra)
	from urllib.parse import quote

	return {"key": key, "text": text, "wa_link": f"https://wa.me/91{a.phone_number}?text={quote(text)}" if a.phone_number else None}


# ---------- WorkIndia Excel (R2) ----------

def upload_workindia(user: str, file_url: str, job: str | None = None) -> dict:
	"""HR uploads WorkIndia's 'Export to Excel'. Columns are matched by name; age / gender / DOB columns are never read;
	the same mobile is not entered twice. Returns made / skipped and the W0 template text for each new candidate."""
	from sk_app import hiring
	from sk_app.lead_sources import _rows_from_file

	hiring._check(user)
	rows = _rows_from_file(file_url)
	if not rows:
		frappe.throw(_("The file is empty or not an Excel / CSV"))
	header = [str(h or "").strip().lower() for h in rows[0]]
	col = lambda *names: next((i for i, h in enumerate(header) if any(n in h for n in names) and not any(x in h for x in NO_AGE_GENDER)), None)  # noqa: E731
	ci = {"name": col("candidate name", "name"), "mobile": col("mobile", "phone", "contact"), "email": col("email"), "city": col("city", "location"),
		"exp": col("experience", "exp"), "job": col("job title", "job", "role"), "id": col("candidate id", "id")}
	if ci["mobile"] is None:
		frappe.throw(_("No mobile column found in the file"))
	made, skipped, first = 0, 0, []
	for r in rows[1:]:
		get = lambda k: (r[ci[k]] if ci[k] is not None and ci[k] < len(r) else None)  # noqa: E731
		mobile = _mobile(get("mobile"))
		if not mobile:
			skipped += 1
			continue
		if find_by_mobile(mobile):
			skipped += 1
			continue
		doc = write(user, {"applicant_name": get("name"), "mobile": mobile, "email": get("email"), "city": get("city"), "experience": get("exp"), "job": job,
			"workindia_id": get("id")}, source="WorkIndia", note="WorkIndia export")
		made += 1
		if len(first) < 50:
			first.append({"name": doc.name, "applicant_name": doc.applicant_name, "mobile": mobile, "message": message_for(doc.name, "W0")})
	return {"made": made, "skipped": skipped, "first": first, "job": job}


# ---------- DPDP: 6 months ----------

def purge_old() -> int:
	"""Voice files and resume of a candidate not selected (Rejected / Hold) for 6 months are deleted; the row stays."""
	cutoff = add_months(nowdate(), -R.KEEP_MONTHS)
	n = 0
	for a in frappe.get_all("Job Applicant", filters={"status": ["in", ["Rejected", "Hold"]], "modified": ["<", cutoff]}, pluck="name", limit=200):
		for f in frappe.get_all("File", filters={"attached_to_doctype": "Job Applicant", "attached_to_name": a}, pluck="name"):
			frappe.delete_doc("File", f, ignore_permissions=True, force=True)
			n += 1
		for iv in frappe.get_all("Interview", filters={"job_applicant": a}, pluck="name"):
			for f in frappe.get_all("File", filters={"attached_to_doctype": "Interview", "attached_to_name": iv}, pluck="name"):
				frappe.delete_doc("File", f, ignore_permissions=True, force=True)
				n += 1
			frappe.db.set_value("Interview", iv, {"sk_answers": None}, update_modified=False)
		frappe.db.set_value("Job Applicant", a, {"sk_resume_text": None, "resume_attachment": None, "sk_bot_data": None}, update_modified=False)
	return n


def delete_request(name: str) -> int:
	"""Typing DELETE on WhatsApp (W8): the candidate's files and texts go at once; the row stays with status Rejected."""
	frappe.db.set_value("Job Applicant", name, {"status": R.STATUS_NOT, "modified": add_months(nowdate(), -R.KEEP_MONTHS - 1)}, update_modified=False)
	return purge_old()
