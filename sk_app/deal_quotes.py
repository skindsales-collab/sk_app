"""Every quote is an ERPNext Quotation (SK 28-Oct-2026: "many quote generated & sent by app & Claude but it is not
coming in ERP").

Quotes made outside the app's quote screen reached ERPNext only as files on the CRM deal: the AI design team's
BOM / costing / quote Excel ("CabinNN_..._BOM_Costing_Quote_RevN.xlsx", quote value on the deal) and quote PDFs /
Excels a salesperson uploads ("SK_Quotation_....pdf"). Now:

- SK 23-Nov: a quote file on a deal, or the design quote value set on it, gives the deal owner a task (and a note on
  the deal in the app) to make the quote in the app with its scope and specification lines; the outside PDF is never
  the quote and is never attached to a Quotation (before: a draft "as per the attached quotation" at the quote value);
- every hour (and on deploy) any deal missed is caught up.
A deal that already has a Quotation is left as it is (a revision is made in the app).
"""

import re

import frappe
from sk_app.writers import order as order_w
from frappe import _
from frappe.utils import add_days, flt, now_datetime, nowdate


VALUE_FIELD = "custom_design_quote_value"  # set by the AI design team's bom-push (--quote-value, ex-GST)
# SK 28-Oct "all quote ... cabin or machine shifting or job work or any other should be routed through ERP": the
# machine-shifting quote tool keeps its ex-GST total on the deal too
VALUE_FIELDS = (VALUE_FIELD, "ms_quote_total")
SERVICE_ITEM = "SK-JOB"
TASK_MARK = "[Quote] "


def ensure_setup():
	if not frappe.db.exists("DocType", "Quotation") or frappe.db.exists("Item", SERVICE_ITEM):
		return
	from sk_app.cabin_quote import hsn_fields

	from sk_app.writers.item import get_or_make

	get_or_make(SERVICE_ITEM, "Job / service (as per quotation)", hsn_like="job")


from sk_app.file_rules import is_quote_file  # SK 16-Nov: only a PDF is the quote (pure rule, tested)


def _ready() -> bool:
	return bool(frappe.db.exists("DocType", "CRM Deal") and frappe.db.exists("DocType", "Quotation")
		and frappe.get_meta("Quotation").has_field("crm_deal"))


def quotations_of(deal: str) -> list[str]:
	return frappe.get_all("Quotation", filters={"crm_deal": deal, "docstatus": ["<", 2]}, pluck="name", order_by="creation desc")


def quote_files(deal: str) -> list[dict]:
	"""Quote files on the deal and on the mails linked to it (a quote mailed to the customer)."""
	mails = frappe.get_all("Communication", filters={"reference_doctype": "CRM Deal", "reference_name": deal}, pluck="name", limit=0)
	files = frappe.get_all("File", filters={"attached_to_doctype": "CRM Deal", "attached_to_name": deal},
		fields=["name", "file_name", "file_url", "is_private", "creation"], limit=0)
	if mails:
		files += frappe.get_all("File", filters={"attached_to_doctype": "Communication", "attached_to_name": ["in", mails]},
			fields=["name", "file_name", "file_url", "is_private", "creation"], limit=0)
	return sorted((f for f in files if is_quote_file(f.file_name)), key=lambda f: f.creation)


def _fields() -> list[str]:
	meta = frappe.get_meta("CRM Deal")
	return [f for f in VALUE_FIELDS if meta.has_field(f)]


def _value(deal: str) -> float:
	fields = _fields()
	row = frappe.db.get_value("CRM Deal", deal, fields, as_dict=True) if fields else {}
	return next((flt(row.get(f)) for f in fields if flt(row.get(f)) > 0), 0.0)


def make_for_deal(deal: str, amount: float | None = None, by: str | None = None) -> str | None:
	"""SK 23-Nov: a quote PDF made outside SK App (design's own PDF, an upload, a mailed file) or the design quote value
	is NOT the quote any more (before: a draft Quotation "As per the attached quotation" with the PDF attached; the
	Curesense quote 00067 went out with design's header). The deal's own Quotation is returned when it has one; else the
	deal owner gets one task to make the quote in the app (scope and specification lines on the quotation), so every
	quote prints in the final SK format. Nothing is attached to a Quotation from outside."""
	if not _ready():
		return None
	have = quotations_of(deal)
	if have:
		return have[0]
	files = quote_files(deal)
	if files or _value(deal) > 0:
		_ask_quote(deal, files[-1].file_name if files else None, files[-1].file_url if files else None)
	return None


