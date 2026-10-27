"""Marketing list (SK 27-Oct-2026: "we need to add potential customer in marketing list, we will send them Happy New
Year, Happy Diwali etc. greetings for maintaining connection & sending promotions; it is not a lead").

Each person is an ERPNext Contact with sk_marketing = 1 (filter "Marketing list" on the Contact list). Contacts with an
e-mail are also members of the Email Group "Marketing list", so one Newsletter in ERPNext mails the whole list (free).
Greetings go one by one from the person's own WhatsApp (wa.me, free); each send is saved as a comment on the Contact
and counted for that login. When someone shows interest, "Make lead" opens New Lead filled in.
"""

import frappe
from frappe import _
from frappe.utils import getdate

FIELD = "sk_marketing"
CITY = "sk_city"
GROUP = "Marketing list"
SENT = "WhatsApp greeting"
FUNCTIONS = ("Sales", "Marketing")

FESTIVALS = {
	"new_year": "Happy New Year {year}! Wishing you and your family a healthy, happy and successful year.",
	"sankranti": "Happy Makar Sankranti! Til-gul ghya, god god bola. Best wishes for a sweet and successful year.",
	"republic": "Happy Republic Day! Proud to be building India together.",
	"holi": "Happy Holi! May your life be filled with colours of joy and success.",
	"gudi_padwa": "Happy Gudi Padwa! Wishing you a prosperous new year ahead.",
	"independence": "Happy Independence Day! Jai Hind.",
	"ganesh": "Ganpati Bappa Morya! Happy Ganesh Chaturthi to you and your family.",
	"dussehra": "Happy Dussehra! May this Vijayadashami bring you success in every work.",
	"diwali": "Happy Diwali! Wishing you and your family a bright, safe and prosperous Diwali and a happy new year.",
	"promotion": "",
}


def ensure_setup():
	if not frappe.db.exists("DocType", "Contact"):
		return
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	create_custom_fields({"Contact": [
		{"fieldname": FIELD, "label": "Marketing list", "fieldtype": "Check", "insert_after": "company_name", "in_standard_filter": 1,
			"description": "Potential customer for greetings and promotions (not a lead). Added from the SK App."},
		{"fieldname": CITY, "label": "City", "fieldtype": "Data", "insert_after": FIELD},
	]}, update=True)
	frappe.clear_cache(doctype="Contact")
	if not frappe.db.exists("Email Group", GROUP):
		frappe.get_doc({"doctype": "Email Group", "title": GROUP}).insert(ignore_permissions=True)


def _need(user: str):
	from sk_app.store import need

	need(user, *FUNCTIONS)


def _digits(mobile: str | None) -> str:
	d = "".join(c for c in (mobile or "") if c.isdigit())
	return d[-10:] if len(d) >= 10 else d


def _by_mobile(mobile: str) -> str | None:
	d = _digits(mobile)
	if len(d) < 10:
		return None
	# numbers in ERPNext are typed many ways (+91 98220 11223, 098220-11223): compare digits only
	rows = frappe.db.sql("""select parent from `tabContact Phone` where parenttype = 'Contact'
		and replace(replace(replace(replace(phone, ' ', ''), '-', ''), '+', ''), '(', '') like %s limit 1""", (f"%{d}",))
	return rows[0][0] if rows else None


def _join_group(email: str | None):
	if not email or not frappe.db.exists("Email Group", GROUP):
		return
	if not frappe.db.exists("Email Group Member", {"email_group": GROUP, "email": email}):
		frappe.get_doc({"doctype": "Email Group Member", "email_group": GROUP, "email": email}).insert(ignore_permissions=True)


def add(user: str, name: str, mobile: str | None = None, company: str | None = None, city: str | None = None,
		email: str | None = None, photo: str | None = None) -> dict:
	"""Add a person to the Marketing list. The same mobile already in ERPNext is put on the list, not made twice."""
	_need(user)
	name, mobile, email = (name or "").strip(), (mobile or "").strip(), (email or "").strip()
	if not name:
		frappe.throw(_("Please give the person's name"))
	if not mobile and not email:
		frappe.throw(_("Please give a mobile number or e-mail"))
	old = _by_mobile(mobile)
	if old:
		values = {FIELD: 1}
		if city and not frappe.db.get_value("Contact", old, CITY):
			values[CITY] = city.strip()
		frappe.db.set_value("Contact", old, values)
		_join_group(email or frappe.db.get_value("Contact", old, "email_id"))
		return {"name": old, "existing": 1}
	parts = name.split(" ", 1)
	doc = frappe.get_doc({"doctype": "Contact", "first_name": parts[0], "last_name": parts[1] if len(parts) > 1 else None,
		"company_name": (company or "").strip() or None, FIELD: 1, CITY: (city or "").strip() or None})
	if mobile:
		doc.append("phone_nos", {"phone": _digits(mobile) if len(_digits(mobile)) == 10 else mobile, "is_primary_mobile_no": 1})
	if email:
		doc.append("email_ids", {"email_id": email, "is_primary": 1})
	from sk_app.store import attach, insert_for

	insert_for(doc, user)  # Sales users may not create Contacts in ERPNext; kept in their name
	attach(photo, "Contact", doc.name, user)
	_join_group(email)
	return {"name": doc.name, "existing": 0}


