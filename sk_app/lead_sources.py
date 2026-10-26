"""Auto leads from IndiaMART, JustDial and GeM, free routes only (change list point 14, SK 26-Oct-2026).

SK's IndiaMART plan has no Leads API (a paid add-on), so leads come from the mails these portals already send to
cabin@skind.tech: every 5 minutes new mails are read and become Frappe CRM leads with the right owner, source and
segment. A lead from a mobile seen in the last 90 days is added to that lead instead of making a second one. The
IndiaMART Lead Manager Excel export can also be uploaded in the app.
"""

import re

import frappe
from frappe import _
from frappe.utils import add_days, add_to_date, get_datetime, now_datetime, strip_html

SOURCES = {
	"IndiaMART": {"domains": ("indiamart.com",), "setting": "indiamart_mail"},
	"JustDial": {"domains": ("justdial.com", "jdmart.com"), "setting": "justdial_mail"},
	"GeM": {"domains": ("gem.gov.in",), "setting": "gem_mail"},
}
NON_CABIN_WORDS = ("machine shifting", "shifting", "rigging", "dismantl", "relocation", "job work", "machining", "crane")
DUPLICATE_DAYS = 90

# labels used by the portals in their mails / exports (lower case, without ':')
LABELS = {
	"name": ("buyer name", "sender name", "caller name", "customer name", "contact person", "name"),
	"mobile": ("mobile", "mobile no", "mobile number", "sender mobile", "caller phone", "caller number", "phone", "contact number",
		"contact no", "call"),
	"email": ("email", "email id", "sender email", "e-mail"),
	"organization": ("company", "company name", "organization", "organisation", "buyer organisation", "ministry", "department"),
	"city": ("city", "location", "area", "address", "sender city"),
	"requirement": ("requirement", "requirement details", "message", "enquiry", "query", "product", "product name", "subject",
		"item category", "category", "looking for", "description"),
}


def _clean_mobile(text: str) -> str | None:
	for m in re.finditer(r"(?:\+?91[\s-]*)?([6-9]\d{4})[\s-]*(\d{5})", text or ""):
		return m.group(1) + m.group(2)
	return None


def source_of(sender: str | None, subject: str | None = None) -> str | None:
	low = (sender or "").lower()
	for name, spec in SOURCES.items():
		if any(d in low for d in spec["domains"]):
			return name
	subj = (subject or "").lower()
	if "indiamart" in subj:
		return "IndiaMART"
	if "justdial" in subj:
		return "JustDial"
	if "gem bid" in subj or "gem/20" in subj:
		return "GeM"
	return None


def parse_mail(subject: str | None, body: str | None, source: str | None = None) -> dict:
	"""Name, mobile, e-mail, company, city and requirement from a portal mail ("Label: value" lines, any order)."""
	text = strip_html(body or "").replace("\r", "")
	found = {}
	for line in text.split("\n"):
		key, sep, value = line.partition(":")
		if not sep or not value.strip():
			continue
		key = key.strip().lower().strip("*- ")
		for field, labels in LABELS.items():
			if field not in found and key in labels:
				found[field] = value.strip()[:200]
	mobile = _clean_mobile(found.get("mobile") or "") or _clean_mobile(text)
	email = found.get("email")
	if not email:
		m = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", text)
		email = m.group(0) if m and not any(d in m.group(0).lower() for s in SOURCES.values() for d in s["domains"]) else None
	out = {
		"first_name": (found.get("name") or "").split(",")[0].strip()[:80],
		"mobile_no": mobile,
		"email": email if email and "@" in email else None,
		"organization": (found.get("organization") or "").strip()[:140],
		"city": found.get("city"),
		"requirement": found.get("requirement") or (subject or "").strip(),
	}
	if source == "GeM":
		bid = re.search(r"GEM/\d{4}/[A-Z]/\d+", text + " " + (subject or ""), re.I)
		out["first_name"] = out["first_name"] or (f"GeM bid {bid.group(0)}" if bid else "GeM bid")
		end = re.search(r"bid end date(?:/time)?\s*:?\s*([^\n]+)", text, re.I)
		if end:
			out["requirement"] = f"{out['requirement']} (bid ends {end.group(1).strip()[:40]})"
	if not out["first_name"]:
		m = re.search(r"\bfrom\s+([A-Z][\w. ]{2,40})", subject or "")
		out["first_name"] = m.group(1).strip() if m else (out["organization"] or "Enquiry")
	return out


def segment_of(text: str) -> str:
	low = (text or "").lower()
	if "job work" in low or "machining" in low:
		return "Job Work"
	if any(w in low for w in NON_CABIN_WORDS):
		return "Machine Shifting"
	return "Cabin"


def _fallback_owner() -> str | None:
	from sk_app.logins import profile_functions

	for u in frappe.get_all("SK App User", filters={"enabled": 1}, pluck="user"):
		if "Management" in profile_functions(u):
			return u
	return None