def _ask_quote(deal: str, file_name: str | None, file_url: str | None = None):
	"""One open task for the deal owner: make the quote in the app (the outside PDF / value is only a reference)."""
	owner = frappe.db.get_value("CRM Deal", deal, "deal_owner")
	if not owner or frappe.db.exists("ToDo", {"reference_type": "CRM Deal", "reference_name": deal, "status": "Open",
			"description": ["like", TASK_MARK + "%"]}):
		return
	shown = (f'<a href="{file_url}" target="_blank">{file_name}</a>' if file_url else file_name) if file_name else _("the design team's quote value")
	value = _value(deal)
	hint = _("Reference value ₹{0:,.0f} (before GST).").format(value) if value > 0 else ""
	frappe.get_doc({"doctype": "ToDo", "allocated_to": owner, "reference_type": "CRM Deal", "reference_name": deal, "priority": "High",
		"date": nowdate(), "description": TASK_MARK + _("Make the quote in the app: open the deal, Make quotation, and write the scope and "
			"specification lines. {0} is only a reference and is not sent to the customer. {1}").format(shown, hint)}).insert(ignore_permissions=True)


def _close_tasks(deal: str):
	for name in frappe.get_all("ToDo", filters={"reference_type": "CRM Deal", "reference_name": deal, "status": "Open",
			"description": ["like", TASK_MARK + "%"]}, pluck="name"):
		frappe.db.set_value("ToDo", name, "status", "Closed")


def pending(deal: str) -> dict | None:
	"""For the deal screen: a quote file that is not an ERPNext Quotation yet."""
	if not _ready() or quotations_of(deal):
		return None
	files = quote_files(deal)
	return {"file": files[-1].file_name, "value": _value(deal)} if files else None


def enter_amount(user: str, deal: str, amount) -> dict:
	"""SK 23-Nov: an uploaded PDF and its amount no longer make the quote (old app versions still call this)."""
	from sk_app import crm

	crm._check("CRM Deal", deal, "write")
	frappe.throw(_("A PDF made outside SK App is not the quote. Use Make quotation on this deal and write the scope and "
		"specification lines, so the quote prints in the SK format"), title=_("Make the quote in the app"))


# ---------- hooks ----------

def on_file(doc, method=None):
	if doc.attached_to_doctype != "CRM Deal" or not doc.attached_to_name or not is_quote_file(doc.file_name):
		return
	try:
		make_for_deal(doc.attached_to_name)
	except Exception:
		frappe.log_error(f"SK App quotation from quote file {doc.file_name}")


def _won_statuses() -> set:
	if not frappe.db.exists("DocType", "CRM Deal Status"):
		return {"Won"}
	return set(frappe.get_all("CRM Deal Status", filters={"type": "Won"}, pluck="name")) or {"Won"}


def order_from_deal(deal: str) -> str | None:
	"""SK 28-Oct "won deal ... is sales order received" + "all input will need to make data entry in ERP": a deal set to
	Won makes the draft Sales Order from its latest Quotation (made first from the deal value when it has none)."""
	d = frappe.db.get_value("CRM Deal", deal, ["name", "deal_owner", "creation"] + (["deal_value"] if frappe.get_meta("CRM Deal").has_field("deal_value") else []),
		as_dict=True)
	# the deal's order already exists (same lookup as the Won gate: customer, quotations, Customer's PO naming the lead / deal;
	# SK 19-Nov deals 00044 / 00135 were Won by their old back-filled orders and must not get a second one)
	from sk_app.gates import erp_docs

	frappe.local.sk_gate_docs = None
	if erp_docs(deal)[1]:
		return None
	quotes = quotations_of(deal)
	q = quotes[0] if quotes else make_for_deal(deal)  # SK 23-Nov: no quote from the deal value; the owner is asked to make it
	if not q:
		return None
	current = frappe.session.user
	frappe.set_user("Administrator")
	try:
		so = order_w.order_received("Administrator", q)["name"]
	finally:
		frappe.set_user(current)
	if d.deal_owner and frappe.db.exists("User", d.deal_owner):
		frappe.db.set_value("Sales Order", so, "owner", d.deal_owner, update_modified=False)
	return so


def on_deal_update(doc, method=None):
	if frappe.flags.sk_won_from_order:  # Won because its Sales Order was submitted (sk_app.won_deals): no second order
		return
	before = doc.get_doc_before_save()
	if doc.get("status") in _won_statuses() and (not before or before.get("status") != doc.get("status")):
		try:
			order_from_deal(doc.name)
		except Exception:
			frappe.log_error(f"SK App sales order from won deal {doc.name}")
	_quote_from_value(doc, before)


def _quote_from_value(doc, before):
	fields = [f for f in VALUE_FIELDS if doc.meta.has_field(f) and flt(doc.get(f)) > 0]
	if not fields:
		return
	if before and all(flt(before.get(f)) == flt(doc.get(f)) for f in fields):
		return
	try:
		if not quotations_of(doc.name):
			make_for_deal(doc.name)
	except Exception:
		frappe.log_error(f"SK App quotation from design quote value {doc.name}")


