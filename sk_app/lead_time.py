"""Days to make 100 sq ft of cabin (SK 29-Oct-2026): "PO received date, invoice date & size of cabin, area in square
foot ... should reflect in Babasaheb [app]: average days needed for making 100 sq feet cabin".

Each cabin Project keeps its PO date, invoice date and area. Live, with no nightly job:
- a Sales Order submitted for the Project gives the PO date (customer's PO date, else the order date);
- the first Sales Invoice submitted for the Project gives the invoice date;
- every Project save works out the days and the days per 100 sq ft.
Production sees each cabin and the average, and for open cabins the date the average says they should be ready.
"""

import re

import frappe
from frappe.utils import add_days, date_diff, flt, getdate, nowdate

FIELDS = [
	{"fieldname": "sk_lead_time", "label": "Cabin lead time", "fieldtype": "Section Break", "insert_after": "notes",
		"collapsible": 1},
	{"fieldname": "sk_sqft", "label": "Area (sq ft)", "fieldtype": "Float", "insert_after": "sk_lead_time",
		"description": "From the size in the project name when empty"},
	{"fieldname": "sk_po_date", "label": "PO received date", "fieldtype": "Date", "insert_after": "sk_sqft"},
	{"fieldname": "sk_po_date_approx", "label": "PO date is approximate (month only)", "fieldtype": "Check",
		"insert_after": "sk_po_date"},
	{"fieldname": "sk_col_lt", "fieldtype": "Column Break", "insert_after": "sk_po_date_approx"},
	{"fieldname": "sk_invoice", "label": "Invoice", "fieldtype": "Link", "options": "Sales Invoice", "insert_after": "sk_col_lt"},
	{"fieldname": "sk_invoice_date", "label": "Invoice date", "fieldtype": "Date", "insert_after": "sk_invoice"},
	{"fieldname": "sk_days", "label": "Days PO to invoice", "fieldtype": "Int", "read_only": 1, "insert_after": "sk_invoice_date"},
	{"fieldname": "sk_days_per_100", "label": "Days per 100 sq ft", "fieldtype": "Float", "precision": "1", "read_only": 1,
		"insert_after": "sk_days"},
]


def ensure_setup():
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	create_custom_fields({"Project": FIELDS}, update=True)


def area(text: str | None) -> float:
	"""'Office Cabin 30ft x 10ft x 8.6ft' → 300 sq ft."""
	m = re.search(r"(\d+(?:\.\d+)?)\s*(?:ft|')?\s*[x×*]\s*(\d+(?:\.\d+)?)", text or "", re.I)
	return flt(m.group(1)) * flt(m.group(2)) if m else 0


def per_100(days, sqft) -> float:
	return round(flt(days) * 100 / flt(sqft), 1) if flt(sqft) > 0 and days is not None and days >= 0 else 0


def _has_fields(doc) -> bool:
	return doc.meta.has_field("sk_days_per_100")


def on_project_validate(doc, method=None):
	if not _has_fields(doc):
		return
	if not flt(doc.sk_sqft):
		doc.sk_sqft = area(doc.project_name)
	if not doc.sk_po_date and doc.sales_order:
		so = frappe.db.get_value("Sales Order", doc.sales_order, ["docstatus", "po_date", "transaction_date"], as_dict=True)
		if so and so.docstatus == 1:
			doc.sk_po_date = so.po_date or so.transaction_date
	if doc.sk_po_date and doc.sk_invoice_date:
		doc.sk_days = date_diff(doc.sk_invoice_date, doc.sk_po_date)
		doc.sk_days_per_100 = per_100(doc.sk_days, doc.sk_sqft)
	else:
		doc.sk_days, doc.sk_days_per_100 = None, 0


def _set_project(project: str, values: dict):
	"""Fill the Project's empty lead-time fields; never stops the order or invoice being submitted."""
	try:
		_fill(project, values)
	except Exception:
		frappe.log_error(title=f"SK App: cabin lead time on {project}")


def _fill(project: str, values: dict):
	p = frappe.get_doc("Project", project)
	if not _has_fields(p):
		return
	changed = False
	for k, v in values.items():
		if v and not p.get(k):
			p.set(k, v)
			changed = True
	if changed:
		p.flags.ignore_permissions = True
		p.save()


def on_sales_order_submit(doc, method=None):
	"""A cabin's order is submitted: its PO date goes to the Project (when the Project does not have one yet)."""
	for project in {doc.get("project")} | {i.get("project") for i in doc.items} - {None, ""}:
		if project:
			_set_project(project, {"sk_po_date": doc.po_date or doc.transaction_date, "sales_order": doc.name})


def _projects_of_invoice(doc) -> set:
	out = {doc.get("project")} | {i.get("project") for i in doc.items}
	for so in {i.get("sales_order") for i in doc.items} - {None, ""}:
		out |= set(frappe.get_all("Project", filters={"sales_order": so}, pluck="name"))
	return out - {None, ""}


def on_sales_invoice_submit(doc, method=None):
	"""The cabin is invoiced: its first invoice date closes the lead time."""
	if doc.is_return:
		return
	for project in _projects_of_invoice(doc):
		_set_project(project, {"sk_invoice": doc.name, "sk_invoice_date": doc.posting_date})


def board(user: str) -> dict:
	"""Production: each invoiced cabin's days and days per 100 sq ft, the average, and open cabins against it."""
	from sk_app.cabin_projects import cabin_no, project_customer
	from sk_app.store import need

	need(user, "Production", "Management", "Quality", "Sales")
	if not frappe.get_meta("Project").has_field("sk_days_per_100"):
		return {"average": 0, "done": [], "open": []}
	rows = frappe.get_all("Project", filters={"sk_sqft": [">", 0]}, fields=["name", "project_name", "status", "sk_sqft",
		"sk_po_date", "sk_po_date_approx", "sk_invoice", "sk_invoice_date", "sk_days", "sk_days_per_100"],
		order_by="sk_invoice_date desc, sk_po_date desc", limit=0)

	def row(p):
		return {"project": p.name, "cabin": cabin_no(p.name) or p.project_name, "customer": project_customer(p.name),
			"size": p.project_name.split("·")[-1].strip(), "sqft": flt(p.sk_sqft), "po_date": str(p.sk_po_date or ""),
			"approx": p.sk_po_date_approx, "invoice": p.sk_invoice, "invoice_date": str(p.sk_invoice_date or ""),
			"days": p.sk_days, "per_100": flt(p.sk_days_per_100)}

	done = [row(p) for p in rows if p.sk_invoice_date and p.sk_po_date]
	# area-weighted: total days over total area, so one tiny cabin does not swing the figure
	sqft = sum(d["sqft"] for d in done)
	average = round(sum(flt(d["days"]) for d in done) * 100 / sqft, 1) if sqft else 0
	today = getdate(nowdate())
	open_ = []
	for p in rows:
		if p.sk_invoice_date or p.status in ("Completed", "Cancelled"):
			continue
		r = row(p)
		if average and p.sk_po_date:
			due = add_days(p.sk_po_date, round(average * flt(p.sk_sqft) / 100))
			r["due"] = str(due)
			r["late"] = getdate(due) < today
		open_.append(r)
	return {"average": average, "count": len(done), "done": done, "open": open_}
