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

def _product_names() -> list:
	from sk_app.products import names_for

	try:
		return names_for()
	except Exception:
		return []

def _closed(status_doctype: str) -> list[str]:
	if status_doctype == "CRM Lead Status":
		from sk_app.lead_status import closed_lead_statuses

		return closed_lead_statuses()
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

# Files the AI or design team attach that are for the customer: PDFs, but not internal costing / BOM / shop drawings
INTERNAL_FILE_WORDS = ("bom", "costing", "cost_sheet", "manufacturing", "internal", "job_card")

def _for_customer(file_name: str) -> bool:
	name = (file_name or "").lower()
	return name.endswith(".pdf") and not any(w in name for w in INTERNAL_FILE_WORDS)

def _sent_files(user: str) -> set:
	return set(frappe.get_all("SK Work Log", filters={"user": user, "reference_doctype": "File"}, pluck="reference_name"))

REVISION_STATUS = "Revision Requested"

def _design_status_field(doctype: str) -> str | None:
	"""The Design Status select on CRM Deal / Lead used by the AI design flow (found by its 'Revision Requested' option)."""
	for df in frappe.get_meta(doctype).fields:
		if df.fieldtype == "Select" and REVISION_STATUS in (df.options or "").split("\n"):
			return df.fieldname
	return None

SENT_STATUS = "Sent to Design"

CONVERT = "crm.fcrm.doctype.crm_lead.crm_lead.convert_to_deal"

def _design_target(doctype: str, name: str) -> tuple[str, str]:
	"""Corrections go to the deal when the lead is converted, because design works on the deal."""
	if doctype == "CRM Lead":
		deal = frappe.db.get_value("CRM Deal", {"lead": name})
		if deal:
			return "CRM Deal", deal
	return doctype, name

SHARE_DAYS = 30

# Swati 26-Oct (item 8): a Customer name column on the deals list, in Frappe CRM (/crm/deals) and in My Deals
CUSTOMER_FIELD = "sk_customer_name"

DEAL_LIST_FUNCTIONS = ("Sales", "Marketing", "Machine Shifting", "Management")

def _customer_gaps(customer: str) -> dict:
	"""SK 29-Oct (Aditya: details asked 3 times): the deal screen asks only what the customer still lacks."""
	from sk_app import gates

	miss = gates.customer_missing(customer, segment=True)
	return {"name": customer, "missing": [t for _k, t in miss], "keys": sorted({k for k, _t in miss})}