def mail_quotes(days: int = 3) -> int:
	"""A quote mailed from a team box (e.g. service@ to Rothe Erde, Cc sales@): the mail goes onto the customer's deal and
	the Quotation is made; with no deal yet, the box's people get a task to make the lead / deal from the mail."""
	from sk_app import mailbox

	boxes = set(mailbox.team_boxes())
	files = frappe.get_all("File", filters={"attached_to_doctype": "Communication", "file_name": ["like", "%quot%"],
		"creation": [">=", add_days(now_datetime(), -days)]}, fields=["attached_to_name", "file_name"], limit=0)
	made = 0
	for f in files:
		c = frappe.db.get_value("Communication", f.attached_to_name, ["name", "sender", "recipients", "cc", "reference_doctype",
			"reference_name", "subject"], as_dict=True)
		if not c or (c.sender or "").strip().lower() not in boxes:
			continue  # a supplier's quote to us is not a sales quote
		deal = c.reference_name if c.reference_doctype == "CRM Deal" else None
		for addr in ([] if deal else re.findall(r"[\w.+-]+@[\w-]+\.[\w.-]+", c.recipients or "")):
			ref = mailbox._known(addr.lower()) if addr.lower() not in boxes else None
			if ref and ref[0] == "CRM Deal":
				deal = ref[1]
				break
		if not deal:
			_ask_link(c, f.file_name, c.sender.strip().lower())
			continue
		if c.reference_doctype != "CRM Deal":
			frappe.db.set_value("Communication", c.name, {"reference_doctype": "CRM Deal", "reference_name": deal}, update_modified=False)
		if not quotations_of(deal) and make_for_deal(deal):
			made += 1
	return made


def _ask_link(c, file_name: str, box: str):
	from sk_app import mailbox

	if frappe.db.exists("ToDo", {"reference_type": "Communication", "reference_name": c.name, "description": ["like", TASK_MARK + "%"]}):
		return
	to = (re.findall(r"[\w.+-]+@[\w-]+\.[\w.-]+", c.recipients or "") or [""])[0]
	for p in mailbox.people_of(box):
		frappe.get_doc({"doctype": "ToDo", "allocated_to": p.user, "reference_type": "Communication", "reference_name": c.name,
			"priority": "High", "date": nowdate(), "description": TASK_MARK + _("Quote {0} mailed to {1} is not on a deal: open the mail in "
				"the app and make the lead / deal, so ERPNext makes the Quotation.").format(file_name, to)}).insert(ignore_permissions=True)


def link_loose_quotations() -> int:
	"""A draft Quotation made without a deal (e.g. Rothe Erde) goes onto its customer's latest open deal."""
	won_lost = set(frappe.get_all("CRM Deal Status", filters={"type": ["in", ["Won", "Lost"]]}, pluck="name"))
	meta = frappe.get_meta("CRM Deal")
	n = 0
	for q in frappe.get_all("Quotation", filters={"docstatus": ["<", 2], "quotation_to": "Customer", "crm_deal": ["is", "not set"]},
			fields=["name", "party_name", "customer_name"], limit=0):
		filters = [{"erpnext_customer": q.party_name}] if meta.has_field("erpnext_customer") else []
		filters.append({"organization": q.customer_name or q.party_name})
		deal = None
		for flt_ in filters:
			for d in frappe.get_all("CRM Deal", filters=flt_, fields=["name", "status"], order_by="modified desc"):
				if d.status not in won_lost:
					deal = d.name
					break
			if deal:
				break
		if deal:
			frappe.db.set_value("Quotation", q.name, "crm_deal", deal, update_modified=False)
			n += 1
	return n


def sync() -> int:
	"""Hourly and on deploy: every deal with a quote file or a design quote value and no Quotation yet."""
	if not _ready():
		return 0
	deals = {f.attached_to_name for f in frappe.get_all("File", filters={"attached_to_doctype": "CRM Deal", "file_name": ["like", "%quot%"]},
		fields=["attached_to_name"], limit=0)}
	for f in _fields():
		deals |= set(frappe.get_all("CRM Deal", filters={f: [">", 0]}, pluck="name", limit=0))
	made = 0
	try:
		link_loose_quotations()
		made += mail_quotes()
	except Exception:
		frappe.log_error("SK App quotes from mail / loose quotations")
	for deal in sorted(d for d in deals if d):
		if quotations_of(deal) or not frappe.db.exists("CRM Deal", deal):
			continue
		try:
			if make_for_deal(deal):
				made += 1
		except Exception:
			frappe.log_error(f"SK App quotation for deal {deal}")
	return made
