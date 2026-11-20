"""The one CRM Lead writer (linear flow map, Flow 1 step 1). The app lead form and the mail scan (IndiaMART, JustDial,
GeM) each made a lead their own way; the mail scan skipped the mandatory fields silently. On the New path of Sales both
come through here: the same fields, owner, segment, first status, requirement note and photo, and the mandatory gate
reported the one way (the app still stops; a mail lead is saved and its gaps go to SK Rule Log so someone completes it).
Same inputs and outputs for the user (SK 4-Nov)."""

import frappe
from frappe import _

from sk_app.core.rules import report
from sk_app.writers.lead_rules import problems, shape


def write(user: str | None, data: dict, *, stop_on_missing: bool, requirement: str | None = None, photo: str | None = None,
		no_gstin=0):
	"""data: first_name, organization, mobile_no, email, source, segment, product, owner, status. Returns the saved lead."""
	from sk_app import crm, gates

	d = shape(data)
	if d["source"] and not frappe.db.exists("CRM Lead Source", d["source"]):
		from sk_app.lead_sources import _ensure_source

		_ensure_source(d["source"])
	found = problems(d)
	if found and stop_on_missing:
		gates.stop(_("Lead cannot be saved"), [(k[5:], w) for k, w in found])
	status = data.get("status")
	status = [status] if status and frappe.db.exists("CRM Lead Status", status) \
		else frappe.get_all("CRM Lead Status", order_by="position asc", pluck="name", limit=1)
	doc = frappe.new_doc("CRM Lead")
	doc.update({k: v for k, v in d.items() if v is not None and (k in ("first_name", "organization", "mobile_no", "email", "source", "lead_owner")
		or doc.meta.has_field(k))})
	doc.status = status[0] if status else "New"
	if frappe.utils.cint(no_gstin) and doc.meta.has_field(gates.NO_GSTIN):
		doc.set(gates.NO_GSTIN, 1)
	link_customer(doc, data.get("customer"))  # SK 14-Nov PR G: the picked customer, else the one the mobile / mail domain matches
	if not stop_on_missing:
		doc.flags.ignore_permissions = True
		doc.flags.ignore_mandatory = True
	doc.insert()
	report("Sales", doc, found, title=_("Lead data missing"))
	if (requirement or "").strip():
		frappe.get_doc({"doctype": "FCRM Note", "title": _("Requirement"), "content": requirement.strip(),
			"reference_doctype": "CRM Lead", "reference_docname": doc.name}).insert(ignore_permissions=True)
	if photo and user:
		crm._attach(photo, "CRM Lead", doc.name, user)
	return doc


def find_customer(mobile: str | None, email: str | None) -> str | None:
	"""The existing ERPNext customer of an incoming lead: same mobile (last 10 digits) on the Customer or one of its
	contacts, else the same company e-mail domain on a contact. Public mail domains never match."""
	from sk_app.writers.lead_rules import customer_match_keys

	keys = customer_match_keys(mobile, email)
	if keys["mobile10"]:
		cust = frappe.db.get_value("Customer", {"mobile_no": ["like", f"%{keys['mobile10']}"], "disabled": 0}, "name")
		if cust:
			return cust
		for contact in frappe.get_all("Contact", filters={"mobile_no": ["like", f"%{keys['mobile10']}"]}, pluck="name", limit=5):
			cust = frappe.db.get_value("Dynamic Link", {"parent": contact, "parenttype": "Contact", "link_doctype": "Customer"}, "link_name")
			if cust:
				return cust
	if keys["domain"]:
		for contact in frappe.get_all("Contact", filters={"email_id": ["like", f"%@{keys['domain']}"]}, pluck="name", limit=5):
			cust = frappe.db.get_value("Dynamic Link", {"parent": contact, "parenttype": "Contact", "link_doctype": "Customer"}, "link_name")
			if cust:
				return cust
	return None


