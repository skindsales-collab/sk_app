"""Minimum input → quote (SK 1-Nov-2026, all salespeople).

SK: "when Aditya sends input through the app he is not able to get a quote" (same for Rushi). The two AI pickups that
make quotes read boxes on the CRM Deal that the app never filled:
- the Machine Shifting quote AI picks a deal when Segment (custom_segment) is Machine Shifting / Job Work and Quote
  Status (ms_quote_status) is "Sent to Quote";
- the cabin design AI picks a deal when Design Status (custom_design_status) is "Sent to Design".
The person only types / speaks the requirement or adds a photo. The app fills those boxes itself:
- every deal: custom_segment follows the segment picked in the app (sk_segment);
- an open Non-Cabin deal with no quotation yet goes to "Sent to Quote";
- an open cabin deal with no quotation yet goes to "Sent to Design" when the stage "Sent to Design" is picked, or when
  it is new and has a photo, size or requirement;
- a new lead with input is routed at once (route_lead): a standard cabin with its size gets the rate-card quotation
  straight away, other cabins go to design, Non-Cabin goes to the quote AI.
When a quote is being made by hand in the app (frappe.flags.sk_quote_in_hand) nothing is sent to an AI, so there is
never a second quote for the same deal.
"""

import re

import frappe
from sk_app.writers import lead as lead_w
from frappe import _
from frappe.utils import add_days, get_datetime, now_datetime

from sk_app.segments import CABIN, NON_CABIN, main_of, sub_of

SENT_TO_QUOTE, NOT_REQUESTED = "Sent to Quote", "Not Requested"
SENT_TO_DESIGN, NOT_REQUIRED = "Sent to Design", "Not Required"
STANDARD = "Standard Cabin (GI / ACP)"
NEW_DAYS = 3  # a deal this new with input goes to design / quote by itself; older ones only when the stage is picked
# cabin type in the rate card from the words the salesperson used (default: office)
TYPE_WORDS = [("frp_security", ("frp",)), ("security", ("security", "guard", "watchman", "सिक्युरिटी", "सुरक्षा")),
	("toilet", ("toilet", "wc", "washroom", "टॉयलेट")), ("storage", ("storage", "store room", "godown", "स्टोअर"))]
SIZE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:ft|feet|foot|fit|'|फूट)?\s*(?:x|×|\*|by|बाय)\s*(\d+(?:\.\d+)?)", re.IGNORECASE)


# ---------- reading the free text ----------

def guess_size(text: str | None) -> tuple[float, float] | None:
	"""'20x10', '20 ft x 10 ft', "20' x 10'", '20 by 10' → (20, 10): the longer side is the length."""
	m = SIZE_RE.search(text or "")
	if not m:
		return None
	a, b = float(m.group(1)), float(m.group(2))
	if a <= 0 or b <= 0:
		return None
	return (max(a, b), min(a, b))


def guess_type(text: str | None) -> str:
	low = (text or "").lower()
	return next((key for key, words in TYPE_WORDS if any(w in low for w in words)), "office")


def needs_design(text: str | None) -> bool:
	"""Words that mean the cabin is outside the rate card (LGSF, ACP, container, modular...)."""
	low = (text or "").lower()
	return any(w in low for w in ("lgsf", "acp", "premium", "container", "modular", "labour camp", "g+1", "bunk", "kiosk", "puf", "eps"))


# ---------- the CRM Deal hook ----------

def _has(doc, field: str) -> bool:
	return bool(doc.meta.has_field(field))


def _closed(status: str | None) -> bool:
	if not status or not frappe.db.exists("DocType", "CRM Deal Status"):
		return False
	return frappe.db.get_value("CRM Deal Status", status, "type") in ("Won", "Lost")


def _has_quotation(deal: str | None) -> bool:
	if not deal or not frappe.get_meta("Quotation").has_field("crm_deal"):
		return False
	return bool(frappe.db.exists("Quotation", {"crm_deal": deal, "docstatus": ["<", 2]}))


def _is_new(doc) -> bool:
	return doc.is_new() or not doc.creation or get_datetime(doc.creation) >= add_days(now_datetime(), -NEW_DAYS)


def _has_input(doc) -> bool:
	"""A photo / file, a note (requirement) or a size on the deal or on its lead."""
	if any(doc.get(f) for f in ("custom_length_ft", "custom_special_requirements", "sk_product", "custom_design_notes") if _has(doc, f)):
		return True
	refs = [("CRM Deal", doc.name)] if doc.name and not doc.is_new() else []
	if doc.get("lead"):
		refs.append(("CRM Lead", doc.lead))
	for dt, name in refs:
		if frappe.db.exists("File", {"attached_to_doctype": dt, "attached_to_name": name}):
			return True
		if frappe.db.exists("DocType", "FCRM Note") and frappe.db.exists("FCRM Note", {"reference_doctype": dt, "reference_docname": name}):
			return True
	return False


