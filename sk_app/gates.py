"""Mandatory gate (SK 28-Oct-2026), applied in the app and in ERPNext (doc events), so neither the phone, the desk nor
the API can move a record on with its data missing. The rules themselves are in gate_rules.py.

Drafts made in the background (mail leads, design quote values) are still saved; the gate is on the step that moves
the record on: lead status, quotation submit, sales order submit, deal won. Junk / lost needs nothing.
"""

import frappe
from sk_app.writers import requisition as req_w
from sk_app import purchase_screens
from frappe import _
from frappe.utils import flt

from sk_app import gate_rules as R
from sk_app import lead_status
from sk_app.core.people import is_ceo as _shared_is_ceo  # one CEO check for every screen (rebuild Phase 0)

GST_NOTE = "sk_gst_note"
CUSTOMER_LINK = "sk_customer"  # SK 14-Nov PR G: Link Customer on CRM Lead and CRM Deal
NO_GSTIN = "sk_no_gstin"  # SK 4-Nov: a non-GST customer, ticked on the new lead; its deal's customer is made Unregistered


def ensure_setup():
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	fields = {
		"Customer": [{"fieldname": GST_NOTE, "label": "Why no GSTIN (unregistered)", "fieldtype": "Small Text",
			"insert_after": "gst_category", "depends_on": "eval:doc.gst_category=='Unregistered'"}],
		"Material Request": [{"fieldname": "sk_reason", "label": "Reason", "fieldtype": "Small Text", "insert_after": "sk_cabin"}],
	}
	# same label + type on lead and deal, so Frappe CRM's Convert copies the tick onto the deal
	no_gstin = {"fieldname": NO_GSTIN, "label": "No GSTIN (unregistered customer)", "fieldtype": "Check", "default": "0"}
	# SK 14-Nov (PR G): the existing ERPNext customer a lead / deal belongs to, so nothing is typed twice and no second customer is made
	customer = {"fieldname": CUSTOMER_LINK, "label": "ERPNext customer (existing)", "fieldtype": "Link", "options": "Customer"}
	for dt, after in (("CRM Lead", "organization"), ("CRM Deal", "organization")):
		if frappe.db.exists("DocType", dt):
			fields[dt] = [{**no_gstin, "insert_after": after}, {**customer, "insert_after": NO_GSTIN}]
	create_custom_fields(fields, update=True)


def _skip() -> bool:
	return bool(frappe.flags.in_install or frappe.flags.in_migrate or frappe.flags.in_import or frappe.flags.in_patch
		or frappe.flags.sk_no_gate)


def stop(title: str, missing: list):
	"""One message with every missing item, in plain words (the app shows it as it is)."""
	frappe.throw(_("{0}. Please fill first:").format(title) + "\n" + R.words(missing), title=_("Data missing"))


# ---------- lead / deal ----------

def _step(doctype: str, status: str | None) -> str | None:
	"""The gate step of a status: New … Negotiations, Won, or None for closed-not-won (junk / lost: no data needed)."""
	sd = "CRM Lead Status" if doctype == "CRM Lead" else "CRM Deal Status"
	kind = frappe.db.get_value(sd, status, "type") if status and frappe.db.exists(sd, status) else None
	if kind == "Won":
		return "Won"
	if kind in ("Lost", "Junk"):
		return None
	return lead_status.step_of(status, deal=doctype == "CRM Deal")


def deal_of(doctype: str, doc) -> str | None:
	if doctype == "CRM Deal":
		return doc.name
	return frappe.db.get_value("CRM Deal", {"lead": doc.name}) if doc.name else None


def orders_by_po(names) -> list:
	"""Sales Orders whose Customer's PO names one of these leads / deals ('From CRM-LEAD-2026-00635', SK 18-Nov)."""
	names = [n for n in names if n]
	out = []
	for n in names:
		for o in frappe.get_all("Sales Order", filters={"po_no": ["like", f"%{n}%"], "docstatus": ["<", 2]},
				fields=["name", "docstatus", "transaction_date", "po_no"]):
			if R.po_refers_to(o.po_no, names) and o.name not in {x.name for x in out}:
				out.append(o)
	return out


