"""Collect a person's open work from ERPNext / Frappe CRM as WorkItems."""

import frappe
from frappe.utils import add_to_date, get_datetime, getdate

from sk_app.logic import WorkItem

OPEN_TASK_STATUSES = ["Open", "Working", "Overdue", "Pending Review"]
CLOSED_LEAD_TYPES = ["Won", "Lost", "Junk"]


def open_tasks(user: str) -> list[WorkItem]:
	"""ERPNext Tasks assigned to the user (via Assign To) that are not done. Works for every function."""
	rows = frappe.get_all(
		"Task",
		filters={"status": ["in", OPEN_TASK_STATUSES], "_assign": ["like", f'%"{user}"%']},
		fields=["name", "subject", "exp_end_date", "priority", "expected_time", "project"],
		order_by="exp_end_date asc",
		limit=50,
	)
	prio = {"Urgent": 1, "High": 2, "Medium": 3, "Low": 4}
	return [
		WorkItem(
			"task", r.subject, "Task", r.name,
			due=get_datetime(r.exp_end_date) if r.exp_end_date else None,
			minutes=int((r.expected_time or 1) * 60),
			priority=prio.get(r.priority, 3),
			extra={"project": r.project},
		)
		for r in rows
	]


def open_todos(user: str) -> list[WorkItem]:
	"""Open ToDos allocated to the user that are not already covered by a Task or a CRM lead / deal / task.
	(Frappe CRM makes an 'Assignment for CRM Lead ...' ToDo for every owner, which would show the lead twice.)"""
	rows = frappe.get_all(
		"ToDo",
		filters={"allocated_to": user, "status": "Open", "reference_type": ["not in", ["Task", "CRM Lead", "CRM Deal", "CRM Task"]]},
		fields=["name", "description", "date", "priority", "reference_type", "reference_name"],
		limit=30,
	)
	prio = {"High": 2, "Medium": 3, "Low": 4}
	items = []
	for r in rows:
		title = frappe.utils.strip_html(r.description or "")[:80] or r.reference_name or r.name
		items.append(WorkItem("task", title, r.reference_type or "ToDo", r.reference_name or r.name,
			due=get_datetime(r.date) if r.date else None, priority=prio.get(r.priority, 3)))
	return items


def _lead_status_types() -> dict:
	if not frappe.db.exists("DocType", "CRM Lead Status"):
		return {}
	return {r.name: r.type for r in frappe.get_all("CRM Lead Status", fields=["name", "type"])}


def _label(doctype, name):
	from sk_app.crm import label

	return label(doctype, name)


def open_leads(user: str) -> list[WorkItem]:
	"""Frappe CRM leads owned by the user and not converted or closed."""
	if not frappe.db.exists("DocType", "CRM Lead"):
		return []
	types = _lead_status_types()
	rows = frappe.get_all(
		"CRM Lead",
		filters={"lead_owner": user, "converted": 0},
		fields=["name", "lead_name", "organization", "status", "source", "response_by", "first_responded_on", "creation"],
		order_by="creation desc",
		limit=0,  # SK 27-Oct: all leads, not the first few
	)
	items = []
	for r in rows:
		if types.get(r.status) in CLOSED_LEAD_TYPES:
			continue
		title = _label("CRM Lead", r.name)
		if not r.first_responded_on:
			due = get_datetime(r.response_by) if r.response_by else add_to_date(r.creation, minutes=5)
			items.append(WorkItem("lead_new", title, "CRM Lead", r.name, due=due, minutes=10, priority=1,
				extra={"source": r.source, "status": r.status, "created": str(r.creation)}))
		else:
			items.append(WorkItem("lead_followup", title, "CRM Lead", r.name, minutes=15, priority=2,
				extra={"source": r.source, "status": r.status, "created": str(r.creation)}))
	return items


