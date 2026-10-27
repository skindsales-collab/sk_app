"""Team mailboxes in the app (change list point 14, SK 26-Oct-2026).

cabin@ for the sales team (Rushi, Swati, Pranali, Rahul), service@ for Aditya, acc@ for Accounts, sales@ for the CEO,
info@ for HR (SK App Settings > Team mailboxes). ERPNext's Email Accounts fetch the mails; the app shows each team
its box, with a status per mail so two people never answer the same one: New → Taken by … → Replied / Lead made.
"""

import frappe
from frappe import _
from frappe.utils import add_days, add_to_date, getdate, now_datetime, strip_html

from sk_app.logic import parse_lines

STATUSES = ("New", "Taken", "Replied", "Lead made", "Not a lead")
DEFAULT_MAP = ("cabin@skind.tech: Sales, Marketing\nservice@skind.tech: Machine Shifting, service@skind.tech\n"
	"acc@skind.tech: Accounts\nsales@skind.tech: Management\ninfo@skind.tech: HR\n"
	# SK 27-Oct: prod@ for Production (Babasaheb) and Store (Yogesh)
	"prod@skind.tech: 9730517277@staff.skind.local, 9970960806@staff.skind.local")


def team_boxes() -> dict:
	"""{mailbox: [functions or logins]} from SK App Settings."""
	text = frappe.get_cached_doc("SK App Settings").get("mailbox_map") or ""
	out = {}
	# a box set in SK App Settings wins; a box only in the default list (added later, e.g. prod@) still shows
	for line in parse_lines(DEFAULT_MAP) + parse_lines(text):
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
	fields = ["name", "recipients", "sender", "subject", "sk_mail_status", "sk_taken_by", "reference_doctype", "reference_name",
		"sent_or_received", "email_account"] + (["sk_box"] if _has_box_field() else [])
	row = frappe.db.get_value("Communication", comm, fields, as_dict=True)
	if not row:
		frappe.throw(_("Mail not found"))
	mine = boxes_for(user)
	box = _box_of(row, mine, _account_boxes())
	if box not in mine:
		frappe.throw(_("This mail is not in your team mailbox"), frappe.PermissionError)
	row["box"] = box
	return row


def _has_box_field() -> bool:
	return frappe.get_meta("Communication").has_field("sk_box")


def _account_boxes() -> dict:
	return {a.name: a.email_id.lower() for a in frappe.get_all("Email Account", fields=["name", "email_id"]) if a.email_id}


def _box_of(row, boxes: list[str], box_of_account: dict) -> str | None:
	"""A mail moved to another team (sk_box) belongs there; else the team address it was sent to, else the account
	that fetched it (a mail Bcc'd or forwarded to cabin@ has another address in its recipients)."""
	if row.get("sk_box"):
		return row.sk_box
	return next((b for b in boxes if b in (row.recipients or "").lower()), None) or box_of_account.get(row.email_account)


def _received(boxes: list[str], since=None, fields=None, filters=None, limit=0, start=0):
	acc = _accounts(boxes)
	or_filters = [["recipients", "like", f"%{b}%"] for b in boxes] + ([["email_account", "in", acc]] if acc else [])
	if _has_box_field():
		or_filters.append(["sk_box", "in", boxes])
	f = {"communication_medium": "Email", "sent_or_received": "Received", **(filters or {})}
	if since:
		f["communication_date"] = [">=", since]
	return frappe.get_all("Communication", filters=f, or_filters=or_filters, order_by="communication_date desc",
		fields=["name", "recipients", "email_account", "sk_mail_status", "reference_doctype", "communication_date"]
		+ (["sk_box"] if _has_box_field() else []) + (fields or []), limit=limit, start=start)


def _status(r) -> str:
	return r.sk_mail_status or ("Lead made" if r.reference_doctype in ("CRM Lead", "CRM Deal") else "New")


def counts(boxes: list[str]) -> dict:
	"""Per mailbox (SK 27-Oct): received today, leads made and replied today, waiting (New), waiting over 2 hours / 1 day."""
	out = {b: {"box": b, "today": 0, "leads_today": 0, "replied_today": 0, "waiting": 0, "late": 0, "day_late": 0} for b in boxes}
	if not boxes:
		return out
	today, now, box_of = getdate(), now_datetime(), _account_boxes()
	for r in _received(boxes, since=add_days(today, -30)):
		b = _box_of(r, boxes, box_of)
		if b not in out:
			continue
		c, st = out[b], _status(r)
		if getdate(r.communication_date) == today:
			c["today"] += 1
			c["leads_today"] += st == "Lead made"
			c["replied_today"] += st == "Replied"
		if st == "New":
			c["waiting"] += 1
			c["late"] += r.communication_date < add_to_date(now, hours=-2)
			c["day_late"] += r.communication_date < add_to_date(now, days=-1)
	return out