def erp_docs(deal: str | None, lead: str | None = None) -> tuple[list, list]:
	cache = getattr(frappe.local, "sk_gate_docs", None)
	if cache is None:  # frappe.local has no __dict__ (28-Oct: that error blocked every CRM Lead / Deal save)
		cache = frappe.local.sk_gate_docs = {}
	# a deal being made right now (not saved yet) has no quotation or order (28-Oct: a new deal saved as Won crashed here);
	# a lead with no deal still finds its order by the Customer's PO (SK 18-Nov)
	if not deal or not frappe.db.exists("CRM Deal", deal):
		if not lead:
			return [], []
		if ("lead", lead) not in cache:
			cache[("lead", lead)] = ([], orders_by_po([lead]))
		return cache[("lead", lead)]
	if deal in cache:
		return cache[deal]
	quotes = []
	if frappe.get_meta("Quotation").has_field("crm_deal"):
		quotes = frappe.get_all("Quotation", filters={"crm_deal": deal, "docstatus": ["<", 2]}, fields=["name", "docstatus"])
	from sk_app.erp_flow import customer_of

	customer = customer_of(deal)
	if not customer:  # a deal with no ERPNext customer link yet: the customer of the same name (back-filled deals, Indeva 00044)
		org = frappe.db.get_value("CRM Deal", deal, "organization")
		customer = frappe.db.get_value("Customer", {"customer_name": org}) if org else None
	# SK 17-Nov ("won date is SO date only"): a submitted Sales Order of the deal's customer wins the deal whatever the
	# order's creation date or PO number (Indeva SO 00120 of 16-Sep was back-filled on 30-Oct with 'NO PO - verbal order')
	orders = frappe.get_all("Sales Order", filters={"customer": customer, "docstatus": ["<", 2]}, fields=["name", "docstatus", "transaction_date"],
		order_by="transaction_date desc") if customer else []
	if frappe.get_meta("Quotation").has_field("crm_deal") and quotes:
		for so in frappe.get_all("Sales Order Item", filters={"prevdoc_docname": ["in", [q.name for q in quotes]], "docstatus": ["<", 2]}, pluck="parent", distinct=True):
			if so not in {o.name for o in orders}:
				d = frappe.db.get_value("Sales Order", so, ["name", "docstatus", "transaction_date"], as_dict=True)
				if d:
					orders.append(d)
	lead = lead or frappe.db.get_value("CRM Deal", deal, "lead")
	for o in orders_by_po([deal, lead]):
		if o.name not in {x.name for x in orders}:
			orders.append(o)
	cache[deal] = (quotes, orders)
	return quotes, orders


def record_missing(doctype: str, doc) -> list:
	d = doc.as_dict() if hasattr(doc, "as_dict") else dict(doc)
	if doctype == "CRM Deal":
		# the deal's contact person is its lead_name (organization when the CRM has no such field)
		d["first_name"] = d.get("lead_name") if doc.meta.has_field("lead_name") else d.get("organization")
	return R.lead_missing(d)


def status_missing(doctype: str, doc, status: str) -> list:
	"""Everything that stops the record moving to this status (empty = may move)."""
	step = _step(doctype, status)
	if step is None or step == "New":
		return []
	missing = record_missing(doctype, doc)
	if step in ("Quotation", "Negotiations", "Won"):
		missing += R.deal_step_needs(step, *erp_docs(deal_of(doctype, doc), doc.name if doctype == "CRM Lead" else None))
	return missing


def check_crm(doc, method=None):
	"""CRM Lead / CRM Deal validate: the status moves on only with the lead data and the step's ERPNext document."""
	if _skip():
		return
	frappe.local.sk_gate_docs = None
	before = doc.get_doc_before_save()
	if before and before.get("status") == doc.get("status"):
		return
	if not before and _step(doc.doctype, doc.get("status")) in (None, "New"):
		return  # a new enquiry (mail / portal / upload) is saved as it comes; it cannot move on until completed
	missing = status_missing(doc.doctype, doc, doc.get("status"))
	if missing:
		stop(_("{0} cannot move to {1}").format(doc.name or _("This lead"), doc.get("status")), missing)


def lead_step(lead: str) -> str | None:
	return _step("CRM Lead", frappe.db.get_value("CRM Lead", lead, "status"))


