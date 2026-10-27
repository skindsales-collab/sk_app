"""Team mailboxes in the app (change list point 14, SK 26-Oct-2026).

cabin@ for the sales team (Rushi, Swati, Pranali, Rahul), service@ for Aditya, acc@ for Accounts, sales@ for the CEO,
info@ for HR (SK App Settings > Team mailboxes). ERPNext's Email Accounts fetch the mails; the app shows each team
its box, with a status per mail so two people never answer the same one: New → Taken by … → Replied / Lead made.
"""

import frappe
from frappe import _
from frappe.utils import add_days, getdate, now_datetime, strip_html

from sk_app.logic import parse_lines

STATUSES = ("New", "Taken", "Replied", "Lead made", "Not a lead")
DEFAULT_MAP = ("cabin@skind.tech: Sales, Marketing\nservice@skind.tech: Machine Shifting, service@skind.tech\n"
	"acc@skind.tech: Accounts\nsales@skind.tech: Management\ninfo@skind.tech: HR")


def team_boxes() -> dict:
	"""{mailbox: [functions or logins]} from SK App Settings."""
	text = frappe.get_cached_doc("SK App Settings").get("mailbox_map") or DEFAULT_MAP
	out = {}
	for line in parse_lines(text):
		box, sep, who = line.partition(":")
		if sep and "@" in box:
			out[box.strip().lower()] = [w.strip() for w in who.split(",") if w.strip()]
	return out


def boxes_for(user: str) -> list[str]:
	from sk_app.logins import profile_functions

	mine = set(profile_functions(user)) | {user}
	if user == "Administrator" or "Management" in mine:  # SK 27-Oct: the CEO checks every team mailbox
		return list(team_boxes())
	return [box for box, who in team_boxes().items() if mine & set(who)]


def _accounts(boxes: list[str]) -> list[str]:
	"""ERPNext Email Accounts of the boxes: a mail forwarded or Bcc'd to cabin@ has another address in its recipients."""
	return frappe.get_all("Email Account", filters={"email_id": ["in", boxes]}, pluck="name") if boxes else []


def people_of(box: str) -> list[dict]:
	from sk_app.logins import profile_functions

	who = set(team_boxes().get(box, []))
	rows = frappe.get_all("SK App User", filters={"enabled": 1}, fields=["user", "full_name"])
	return [r for r in rows if r.user in who or who & set(profile_functions(r.user))]


def _check(user: str, comm: str) -> frappe._dict:
	row = frappe.db.get_value("Communication", comm, ["name", "recipients", "sender", "subject", "sk_mail_status", "sk_taken_by",
		"reference_doctype", "reference_name", "sent_or_received", "email_account"], as_dict=True)
	if not row:
		frappe.throw(_("Mail not found"))
	mine = boxes_for(user)
	account_box = (frappe.db.get_value("Email Account", row.email_account, "email_id") or "").lower() if row.email_account else ""
	box = next((b for b in mine if b in (row.recipients or "").lower()), None) or (account_box if account_box in mine else None)
	if not box:
		frappe.throw(_("This mail is not in your team mailbox"), frappe.PermissionError)
	row["box"] = box
	return row


def inbox(user: str, days: int = 30) -> dict:
	"""Mails received in the person's team mailboxes, newest first, with their status."""
	boxes = boxes_for(user)
	if not boxes:
		return {"boxes": [], "mails": []}
	rows = frappe.get_all("Communication", filters={"communication_medium": "Email", "sent_or_received": "Received",
		"communication_date": [">=", add_days(getdate(), -int(days))]},
		or_filters=[["recipients", "like", f"%{b}%"] for b in boxes] + ([["email_account", "in", acc]] if (acc := _accounts(boxes)) else []),
		fields=["name", "subject", "sender", "sender_full_name", "recipients", "communication_date", "text_content", "content",
			"sk_mail_status", "sk_taken_by", "reference_doctype", "reference_name", "has_attachment", "email_account"],
		order_by="communication_date desc", limit=150)
	box_of = {a.name: a.email_id.lower() for a in frappe.get_all("Email Account", fields=["name", "email_id"]) if a.email_id}
	names = {}
	for r in rows:
		r["box"] = next((b for b in boxes if b in (r.recipients or "").lower()), None) or box_of.get(r.email_account) or boxes[0]
		r["status"] = r.sk_mail_status or ("Lead made" if r.reference_doctype in ("CRM Lead", "CRM Deal") else "New")
		if r.sk_taken_by and r.sk_taken_by not in names:
			names[r.sk_taken_by] = frappe.utils.get_fullname(r.sk_taken_by)
		r["taken_by_name"] = names.get(r.sk_taken_by)
		r["preview"] = (r.text_content or strip_html(r.content or ""))[:200]
		r.pop("content", None)
		r.pop("text_content", None)
		from sk_app.lead_sources import source_of

		r["source"] = source_of(r.sender, r.subject)
	return {"boxes": boxes, "mails": rows, "new": sum(1 for r in rows if r["status"] == "New")}