def owner_for(source: str | None, segment: str) -> str | None:
	"""Who gets the lead (SK): machine shifting / job work → Aditya; IndiaMART / JustDial (digital) → Pranali;
	other cabin enquiries and GeM → Rushi, who gives them to the team."""
	s = frappe.get_cached_doc("SK App Settings")
	if segment in ("Machine Shifting", "Job Work") and s.get("lead_owner_noncabin"):
		return s.lead_owner_noncabin
	if source in ("IndiaMART", "JustDial") and s.get("lead_owner_digital"):
		return s.lead_owner_digital
	return s.get("lead_owner_cabin") or _fallback_owner()


def _ensure_source(name: str | None):
	if name and frappe.db.exists("DocType", "CRM Lead Source") and not frappe.db.exists("CRM Lead Source", name):
		frappe.get_doc({"doctype": "CRM Lead Source", "source_name": name}).insert(ignore_permissions=True)


def find_duplicate(mobile: str | None, email: str | None = None) -> str | None:
	"""A lead from the same mobile (or e-mail) in the last 90 days."""
	since = add_days(now_datetime(), -DUPLICATE_DAYS)
	for field, value in (("mobile_no", mobile), ("email", email)):
		if value:
			like = f"%{value[-10:]}" if field == "mobile_no" else value
			name = frappe.db.get_value("CRM Lead", {field: ["like", like], "creation": [">=", since]}, "name", order_by="creation desc")
			if name:
				return name
	return None


def make_lead(data: dict, source: str | None, owner: str | None = None, note: str | None = None) -> dict:
	"""New CRM Lead from portal data, or a note on the earlier lead of the same customer."""
	if not frappe.db.exists("DocType", "CRM Lead"):
		frappe.throw(_("Frappe CRM is not installed"))
	text = " ".join(str(data.get(k) or "") for k in ("requirement", "organization"))
	segment = data.get("segment") or segment_of(text)
	requirement = "\n".join(p for p in (data.get("requirement"), data.get("city") and f"City: {data['city']}", note) if p)
	old = find_duplicate(data.get("mobile_no"), data.get("email"))
	if old:
		frappe.get_doc({"doctype": "FCRM Note", "title": f"Again from {source or 'mail'}"[:80], "content": requirement or text,
			"reference_doctype": "CRM Lead", "reference_docname": old}).insert(ignore_permissions=True)
		return {"lead": old, "new": False}
	_ensure_source(source)
	status = frappe.get_all("CRM Lead Status", order_by="position asc", pluck="name", limit=1)
	doc = frappe.get_doc({"doctype": "CRM Lead", "first_name": data.get("first_name") or "Enquiry",
		"mobile_no": data.get("mobile_no"), "email": data.get("email"), "organization": data.get("organization") or None,
		"source": source, "lead_owner": owner or owner_for(source, segment), "status": status[0] if status else "New"})
	if doc.meta.has_field("sk_segment"):
		doc.sk_segment = segment
	doc.flags.ignore_permissions = True
	doc.flags.ignore_mandatory = True
	doc.insert()
	if requirement:
		frappe.get_doc({"doctype": "FCRM Note", "title": _("Requirement"), "content": requirement,
			"reference_doctype": "CRM Lead", "reference_docname": doc.name}).insert(ignore_permissions=True)
	return {"lead": doc.name, "new": True}


def _settings():
	return frappe.get_single("SK App Settings")


def scan(since=None) -> dict:
	"""Scheduler, every 5 minutes: portal mails received since the last check become leads."""
	s = _settings()
	if not s.get("auto_leads") or not frappe.db.exists("DocType", "CRM Lead"):
		return {"made": 0}
	start = get_datetime(since or s.get("last_lead_scan") or add_days(now_datetime(), -2))
	now = now_datetime()
	rows = frappe.get_all("Communication", filters={"communication_medium": "Email", "sent_or_received": "Received",
		"creation": [">=", add_to_date(start, minutes=-10)], "sk_mail_status": ["in", ["", None, "New"]]},
		fields=["name", "sender", "subject", "content", "text_content", "reference_doctype"], order_by="creation asc", limit=200)
	made = 0
	for r in rows:
		source = source_of(r.sender, r.subject)
		if not source or not s.get(SOURCES[source]["setting"]) or r.reference_doctype == "CRM Lead":
			continue
		try:
			data = parse_mail(r.subject, r.text_content or r.content, source)
			res = make_lead(data, source)
			frappe.db.set_value("Communication", r.name, {"reference_doctype": "CRM Lead", "reference_name": res["lead"],
				"sk_mail_status": "Lead made"}, update_modified=False)
			made += 1 if res["new"] else 0
		except Exception:
			frappe.log_error(f"SK App lead from mail {r.name}")
	frappe.db.set_single_value("SK App Settings", "last_lead_scan", now)
	return {"made": made, "checked": len(rows)}


# ---------- IndiaMART Lead Manager export (Excel / CSV) ----------

HEADER_KEYS = {
	"first_name": ("sender name", "buyer name", "name", "contact person"),
	"mobile_no": ("sender mobile", "mobile", "mobile no", "phone", "sender phone", "contact number"),
	"email": ("sender email", "email", "email id"),
	"organization": ("company name", "sender company", "company", "organization"),
	"city": ("city", "sender city", "location"),
	"requirement": ("query message", "message", "enquiry", "requirement", "product name", "subject", "query product name"),
}