def lead_qualified(lead: str) -> bool:
	"""SK 4-Nov: the lead had its qualifying step (spoken to, marked Qualified or later), so it may become a deal."""
	return R.lead_may_become_deal(lead_step(lead))


def check_new_deal(doc, method=None):
	"""CRM Deal before_insert (desk, app and API alike): a deal from a lead that is still New is stopped. Frappe CRM
	marks the lead Qualified only after the deal is made, so the lead's status here is what the salesperson set."""
	if _skip() or not doc.get("lead") or not frappe.db.exists("CRM Lead", doc.lead):
		return
	if not R.lead_may_become_deal(lead_step(doc.lead), _step("CRM Deal", doc.get("status"))):
		frappe.throw(_(R.QUALIFY_FIRST), title=_("Lead not qualified yet"))


def gate_for(doctype: str, doc) -> dict:
	"""For the detail screen: what is missing on the record, and which status chips are locked and why."""
	locked = {}
	sd = "CRM Lead Status" if doctype == "CRM Lead" else "CRM Deal Status"
	# SK 21-Nov: a lead with no call where the customer was spoken to shows "Log a call first" on Qualified and later
	# chips before the tap (Swati, Curesense: the error came only after tapping)
	no_call = doctype == "CRM Lead" and not lead_had_call(doc.get("name"))
	for status in frappe.get_all(sd, pluck="name"):
		m = [t for _k, t in status_missing(doctype, doc, status)]
		step = _step(doctype, status)
		if no_call and step not in (None, "New", "Won"):
			m = [_("Log a call first (Call > Talked)")] + m
		if m:
			locked[status] = m
	return {"missing": [{"key": k, "text": t} for k, t in record_missing(doctype, doc)], "locked": locked, "rules": R.RULES}


LEAD_EDIT = ("first_name", "organization", "mobile_no", "source", "sk_segment")


def complete_lead(doctype: str, name: str, values: dict) -> dict:
	"""The detail screen's "Complete details" card: fill the missing fields (old 'Enquiry' leads included)."""
	from sk_app import crm
	from sk_app.segments import sub_of

	crm._check(doctype, name, "write")
	doc = frappe.get_doc(doctype, name)
	for f in LEAD_EDIT:
		v = str((values or {}).get(f) or "").strip()
		target = "lead_name" if f == "first_name" and doctype == "CRM Deal" else f
		if not v or not doc.meta.has_field(target):
			continue
		if f == "sk_segment":
			v = sub_of(v)
		if f == "source" and not frappe.db.exists("CRM Lead Source", v):
			continue
		df = doc.meta.get_field(target)
		if df.fieldtype == "Link" and not frappe.db.exists(df.options, v):
			if df.options != "CRM Organization":
				continue
			frappe.get_doc({"doctype": "CRM Organization", "organization_name": v}).insert()  # the deal's company, made once
		doc.set(target, v)
	owner = "lead_owner" if doctype == "CRM Lead" else "deal_owner"
	if doc.meta.has_field(owner) and not doc.get(owner):
		doc.set(owner, frappe.session.user)
	doc.save()
	return gate_for(doctype, doc)


# ---------- customer ----------

def _billing(customer: str) -> dict | None:
	addr = frappe.db.get_value("Customer", customer, "customer_primary_address")
	if not addr:
		addr = frappe.db.get_value("Dynamic Link", {"link_doctype": "Customer", "link_name": customer, "parenttype": "Address"}, "parent")
	fields = ["name", "state", "pincode"] + (["gstin"] if frappe.db.has_column("Address", "gstin") else [])
	return frappe.db.get_value("Address", addr, fields, as_dict=True) if addr else None


def customer_data(customer: str) -> dict:
	meta = frappe.get_meta("Customer")
	fields = [f for f in ("customer_name", "customer_type", "gst_category", "gstin", GST_NOTE, "mobile_no") if meta.has_field(f)]
	d = frappe.db.get_value("Customer", customer, fields, as_dict=True) or {}
	a = _billing(customer) or {}
	if not d.get("mobile_no"):
		contact = frappe.db.get_value("Dynamic Link", {"link_doctype": "Customer", "link_name": customer, "parenttype": "Contact"}, "parent")
		d["mobile_no"] = contact and frappe.db.get_value("Contact", contact, "mobile_no")
	return {**d, "address_state": a.get("state"), "address_pincode": a.get("pincode")}


