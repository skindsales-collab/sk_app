"""Frappe CRM on the phone: follow-up list, lead / deal detail, new lead, status, notes, call log, files, ERP PDFs.

Every read goes through frappe.get_list / has_permission and every write through doc.insert / doc.save with the
user's own CRM permissions (Sales User / Sales Manager), so the app can never see or change more than CRM allows.
"""

import re

import frappe
from frappe import _
from frappe.utils import add_to_date, get_datetime, now_datetime, strip_html, time_diff_in_seconds

from sk_app import lead_status
from sk_app.segments import SUB_SEGMENTS as SEGMENTS
from sk_app.segments import TREE as SEGMENT_TREE
from sk_app.segments import CABIN, main_of, sub_of

CALL_OUTCOMES = ["Talked", "No answer", "Busy", "Missed", "Call back later", "Wrong number"]
CALL_LOG_STATUS = {"Talked": "Completed", "Call back later": "Completed", "No answer": "No Answer", "Busy": "Busy", "Missed": "No Answer",
	"Wrong number": "Failed"}
CRM_DOCTYPES = ("CRM Lead", "CRM Deal")
CLOSED_LEAD_TYPES = ("Won", "Lost", "Junk")
OPEN_TASK_STATUSES = ("Backlog", "Todo", "In Progress")
PDF_DOCTYPES = ("Quotation", "Sales Order")


def installed() -> bool:
	return bool(frappe.db.exists("DocType", "CRM Lead"))


def _check(doctype: str, name: str, ptype: str = "read"):
	if doctype not in CRM_DOCTYPES:
		frappe.throw(_("Not a CRM record"))
	if not frappe.has_permission(doctype, ptype, name) and not _in_my_team(doctype, name):
		frappe.throw(_("No access to {0}").format(name), frappe.PermissionError)


def _in_my_team(doctype: str, name: str) -> bool:
	"""A sales manager opens his own people's leads / deals from Team Leads without the ERPNext Sales Manager role
	(that role shows every lead of the company in CRM, SK 26-Oct: each person sees only their own)."""
	from sk_app.day_report import _team

	owner = frappe.db.get_value(doctype, name, "lead_owner" if doctype == "CRM Lead" else "deal_owner")
	return bool(owner) and owner in {p.user for p in _team(frappe.session.user)}


def options() -> dict:
	if not installed():
		return {"crm": False}
	return {
		"crm": True,
		"lead_statuses": lead_status.app_statuses(),  # SK 27-Oct: his 8 steps
		"deal_statuses": frappe.get_all("CRM Deal Status", fields=["name", "type"], order_by="position asc"),
		"sources": frappe.get_all("CRM Lead Source", pluck="name", order_by="name asc"),
		"segments": SEGMENTS,
		"segment_tree": SEGMENT_TREE,
		"products": _product_names(),
		"call_outcomes": CALL_OUTCOMES,
	}


def label(doctype: str, name: str) -> str:
	"""Customer · product for a lead / deal, never the CRM number when a name is known (SK 26-Oct point 7)."""
	if doctype not in ("CRM Lead", "CRM Deal") or not name or not frappe.db.exists(doctype, name):
		return name or ""
	meta = frappe.get_meta(doctype)
	fields = [f for f in ("organization", "lead_name", "first_name", "sk_customer_name", "sk_product", "sk_segment") if meta.has_field(f)]
	v = frappe.db.get_value(doctype, name, fields, as_dict=True) or {}
	who = v.get("organization") or v.get("sk_customer_name") or v.get("lead_name") or v.get("first_name") or name
	what = v.get("sk_product") or v.get("sk_segment")
	return f"{who} · {what}" if what else who


def _product_names() -> list:
	from sk_app.products import names_for

	try:
		return names_for()
	except Exception:
		return []


def _closed(status_doctype: str) -> list[str]:
	return frappe.get_all(status_doctype, filters={"type": ["in", CLOSED_LEAD_TYPES]}, pluck="name")