def link_customer(doc, customer: str | None = None) -> str | None:
	"""Put the existing customer on the lead (sk_customer); fill the company name from it when the lead has none."""
	from sk_app.gates import CUSTOMER_LINK

	if not doc.meta.has_field(CUSTOMER_LINK):
		return None
	cust = customer if customer and frappe.db.exists("Customer", customer) else find_customer(doc.get("mobile_no"), doc.get("email"))
	if cust:
		doc.set(CUSTOMER_LINK, cust)
		if not doc.get("organization"):
			doc.organization = frappe.db.get_value("Customer", cust, "customer_name")
	return cust


# ---------- Plan A (SK 9-Nov): moved here unchanged from crm.py ----------
from frappe import _
from frappe.utils import add_to_date, now_datetime, time_diff_in_seconds
from sk_app.crm import CALL_LOG_STATUS, CALL_OUTCOMES, CONVERT, CRM_DOCTYPES, CUSTOMER_FIELD, DEAL_LIST_FUNCTIONS, REVISION_STATUS, SENT_STATUS, _attach, _check, _design_status_field, _design_target, _sent_files, installed
from sk_app.sales_screens import deal_customer_name, options
from sk_app.segments import CABIN, main_of, sub_of
import frappe
import re


def new_lead(user: str, first_name: str, mobile_no: str | None = None, organization: str | None = None,
		email: str | None = None, source: str | None = None, segment: str | None = None,
		requirement: str | None = None, photo: str | None = None, product: str | None = None, status: str | None = None,
		no_gstin=0, customer: str | None = None) -> str:
	if not installed():
		frappe.throw(_("Frappe CRM is not installed"))
	# point 2 + SK 28-Oct mandatory gate: the lead is saved only with a real name, contact person, mobile, segment and
	# source, so the right team gets it and nothing is named "Enquiry"
	from sk_app import gates

	segment = sub_of(segment)
	missing = gates.R.lead_missing({"first_name": first_name, "organization": organization, "mobile_no": mobile_no,
		"sk_segment": segment, "source": source if source and frappe.db.exists("CRM Lead Source", source) else None, "lead_owner": user})
	if missing:
		gates.stop(_("Lead cannot be saved"), missing)
	from sk_app.core.switch import use_new

	if use_new("Sales", user):  # rebuild: the one CRM Lead writer (linear flow map, Flow 1 step 1)
		from sk_app.writers import lead as lw

		return lw.write(user, {"first_name": first_name, "mobile_no": mobile_no, "organization": organization, "email": email,
			"source": source, "segment": segment, "product": product, "owner": user, "status": status, "customer": customer}, stop_on_missing=True,
			requirement=requirement, photo=photo, no_gstin=no_gstin).name
	# SK 27-Oct: the status is picked on the form (New by default)
	status = [status] if status and frappe.db.exists("CRM Lead Status", status) else frappe.get_all("CRM Lead Status", order_by="position asc", pluck="name", limit=1)
	doc = frappe.get_doc({
		"doctype": "CRM Lead", "first_name": first_name.strip(), "mobile_no": (mobile_no or "").strip() or None,
		"organization": (organization or "").strip() or None, "email": (email or "").strip() or None,
		"source": source or None, "lead_owner": user, "status": status[0] if status else "New",
	})
	if segment and doc.meta.has_field("sk_segment"):
		doc.sk_segment = segment
	if product and doc.meta.has_field("sk_product"):
		doc.sk_product = product[:140]
	if frappe.utils.cint(no_gstin) and doc.meta.has_field(gates.NO_GSTIN):
		doc.set(gates.NO_GSTIN, 1)  # SK 4-Nov: non-GST customer; its ERPNext customer is made Unregistered, no GSTIN asked
	link_customer(doc, customer)  # SK 14-Nov PR G (old path too)
	doc.insert()
	if (requirement or "").strip():
		frappe.get_doc({"doctype": "FCRM Note", "title": _("Requirement"), "content": requirement.strip(),
			"reference_doctype": "CRM Lead", "reference_docname": doc.name}).insert()
	_attach(photo, "CRM Lead", doc.name, user)
	return doc.name