def customer_missing(customer: str | None, segment: bool = False) -> list:
	"""What the customer still lacks. segment=True (a new quote from a deal, the deal's customer card) also asks for the
	Cabin / Non-Cabin group, filled from the deal by itself. Submitting an existing quote / order, and the night check,
	never ask for it: an old order with no deal would have no place to set it (found 24-Nov before the push)."""
	if not customer:
		return [("customer", "Customer")]
	out = R.customer_missing(customer_data(customer))
	if segment:
		from sk_app.segments import all_groups

		if frappe.db.get_value("Customer", customer, "customer_group") not in all_groups():
			out.append(("segment", "Segment (Cabin / Non-Cabin): set it on the deal, the customer takes it"))
	return out


def complete_customer(customer: str, gstin=None, unregistered=0, gst_note=None, address=None, city=None, state=None,
		pincode=None, mobile=None) -> dict:
	"""Fill GSTIN / unregistered reason, billing address and mobile on a customer (from the deal screen)."""
	doc = frappe.get_doc("Customer", customer)
	doc.check_permission("write")
	gstin = (gstin or "").strip().upper()
	if gstin:
		if not R.gstin_ok(gstin):
			frappe.throw(_("GSTIN {0} is not 15 letters / digits. Please check it").format(gstin))
		doc.gstin = gstin
		if doc.get("gst_category") in (None, "", "Unregistered"):
			doc.gst_category = "Registered Regular"
	elif frappe.utils.cint(unregistered):
		# SK 4-Nov: a non-GST customer is saved with no GSTIN; the reason is optional (the tick itself is the record)
		doc.gst_category = "Unregistered"
		if doc.get("gstin"):
			doc.gstin = None
		if doc.meta.has_field(GST_NOTE) and ((gst_note or "").strip() or not doc.get(GST_NOTE)):
			doc.set(GST_NOTE, (gst_note or "").strip() or _("{0} (ticked by {1} on {2})").format(
				_(R.UNREGISTERED_NOTE), frappe.session.user, frappe.utils.nowdate()))
	doc.save()
	# SK 1-Nov minimum input: the state comes from the GSTIN (first 2 digits) when it is not given
	if not (state or "").strip():
		from sk_app.auto_fill import state_from_gstin

		state = state_from_gstin(gstin or doc.get("gstin")) or state
	if (state or "").strip() and (address or "").strip():
		have = _billing(customer)
		a = frappe.get_doc("Address", have["name"]) if have else frappe.new_doc("Address")
		a.update({"address_title": doc.customer_name, "address_type": "Billing", "address_line1": address.strip(),
			"city": (city or "").strip() or a.get("city") or state.strip(), "state": state.strip(), "pincode": (pincode or "").strip(),
			"country": a.get("country") or "India", "is_primary_address": 1})
		if gstin and a.meta.has_field("gstin"):
			a.gstin = gstin
		if not have:
			a.append("links", {"link_doctype": "Customer", "link_name": customer})
		a.save() if have else a.insert()
		if not doc.get("customer_primary_address"):
			frappe.db.set_value("Customer", customer, "customer_primary_address", a.name)
	if (mobile or "").strip() and not customer_data(customer).get("mobile_no"):
		c = frappe.new_doc("Contact")
		c.first_name = doc.customer_name
		c.append("phone_nos", {"phone": mobile.strip(), "is_primary_mobile_no": 1})
		c.append("links", {"link_doctype": "Customer", "link_name": customer})
		c.insert()
		frappe.db.set_value("Customer", customer, "customer_primary_contact", c.name)
	try:  # SK 27-Nov: the open "[Quote]" task on My Day says at once that the customer part is done
		from sk_app.deal_quotes import refresh_task

		for deal in frappe.get_all("CRM Deal", filters={"erpnext_customer": customer}, pluck="name", limit=20):
			refresh_task(deal)
	except Exception:
		frappe.log_error(f"SK App quote task refresh for {customer}")
	return {"name": customer, "missing": [t for _k, t in customer_missing(customer)]}