def _open_tasks_by_doc(user: str) -> dict:
	rows = frappe.get_all("CRM Task", filters={"assigned_to": user, "status": ["in", OPEN_TASK_STATUSES]},
		fields=["reference_doctype", "reference_docname", "title", "due_date"], order_by="due_date asc")
	out = {}
	for r in rows:
		out.setdefault((r.reference_doctype, r.reference_docname), r)
	return out


def _last_activity(doctype: str, names: list[str]) -> dict:
	"""Latest note or call per record, as {name: {"on": datetime, "text": str}}."""
	if not names:
		return {}
	out = {}
	notes = frappe.get_all("FCRM Note", filters={"reference_doctype": doctype, "reference_docname": ["in", names]},
		fields=["reference_docname", "title", "creation"], order_by="creation desc")
	calls = frappe.get_all("CRM Call Log", filters={"reference_doctype": doctype, "reference_docname": ["in", names]},
		fields=["reference_docname", "status", "type", "creation"], order_by="creation desc")
	for r in notes:
		out.setdefault(r.reference_docname, {"on": r.creation, "text": r.title})
	for r in calls:
		cur = out.get(r.reference_docname)
		if not cur or r.creation > cur["on"]:
			out[r.reference_docname] = {"on": r.creation, "text": f"{r.type} call: {r.status}"}
	return out


def follow_up(user: str, for_manager: bool = False) -> list[dict]:
	"""All open leads and deals of the user with their next due action, overdue first.
	for_manager: read for the person's manager (Team Leads), who may not hold CRM rights on others' records."""
	# people outside Sales / Marketing (Accounts, Store, factory ...) have no CRM access: nothing to follow up
	if not installed() or not frappe.has_permission("CRM Lead", "read", user=user):
		return []
	get = frappe.get_all if for_manager else frappe.get_list
	now = now_datetime()
	tasks = _open_tasks_by_doc(user)
	rows = []
	closed_leads = _closed("CRM Lead Status")
	from sk_app.cold_calls import not_cold

	lead_filters = {"lead_owner": user, "converted": 0, **not_cold()}
	if closed_leads:
		lead_filters["status"] = ["not in", closed_leads]
	for r in get("CRM Lead", filters=lead_filters, limit_page_length=0, order_by="modified desc",
			fields=["name", "lead_name", "organization", "status", "mobile_no", "phone", "email", "source",
				"response_by", "first_responded_on", "creation"]):
		task = tasks.get(("CRM Lead", r.name))
		due, why = None, None
		if task and task.due_date:
			due, why = task.due_date, task.title
		elif not r.first_responded_on:
			due, why = r.response_by or add_to_date(r.creation, minutes=5), _("First call")
		rows.append({"doctype": "CRM Lead", "name": r.name, "title": r.organization or r.lead_name or r.name,
			"person": r.lead_name, "status": r.status, "mobile": r.mobile_no or r.phone, "email": r.email,
			"source": r.source, "due": due, "next": why, "new": not r.first_responded_on})
	closed_deals = _closed("CRM Deal Status")
	deal_filters = {"deal_owner": user}
	if closed_deals:
		deal_filters["status"] = ["not in", closed_deals]
	for r in [] if not frappe.has_permission("CRM Deal", "read", user=user) else get("CRM Deal", filters=deal_filters, limit_page_length=0, order_by="modified desc",
			fields=["name", "organization", "lead_name", "status", "mobile_no", "phone", "email", "next_step",
				"expected_closure_date", "deal_value"]):
		task = tasks.get(("CRM Deal", r.name))
		due, why = (task.due_date, task.title) if task and task.due_date else (r.expected_closure_date, r.next_step)
		rows.append({"doctype": "CRM Deal", "name": r.name, "title": r.organization or r.lead_name or r.name,
			"person": r.lead_name, "status": r.status, "mobile": r.mobile_no or r.phone, "email": r.email,
			"due": due, "next": why or r.next_step, "value": r.deal_value, "new": False})
	for dt in CRM_DOCTYPES:
		last = _last_activity(dt, [r["name"] for r in rows if r["doctype"] == dt])
		for r in rows:
			if r["doctype"] == dt and r["name"] in last:
				r["last"] = last[r["name"]]
	for r in rows:
		r["overdue"] = bool(r["due"] and get_datetime(r["due"]) < now)
	far = get_datetime("2999-12-31")
	rows.sort(key=lambda r: (not r["overdue"], not r["new"], get_datetime(r["due"]) if r["due"] else far))
	return rows