def set_status(doctype: str, name: str, status: str, lost_reason: str | None = None, lost_notes: str | None = None) -> str:
	_check(doctype, name, "write")
	status_dt = "CRM Lead Status" if doctype == "CRM Lead" else "CRM Deal Status"
	if not frappe.db.exists(status_dt, status):
		frappe.throw(_("Unknown status {0}").format(status))
	doc = frappe.get_doc(doctype, name)
	doc.status = status
	# SK 20-Nov: Deal Loss / Junk Lead / Lost (status type Lost) need the reason ERPNext asks for; the app picks it with a note
	if frappe.get_cached_value(status_dt, status, "type") == "Lost":
		lost_reason, lost_notes = (lost_reason or "").strip(), (lost_notes or "").strip()
		if not lost_reason or not frappe.db.exists("CRM Lost Reason", lost_reason):
			frappe.throw(_("Pick the reason it was lost"))
		if lost_reason == "Other" and not lost_notes:
			frappe.throw(_("Write a short note for the reason 'Other'"))
		doc.lost_reason = lost_reason
		if lost_notes:
			doc.lost_notes = lost_notes
	doc.save()
	if doctype == "CRM Lead" and not frappe.db.exists("CRM Deal", {"lead": name}):
		from sk_app import gates, quote_pickup

		if gates.lead_qualified(name):
			# SK 4-Nov: the lead goes for its quote (deal + rate-card quote / design) once it is Qualified, not on save
			quote_pickup.after_input(frappe.session.user, doctype, name)
	return doc.status

def set_requirement(user: str, doctype: str, name: str, text: str) -> dict:
	"""SK 20-Nov: the requirement box on the lead / deal. Kept on the lead and its deal alike (sk_product), the full text
	also as a note (history), then the lead / deal goes for its quote as with any requirement."""
	_check(doctype, name, "write")
	text = (text or "").strip()
	if not text:
		frappe.throw(_("Please write the requirement"))
	short = " ".join(text.split())[:140]  # sk_product is a one-line field; the full text stays in the note
	targets = [(doctype, name)]
	if doctype == "CRM Lead":
		deal = frappe.db.get_value("CRM Deal", {"lead": name})
		if deal:
			targets.append(("CRM Deal", deal))
	else:
		lead = frappe.db.get_value("CRM Deal", name, "lead")
		if lead and frappe.db.exists("CRM Lead", lead):
			targets.append(("CRM Lead", lead))
	for dt, n in targets:
		if frappe.get_meta(dt).has_field("sk_product"):
			frappe.db.set_value(dt, n, "sk_product", short)
	add_note(user, doctype, name, _("Requirement: {0}").format(text))
	return {"requirement": short}

def add_note(user: str, doctype: str, name: str, text: str | None = None, photo: str | None = None, first_response: bool = True,
		talked: bool = False) -> str | None:
	_check(doctype, name, "write")
	text = (text or "").strip()
	if not text and not photo:
		frappe.throw(_("Please type, speak or attach something"))
	_attach(photo, doctype, name, user)
	note = None
	if text:
		note = frappe.get_doc({"doctype": "FCRM Note", "title": text[:80], "content": text,
			"reference_doctype": doctype, "reference_docname": name}).insert().name
	if first_response:
		# SK 20-Nov (Swati, "CNA" typed as a note stayed "No call yet"): a note on the lead is work done on it
		_mark_first_response(doctype, name)
	from sk_app import quote_pickup
	from sk_app.writers.lead_rules import note_moves_to_quote

	# SK 1-Nov: a requirement / photo added later also goes for its quote; SK 20-Nov: never a "CNA" (no answer) note
	if note_moves_to_quote(text, bool(photo), talked):
		quote_pickup.after_input(user, doctype, name)
	return note

def _mark_first_response(doctype: str, name: str):
	"""A call or message from the app counts as the first response (the 5-minute rule and the 'leads worked' KPI)."""
	meta = frappe.get_meta(doctype)
	if not meta.has_field("first_responded_on") or frappe.db.get_value(doctype, name, "first_responded_on"):
		return
	now = now_datetime()
	values = {"first_responded_on": now}
	if meta.has_field("first_response_time"):
		values["first_response_time"] = max(0, time_diff_in_seconds(now, frappe.db.get_value(doctype, name, "creation")))
	frappe.db.set_value(doctype, name, values)