# ---------- quotation / sales order ----------

def _rows(doc) -> list[dict]:
	return [{"qty": flt(i.qty), "rate": flt(i.rate)} for i in doc.get("items") or []]


def _deal_of_quote(doc) -> str | None:
	if doc.get("crm_deal"):
		return doc.crm_deal
	if doc.get("quotation_to") == "CRM Lead" or doc.get("quotation_to") == "Lead":
		return frappe.db.get_value("CRM Deal", {"lead": doc.party_name}, "name")
	return None


def check_quote_step(doc, method=None):
	"""Quotation before_insert and before_submit (desk, app, AI and API alike, SK 21-Nov): a quote is made / sent only
	after the steps before it: cabin = drawing approved on the deal; Non-Cabin = the deal exists (qualified lead).
	A quotation with no deal at all (an old customer's direct quote from the desk) is left as it was."""
	if _skip() or frappe.flags.sk_skip_quote_step:
		return
	from sk_app import quote_step_rules as Q
	from sk_app.segments import main_of, sub_of

	deal = _deal_of_quote(doc)
	if not deal:
		if doc.get("quotation_to") in ("CRM Lead", "Lead"):
			frappe.throw(_(Q.QUALIFY_FIRST_QUOTE), title=_("Step missing"))
		return
	d = frappe.db.get_value("CRM Deal", deal, ["sk_segment", "custom_design_status"], as_dict=True) if frappe.get_meta("CRM Deal").has_field("custom_design_status") \
		else frappe._dict(sk_segment=frappe.db.get_value("CRM Deal", deal, "sk_segment"), custom_design_status=None)
	why = Q.quote_problem(main_of(sub_of(d.sk_segment)), d.custom_design_status, True)
	if why:
		frappe.throw(_(why) + f" ({deal}: {d.custom_design_status or '-'})", title=_("Step missing"))
	# SK 23-Nov (approved): the customer's GSTIN (or No GSTIN), billing address and mobile are filled on the deal BEFORE a
	# quote is made, so no quote is left as a draft that cannot be submitted
	if doc.is_new() and doc.get("quotation_to") == "Customer" and doc.get("party_name"):
		missing = customer_missing(doc.party_name, segment=True)
		if missing:
			frappe.throw(_("Fill the customer details on the deal first (Customer card on the deal in SK App), then make the quote:")
				+ "\n" + "\n".join(f"• {t}" for _k, t in missing), title=_("Customer details missing"))


def check_lead_not_back_to_new(doc, method=None):
	"""CRM Lead validate (every route): once past New, a lead is never set back to New."""
	if _skip() or doc.is_new():
		return
	from sk_app import quote_step_rules as Q

	before = doc.get_doc_before_save()
	if before and Q.back_to_new(before.get("status"), doc.get("status")):
		frappe.throw(_(Q.BACK_TO_NEW).format(before.status), title=_("Step back not allowed"))
	# SK 23-Nov checker: only SK's 8 stages are picked (a stray "Junk" was used beside "Junk Lead"); old values stay as they are
	from sk_app.lead_status import NAMES

	if before and doc.get("status") != before.get("status") and doc.get("status") not in NAMES:
		frappe.throw(_("Stage '{0}' is not one of SK's stages. Pick one of: {1}").format(doc.status, ", ".join(NAMES)), title=_("Stage"))


def check_quote_scope(doc, method=None):
	"""Quotation before_submit (SK 23-Nov, every route): no design / attached PDF as the quote; the scope and
	specification lines are on the quotation, so it prints in the final SK format."""
	if _skip() or doc.get("quotation_to") != "Customer":
		return
	from sk_app import quote_step_rules as Q

	why = Q.scope_problem([{"item_code": r.item_code, "item_name": r.item_name, "description": r.description} for r in doc.get("items") or []],
		bool(doc.get("sk_cabin_request")))
	if why:
		frappe.throw(_(why), title=_("Scope missing"))


def lead_had_call(lead: str) -> int:
	"""Calls on the lead where the customer was spoken to (CRM Call Log Completed, logged from the app or the phone list)."""
	if not frappe.db.exists("DocType", "CRM Call Log"):
		return 1
	return frappe.db.count("CRM Call Log", {"reference_doctype": "CRM Lead", "reference_docname": lead, "status": "Completed"})