def _sent(names: list[str]) -> dict:
	out = {}
	if not names:
		return out
	for c in frappe.get_all("Comment", filters={"reference_doctype": "Contact", "reference_name": ["in", names], "comment_type": "Info",
			"content": ["like", f"{SENT}%"]}, fields=["reference_name", "content", "creation"], order_by="creation asc", limit=0):
		x = out.setdefault(c.reference_name, {"n": 0, "last": None, "what": None})
		x["n"] += 1
		x["last"], x["what"] = str(c.creation), c.content.split(":", 1)[-1].strip()
	return out


def people(user: str, q: str | None = None) -> dict:
	"""The whole Marketing list (shared by Sales and Marketing): not greeted yet first."""
	_need(user)
	if not frappe.get_meta("Contact").has_field(FIELD):
		return {"rows": [], "today": 0, "newsletter": "/app/newsletter/new", "group": None}
	or_filters = None
	if (q or "").strip():
		like = f"%{q.strip()}%"
		or_filters = [["first_name", "like", like], ["last_name", "like", like], ["company_name", "like", like],
			["mobile_no", "like", like], [CITY, "like", like]]
	rows = frappe.get_all("Contact", filters={FIELD: 1}, or_filters=or_filters, fields=["name", "first_name", "last_name", "company_name",
		"mobile_no", "phone", "email_id", CITY, "owner"], order_by="creation desc", limit=0)
	sent = _sent([r.name for r in rows])
	out = []
	for r in rows:
		s = sent.get(r.name, {"n": 0, "last": None, "what": None})
		out.append({"doctype": "Contact", "name": r.name, "person": " ".join(filter(None, [r.first_name, r.last_name])),
			"title": r.company_name or " ".join(filter(None, [r.first_name, r.last_name])), "company": r.company_name,
			"mobile": r.mobile_no or r.phone, "email": r.email_id, "city": r.get(CITY), "added_by": r.owner,
			"greetings": s["n"], "last": s["last"], "last_what": s["what"]})
	out.sort(key=lambda r: (r["greetings"] > 0, r["last"] or ""))
	today = frappe.db.count("Comment", {"reference_doctype": "Contact", "comment_type": "Info", "owner": user,
		"content": ["like", f"{SENT}%"], "creation": [">=", getdate()]})
	return {"rows": out, "today": today, "newsletter": "/app/newsletter/new",
		"group": f"/app/email-group/{GROUP}" if frappe.db.exists("Email Group", GROUP) else None,
		"erpnext": "/app/contact?sk_marketing=1"}


def message(user: str, festival: str, text: str | None = None) -> str:
	if festival not in FESTIVALS:
		frappe.throw(_("Unknown greeting"))
	body = (text or "").strip() or FESTIVALS[festival].format(year=getdate().year + (1 if getdate().month == 12 else 0))
	if not body:
		frappe.throw(_("Please type the promotion message"))
	who = frappe.db.get_value("User", user, "full_name") or ""
	return f"{body}\n\n{who + ', ' if who else ''}SK Ind Tech Solutions Pvt Ltd"


def greet(user: str, contact: str, festival: str, text: str | None = None) -> dict:
	"""The WhatsApp text for one person, saved as sent on the Contact (counted for this login)."""
	_need(user)
	if not frappe.db.get_value("Contact", contact, FIELD):
		frappe.throw(_("Not on the Marketing list"))
	msg = message(user, festival, text)
	c = frappe.get_doc({"doctype": "Comment", "comment_type": "Info", "reference_doctype": "Contact", "reference_name": contact,
		"content": f"{SENT}: {festival.replace('_', ' ').title()}", "comment_email": user})
	c.insert(ignore_permissions=True)
	frappe.db.set_value("Comment", c.name, "owner", user, update_modified=False)
	return {"message": msg, "mobile": frappe.db.get_value("Contact", contact, "mobile_no") or frappe.db.get_value("Contact", contact, "phone")}


def lead_made(user: str, contact: str, lead: str) -> dict:
	"""After "Make lead": the lead is linked on the Contact; the person stays on the list for greetings."""
	_need(user)
	frappe.get_doc({"doctype": "Comment", "comment_type": "Info", "reference_doctype": "Contact", "reference_name": contact,
		"content": f"Made lead {lead}", "comment_email": user}).insert(ignore_permissions=True)
	return {"contact": contact, "lead": lead}


def sent_count(user: str, period) -> int:
	return frappe.db.count("Comment", {"reference_doctype": "Contact", "comment_type": "Info", "owner": user,
		"content": ["like", f"{SENT}%"], "creation": period})
