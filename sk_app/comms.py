"""Calls, reminders and mail on the phone, all free: calls are logged by hand after the phone's own dialer (with talk
time), reminders are CRM Tasks or private calendar Events, and mail goes through the company Email Account in ERPNext.
Paid parts (automatic call recording, WhatsApp Business API inbox) are only shown as locked tiles in the app."""

import frappe
from frappe import _
from frappe.utils import add_days, add_to_date, cint, get_datetime, getdate, now_datetime, strip_html

from sk_app import crm, marketing_list
from sk_app.logic import WorkItem

TALKED = ("Completed",)
NOT_CONNECTED = ("No Answer", "Busy")  # missed incoming, or customer did not pick up
REPEATS = ("", "Daily", "Weekly", "Monthly")
REMINDER_COLOR = "#c8102e"


# ---------- Calls and talk time ----------

def _period(start, end) -> list:
	return ["between", [f"{getdate(start)} 00:00:00", f"{getdate(end)} 23:59:59"]]


def call_totals(user: str, start, end=None) -> dict:
	"""Calls the user logged between two dates: count, answered, talk time (seconds), missed / not answered."""
	if not crm.installed():
		return {"calls": 0, "talked": 0, "talk_seconds": 0, "missed": 0, "whatsapp": 0, "mails": 0}
	rows = frappe.get_all("CRM Call Log", filters={"creation": _period(start, end or start)},
		or_filters={"caller": user, "receiver": user}, fields=["status", "duration"])
	period = _period(start, end or start)
	# SK 27-Oct: every call, WhatsApp and mail goes through the app and is counted per login (free route: WhatsApp is
	# the note saved after tapping 💬, mail is what was sent from the app)
	whatsapp = frappe.db.count("FCRM Note", {"owner": user, "creation": period, "title": ["like", "WhatsApp%"]}) \
		if frappe.db.exists("DocType", "FCRM Note") else 0
	whatsapp += marketing_list.sent_count(user, period)  # festival greetings to the Marketing list
	mails = frappe.db.count("Communication", {"owner": user, "creation": period, "communication_medium": "Email",
		"sent_or_received": "Sent"})
	return {"calls": len(rows), "talked": sum(1 for r in rows if r.status in TALKED),
		"talk_seconds": int(sum(r.duration or 0 for r in rows)), "missed": sum(1 for r in rows if r.status in NOT_CONNECTED),
		"whatsapp": whatsapp, "mails": mails}


def my_calls(user: str, days: int = 7) -> dict:
	"""Call history of the last `days` days with the lead / deal name, plus today's and this week's totals."""
	today = getdate()
	week_start = add_days(today, -today.weekday())
	rows = []
	if crm.installed():
		rows = frappe.get_all("CRM Call Log", filters={"creation": [">=", add_days(today, -cint(days))]},
			or_filters={"caller": user, "receiver": user},
			fields=["name", "type", "status", "duration", "to", "from", "start_time", "creation", "reference_doctype",
				"reference_docname", "note"], order_by="creation desc", limit=100)
	titles = {}
	for r in rows:
		key = (r.reference_doctype, r.reference_docname)
		if r.reference_docname and key not in titles and r.reference_doctype in crm.CRM_DOCTYPES:
			titles[key] = crm.label(r.reference_doctype, r.reference_docname)
		r["title"] = titles.get(key) or r.to
		r["note_text"] = frappe.db.get_value("FCRM Note", r.note, "title") if r.note else ""
	return {"today": call_totals(user, today), "week": call_totals(user, week_start, today), "calls": rows}


def team_calls(manager: str, day=None) -> dict:
	"""Calls and talk time of each team member for the day and the week, for the manager."""
	from sk_app.day_report import _team

	day = getdate(day)
	week_start = add_days(day, -day.weekday())
	people = []
	for p in _team(manager):
		people.append({"user": p.user, "full_name": p.full_name, "function": p.home,
			"day": call_totals(p.user, day), "week": call_totals(p.user, week_start, day)})
	people.sort(key=lambda p: -p["day"]["talk_seconds"])
	return {"date": str(day), "people": people}


def add_call(user: str, doctype: str, name: str, direction: str = "Outgoing", outcome: str | None = None,
		minutes=None, text: str | None = None) -> dict:
	"""A call made or received outside the app (customer called me, call from the phone's own list)."""
	if direction not in ("Outgoing", "Incoming"):
		frappe.throw(_("Unknown call type"))
	seconds = max(0, int(float(minutes or 0) * 60))
	return crm.log_contact(user, doctype, name, "Call", outcome, text, None, seconds, direction)