def _files(doctype: str, name: str) -> list[dict]:
	rows = frappe.get_all("File", filters={"attached_to_doctype": doctype, "attached_to_name": name, "is_folder": 0},
		fields=["name", "file_name", "file_url", "owner", "creation"], order_by="creation desc")
	for r in rows:
		r["for_customer"] = _for_customer(r.file_name)
	return rows


def _pdf(doctype: str, name: str) -> str:
	return f"/api/method/frappe.utils.print_format.download_pdf?doctype={doctype.replace(' ', '%20')}&name={name}"


def _erp_docs(deal: dict | None) -> dict:
	"""Quotations and Sales Orders linked to a deal (ERPNext CRM integration on the same site)."""
	out = {"quotations": [], "sales_orders": []}
	if not deal:
		return out
	quotes = []
	if frappe.has_permission("Quotation", "read") and frappe.get_meta("Quotation").has_field("crm_deal"):
		quotes = frappe.get_list("Quotation", filters={"crm_deal": deal["name"], "docstatus": ["<", 2]},
			fields=["name", "status", "grand_total", "net_total", "transaction_date", "docstatus"], order_by="creation desc")
	out["quotations"] = [{**q, "pdf": _pdf("Quotation", q.name)} for q in quotes]
	customer = deal.get("erpnext_customer")
	if not customer and frappe.get_meta("Customer").has_field("crm_deal"):
		customer = frappe.db.get_value("Customer", {"crm_deal": deal["name"]})
	if customer and frappe.has_permission("Sales Order", "read"):
		orders = frappe.get_list("Sales Order", filters={"customer": customer, "docstatus": ["<", 2]},
			fields=["name", "status", "grand_total", "transaction_date", "delivery_date", "docstatus"],
			order_by="creation desc", limit_page_length=20)
		out["sales_orders"] = [{**o, "pdf": _pdf("Sales Order", o.name)} for o in orders]
	return out


def _quote_pending(deal: dict | None) -> dict | None:
	"""SK 28-Oct: a quote file on the deal that is not an ERPNext Quotation yet (the salesperson types its amount once)."""
	if not deal:
		return None
	from sk_app import deal_quotes

	try:
		return deal_quotes.pending(deal["name"])
	except Exception:
		return None


DETAIL_FIELDS = {
	"CRM Lead": ["name", "lead_name", "first_name", "organization", "status", "mobile_no", "phone", "email", "source",
		"industry", "job_title", "lead_owner", "converted", "first_responded_on", "response_by", "creation", "website"],
	"CRM Deal": ["name", "lead_name", "organization", "status", "mobile_no", "phone", "email", "source", "deal_owner",
		"next_step", "expected_closure_date", "deal_value", "probability", "lead", "creation", "erpnext_customer"],
}


def _products(doctype: str, name: str) -> list:
	"""Point 8: product cards for this customer (the product asked first), for one-tap sharing."""
	try:
		from sk_app.products import for_record

		return for_record(doctype, name)
	except Exception:
		frappe.log_error("SK App product cards")
		return []