def open_deals(user: str) -> list[WorkItem]:
	"""Frappe CRM deals owned by the user that are still open."""
	if not frappe.db.exists("DocType", "CRM Deal"):
		return []
	closed = [r.name for r in frappe.get_all("CRM Deal Status", filters={"type": ["in", ["Won", "Lost"]]})]
	filters = {"deal_owner": user}
	if closed:
		filters["status"] = ["not in", closed]
	rows = frappe.get_all(
		"CRM Deal",
		filters=filters,
		fields=["name", "organization", "lead_name", "status", "next_step", "expected_closure_date", "deal_value"]
			+ (["sk_customer_name"] if frappe.get_meta("CRM Deal").has_field("sk_customer_name") else []),
		order_by="modified desc",
		limit=0,
	)
	return [
		WorkItem("deal", _label("CRM Deal", r.name), "CRM Deal", r.name,
			due=get_datetime(r.expected_closure_date) if r.expected_closure_date else None,
			minutes=30, priority=2, extra={"status": r.status, "next_step": r.next_step, "value": r.deal_value,
				"customer": r.get("sk_customer_name") or r.lead_name})
		for r in rows
	]


def open_crm_tasks(user: str) -> list[WorkItem]:
	"""Frappe CRM tasks assigned to the user that are not done or cancelled."""
	if not frappe.db.exists("DocType", "CRM Task"):
		return []
	rows = frappe.get_all("CRM Task", filters={"assigned_to": user, "status": ["in", ["Backlog", "Todo", "In Progress"]]},
		fields=["name", "title", "due_date", "priority", "reference_doctype", "reference_docname"], order_by="due_date asc", limit=30)
	prio = {"High": 1, "Medium": 2, "Low": 3}
	return [
		WorkItem("crm_task", f"{r.title} · {_label(r.reference_doctype, r.reference_docname)}" if r.reference_docname else r.title,
			r.reference_doctype or "CRM Task", r.reference_docname or r.name,
			due=get_datetime(r.due_date) if r.due_date else None, minutes=15, priority=prio.get(r.priority, 2),
			extra={"task": r.name})
		for r in rows
	]


def files_to_send(user: str) -> list[WorkItem]:
	"""Customer drawings / PDFs the AI or design attached to the user's leads and deals: send them to the customer."""
	from sk_app.crm import files_to_send as pending_files

	return [
		WorkItem("send_file", f"{f.file_name} → {f.title}", "File", f.name, due=get_datetime(f.creation),
			minutes=5, priority=1, extra={"ref_doctype": f.doctype, "ref_name": f.attached_to_name})
		for f in pending_files(user)
	]


def stale_quotes(user: str, days: int = 7) -> list[WorkItem]:
	"""Submitted quotations by the user, still open and older than `days` (follow-up due)."""
	cutoff = add_to_date(getdate(), days=-days)
	rows = frappe.get_all(
		"Quotation",
		filters={"owner": user, "docstatus": 1, "status": "Open", "transaction_date": ["<=", cutoff]},
		fields=["name", "party_name", "grand_total", "transaction_date"],
		limit=20,
	)
	return [WorkItem("quote", f"{r.name} ({r.party_name})", "Quotation", r.name, minutes=15, priority=2) for r in rows]


def dsi_due(user: str) -> list[WorkItem]:
	if frappe.db.exists("SK DSI Entry", {"user": user, "date": getdate()}):
		return []
	# after all real work (SK): no due time, so it is never "overdue" ahead of jobs; only the Day Report comes later
	return [WorkItem("dsi", "Daily Small Improvement", "SK DSI Entry", "", minutes=5, priority=9,
		extra={"due_at": f"{getdate()} 17:30:00"})]


def collect(user: str, function: str) -> list[WorkItem]:
	"""Everything open for the person. Sales and Marketing add CRM work; every function gets tasks, ToDos and DSI."""
	items = open_tasks(user) + open_todos(user)
	if function in ("Sales", "Marketing", "Machine Shifting", "Design"):
		items += open_leads(user) + open_deals(user) + open_crm_tasks(user) + files_to_send(user)
	if function == "Sales":
		items += stale_quotes(user)
	items += dsi_due(user)
	from sk_app.comms import reminder_items
	from sk_app.day_report import reminder

	items += reminder(user) + reminder_items(user)
	return items