def log_contact(user: str, doctype: str, name: str, channel: str, outcome: str | None = None,
		text: str | None = None, photo: str | None = None, duration: int | None = None, direction: str = "Outgoing") -> dict:
	"""Record what happened after the person tapped Call / WhatsApp / Email in the app.
	`duration` is the talk time in seconds the person confirmed (the app measures the time away on the call)."""
	_check(doctype, name, "write")
	if channel not in ("Call", "WhatsApp", "Email"):
		frappe.throw(_("Unknown channel"))
	if outcome and outcome not in CALL_OUTCOMES:
		frappe.throw(_("Unknown outcome"))
	text = (text or "").strip()
	seconds = max(0, int(duration or 0)) if outcome in (None, "Talked", "Call back later") else 0
	talk = f"{seconds // 60}:{seconds % 60:02d} min" if channel == "Call" and seconds else None
	summary = " · ".join(p for p in (channel if direction == "Outgoing" else _("Incoming call"), outcome, talk, text) if p)
	note = add_note(user, doctype, name, summary, photo, first_response=False,  # a wrong number is not a response
		talked=outcome == "Talked" and bool(text))  # a real talk with what was said may go for its quote
	if channel == "Call":
		# both are Phone fields; "0" when a number is not known (the user's own mobile may be blank in ERPNext)
		to = frappe.db.get_value(doctype, name, "mobile_no") or frappe.db.get_value(doctype, name, "phone") or "0"
		mine = frappe.db.get_value("User", user, ["mobile_no", "phone"], as_dict=True) or {}
		me = mine.get("mobile_no") or mine.get("phone") or "0"
		end = now_datetime()
		log = frappe.get_doc({
			"doctype": "CRM Call Log", "id": frappe.generate_hash(length=16), "type": direction,
			"status": CALL_LOG_STATUS.get(outcome, "Completed"),
			"from": me if direction == "Outgoing" else to, "to": to if direction == "Outgoing" else me,
			"telephony_medium": "Manual", "start_time": add_to_date(end, seconds=-seconds), "end_time": end,
			"duration": seconds, "note": note, "reference_doctype": doctype, "reference_docname": name,
		})
		# the person who handled the call: caller when we called, receiver when the customer called
		log.set("caller" if direction == "Outgoing" else "receiver", user)
		log.insert()
	if outcome != "Wrong number":
		_mark_first_response(doctype, name)
	return {"note": note}

def mark_file_sent(user: str, file: str, channel: str = "WhatsApp") -> bool:
	"""Record that the user sent a CRM file to the customer: Work Book entry (clears the reminder) + CRM note."""
	row = frappe.db.get_value("File", file, ["file_name", "attached_to_doctype", "attached_to_name"], as_dict=True)
	if not row or row.attached_to_doctype not in CRM_DOCTYPES:
		frappe.throw(_("File not found"))
	_check(row.attached_to_doctype, row.attached_to_name, "write")
	if file in _sent_files(user):
		return True
	text = _("Sent {0} to customer on {1}").format(row.file_name, channel)
	frappe.get_doc({"doctype": "SK Work Log", "user": user, "date": frappe.utils.getdate(), "entry_type": "Task Update",
		"description": text, "reference_doctype": "File", "reference_name": file, "status": "Done"}).insert(ignore_permissions=True)
	add_note(user, row.attached_to_doctype, row.attached_to_name, text)
	return True

def _to_deal(user: str, lead: str, seg=None) -> tuple[str | None, str | None]:
	"""Frappe CRM's own Convert (deal.lead links back), owned by the salesperson, with the lead's segment."""
	deal = frappe.db.get_value("CRM Deal", {"lead": lead})
	if not deal:
		from sk_app import gates

		if not gates.lead_qualified(lead):
			return None, _(gates.R.QUALIFY_FIRST)  # SK 4-Nov: no deal before the customer is spoken to
		frappe.db.savepoint("sk_to_deal")
		try:
			deal = frappe.get_attr(CONVERT)(lead)
		except Exception as e:
			frappe.db.rollback(save_point="sk_to_deal")
			frappe.clear_messages()
			frappe.log_error("SK App convert to deal")
			return None, re.sub(r"<[^>]*>", "", str(e))[:200] or _("Could not make the deal")
		deal = deal if isinstance(deal, str) else frappe.db.get_value("CRM Deal", {"lead": lead})
	doc = frappe.get_doc("CRM Deal", deal)
	changed = False
	if doc.meta.has_field("deal_owner") and not doc.get("deal_owner"):
		doc.deal_owner, changed = user, True
	if seg and doc.meta.has_field("sk_segment") and not doc.get("sk_segment"):
		doc.sk_segment, changed = seg, True
	if changed:
		doc.flags.ignore_permissions = True
		doc.save()
	return deal, None