def detail(doctype: str, name: str) -> dict:
	_check(doctype, name)
	meta = frappe.get_meta(doctype)
	fields = [f for f in DETAIL_FIELDS[doctype] + ["sk_segment", "sk_product", "sk_cold"] if f == "name" or meta.has_field(f)]
	doc = frappe.db.get_value(doctype, name, fields, as_dict=True)
	ref = {"reference_doctype": doctype, "reference_docname": name}
	deal = None
	if doctype == "CRM Deal":
		deal = doc
	elif doc.get("converted"):
		deal = frappe.db.get_value("CRM Deal", {"lead": name}, ["name", "erpnext_customer"], as_dict=True)
	notes = frappe.get_all("FCRM Note", filters=ref, fields=["title", "content", "owner", "creation"],
		order_by="creation desc", limit=30)
	# CRM comments (design questions, drawing corrections) shown with the notes, newest first
	for c in frappe.get_all("Comment", filters={"reference_doctype": doctype, "reference_name": name, "comment_type": "Comment"},
			fields=["content", "owner", "creation"], order_by="creation desc", limit=30):
		text = strip_html(c.content or "")
		notes.append(frappe._dict(title="💬 " + text[:80], content=text, owner=c.owner, creation=c.creation))
	notes.sort(key=lambda n: n.creation, reverse=True)
	for n in notes:
		n["content"] = strip_html(n.content or "")[:1000]
	field = _design_status_field(doctype)
	if field:
		doc["design_status"] = frappe.db.get_value(doctype, name, field)
	from sk_app import erp_flow, gates

	erp = _erp_docs(deal)
	customer = erp_flow.customer_of(deal["name"]) if deal else None
	return {
		"gate": _gate(doctype, name),
		"customer": customer and {"name": customer, "missing": [t for _k, t in gates.customer_missing(customer)]},
		"doctype": doctype,
		"doc": doc,
		"notes": notes,
		"tasks": frappe.get_all("CRM Task", filters=ref, fields=["name", "title", "status", "due_date", "assigned_to"],
			order_by="due_date asc", limit=30),
		"calls": frappe.get_all("CRM Call Log", filters=ref, fields=["type", "status", "duration", "caller", "creation"],
			order_by="creation desc", limit=30),
		"files": _files(doctype, name) + (_files("CRM Deal", deal["name"]) if deal and doctype == "CRM Lead" else []),
		"deal": deal and deal["name"],
		"products": _products(doctype, name),
		**erp,
		"quote_pending": _quote_pending(deal),
		"crm_url": f"/crm/{'leads' if doctype == 'CRM Lead' else 'deals'}/{name}",
	}


def _gate(doctype: str, name: str) -> dict | None:
	"""SK 28-Oct mandatory gate on the detail screen: missing data and locked status chips (never breaks the screen)."""
	from sk_app import gates

	try:
		return gates.gate_for(doctype, frappe.get_doc(doctype, name))
	except Exception:
		frappe.log_error("SK App mandatory gate")
		return None


def _attach(file_url: str | None, doctype: str, name: str, user: str):
	"""Attach a file the user uploaded from the phone (upload_file without a parent) to the CRM record."""
	if not file_url:
		return
	file_name = frappe.db.get_value("File", {"file_url": file_url, "owner": user, "attached_to_name": ["is", "not set"]})
	if file_name:
		frappe.db.set_value("File", file_name, {"attached_to_doctype": doctype, "attached_to_name": name})
		return
	# Swati 26-Oct: the same photo sent twice, or a file ERPNext already had, has no free File row: attach a copy
	src = frappe.db.get_value("File", {"file_url": file_url}, ["file_name", "is_private"], as_dict=True)
	if not src or frappe.db.exists("File", {"file_url": file_url, "attached_to_doctype": doctype, "attached_to_name": name}):
		return
	frappe.get_doc({"doctype": "File", "file_url": file_url, "file_name": src.file_name, "is_private": src.is_private,
		"attached_to_doctype": doctype, "attached_to_name": name}).insert(ignore_permissions=True)


def new_lead(user: str, first_name: str, mobile_no: str | None = None, organization: str | None = None,
		email: str | None = None, source: str | None = None, segment: str | None = None,
		requirement: str | None = None, photo: str | None = None, product: str | None = None, status: str | None = None) -> str:
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
	doc.insert()
	if (requirement or "").strip():
		frappe.get_doc({"doctype": "FCRM Note", "title": _("Requirement"), "content": requirement.strip(),
			"reference_doctype": "CRM Lead", "reference_docname": doc.name}).insert()
	_attach(photo, "CRM Lead", doc.name, user)
	return doc.name


def set_status(doctype: str, name: str, status: str) -> str:
	_check(doctype, name, "write")
	status_dt = "CRM Lead Status" if doctype == "CRM Lead" else "CRM Deal Status"
	if not frappe.db.exists(status_dt, status):
		frappe.throw(_("Unknown status {0}").format(status))
	doc = frappe.get_doc(doctype, name)
	doc.status = status
	doc.save()
	return doc.status