def segment_value(doc, sub: str | None) -> str | None:
	"""custom_segment (Cabin / Machine Shifting / Job Work) for the app's segment."""
	if not sub or not _has(doc, "custom_segment"):
		return None
	options = (doc.meta.get_field("custom_segment").options or "").split("\n")
	main = main_of(sub)
	if main == CABIN:
		return "Cabin" if "Cabin" in options else None
	if main == NON_CABIN:
		return sub if sub in options else ("Machine Shifting" if "Machine Shifting" in options else None)
	return None


def on_deal_validate(doc, method=None):
	"""CRM Deal validate: fill the boxes the quote / design AIs read (see the module note)."""
	sub = sub_of(doc.get("sk_segment"))
	seg = segment_value(doc, sub)
	if seg and doc.get("custom_segment") != seg:
		doc.custom_segment = seg
	if frappe.flags.sk_quote_in_hand or _closed(doc.get("status")):
		return
	main = main_of(sub)
	if main == NON_CABIN and _has(doc, "ms_quote_status"):
		if (doc.get("ms_quote_status") or NOT_REQUESTED) == NOT_REQUESTED and not doc.get("ms_quote_no") \
				and _is_new(doc) and not _has_quotation(doc.name):
			doc.ms_quote_status = SENT_TO_QUOTE
	elif main == CABIN and _has(doc, "custom_design_status"):
		# SK 20-Nov: ticks from the requirement words and the budget from "Annual Revenue", before the design reads it
		from sk_app.writers.lead_rules import cabin_fill

		for f, v in cabin_fill(doc.as_dict()).items():
			if _has(doc, f):
				doc.set(f, v)
		if (doc.get("custom_design_status") or NOT_REQUIRED) != NOT_REQUIRED or _has_quotation(doc.name) or _has_order(doc.name):
			return
		picked = doc.get("status") == SENT_TO_DESIGN  # the CRM stage alone made nothing happen (Rushi, 30-Oct)
		if picked or (_is_new(doc) and _has_input(doc)):
			doc.custom_design_status = SENT_TO_DESIGN


def _has_order(deal: str) -> bool:
	"""SK 20-Nov: a deal whose Sales Order already exists (back-filled orders too) is not sent for design, so no
	'for design' mail goes out for it. Same lookup as the Won gate."""
	if not deal or not frappe.db.exists("CRM Deal", deal):
		return False
	from sk_app.gates import erp_docs

	frappe.local.sk_gate_docs = None
	return bool(erp_docs(deal)[1])


# ---------- a new lead from the app ----------

def _requirement(lead: str) -> str:
	if not frappe.db.exists("DocType", "FCRM Note"):
		return ""
	notes = frappe.get_all("FCRM Note", filters={"reference_doctype": "CRM Lead", "reference_docname": lead}, pluck="content")
	return "\n".join(re.sub(r"<[^>]*>", " ", n or "") for n in notes)


def _rate_card_quote(user: str, lead: str, text: str) -> dict | None:
	"""Standard cabin with its size in the requirement → the rate-card quotation now (a draft the salesperson can
	revise). None when the rate card cannot price it (then it goes to design)."""
	from sk_app import cabin_quote

	size = guess_size(text)
	if not size or needs_design(text):
		return None
	req = {"type": guess_type(text), "length": size[0], "width": size[1], "qty": 1, "options": {}, "km": 0, "crane": False}
	frappe.db.savepoint("sk_auto_quote")
	try:
		cabin_quote.price(req)  # outside the rate card (size / fixed sizes) → design
		r = cabin_quote.make(user, req, lead=lead)
	except Exception as e:
		frappe.db.rollback(save_point="sk_auto_quote")
		frappe.clear_messages()
		frappe.flags.sk_quote_in_hand = False
		frappe.log_error(f"SK App auto cabin quote {lead}")
		return {"failed": re.sub(r"<[^>]*>", "", str(e))[:200]}
	return r


def _copy_inputs(user: str, lead: str, deal: str):
	from sk_app import crm

	for f in frappe.get_all("File", filters={"attached_to_doctype": "CRM Lead", "attached_to_name": lead}, pluck="file_url"):
		if not frappe.db.exists("File", {"attached_to_doctype": "CRM Deal", "attached_to_name": deal, "file_url": f}):
			crm._attach(f, "CRM Deal", deal, user)
	if not frappe.db.exists("DocType", "FCRM Note"):
		return
	for n in frappe.get_all("FCRM Note", filters={"reference_doctype": "CRM Lead", "reference_docname": lead}, fields=["title", "content"]):
		if not frappe.db.exists("FCRM Note", {"reference_doctype": "CRM Deal", "reference_docname": deal, "content": n.content}):
			frappe.get_doc({"doctype": "FCRM Note", "title": n.title, "content": n.content, "reference_doctype": "CRM Deal",
				"reference_docname": deal}).insert(ignore_permissions=True)