def read(user: str, comm: str) -> dict:
	row = _check(user, comm)
	doc = frappe.db.get_value("Communication", comm, ["content", "text_content", "communication_date", "sender_full_name"], as_dict=True)
	files = frappe.get_all("File", filters={"attached_to_doctype": "Communication", "attached_to_name": comm},
		fields=["file_name", "file_url"])
	return {**row, "text": (doc.text_content or strip_html(doc.content or ""))[:6000], "date": str(doc.communication_date),
		"from_name": doc.sender_full_name, "files": files, "people": people_of(row.box)}


def _set(comm: str, **values):
	frappe.db.set_value("Communication", comm, values, update_modified=False)


def take(user: str, comm: str) -> dict:
	row = _check(user, comm)
	if row.sk_taken_by and row.sk_taken_by != user and row.sk_mail_status == "Taken":
		frappe.throw(_("{0} has already taken this mail").format(frappe.utils.get_fullname(row.sk_taken_by)))
	_set(comm, sk_mail_status="Taken", sk_taken_by=user)
	return {"ok": True}


def give(user: str, comm: str, to_user: str) -> dict:
	"""The team's manager gives a mail to one person."""
	row = _check(user, comm)
	if to_user not in {p.user for p in people_of(row.box)}:
		frappe.throw(_("Pick a person of this mailbox"))
	_set(comm, sk_mail_status="Taken", sk_taken_by=to_user)
	from sk_app.store import _todo

	_todo(to_user, "Communication", comm, f"Mail to answer: {row.subject or ''}"[:140])
	return {"ok": True}


def not_a_lead(user: str, comm: str) -> dict:
	_check(user, comm)
	_set(comm, sk_mail_status="Not a lead", sk_taken_by=user)
	return {"ok": True}


def make_lead(user: str, comm: str, segment: str | None = None) -> dict:
	"""Unknown sender → a CRM Lead owned by the person (known customer → note on the earlier lead)."""
	from sk_app import lead_sources

	row = _check(user, comm)
	if row.reference_doctype in ("CRM Lead", "CRM Deal") and row.reference_name:
		return {"lead": row.reference_name, "new": False}
	doc = frappe.db.get_value("Communication", comm, ["content", "text_content", "sender", "sender_full_name"], as_dict=True)
	source = lead_sources.source_of(doc.sender, row.subject) or "Email"
	data = lead_sources.parse_mail(row.subject, doc.text_content or doc.content, source)
	if source == "Email":
		data["email"] = data.get("email") or (doc.sender or "").strip()
		data["first_name"] = doc.sender_full_name or data["first_name"]
	if segment:
		data["segment"] = segment
	res = lead_sources.make_lead(data, source, owner=user, note=f"From mail to {row.box}: {row.subject or ''}")
	_set(comm, reference_doctype="CRM Lead", reference_name=res["lead"], sk_mail_status="Lead made", sk_taken_by=user)
	return res


def reply(user: str, comm: str, message: str) -> dict:
	"""Reply from the team mailbox, signed with the person's name and mobile; kept on the lead when there is one."""
	from frappe.core.doctype.communication.email import _make

	row = _check(user, comm)
	if not (message or "").strip():
		frappe.throw(_("Please write or speak the reply"))
	if not frappe.db.exists("Email Account", {"email_id": row.box, "enable_outgoing": 1}):
		frappe.throw(_("{0} cannot send mail yet. Please ask the admin to switch on sending for it in ERPNext.").format(row.box))
	mobile = frappe.db.get_value("User", user, "mobile_no") or ""
	sign = f"\n\n--\n{frappe.utils.get_fullname(user)}{(' · ' + mobile) if mobile else ''}\nSK Ind Tech Solutions Pvt Ltd"
	html = "<br>".join(frappe.utils.escape_html(line) for line in (message.strip() + sign).splitlines())
	subject = row.subject or ""
	if not subject.lower().startswith("re:"):
		subject = "Re: " + subject
	res = _make(doctype=row.reference_doctype, name=row.reference_name, content=html, subject=subject, sender=row.box,
		sender_full_name=frappe.utils.get_fullname(user), recipients=row.sender, send_email=1, in_reply_to=comm)
	_set(comm, sk_mail_status="Replied", sk_taken_by=user)
	if row.reference_doctype in ("CRM Lead", "CRM Deal"):
		from sk_app.crm import _mark_first_response

		_mark_first_response(row.reference_doctype, row.reference_name)
	return {"name": res.get("name") if isinstance(res, dict) else res}


def badge(user: str) -> int:
	boxes = boxes_for(user)
	if not boxes:
		return 0
	try:
		return frappe.db.count("Communication", filters={"communication_medium": "Email", "sent_or_received": "Received",
			"communication_date": [">=", add_days(now_datetime(), -7)], "sk_mail_status": ["in", ["", None, "New"]],
			"reference_doctype": ["not in", ["CRM Lead", "CRM Deal"]], "recipients": ["like", f"%{boxes[0]}%"]})
	except Exception:
		return 0