def convert_lead(user: str, lead: str) -> dict:
	"""SK 27-Oct: "Convert to Deal option not showing" in the app: the same Convert as the CRM screen."""
	_check("CRM Lead", lead, "write")
	seg = frappe.db.get_value("CRM Lead", lead, "sk_segment") if frappe.get_meta("CRM Lead").has_field("sk_segment") else None
	deal, reason = _to_deal(user, lead, seg)
	if not deal:
		frappe.throw(reason)
	for f in frappe.get_all("File", filters={"attached_to_doctype": "CRM Lead", "attached_to_name": lead}, pluck="file_url"):
		_attach(f, "CRM Deal", deal, user)
	return {"deal": deal}

def send_to_design(user: str, lead: str) -> dict:
	"""New Lead "Send to design" switch (SK OK 26-Oct): the AI design pickup reads CRM Deals only, so the lead becomes a
	deal with Frappe CRM's own conversion (deal.lead links back), owned by the salesperson, Design Status "Sent to
	Design", with the lead's photos / sketch and requirement notes copied onto the deal. Cabin segments only."""
	_check("CRM Lead", lead, "write")
	seg = frappe.db.get_value("CRM Lead", lead, "sk_segment") if frappe.get_meta("CRM Lead").has_field("sk_segment") else None
	if seg and main_of(seg) != CABIN:
		return {"sent": False, "reason": _("Only Cabin enquiries go to design")}
	deal, reason = _to_deal(user, lead, seg)
	if not deal:
		return {"sent": False, "reason": reason}
	doc = frappe.get_doc("CRM Deal", deal)
	field = _design_status_field("CRM Deal")
	status_set = bool(field and SENT_STATUS in (doc.meta.get_field(field).options or "").split("\n"))
	if status_set:
		doc.set(field, SENT_STATUS)
	doc.flags.ignore_permissions = True
	doc.save()
	for f in frappe.get_all("File", filters={"attached_to_doctype": "CRM Lead", "attached_to_name": lead}, pluck="file_url"):
		_attach(f, "CRM Deal", deal, user)
	for n in frappe.get_all("FCRM Note", filters={"reference_doctype": "CRM Lead", "reference_docname": lead}, fields=["title", "content"]):
		if not frappe.db.exists("FCRM Note", {"reference_doctype": "CRM Deal", "reference_docname": deal, "content": n.content}):
			frappe.get_doc({"doctype": "FCRM Note", "title": n.title, "content": n.content, "reference_doctype": "CRM Deal",
				"reference_docname": deal}).insert(ignore_permissions=True)
	return {"sent": True, "deal": deal, "status_set": status_set}

def request_correction(user: str, doctype: str, name: str, text: str | None = None, file: str | None = None,
		photo: str | None = None) -> dict:
	"""Salesperson's drawing correction from the phone: CRM comment (+ marked-up photo) and Design Status
	'Revision Requested', so the design AI sends the next revision, which then alerts the salesperson at once."""
	doctype, name = _design_target(doctype, name)
	_check(doctype, name, "write")
	text = (text or "").strip()
	if not text and not photo:
		frappe.throw(_("Please type, speak or photo the correction"))
	drawing = frappe.db.get_value("File", file, "file_name") if file else None
	_attach(photo, doctype, name, user)
	body = _("Drawing correction") + (f" ({drawing})" if drawing else "") + ":\n" + (text or _("see attached photo"))
	doc = frappe.get_doc(doctype, name)
	doc.add_comment("Comment", body)
	field = _design_status_field(doctype)
	status_set = False
	if field:
		doc.set(field, REVISION_STATUS)
		doc.save()
		status_set = True
	frappe.get_doc({"doctype": "SK Work Log", "user": user, "date": frappe.utils.getdate(), "entry_type": "Task Update",
		"description": body[:500], "reference_doctype": doctype, "reference_name": name, "status": "Done"}).insert(ignore_permissions=True)
	return {"doctype": doctype, "name": name, "status_set": status_set}