# ---------- Reminders ----------

def add_reminder(user: str, title: str, when: str, repeat: str | None = None, doctype: str | None = None,
		name: str | None = None, for_user: str | None = None) -> dict:
	"""Own reminder with date and time. On a lead / deal it is a CRM Task (shows in CRM too); otherwise a private
	calendar Event. A manager can give it to a team member (for_user)."""
	title = (title or "").strip()
	if not title:
		frappe.throw(_("Please say what to do"))
	at = get_datetime(when)
	if not at:
		frappe.throw(_("Please pick the date and time"))
	repeat = repeat or ""
	if repeat not in REPEATS:
		frappe.throw(_("Unknown repeat"))
	target = user
	if for_user and for_user != user:
		from sk_app.day_report import _team

		if for_user not in {p.user for p in _team(user)}:
			frappe.throw(_("{0} is not in your team").format(for_user), frappe.PermissionError)
		target = for_user
	if doctype and name and not repeat:
		crm._check(doctype, name, "write")
		task = frappe.get_doc({"doctype": "CRM Task", "title": title[:140], "reference_doctype": doctype,
			"reference_docname": name, "assigned_to": target, "due_date": at, "status": "Todo", "priority": "Medium"})
		task.insert()
		return {"doctype": "CRM Task", "name": task.name}
	ev = frappe.get_doc({"doctype": "Event", "subject": title, "starts_on": at, "ends_on": add_to_date(at, minutes=15),
		"event_type": "Private", "event_category": "Other", "color": REMINDER_COLOR, "status": "Open",
		"repeat_this_event": 1 if repeat else 0, "repeat_on": repeat or None, "send_reminder": 0})
	if repeat == "Weekly":
		ev.set(at.strftime("%A").lower(), 1)
	if doctype and name:
		crm._check(doctype, name)
		ev.reference_doctype, ev.reference_docname = doctype, name
	ev.insert(ignore_permissions=True)
	if target != user:
		ev.db_set("owner", target)
	return {"doctype": "Event", "name": ev.name}


def reminders_between(user: str, start, end) -> list[dict]:
	"""The user's reminders (own Events in SK red, repeats expanded, and CRM Tasks with a time) between two days."""
	from frappe.desk.doctype.event.event import get_events

	out = []
	for e in get_events(getdate(start), getdate(end)):
		if e.get("owner") != user or e.get("color") != REMINDER_COLOR:
			continue
		out.append({"doctype": "Event", "name": e.name, "title": e.subject, "at": str(get_datetime(e.starts_on)),
			"repeat": e.get("repeat_on") if e.get("repeat_this_event") else ""})
	if crm.installed():
		for t in frappe.get_all("CRM Task", filters={"assigned_to": user, "status": ["in", ["Backlog", "Todo", "In Progress"]],
				"due_date": _period(start, end)}, fields=["name", "title", "due_date", "reference_doctype", "reference_docname"]):
			out.append({"doctype": "CRM Task", "name": t.name, "title": t.title, "at": str(t.due_date),
				"ref_doctype": t.reference_doctype, "ref_name": t.reference_docname})
	out.sort(key=lambda r: r["at"])
	return out


def due_reminders(user: str, now=None, ahead_minutes: int = 1) -> list[dict]:
	"""Reminders whose time has come in the last hour (the open app buzzes for each once)."""
	now = get_datetime(now or now_datetime())
	since = add_to_date(now, hours=-1)
	until = add_to_date(now, minutes=ahead_minutes)
	return [r for r in reminders_between(user, since, until) if since <= get_datetime(r["at"]) <= until]


def reminder_items(user: str, now=None) -> list[WorkItem]:
	"""Today's own Event reminders for My Day and the guide card (CRM Tasks already come in through work.collect)."""
	now = get_datetime(now or now_datetime())
	soon = add_to_date(now, minutes=30)
	items = []
	for r in reminders_between(user, now.date(), now.date()):
		if r["doctype"] != "Event":
			continue
		at = get_datetime(r["at"])
		# top of the card only when its time is near; earlier in the day it waits its turn
		items.append(WorkItem("reminder", r["title"], "Event", r["name"], due=at, minutes=10, priority=1 if at <= soon else 3))
	return items