def _send_for_quote(user: str, lead: str, seg: str | None, text: str) -> dict:
	"""Non-Cabin: the lead becomes a deal (Frappe CRM's own convert) that the Machine Shifting quote AI picks up."""
	from sk_app import crm

	deal, reason = lead_w._to_deal(user, lead, seg)
	if not deal:
		return {"route": "none", "reason": reason}
	_copy_inputs(user, lead, deal)
	doc = frappe.get_doc("CRM Deal", deal)
	if _has(doc, "ms_notes") and text.strip() and not doc.get("ms_notes"):
		doc.ms_notes = text.strip()[:2000]
	if _has(doc, "ms_site_photos") and not doc.get("ms_site_photos"):
		doc.ms_site_photos = frappe.db.get_value("File", {"attached_to_doctype": "CRM Deal", "attached_to_name": deal}, "file_url")
	if _has(doc, "ms_quote_status") and (doc.get("ms_quote_status") or NOT_REQUESTED) == NOT_REQUESTED and not _has_quotation(deal):
		doc.ms_quote_status = SENT_TO_QUOTE
	doc.flags.ignore_permissions = True
	doc.save()
	return {"route": "ms_quote", "deal": deal, "sent": doc.get("ms_quote_status") == SENT_TO_QUOTE}


def route_lead(user: str, lead: str) -> dict:
	"""After the app saves a new lead: no switch, no extra box. Returns what happened, for the 'lead saved' screen."""
	from sk_app import crm

	crm._check("CRM Lead", lead, "write")
	from sk_app import gates

	if not frappe.db.exists("CRM Deal", {"lead": lead}) and not gates.lead_qualified(lead):
		# SK 4-Nov (Nishant: "Call busy" typed as the requirement made a deal): a New lead stays a lead
		return {"route": "none", "reason": _(gates.R.QUALIFY_FIRST)}
	seg = sub_of(frappe.db.get_value("CRM Lead", lead, "sk_segment")) if frappe.get_meta("CRM Lead").has_field("sk_segment") else None
	product = frappe.db.get_value("CRM Lead", lead, "sk_product") if frappe.get_meta("CRM Lead").has_field("sk_product") else None
	text = "\n".join(x for x in (product or "", _requirement(lead)) if x)
	photo = frappe.db.exists("File", {"attached_to_doctype": "CRM Lead", "attached_to_name": lead})
	if not (text.strip() or photo):
		return {"route": "none", "reason": _("No requirement or photo yet: add it on the lead and it goes for its quote")}
	main = main_of(seg)
	if main == NON_CABIN:
		return _send_for_quote(user, lead, seg, text)
	if main != CABIN:
		return {"route": "none", "reason": _("Pick the segment first")}
	failed = None
	if seg == STANDARD:
		q = _rate_card_quote(user, lead, text)
		if q and not q.get("failed"):
			return {"route": "quote", "deal": frappe.db.get_value("CRM Deal", {"lead": lead}), "quotation": q["name"],
				"ref": q.get("ref"), "grand_total": q.get("grand_total"), "pdf": q.get("pdf"), "discount_waiting": q.get("discount_waiting")}
		failed = q and q.get("failed")
	r = lead_w.send_to_design(user, lead)
	return {"route": "design" if r.get("sent") else "none", "deal": r.get("deal"), "reason": r.get("reason"), "quote_failed": failed}


def after_input(user: str, doctype: str, name: str):
	"""A note / photo added later from the app: a lead not yet routed is routed now; a deal is checked again (the
	CRM Deal hook above). Never stops the note from saving: a problem is only logged."""
	try:
		if doctype == "CRM Lead":
			if not frappe.db.exists("CRM Deal", {"lead": name}):
				route_lead(user, name)
		elif doctype == "CRM Deal":
			doc = frappe.get_doc("CRM Deal", name)
			before = (doc.get("ms_quote_status"), doc.get("custom_design_status"))
			on_deal_validate(doc)
			if (doc.get("ms_quote_status"), doc.get("custom_design_status")) != before:
				doc.flags.ignore_permissions = True
				doc.save()
	except Exception:
		frappe.clear_messages()
		frappe.log_error(f"SK App quote routing after input {name}")