def alert_owner(user: str):
	"""Background job: a fresh 'what to do now' card for the owner, built with their own permissions."""
	from sk_app import guide

	current = frappe.session.user
	frappe.set_user(user)
	try:
		guide.make_card(user, use_claude=False)
	finally:
		frappe.set_user(current)

def ensure_deal_customer_field():
	if not frappe.db.exists("DocType", "CRM Deal"):
		return
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	create_custom_fields({"CRM Deal": [{"fieldname": CUSTOMER_FIELD, "label": "Customer Name", "fieldtype": "Data",
		"read_only": 1, "in_list_view": 1, "in_standard_filter": 1, "insert_after": "organization"}]}, update=True)

def backfill_deal_customers():
	if not frappe.db.exists("DocType", "CRM Deal") or not frappe.get_meta("CRM Deal").has_field(CUSTOMER_FIELD):
		return
	for name in frappe.get_all("CRM Deal", filters={CUSTOMER_FIELD: ["is", "not set"]}, pluck="name"):
		frappe.db.set_value("CRM Deal", name, CUSTOMER_FIELD, deal_customer_name(frappe.get_doc("CRM Deal", name)), update_modified=False)

def ensure_deal_list_views(users: list[str] | None = None):
	"""Frappe CRM shows each person's standard deals list (CRM View Settings, is_standard) when one exists: give the
	sales people one with Customer Name first, or add the column to the one they already have."""
	if not frappe.db.exists("DocType", "CRM View Settings") or not frappe.get_meta("CRM Deal").has_field(CUSTOMER_FIELD):
		return
	from frappe.model.base_document import get_controller

	from sk_app.store import _users_with_function

	defaults = get_controller("CRM Deal").default_list_data()
	col = {"label": "Customer Name", "type": "Data", "key": CUSTOMER_FIELD, "width": "12rem"}
	users = users or list(dict.fromkeys(u for f in DEAL_LIST_FUNCTIONS for u in _users_with_function(f)))
	for user in users:
		name = frappe.db.get_value("CRM View Settings", {"dt": "CRM Deal", "type": "list", "is_standard": 1, "user": user})
		if name:
			view = frappe.get_doc("CRM View Settings", name)
			columns = frappe.parse_json(view.columns or "[]") or list(defaults["columns"])
			rows = frappe.parse_json(view.rows or "[]") or list(defaults["rows"])
		else:
			view = frappe.get_doc({"doctype": "CRM View Settings", "dt": "CRM Deal", "type": "list", "is_standard": 1,
				"user": user, "label": "List", "load_default_columns": 0})
			columns, rows = list(defaults["columns"]), list(defaults["rows"])
		if any(c.get("key") == CUSTOMER_FIELD for c in columns):
			continue
		view.columns = frappe.as_json([col] + columns)
		view.rows = frappe.as_json(rows + [CUSTOMER_FIELD] if CUSTOMER_FIELD not in rows else rows)
		view.flags.ignore_permissions = True
		view.save()

def setup_deal_customer_column():
	try:
		ensure_deal_customer_field()
		backfill_deal_customers()
		ensure_deal_list_views()
	except Exception:
		frappe.log_error("SK App deals Customer Name column")


def save_site_checklist(user: str, deal: str, answers: dict, note: str | None = None, photo: str | None = None) -> str | None:
	"""Machine Shifting site survey: 8 yes/no points + photo, kept as one note on the deal (feeds the quote pickup)."""
	from sk_app.writers.lead_rules import site_checklist_missing, site_checklist_text

	missing = site_checklist_missing(answers, photo)
	if missing:
		frappe.throw(_("Please fill: {0}").format(", ".join(missing)))
	return add_note(user, "CRM Deal", deal, site_checklist_text(answers, note), photo)