def check_quotation(doc, method=None):
	"""Quotation before_submit: complete customer, items with rate, GST, valid till."""
	if _skip():
		return
	missing = R.quotation_missing({"party_name": doc.party_name, "valid_till": doc.valid_till, "items": _rows(doc),
		"taxes": len(doc.get("taxes") or []), "total_taxes_and_charges": doc.total_taxes_and_charges, "terms": doc.terms})
	if doc.quotation_to == "Customer" and doc.party_name:
		missing += [(k, _("Customer: {0}").format(t)) for k, t in customer_missing(doc.party_name)]
	if missing:
		stop(_("Quotation {0} cannot be submitted").format(doc.name), missing)


def _has_file(doctype: str, name: str | None) -> bool:
	return bool(name and frappe.db.exists("File", {"attached_to_doctype": doctype, "attached_to_name": name}))


def check_sales_order(doc, method=None):
	"""Sales Order before_submit: PO, delivery date, value, items, complete customer."""
	if _skip():
		return
	missing = R.order_missing({"transaction_date": doc.transaction_date, "delivery_date": doc.delivery_date, "po_no": doc.po_no,
		"po_date": doc.get("po_date"), "po_file": _has_file("Sales Order", doc.name), "items": _rows(doc), "grand_total": doc.grand_total})
	cust = [(k, _("Customer: {0}").format(t)) for k, t in customer_missing(doc.customer)]
	if doc.customer:
		fill_addresses(doc)  # SK 29-Oct: the order acknowledgement prints Bill to and Ship to
	if cust and not missing and _ceo_old_order(doc):
		# SK 31-Oct: old order submitted by the CEO with customer data pending; the gap stays on record for later
		doc.add_comment("Comment", _("Submitted by CEO with customer data pending (old order): {0}").format(R.words(cust)))
		return
	missing += cust
	if missing:
		stop(_("Sales Order {0} cannot be submitted").format(doc.name), missing)
	if R.is_placeholder_po(doc.po_no) and not _has_file("Sales Order", doc.name):
		# SK 4-Nov rebuild (S5): Warn only first (SK Rule Log); Sales rules on Enforce stop it
		from sk_app.core.rules import report

		report("Sales", doc, [("po_placeholder", _("Sales Order {0}: '{1}' is not a customer PO number; please type the real PO "
			"number or attach the PO copy").format(doc.name, doc.po_no))], title=_("Customer PO number"))


def _ceo_old_order(doc) -> bool:
	from sk_app.requisition import _is_ceo

	return R.old_order_data_pending(doc.transaction_date, _is_ceo(frappe.session.user))


INVOICE_CUSTOMER_KEYS = ("customer_name", "gstin", "address")  # a tax invoice needs these; the mobile is the order's gate


def fill_addresses(doc):
	"""Bill to / Ship to left empty on a sales document take the customer's own address (Ship to defaults to Bill to)."""
	from frappe.contacts.doctype.address.address import get_address_display

	from sk_app import tax_invoice

	if not doc.get("customer_address"):
		bill = tax_invoice.party_address(doc.customer)
		if bill:
			doc.customer_address = bill.name
			doc.address_display = get_address_display(bill.name)
	if doc.get("customer_address") and not doc.get("shipping_address_name"):
		ship = tax_invoice.party_address(doc.customer, shipping=True)
		doc.shipping_address_name = ship.name if ship else doc.customer_address
		doc.shipping_address = get_address_display(doc.shipping_address_name)


def check_sales_invoice(doc, method=None):
	"""Sales Invoice / Delivery Note before_submit (SK 29-Oct, Shraddha): the invoice and the delivery challan must show
	the buyer (Bill to) and the consignee (Ship to)."""
	if _skip() or not doc.customer:
		return
	fill_addresses(doc)
	missing = [(k, _("Customer: {0}").format(t)) for k, t in customer_missing(doc.customer) if k in INVOICE_CUSTOMER_KEYS]
	if not doc.get("customer_address") and not any(k == "address" for k, _t in missing):
		missing.append(("address", _("Bill to address")))
	if missing:
		stop(_("{0} {1} cannot be submitted").format(_(doc.doctype), doc.name), missing)