def done_reminder(user: str, doctype: str, name: str) -> bool:
	if doctype == "CRM Task":
		task = frappe.get_doc("CRM Task", name)
		if task.assigned_to != user:
			frappe.throw(_("Not your reminder"), frappe.PermissionError)
		task.status = "Done"
		task.save()
	elif doctype == "Event":
		ev = frappe.get_doc("Event", name)
		if ev.owner != user:
			frappe.throw(_("Not your reminder"), frappe.PermissionError)
		if not ev.repeat_this_event:
			ev.db_set("status", "Completed")
	else:
		frappe.throw(_("Unknown reminder"))
	return True


# ---------- Mail (free: company email connected in ERPNext) ----------

def mail_ready() -> bool:
	"""True when ERPNext has an outgoing Email Account, so the app can send mail."""
	return bool(frappe.db.exists("Email Account", {"enable_outgoing": 1}))


def _my_records(user: str) -> dict:
	"""{(doctype, name): title} of the user's open leads and deals."""
	return {(r["doctype"], r["name"]): r["title"] for r in crm.follow_up(user)}


def my_mail(user: str, limit: int = 50) -> dict:
	"""Emails sent to / received from the customers of the user's leads and deals, newest first."""
	recs = _my_records(user)
	rows = []
	for dt in crm.CRM_DOCTYPES:
		names = [n for d, n in recs if d == dt]
		if not names:
			continue
		rows += frappe.get_all("Communication", filters={"communication_medium": "Email", "reference_doctype": dt,
			"reference_name": ["in", names]}, fields=["name", "subject", "sender", "recipients", "sent_or_received",
			"communication_date", "reference_doctype", "reference_name", "text_content", "content", "seen", "has_attachment"],
			order_by="communication_date desc", limit=limit)
	rows.sort(key=lambda r: get_datetime(r.communication_date or "2000-01-01"), reverse=True)
	for r in rows:
		r["title"] = recs.get((r.reference_doctype, r.reference_name), r.reference_name)
		r["preview"] = (r.text_content or strip_html(r.content or ""))[:160]
		r.pop("content", None)
		r.pop("text_content", None)
	return {"ready": mail_ready(), "mails": rows[:limit]}


def mail_thread(doctype: str, name: str) -> list[dict]:
	crm._check(doctype, name)
	rows = frappe.get_all("Communication", filters={"communication_medium": "Email", "reference_doctype": doctype,
		"reference_name": name}, fields=["name", "subject", "sender", "recipients", "sent_or_received", "communication_date",
		"text_content", "content"], order_by="communication_date desc", limit=30)
	for r in rows:
		r["text"] = (r.text_content or strip_html(r.content or ""))[:3000]
		r.pop("content", None)
		r.pop("text_content", None)
	return rows


def send_mail(user: str, doctype: str, name: str, to: str, subject: str, message: str, files: list | None = None) -> str:
	"""Send an email to the customer from the app; it is saved on the lead / deal (CRM shows it too)."""
	from frappe.core.doctype.communication.email import make

	crm._check(doctype, name, "write")
	if not mail_ready():
		frappe.throw(_("Company email is not connected to ERPNext yet. Please ask the admin to set up the Email Account."))
	to = (to or "").strip()
	if not to or "@" not in to:
		frappe.throw(_("Please give the customer's email"))
	if not (subject or "").strip() or not (message or "").strip():
		frappe.throw(_("Please write the subject and the message"))
	attachments = []
	own = {(doctype, name)}
	if doctype == "CRM Lead":
		own.add(("CRM Deal", frappe.db.get_value("CRM Deal", {"lead": name})))
	for f in files or []:
		if ":" in f:  # "Quotation:SAL-QTN-0001": the ERPNext PDF of a quotation / sales order
			dt, dn = f.split(":", 1)
			if dt in crm.PDF_DOCTYPES and frappe.has_permission(dt, "read", dn):
				attachments.append(frappe.attach_print(dt, dn, file_name=dn))
			continue
		row = frappe.db.get_value("File", f, ["attached_to_doctype", "attached_to_name"], as_dict=True)
		if row and (row.attached_to_doctype, row.attached_to_name) in own:
			attachments.append(f)
	html = "<br>".join(frappe.utils.escape_html(line) for line in message.strip().splitlines())
	res = make(doctype=doctype, name=name, content=html, subject=subject.strip(), recipients=to, send_email=1,
		sender_full_name=frappe.utils.get_fullname(user), attachments=attachments)
	crm._mark_first_response(doctype, name)
	return res.get("name") if isinstance(res, dict) else res
