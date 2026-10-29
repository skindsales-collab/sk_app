"""One Project and one cost centre per cabin (SK 29-Oct-2026): "add all cabins in manufacturing process flow ... create
cost center as per each project & add respective inventory".

Each cabin has a Project ("Cabin 314 · HD Hyundai · Electric Control Room 8ft x 6ft x 8.6ft") whose default cost centre
sits under "Cabin Orders". The Work Order carries the Project; from there, live on every save:
- every material, purchase, subcontract-bill and sales row of that cabin gets the Project and its cost centre, so the
  cabin's material and cost add up in the Project and in the cost-centre P&L;
- boards and job cards show "Cabin 314 · customer · size", also before the Sales Order is submitted.

Cabins already in production when ERPNext went live: the Work Order lists the stages already done (sk_done_stages).
When Production submits it, those Job Cards are closed at once, in route order, so the board shows the real status.
"""

import re

import frappe
from frappe import _
from frappe.utils import flt, now_datetime

DONE_FIELD = "sk_done_stages"


def ensure_setup():
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	create_custom_fields({"Work Order": [{"fieldname": DONE_FIELD, "label": "Stages already done (before ERPNext)",
		"fieldtype": "Small Text", "insert_after": "project", "allow_on_submit": 0,
		"description": "One operation per line or comma separated, e.g. Fabrication, Painting. They are closed when the "
		"Work Order is submitted."}]}, update=True)


def cabin_no(project: str | None) -> str | None:
	"""'Cabin 314' from a cabin Project's name."""
	if not project:
		return None
	name = frappe.db.get_value("Project", project, "project_name") or ""
	m = re.match(r"\s*(Cabin\s+\S+?)\s*(?:·|$)", name)
	return m.group(1) if m else None


def project_customer(project: str | None) -> str | None:
	customer = frappe.db.get_value("Project", project, "customer") if project else None
	return frappe.db.get_value("Customer", customer, "customer_name") if customer else None


def _cost_centre(project: str | None, cache: dict) -> str | None:
	if not project:
		return None
	if project not in cache:
		cache[project] = frappe.db.get_value("Project", project, "cost_center")
	return cache[project]


def _project_of_job(doc) -> str | None:
	"""Project of the document's Work Order, or of the subcontract job card a bill is for."""
	wo = doc.get("work_order")
	if not wo and doc.get("sk_job_card"):
		wo = frappe.db.get_value("Job Card", doc.sk_job_card, "work_order")
	return frappe.db.get_value("Work Order", wo, "project") if wo else None


def set_cost_centre(doc, method=None):
	"""validate: a row of a cabin's Project is booked to that Project's cost centre (the header too, when it has one)."""
	if doc.docstatus:
		return
	cache = {}
	if doc.meta.has_field("project"):
		if not doc.get("project"):
			doc.project = _project_of_job(doc)
		header = doc.get("project")
	else:
		header = _project_of_job(doc)  # Material Request: the Project is on its rows only
	for row in doc.get("items") or []:
		project = row.get("project") or header
		cc = _cost_centre(project, cache)
		if not cc:
			continue
		if row.meta.has_field("project") and not row.get("project"):
			row.project = project
		if row.meta.has_field("cost_center"):
			row.cost_center = cc
	cc = _cost_centre(header, cache)
	if cc and doc.meta.has_field("cost_center"):
		doc.cost_center = cc


def done_stages(text: str | None) -> list[str]:
	return [s.strip() for s in re.split(r"[,\n]", text or "") if s.strip()]


def close_done_stages(doc, method=None):
	"""Work Order on_submit: the Job Cards of stages already done are closed with the full quantity and posted in
	route order. A card ERPNext will not post (quality check, material) stays a closed draft and shows done."""
	stages = {s.lower() for s in done_stages(doc.get(DONE_FIELD))}
	if not stages:
		return
	from sk_app.store import try_submit

	now = now_datetime()
	cards = frappe.get_all("Job Card", filters={"work_order": doc.name, "docstatus": 0}, fields=["name", "operation"],
		order_by="sequence_id asc, creation asc")
	for card in cards:
		if (card.operation or "").lower() not in stages:
			continue
		jc = frappe.get_doc("Job Card", card.name)
		jc.append("time_logs", {"from_time": now, "to_time": now, "time_in_mins": 0, "completed_qty": flt(jc.for_quantity) or 1})
		jc.total_completed_qty = flt(jc.for_quantity) or 1
		jc.status = "Completed"
		jc.flags.ignore_permissions = True
		jc.flags.ignore_validate = True
		jc.save()
		jc.add_comment("Comment", _("Stage already done before ERPNext ({0})").format(", ".join(done_stages(doc.get(DONE_FIELD)))))
		try_submit(frappe.get_doc("Job Card", jc.name))