def inbox(user: str, box: str | None = None, q: str | None = None, start: int = 0, limit: int = 100) -> dict:
	"""All mails received in the person's team mailboxes (SK 27-Oct: "all mail need to show on respective app"),
	newest first, with their status; Show more loads the next 100, search finds any."""
	boxes = boxes_for(user)
	if not boxes:
		return {"boxes": [], "mails": [], "counts": []}
	want = [box] if box in boxes else boxes
	filters = {}
	if (q or "").strip():
		filters["subject"] = ["like", f"%{q.strip()}%"]
	extra = ["subject", "sender", "sender_full_name", "text_content", "content", "sk_taken_by", "reference_name", "has_attachment"]
	rows = _received(want, fields=extra, filters=filters, limit=int(limit) + 1, start=int(start))
	if (q or "").strip() and len(rows) <= int(limit):  # also by sender
		seen = {r.name for r in rows}
		rows += [r for r in _received(want, fields=extra, filters={"sender": ["like", f"%{q.strip()}%"]}, limit=int(limit))
			if r.name not in seen]
	more = len(rows) > int(limit)
	rows = rows[:int(limit)]
	box_of, names, out = _account_boxes(), {}, []
	from sk_app.lead_sources import source_of

	for r in rows:
		r["box"] = _box_of(r, want, box_of)
		if r["box"] not in want:  # moved to another team
			continue
		r["status"] = _status(r)
		if r.sk_taken_by and r.sk_taken_by not in names:
			names[r.sk_taken_by] = frappe.utils.get_fullname(r.sk_taken_by)
		r["taken_by_name"] = names.get(r.sk_taken_by)
		r["preview"] = (r.text_content or strip_html(r.content or ""))[:200]
		r.pop("content", None)
		r.pop("text_content", None)
		r["source"] = source_of(r.sender, r.subject)
		out.append(r)
	c = counts(boxes)
	return {"boxes": boxes, "box": box if box in boxes else None, "mails": out, "more": more,
		"new": sum(x["waiting"] for x in c.values()), "counts": list(c.values()),
		"all_boxes": sorted(team_boxes())}


def read(user: str, comm: str) -> dict:
	row = _check(user, comm)
	doc = frappe.db.get_value("Communication", comm, ["content", "text_content", "communication_date", "sender_full_name"], as_dict=True)
	files = frappe.get_all("File", filters={"attached_to_doctype": "Communication", "attached_to_name": comm},
		fields=["file_name", "file_url"])
	return {**row, "text": (doc.text_content or strip_html(doc.content or ""))[:6000], "date": str(doc.communication_date),
		"from_name": doc.sender_full_name, "files": files, "people": people_of(row.box),
		"move_to": [b for b in sorted(team_boxes()) if b != row.box]}


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


def badges(user: str) -> dict:
	"""Mail icon: mails waiting (New); mail_late: still New after 1 day (Decide Now)."""
	try:
		c = counts(boxes_for(user)).values()
	except Exception:
		return {}
	out = {"mail": sum(x["waiting"] for x in c), "mail_late": sum(x["day_late"] for x in c)}
	return {k: v for k, v in out.items() if v}


def move(user: str, comm: str, to_box: str) -> dict:
	"""SK 27-Oct: a customer enquiry that came to info@ (or any box) is moved to the right team with one tap."""
	row = _check(user, comm)
	to_box = (to_box or "").strip().lower()
	if to_box not in team_boxes() or to_box == row.box:
		frappe.throw(_("Pick the team mailbox to move it to"))
	if not _has_box_field():
		frappe.throw(_("Please update the site first"))
	_set(comm, sk_box=to_box, sk_mail_status="New", sk_taken_by=None)
	frappe.get_doc({"doctype": "Comment", "comment_type": "Info", "reference_doctype": "Communication", "reference_name": comm,
		"content": f"Moved from {row.box} to {to_box} by {frappe.utils.get_fullname(user)}"}).insert(ignore_permissions=True)
	_notify([p.user for p in people_of(to_box)], f"Mail moved to {to_box}: {row.subject or ''}", "Communication", comm)
	return {"box": to_box}


def _notify(users, subject: str, doctype=None, name=None):
	for u in set(users):
		try:
			frappe.get_doc({"doctype": "Notification Log", "for_user": u, "type": "Alert", "subject": subject[:140],
				"document_type": doctype, "document_name": name}).insert(ignore_permissions=True)
		except Exception:
			frappe.log_error("SK App mail notification")


def link_known():
	"""Scheduler, every 5 minutes: a mail from a customer who is already a lead or deal goes onto that lead / deal and
	to its owner (SK 27-Oct: ownership is kept, all communication through ERPNext and the app)."""
	if not frappe.db.exists("DocType", "CRM Lead"):
		return 0
	boxes = list(team_boxes())
	if not boxes:
		return 0
	rows = _received(boxes, since=add_days(now_datetime(), -2), fields=["sender", "subject"],
		filters={"sk_mail_status": ["in", ["", None, "New"]]})
	linked = 0
	for r in rows:
		if r.reference_doctype in ("CRM Lead", "CRM Deal") or not r.sender or r.sender.lower() in boxes:
			continue
		ref = _known(r.sender.strip().lower())
		if not ref:
			continue
		doctype, name, owner = ref
		values = {"reference_doctype": doctype, "reference_name": name}
		if owner:
			values.update(sk_mail_status="Taken", sk_taken_by=owner)
		_set(r.name, **values)
		if owner:
			from sk_app.store import _todo

			_todo(owner, doctype, name, f"Customer mail: {r.subject or ''}"[:140])
		linked += 1
	return linked


def _known(email: str):
	if frappe.get_meta("CRM Deal").has_field("email"):
		d = frappe.db.get_value("CRM Deal", {"email": email}, ["name", "deal_owner"], order_by="modified desc")
		if d:
			return ("CRM Deal", d[0], d[1])
	d = frappe.db.get_value("CRM Lead", {"email": email, "converted": 0}, ["name", "lead_owner"], order_by="modified desc")
	return ("CRM Lead", d[0], d[1]) if d else None


def remind():
	"""Hourly: a mail still New after 2 hours reminds its team (ERPNext bell + the app's Mail badge)."""
	for box, c in counts(list(team_boxes())).items():
		if c["late"]:
			_notify([p.user for p in people_of(box)], f"{c['late']} mail(s) waiting over 2 hours in {box}")
