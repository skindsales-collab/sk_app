"""Mandatory gate (SK 28-Oct-2026), applied in the app and in ERPNext (doc events), so neither the phone, the desk nor
the API can move a record on with its data missing. The rules themselves are in gate_rules.py.

Drafts made in the background (mail leads, design quote values) are still saved; the gate is on the step that moves
the record on: lead status, quotation submit, sales order submit, deal won. Junk / lost needs nothing.
"""

import frappe
from frappe import _
from frappe.utils import flt

from sk_app import gate_rules as R
from sk_app import lead_status

GST_NOTE = "sk_gst_note"


def ensure_setup():
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	create_custom_fields({
		"Customer": [{"fieldname": GST_NOTE, "label": "Why no GSTIN (unregistered)", "fieldtype": "Small Text",
			"insert_after": "gst_category", "depends_on": "eval:doc.gst_category=='Unregistered'"}],
		"Material Request": [{"fieldname": "sk_reason", "label": "Reason", "fieldtype": "Small Text", "insert_after": "sk_cabin"}],
	}, update=True)


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


def erp_docs(deal: str | None) -> tuple[list, list]:
	if not deal:
		return [], []
	cache = getattr(frappe.local, "sk_gate_docs", None)
	if cache is None:  # frappe.local has no __dict__ (28-Oct: that error blocked every CRM Lead / Deal save)
		cache = frappe.local.sk_gate_docs = {}
	if deal in cache:
		return cache[deal]
	quotes = []
	if frappe.get_meta("Quotation").has_field("crm_deal"):
		quotes = frappe.get_all("Quotation", filters={"crm_deal": deal, "docstatus": ["<", 2]}, fields=["name", "docstatus"])
	from sk_app.erp_flow import customer_of

	customer = customer_of(deal)
	since = frappe.db.get_value("CRM Deal", deal, "creation")
	# orders of this deal's customer made since the deal (an old order of the same customer does not win a new deal)
	orders = frappe.get_all("Sales Order", filters={"customer": customer, "docstatus": ["<", 2], "creation": [">=", since]},
		fields=["name", "docstatus"]) if customer and since else []
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
		missing += R.deal_step_needs(step, *erp_docs(deal_of(doctype, doc)))
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


def gate_for(doctype: str, doc) -> dict:
	"""For the detail screen: what is missing on the record, and which status chips are locked and why."""
	locked = {}
	sd = "CRM Lead Status" if doctype == "CRM Lead" else "CRM Deal Status"
	for status in frappe.get_all(sd, pluck="name"):
		m = status_missing(doctype, doc, status)
		if m:
			locked[status] = [t for _k, t in m]
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
	return frappe.db.get_value("Address", addr, ["name", "state", "pincode", "gstin"], as_dict=True) if addr else None


def customer_data(customer: str) -> dict:
	meta = frappe.get_meta("Customer")
	fields = [f for f in ("customer_name", "gst_category", "gstin", GST_NOTE, "mobile_no") if meta.has_field(f)]
	d = frappe.db.get_value("Customer", customer, fields, as_dict=True) or {}
	a = _billing(customer) or {}
	if not d.get("mobile_no"):
		contact = frappe.db.get_value("Dynamic Link", {"link_doctype": "Customer", "link_name": customer, "parenttype": "Contact"}, "parent")
		d["mobile_no"] = contact and frappe.db.get_value("Contact", contact, "mobile_no")
	return {**d, "address_state": a.get("state"), "address_pincode": a.get("pincode")}


def customer_missing(customer: str | None) -> list:
	if not customer:
		return [("customer", "Customer")]
	return R.customer_missing(customer_data(customer))


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
		if not (gst_note or "").strip():
			frappe.throw(_("Please say why the customer has no GSTIN"))
		doc.gst_category = "Unregistered"
		if doc.meta.has_field(GST_NOTE):
			doc.set(GST_NOTE, gst_note.strip())
	doc.save()
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
	return {"name": customer, "missing": [t for _k, t in customer_missing(customer)]}


# ---------- quotation / sales order ----------

def _rows(doc) -> list[dict]:
	return [{"qty": flt(i.qty), "rate": flt(i.rate)} for i in doc.get("items") or []]


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
		"po_file": _has_file("Sales Order", doc.name), "items": _rows(doc), "grand_total": doc.grand_total})
	missing += [(k, _("Customer: {0}").format(t)) for k, t in customer_missing(doc.customer)]
	if missing:
		stop(_("Sales Order {0} cannot be submitted").format(doc.name), missing)


# ---------- purchase request ----------

def check_request(doc, method=None):
	"""Material Request (Purchase) validate: item + qty, required-by date and the reason when it is raised."""
	if _skip() or doc.material_request_type != "Purchase" or not doc.meta.has_field("sk_reason"):
		return
	if not doc.is_new():
		return  # checked when it was raised; the CEO's approval is the next gate (requisition.check_submit)
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
	from sk_app.logins import profile_functions

	owners = _owners(user)
	own = lambda field: {} if owners is None else {field: ["in", owners or [""]]}  # noqa: E731
	groups = []

	def add(key, label, items):
		if items:
			groups.append({"key": key, "label": label, "n": len(items), "rows": items if rows else []})

	if frappe.db.exists("DocType", "CRM Lead"):
		closed = frappe.get_all("CRM Lead Status", filters={"type": ["in", ["Lost", "Junk"]]}, pluck="name")
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
	if user == "Administrator" or "Management" in profile_functions(user):
		items = [{"doctype": "Material Request", "name": r.name, "title": r.name, "meta": f"Waiting CEO · need by {r.schedule_date}"}
			for r in frappe.get_all("Material Request", filters={"docstatus": 0, "material_request_type": "Purchase", "sk_approval": "Waiting CEO"},
				fields=["name", "schedule_date"], limit=0)]
		add("requests", "Purchase requests to approve", items)
	return {"total": sum(g["n"] for g in groups), "groups": groups}
