"""Every quote is an ERPNext Quotation (SK 28-Oct-2026: "many quote generated & sent by app & Claude but it is not
coming in ERP").

Quotes made outside the app's quote screen reached ERPNext only as files on the CRM deal: the AI design team's
BOM / costing / quote Excel ("CabinNN_..._BOM_Costing_Quote_RevN.xlsx", quote value on the deal) and quote PDFs /
Excels a salesperson uploads ("SK_Quotation_....pdf"). Now:

- a quote file on a deal, or the design quote value set on it, makes a draft Quotation for the deal's customer at
  once: linked to the deal (crm_deal), one line "as per the attached quotation" at the quote value, the file attached,
  the deal moved to Quotation;
- a quote file without a value gives the deal owner a task (and a box on the deal in the app) to type the amount once;
  the Quotation is then made the same way;
- every hour (and on deploy) any deal missed is caught up.
A deal that already has a Quotation only gets the new file attached to its latest one (a revision is made in the app).
"""

import re

import frappe
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

	group = frappe.db.get_value("Item Group", {"is_group": 0}, "name") or "All Item Groups"
	frappe.get_doc({"doctype": "Item", "item_code": SERVICE_ITEM, "item_name": "Job / service (as per quotation)", "item_group": group,
		"stock_uom": "Nos", "is_stock_item": 0, "include_item_in_manufacturing": 0, "description": "Job / service (as per quotation)",
		**hsn_fields("job")}).insert(ignore_permissions=True)


def is_quote_file(file_name: str | None) -> bool:
	return "quot" in (file_name or "").lower()


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


def _attach(quotation: str, files: list[dict]):
	have = set(frappe.get_all("File", filters={"attached_to_doctype": "Quotation", "attached_to_name": quotation}, pluck="file_url"))
	for f in files:
		if f.file_url in have:
			continue
		frappe.get_doc({"doctype": "File", "file_name": f.file_name, "file_url": f.file_url, "is_private": f.is_private,
			"attached_to_doctype": "Quotation", "attached_to_name": quotation}).insert(ignore_permissions=True)


def make_for_deal(deal: str, amount: float | None = None, by: str | None = None) -> str | None:
	"""The deal's draft Quotation from its quote (value from the design team or typed by the salesperson)."""
	from sk_app import cabin_quote, erp_flow, segments

	if not _ready():
		return None
	files = quote_files(deal)
	have = quotations_of(deal)
	if have and amount is None:
		_attach(have[0], files)
		return have[0]
	value = flt(amount) if amount is not None else _value(deal)
	if value <= 0:
		if files:
			_ask_amount(deal, files[-1].file_name)
		return None
	current = frappe.session.user
	frappe.set_user("Administrator")  # a background step: the customer and quotation are made for the deal owner
	try:
		customer = erp_flow.make_customer("Administrator", deal)["name"]
		d = frappe.db.get_value("CRM Deal", deal, ["deal_owner", "sk_main_segment"] if frappe.get_meta("CRM Deal").has_field("sk_main_segment")
			else ["deal_owner"], as_dict=True)
		non_cabin = d.get("sk_main_segment") == segments.NON_CABIN
		item = SERVICE_ITEM if non_cabin and frappe.db.exists("Item", SERVICE_ITEM) else cabin_quote.CABIN_ITEM
		what = files[-1].file_name if files else _("the design team's quote")
		doc = frappe.new_doc("Quotation")
		doc.update({"quotation_to": "Customer", "party_name": customer, "crm_deal": deal, "transaction_date": nowdate(),
			"valid_till": add_days(nowdate(), 15), "ignore_pricing_rule": 1})
		if doc.meta.has_field("sk_quote_ref"):
			doc.sk_quote_ref = cabin_quote._new_ref(customer, "JOB" if non_cabin else "CAB")
			doc.sk_rev = 0
		doc.append("items", {"item_code": item, "qty": 1, "rate": value, "description": _("As per the attached quotation: {0}").format(what)})
		doc.flags.ignore_permissions = True
		doc.insert()
		owner = by or d.get("deal_owner")
		if owner and frappe.db.exists("User", owner):
			frappe.db.set_value("Quotation", doc.name, "owner", owner, update_modified=False)
		_attach(doc.name, files)
		cabin_quote._deal_to_quotation(deal)
		_close_tasks(deal)
		return doc.name
	finally:
		frappe.set_user(current)


def _ask_amount(deal: str, file_name: str):
	owner = frappe.db.get_value("CRM Deal", deal, "deal_owner")
	if not owner or frappe.db.exists("ToDo", {"reference_type": "CRM Deal", "reference_name": deal, "status": "Open",
			"description": ["like", TASK_MARK + "%"]}):
		return
	frappe.get_doc({"doctype": "ToDo", "allocated_to": owner, "reference_type": "CRM Deal", "reference_name": deal, "priority": "High",
		"date": nowdate(), "description": TASK_MARK + _("Quote {0} is not in ERPNext yet: open the deal in the app and type the quote amount "
			"(before GST). The ERPNext Quotation is made from it.").format(file_name)}).insert(ignore_permissions=True)


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
	"""The salesperson types the amount of an uploaded quote once."""
	from sk_app import crm

	crm._check("CRM Deal", deal, "write")
	if flt(amount) <= 0:
		frappe.throw(_("Please type the quote amount (before GST)"))
	if quotations_of(deal):
		frappe.throw(_("This deal already has an ERPNext quotation: revise it from the deal"))
	return {"quotation": make_for_deal(deal, flt(amount), user)}


# ---------- hooks ----------

def on_file(doc, method=None):
	if doc.attached_to_doctype != "CRM Deal" or not doc.attached_to_name or not is_quote_file(doc.file_name):
		return
	try:
		make_for_deal(doc.attached_to_name)
	except Exception:
		frappe.log_error(f"SK App quotation from quote file {doc.file_name}")


def on_deal_update(doc, method=None):
	fields = [f for f in VALUE_FIELDS if doc.meta.has_field(f) and flt(doc.get(f)) > 0]
	if not fields:
		return
	before = doc.get_doc_before_save()
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