def _rows_from_file(file_url: str) -> list[list]:
	f = frappe.get_doc("File", {"file_url": file_url})
	content = f.get_content()
	name = (f.file_name or "").lower()
	if name.endswith(".csv"):
		import csv
		import io

		text = content.decode("utf-8-sig", "ignore") if isinstance(content, bytes) else content
		return [r for r in csv.reader(io.StringIO(text))]
	from frappe.utils.xlsxutils import read_xls_file_from_attached_file, read_xlsx_file_from_attached_file

	if name.endswith(".xls"):
		return read_xls_file_from_attached_file(content)
	return read_xlsx_file_from_attached_file(fcontent=content)


def _map_header(row) -> dict:
	cols = {}
	for i, cell in enumerate(row):
		key = str(cell or "").strip().lower().replace("_", " ")
		for field, names in HEADER_KEYS.items():
			if field not in cols and key in names:
				cols[field] = i
	return cols


def upload(user: str, file_url: str, source: str = "IndiaMART") -> dict:
	"""Leads from an exported list: every row with a mobile or e-mail becomes a lead (or a note on the earlier one)."""
	from sk_app.logins import profile_functions

	if not {"Sales", "Marketing", "Management", "AI"} & set(profile_functions(user)):
		frappe.throw(_("Only Sales, Marketing, Management or AI & ERP can upload leads"), frappe.PermissionError)
	if source not in SOURCES and source != "Other":
		frappe.throw(_("Unknown source"))
	rows = _rows_from_file(file_url)
	head_at, cols = None, {}
	for i, row in enumerate(rows[:15]):
		cols = _map_header(row)
		if "mobile_no" in cols or "email" in cols:
			head_at = i
			break
	if head_at is None:
		frappe.throw(_("No 'Mobile' or 'Email' column found in the file"))
	made = added = skipped = 0
	leads = []
	for row in rows[head_at + 1:]:
		get = lambda f: str(row[cols[f]]).strip() if f in cols and cols[f] < len(row) and row[cols[f]] not in (None, "") else ""
		data = {f: get(f) for f in HEADER_KEYS}
		data["mobile_no"] = _clean_mobile(data["mobile_no"]) or None
		if not data["mobile_no"] and not data["email"]:
			skipped += 1
			continue
		res = make_lead(data, source)
		leads.append(res["lead"])
		if res["new"]:
			made += 1
		else:
			added += 1
	return {"made": made, "added_to_old": added, "skipped": skipped, "leads": leads[:50]}


def status(user: str) -> dict:
	"""Lead Sources page (Samir / SK): each source on / off, leads today and this month, last lead, mailboxes set up."""
	from sk_app.logins import profile_functions

	if user != "Administrator" and not {"AI", "Management"} & set(profile_functions(user)):
		frappe.throw(_("Only the AI & ERP desk or the CEO can open this"), frappe.PermissionError)
	s = _settings()
	today = frappe.utils.getdate()
	month_start = today.replace(day=1)
	have_crm = frappe.db.exists("DocType", "CRM Lead")
	out = []
	for name, spec in SOURCES.items():
		count = lambda since: frappe.db.count("CRM Lead", {"source": name, "creation": [">=", since]}) if have_crm else 0
		last = frappe.db.get_value("CRM Lead", {"source": name}, "creation", order_by="creation desc") if have_crm else None
		out.append({"source": name, "on": bool(s.get("auto_leads") and s.get(spec["setting"])), "setting": spec["setting"],
			"today": count(today), "month": count(month_start), "last": str(last) if last else None})
	boxes = []
	from sk_app.mailbox import team_boxes

	for box, who in team_boxes().items():
		acc = frappe.db.get_value("Email Account", {"email_id": box}, ["name", "enable_incoming", "enable_outgoing"], as_dict=True)
		boxes.append({"email": box, "who": who, "set_up": bool(acc), "incoming": bool(acc and acc.enable_incoming),
			"outgoing": bool(acc and acc.enable_outgoing)})
	return {"sources": out, "last_scan": str(s.get("last_lead_scan") or "") or None, "auto": bool(s.get("auto_leads")),
		"mailboxes": boxes, "owners": {k: s.get(k) for k in ("lead_owner_digital", "lead_owner_cabin", "lead_owner_noncabin")}}


def switch(user: str, setting: str, on) -> dict:
	from sk_app.logins import profile_functions

	if not {"AI", "Management"} & set(profile_functions(user)):
		frappe.throw(_("Only the AI & ERP desk or the CEO can switch lead sources"), frappe.PermissionError)
	if setting not in ("auto_leads", *(spec["setting"] for spec in SOURCES.values())):
		frappe.throw(_("Unknown switch"))
	frappe.db.set_single_value("SK App Settings", setting, 1 if str(on) in ("1", "true", "True") else 0)
	return {"ok": True}