def add_note(user: str, doctype: str, name: str, text: str | None = None, photo: str | None = None) -> str | None:
	_check(doctype, name, "write")
	text = (text or "").strip()
	if not text and not photo:
		frappe.throw(_("Please type, speak or attach something"))
	_attach(photo, doctype, name, user)
	if not text:
		return None
	note = frappe.get_doc({"doctype": "FCRM Note", "title": text[:80], "content": text,
		"reference_doctype": doctype, "reference_docname": name}).insert()
	return note.name


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
	note = add_note(user, doctype, name, summary, photo)
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


def new_files(user: str, hours: int = 48) -> list[dict]:
	"""Files (drawings, photos, PDFs) others attached to the user's open leads and deals recently."""
	if not installed():
		return []
	names = [(r["doctype"], r["name"], r["title"]) for r in follow_up(user)]
	if not names:
		return []
	titles = {(dt, n): t for dt, n, t in names}
	cutoff = add_to_date(now_datetime(), hours=-hours)
	out = []
	for dt in CRM_DOCTYPES:
		docnames = [n for d, n, _t in names if d == dt]
		if not docnames:
			continue
		for f in frappe.get_all("File", filters={"attached_to_doctype": dt, "attached_to_name": ["in", docnames],
				"owner": ["!=", user], "creation": [">=", cutoff], "is_folder": 0},
				fields=["name", "file_name", "file_url", "attached_to_name", "creation", "owner"], order_by="creation desc", limit=20):
			out.append(frappe._dict({**f, "doctype": dt, "title": titles[(dt, f.attached_to_name)]}))
	return out


# Files the AI or design team attach that are for the customer: PDFs, but not internal costing / BOM / shop drawings
INTERNAL_FILE_WORDS = ("bom", "costing", "cost_sheet", "manufacturing", "internal", "job_card")


def _for_customer(file_name: str) -> bool:
	name = (file_name or "").lower()
	return name.endswith(".pdf") and not any(w in name for w in INTERNAL_FILE_WORDS)


def _sent_files(user: str) -> set:
	return set(frappe.get_all("SK Work Log", filters={"user": user, "reference_doctype": "File"}, pluck="reference_name"))


def files_to_send(user: str, hours: int = 48) -> list[dict]:
	"""Customer PDFs (e.g. the AI's customer drawing) newly attached to the user's leads / deals and not yet sent."""
	sent = _sent_files(user)
	return [f for f in new_files(user, hours) if _for_customer(f.file_name) and f.name not in sent]


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


REVISION_STATUS = "Revision Requested"


def _design_status_field(doctype: str) -> str | None:
	"""The Design Status select on CRM Deal / Lead used by the AI design flow (found by its 'Revision Requested' option)."""
	for df in frappe.get_meta(doctype).fields:
		if df.fieldtype == "Select" and REVISION_STATUS in (df.options or "").split("\n"):
			return df.fieldname
	return None


SENT_STATUS = "Sent to Design"
CONVERT = "crm.fcrm.doctype.crm_lead.crm_lead.convert_to_deal"


def _to_deal(user: str, lead: str, seg=None) -> tuple[str | None, str | None]:
	"""Frappe CRM's own Convert (deal.lead links back), owned by the salesperson, with the lead's segment."""
	deal = frappe.db.get_value("CRM Deal", {"lead": lead})
	if not deal:
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


def _design_target(doctype: str, name: str) -> tuple[str, str]:
	"""Corrections go to the deal when the lead is converted, because design works on the deal."""
	if doctype == "CRM Lead":
		deal = frappe.db.get_value("CRM Deal", {"lead": name})
		if deal:
			return "CRM Deal", deal
	return doctype, name


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


def on_file_attached(doc, method=None):
	"""A customer PDF (e.g. the AI's drawing) was attached to a lead / deal: alert its owner at once, not at the next hourly card."""
	if doc.attached_to_doctype not in CRM_DOCTYPES or not doc.attached_to_name or not _for_customer(doc.file_name):
		return
	field = "lead_owner" if doc.attached_to_doctype == "CRM Lead" else "deal_owner"
	owner = frappe.db.get_value(doc.attached_to_doctype, doc.attached_to_name, field)
	if owner and owner != doc.owner and frappe.db.exists("SK App User", {"user": owner, "enabled": 1}):
		frappe.enqueue("sk_app.crm.alert_owner", user=owner, enqueue_after_commit=True, queue="short")