# ---------- purchase request ----------

def check_request(doc, method=None):
	"""Material Request (Purchase) validate: item + qty, required-by date and the reason when it is raised."""
	if _skip() or doc.material_request_type != "Purchase" or not doc.meta.has_field("sk_reason"):
		return
	if not doc.is_new():
		return  # checked when it was raised; the CEO's approval is the next gate (req_w.check_submit)
	if not doc.get("sk_reason") and (frappe.flags.in_scheduler or frappe.session.user == "Administrator"):
		doc.sk_reason = _("Auto re-order level (ERPNext)")  # ERPNext's own re-order run is not stopped; the CEO still approves
	missing = R.request_missing({"items": [{"item_code": i.item_code, "qty": flt(i.qty)} for i in doc.items],
		"schedule_date": doc.schedule_date, "reason": doc.get("sk_reason")})
	if missing:
		stop(_("Purchase request cannot be saved"), missing)


# ---------- pending on the main screen ----------

def pending(user: str, rows: bool = False) -> dict:
	"""SK 28-Oct (main screen decision-first): records the person (manager: team, CEO: all) must still complete.
	rows=False: counts only, for Home; rows=True: the records, for the Data missing screen."""
	from sk_app.flows import _owners

	owners = _owners(user)
	own = lambda field: {} if owners is None else {field: ["in", owners or [""]]}  # noqa: E731
	groups = []

	def add(key, label, items):
		if items:
			groups.append({"key": key, "label": label, "n": len(items), "rows": items if rows else []})

	if frappe.db.exists("DocType", "CRM Lead"):
		# junk / lost leads need nothing ("Junk Lead" was type Open on sk-dev, so it was counted); won leads still need their data
		from sk_app.lead_status import is_closed

		closed = [r.name for r in frappe.get_all("CRM Lead Status", fields=["name", "type"]) if is_closed(r.name, r.type) and r.name != "Deal Won"]
		meta = frappe.get_meta("CRM Lead")
		fields = [f for f in ("name", "first_name", "organization", "mobile_no", "phone", "sk_segment", "source", "lead_owner", "status")
			if f == "name" or meta.has_field(f)]
		filters = {"status": ["not in", closed or [""]], **own("lead_owner")}
		if meta.has_field("sk_cold"):
			filters["sk_cold"] = 0
		items = []
		for d in frappe.get_all("CRM Lead", filters=filters, fields=fields, order_by="modified desc", limit=0):
			m = R.lead_missing(d)
			if m:
				items.append({"doctype": "CRM Lead", "name": d.name, "title": d.organization or d.first_name or d.name,
					"meta": f"{d.status} · " + ", ".join(t for _k, t in m)})
		add("leads", "Leads with data missing", items)
	for doctype, label in (("Quotation", "Quotations not submitted"), ("Sales Order", "Sales Orders not submitted")):
		title = "customer_name"
		items = [{"doctype": doctype, "name": r.name, "title": r.get(title) or r.name, "meta": f"Draft · {r.transaction_date} · ₹{flt(r.grand_total):,.0f}"}
			for r in frappe.get_all(doctype, filters={"docstatus": 0, **own("owner")}, fields=["name", title, "transaction_date", "grand_total"],
				order_by="transaction_date asc", limit=0)]
		add(doctype.lower().replace(" ", "_"), label, items)
	if _shared_is_ceo(user):
		items = [{"doctype": "Material Request", "name": r.name, "title": r.name, "meta": f"Waiting CEO · need by {r.schedule_date}"}
			for r in frappe.get_all("Material Request", filters={"docstatus": 0, "material_request_type": "Purchase", "sk_approval": "Waiting CEO"},
				fields=["name", "schedule_date"], limit=0)]
		add("requests", "Purchase requests to approve", items)
	# SK 14-Nov: last night's data check, the person's own items (link, what is wrong, one action); fixed items drop off next night
	try:
		from sk_app.core import night_check

		add("night", "Night check: to fix", night_check.home_rows(user))
	except Exception:
		frappe.log_error("SK night check home rows")
	return {"total": sum(g["n"] for g in groups), "groups": groups}