def alert_owner(user: str):
	"""Background job: a fresh 'what to do now' card for the owner, built with their own permissions."""
	from sk_app import guide

	current = frappe.session.user
	frappe.set_user(user)
	try:
		guide.make_card(user, use_claude=False)
	finally:
		frappe.set_user(current)


def own_file_content(user: str, file_url: str) -> tuple[bytes, str]:
	"""Bytes and media type of an image the user just uploaded (for Claude to read a visiting card)."""
	name = frappe.db.get_value("File", {"file_url": file_url, "owner": user})
	if not name:
		frappe.throw(_("File not found"), frappe.PermissionError)
	ext = file_url.rsplit(".", 1)[-1].lower()
	media = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp", "gif": "image/gif"}.get(ext)
	if not media:
		frappe.throw(_("Please send a photo (JPG or PNG)"))
	content = frappe.get_doc("File", name).get_content()
	if len(content) > 5 * 1024 * 1024:
		frappe.throw(_("Photo is too large (max 5 MB)"))
	return content, media


SHARE_DAYS = 30


def share_link(doctype: str, name: str) -> dict:
	"""Absolute PDF link a customer can open without login (Frappe Document Share Key, valid 30 days)."""
	if doctype not in PDF_DOCTYPES:
		frappe.throw(_("Only Quotation and Sales Order PDFs can be sent"))
	if not frappe.has_permission(doctype, "read", name):
		frappe.throw(_("No access to {0}").format(name), frappe.PermissionError)
	doc = frappe.get_doc(doctype, name)
	key = doc.get_document_share_key(expires_on=frappe.utils.add_days(frappe.utils.today(), SHARE_DAYS))
	url = frappe.utils.get_url(f"{_pdf(doctype, name)}&key={key}")
	party = doc.get("customer_name") or doc.get("party_name") or doc.get("customer") or ""
	return {"url": url, "file_name": f"{name}.pdf", "pdf": _pdf(doctype, name),
		"message": _("Dear {0}, please find {1} {2} from SK Ind Tech Solutions: {3}").format(party, _(doctype), name, url)}


# Swati 26-Oct (item 8): a Customer name column on the deals list, in Frappe CRM (/crm/deals) and in My Deals
CUSTOMER_FIELD = "sk_customer_name"
DEAL_LIST_FUNCTIONS = ("Sales", "Marketing", "Machine Shifting", "Management")


def ensure_deal_customer_field():
	if not frappe.db.exists("DocType", "CRM Deal"):
		return
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	create_custom_fields({"CRM Deal": [{"fieldname": CUSTOMER_FIELD, "label": "Customer Name", "fieldtype": "Data",
		"read_only": 1, "in_list_view": 1, "in_standard_filter": 1, "insert_after": "organization"}]}, update=True)


def deal_customer_name(doc) -> str | None:
	"""The person the salesperson talks to (primary contact, else the lead's name), else the company."""
	contacts = doc.get("contacts") or []
	primary = next((c for c in contacts if c.get("is_primary")), contacts[0] if contacts else None)
	person = (primary and primary.get("full_name")) or " ".join(x for x in (doc.get("first_name"), doc.get("last_name")) if x) \
		or doc.get("lead_name")
	if not person and doc.get("lead"):
		lead = frappe.db.get_value("CRM Lead", doc.lead, ["first_name", "last_name", "lead_name"], as_dict=True) or {}
		person = lead.get("lead_name") or " ".join(x for x in (lead.get("first_name"), lead.get("last_name")) if x)
	return (person or doc.get("organization") or "").strip()[:140] or None


def set_deal_customer(doc, method=None):
	if doc.meta.has_field(CUSTOMER_FIELD):
		doc.set(CUSTOMER_FIELD, deal_customer_name(doc))


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
