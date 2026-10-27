"""Customer complaints from the Sales app (change list point 5, SK 26-Oct-2026).

The salesperson registers a complaint in under a minute (customer, order, spoken or written text, photos / video /
files, type). The app sends it by type to the person who fixes it, with a ToDo and, for factory faults, a Non
Conformance that lands in the subcontractor's "My Fixes". Steps: Registered → Accepted (fix date) → Fixed (after-fix
photo) → Closed only when the customer says OK; not OK sends it back. A passed fix date turns it red for the function
head and Management. ERPNext keeps it as a standard Issue (Support) with a few SK fields.
"""

import frappe
from frappe import _
from frappe.utils import add_days, getdate, now_datetime, nowdate, strip_html

from sk_app.store import _todo, _users_with_function, attach

# type → (function that fixes it, factory fault → Non Conformance too, workstation word for the subcontractor)
TYPES = {
	"Fabrication / welding / structure": ("Production", True, "fabricat"),
	"Painting / rust / colour": ("Production", True, "paint"),
	"Electrical (light, fan, AC, MCB, wiring)": ("Production", True, "electric"),
	"Leakage / roof / door / window / glass": ("Production", True, None),
	"Item missing / short / damaged in transit": ("Stores", False, None),
	"Drawing / size / design not as agreed": ("AI", False, None),
	"Delay in delivery": ("Production", False, None),
	"Bill / GST / payment / documents": ("Accounts", False, None),
	"Machine shifting / job work at site": ("Non-Cabin", False, None),
	"Other / not sure": ("Sales manager", False, None),
}
STAGES = ("Registered", "Accepted", "Fixed", "Closed", "Not OK")
FIX_DAYS = 3  # proposed: fix within 3 days unless a date is agreed with the customer
TAG = "Complaint:"


def ensure_setup():
	"""Issue Types and the SK fields on Issue (standard ERPNext Support)."""
	if not frappe.db.exists("DocType", "Issue"):
		return
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	for t in TYPES:
		if frappe.db.exists("DocType", "Issue Type") and not frappe.db.exists("Issue Type", t):
			frappe.get_doc({"doctype": "Issue Type", "description": t}).insert(ignore_permissions=True, set_name=t)
	create_custom_fields({"Issue": [
		{"fieldname": "sk_section", "label": "SK App complaint", "fieldtype": "Section Break", "insert_after": "description",
			"collapsible": 1},
		{"fieldname": "sk_stage", "label": "Stage", "fieldtype": "Select", "options": "\n" + "\n".join(STAGES), "insert_after": "sk_section",
			"in_list_view": 1, "in_standard_filter": 1},
		{"fieldname": "sk_sales_order", "label": "Sales Order", "fieldtype": "Link", "options": "Sales Order", "insert_after": "sk_stage"},
		{"fieldname": "sk_delivery_note", "label": "Delivery Note", "fieldtype": "Link", "options": "Delivery Note", "insert_after": "sk_sales_order"},
		{"fieldname": "sk_sales_invoice", "label": "Sales Invoice", "fieldtype": "Link", "options": "Sales Invoice", "insert_after": "sk_delivery_note"},
		{"fieldname": "sk_segment", "label": "Segment", "fieldtype": "Data", "insert_after": "sk_sales_invoice", "read_only": 1},
		{"fieldname": "sk_col", "fieldtype": "Column Break", "insert_after": "sk_segment"},
		{"fieldname": "sk_concerned_function", "label": "Sent to (function)", "fieldtype": "Data", "insert_after": "sk_col", "read_only": 1},
		{"fieldname": "sk_concerned_user", "label": "Sent to", "fieldtype": "Link", "options": "User", "insert_after": "sk_concerned_function"},
		{"fieldname": "sk_fix_by", "label": "Fix by", "fieldtype": "Date", "insert_after": "sk_concerned_user"},
		{"fieldname": "sk_customer_ok", "label": "Customer OK", "fieldtype": "Select", "options": "\nYes\nNo", "insert_after": "sk_fix_by"},
		{"fieldname": "sk_fix_cost", "label": "Cost of fix", "fieldtype": "Currency", "insert_after": "sk_customer_ok"},
		{"fieldname": "sk_non_conformance", "label": "Non Conformance", "fieldtype": "Link", "options": "Non Conformance",
			"insert_after": "sk_fix_cost", "read_only": 1},
		{"fieldname": "sk_registered_by", "label": "Registered by", "fieldtype": "Link", "options": "User", "insert_after": "sk_non_conformance",
			"read_only": 1},
	]}, update=True)


def _fixer(ctype: str, by_user: str) -> tuple[str, str | None]:
	"""(function, person) who fixes this type of complaint."""
	function, factory, word = TYPES[ctype]
	if function == "Non-Cabin":
		return "Machine Shifting", frappe.db.get_single_value("SK App Settings", "lead_owner_noncabin") or \
			next(iter(_users_with_function("Machine Shifting")), None)
	if function == "Sales manager":
		return "Sales", frappe.db.get_value("SK App User", {"user": by_user}, "manager") or \
			next(iter(_users_with_function("Management")), None)
	if word:
		ws = frappe.get_all("Workstation", filters={"name": ["like", f"%{word}%"]}, pluck="name")
		sub = frappe.db.get_value("SK App User", {"workstation": ["in", ws or [""]], "enabled": 1}, "user")
		if sub:
			return function, sub
	return function, next(iter(_users_with_function(function)), None)


def _latest_docs(customer: str) -> dict:
	so = frappe.get_all("Sales Order", filters={"customer": customer, "docstatus": 1}, fields=["name", "transaction_date"],
		order_by="transaction_date desc", limit=1)
	dn = frappe.get_all("Delivery Note", filters={"customer": customer, "docstatus": 1}, fields=["name", "posting_date"],
		order_by="posting_date desc", limit=1)
	si = frappe.get_all("Sales Invoice", filters={"customer": customer, "docstatus": 1}, fields=["name"], order_by="posting_date desc", limit=1)
	return {"sales_order": so[0].name if so else None, "delivery_note": dn[0].name if dn else None,
		"sales_invoice": si[0].name if si else None}


def orders(user: str, customer: str) -> dict:
	"""The customer's orders (latest first) for the complaint form; the latest is picked by itself."""
	rows = frappe.get_all("Sales Order", filters={"customer": customer, "docstatus": 1},
		fields=["name", "transaction_date", "base_net_total", "per_delivered"], order_by="transaction_date desc", limit=20)
	for r in rows:
		r["items"] = ", ".join(frappe.get_all("Sales Order Item", filters={"parent": r.name}, pluck="item_name", limit=3))
		r["transaction_date"] = str(r.transaction_date)
	return {"orders": rows, "mobile": frappe.db.get_value("Customer", customer, "mobile_no"), "types": list(TYPES)}


def register(user: str, customer: str, text: str, ctype: str, sales_order: str | None = None, files=None) -> dict:
	from sk_app.segments import SEGMENT_OF_GROUP

	if not frappe.db.exists("Customer", customer):
		frappe.throw(_("Please pick the customer"))
	if not (text or "").strip():
		frappe.throw(_("Please speak or write what is wrong"))
	if ctype not in TYPES:
		frappe.throw(_("Please pick the complaint type"))
	docs = _latest_docs(customer)
	if sales_order:
		docs["sales_order"] = sales_order
		dn = frappe.db.get_value("Delivery Note Item", {"against_sales_order": sales_order, "docstatus": 1}, "parent")
		docs["delivery_note"] = dn or docs["delivery_note"]
	function, person = _fixer(ctype, user)
	group = frappe.db.get_value("Customer", customer, "customer_group")
	issue = frappe.get_doc({"doctype": "Issue", "subject": f"{frappe.db.get_value('Customer', customer, 'customer_name') or customer}: {strip_html(text)[:100]}",
		"customer": customer, "description": text, "issue_type": ctype if frappe.db.exists("Issue Type", ctype) else None,
		"priority": "High" if frappe.db.exists("Issue Priority", "High") else None, "status": "Open", "opening_date": nowdate(),
		"sk_stage": "Registered", "sk_sales_order": docs["sales_order"], "sk_delivery_note": docs["delivery_note"],
		"sk_sales_invoice": docs["sales_invoice"], "sk_segment": SEGMENT_OF_GROUP.get(group) or group,
		"sk_concerned_function": function, "sk_concerned_user": person, "sk_fix_by": add_days(getdate(), FIX_DAYS),
		"sk_registered_by": user})
	issue.flags.ignore_permissions = True
	issue.flags.ignore_mandatory = True
	issue.insert()
	for f in files or []:
		attach(f, "Issue", issue.name, user)
	who = {person} if person else set(_users_with_function(function))
	for u in who - {None}:
		_todo(u, "Issue", issue.name, f"{TAG} {issue.subject}"[:140])
	if TYPES[ctype][1] and frappe.db.exists("DocType", "Non Conformance"):
		from sk_app.quality import _procedure

		nc = frappe.new_doc("Non Conformance")
		nc.subject = f"Customer complaint: {issue.subject}"[:140]
		nc.procedure = _procedure()
		nc.status = "Open"
		nc.details = "\n".join(x for x in (f"Complaint {issue.name} · order {docs['sales_order'] or '-'}", text,
			person and _("Who fixes: {0}").format(frappe.utils.get_fullname(person))) if x)
		nc.flags.ignore_permissions = True
		nc.insert()
		for f in files or []:
			attach(f, "Non Conformance", nc.name, user)
		frappe.db.set_value("Issue", issue.name, "sk_non_conformance", nc.name)
		if person:
			_todo(person, "Non Conformance", nc.name, _("Fix: {0}").format(nc.subject))
	return {"name": issue.name, "function": function, "person": person and frappe.utils.get_fullname(person)}


def _can_see(user: str, issue) -> bool:
	from sk_app.day_report import _team
	from sk_app.logins import profile_functions

	if user == "Administrator" or "Management" in profile_functions(user):
		return True
	if user in (issue.sk_registered_by, issue.sk_concerned_user, issue.owner):
		return True
	if frappe.db.exists("ToDo", {"reference_type": "Issue", "reference_name": issue.name, "allocated_to": user}):
		return True
	return issue.sk_registered_by in {p.user for p in _team(user)}


def _get(user: str, name: str):
	issue = frappe.get_doc("Issue", name)
	if not _can_see(user, issue):
		frappe.throw(_("This complaint is not yours"), frappe.PermissionError)
	return issue


FIELDS = ["name", "subject", "customer", "description", "issue_type", "status", "opening_date", "sk_stage", "sk_sales_order",
	"sk_delivery_note", "sk_segment", "sk_concerned_function", "sk_concerned_user", "sk_fix_by", "sk_customer_ok",
	"sk_registered_by", "sk_non_conformance", "modified"]


def _late(r) -> bool:
	return bool(r.sk_fix_by and getdate(r.sk_fix_by) < getdate() and r.sk_stage in ("Registered", "Accepted", "Not OK"))


def listing(user: str, tab: str = "mine") -> dict:
	"""mine: registered by me (and my team); to_fix: sent to me; all: Management."""
	from sk_app.day_report import _team
	from sk_app.logins import profile_functions

	if not frappe.db.exists("DocType", "Issue") or not frappe.db.has_column("Issue", "sk_stage"):
		return {"rows": [], "types": list(TYPES)}
	base = {"sk_stage": ["is", "set"]}
	mine_users = [user, *(p.user for p in _team(user))]
	todo_issues = frappe.get_all("ToDo", filters={"reference_type": "Issue", "allocated_to": user, "status": "Open"}, pluck="reference_name")
	if tab == "to_fix":
		filters = {**base, "sk_stage": ["in", ["Registered", "Accepted", "Not OK"]]}
		or_filters = [["sk_concerned_user", "=", user], ["name", "in", todo_issues or [""]]]
	elif tab == "all" and ("Management" in profile_functions(user) or user == "Administrator"):
		filters, or_filters = base, None
	else:
		filters, or_filters = {**base, "sk_registered_by": ["in", mine_users]}, None
	rows = frappe.get_all("Issue", filters=filters, or_filters=or_filters, fields=FIELDS, order_by="modified desc", limit=0)
	names = {}
	for r in rows:
		r["late"] = _late(r)
		for f in ("sk_concerned_user", "sk_registered_by"):
			if r.get(f) and r[f] not in names:
				names[r[f]] = frappe.utils.get_fullname(r[f])
		r["concerned_name"] = names.get(r.sk_concerned_user)
		r["by_name"] = names.get(r.sk_registered_by)
		r["customer_name"] = frappe.db.get_value("Customer", r.customer, "customer_name") if r.customer else ""
		r["mobile"] = frappe.db.get_value("Customer", r.customer, "mobile_no") if r.customer else None
		for f in ("opening_date", "sk_fix_by", "modified"):
			r[f] = str(r[f] or "")
	return {"rows": rows, "types": list(TYPES), "to_fix": len(todo_issues)}


def detail(user: str, name: str) -> dict:
	issue = _get(user, name)
	files = frappe.get_all("File", filters={"attached_to_doctype": "Issue", "attached_to_name": name}, fields=["file_name", "file_url"])
	steps = frappe.get_all("Comment", filters={"reference_doctype": "Issue", "reference_name": name, "comment_type": ["in", ["Comment", "Info"]]},
		fields=["content", "creation", "owner"], order_by="creation asc")
	d = {f: issue.get(f) for f in FIELDS}
	d.update({"files": files, "steps": [{"text": strip_html(s.content), "when": str(s.creation)[:16], "by": frappe.utils.get_fullname(s.owner)} for s in steps],
		"late": _late(issue), "customer_name": frappe.db.get_value("Customer", issue.customer, "customer_name"),
		"mobile": frappe.db.get_value("Customer", issue.customer, "mobile_no"),
		"concerned_name": frappe.utils.get_fullname(issue.sk_concerned_user) if issue.sk_concerned_user else issue.sk_concerned_function,
		"is_fixer": user == issue.sk_concerned_user or bool(frappe.db.exists("ToDo", {"reference_type": "Issue", "reference_name": name,
			"allocated_to": user, "status": "Open"})),
		"is_seller": user == issue.sk_registered_by, "can_see": True})
	for f in ("opening_date", "sk_fix_by", "modified"):
		d[f] = str(d[f] or "")
	return d


def _step(name: str, user: str, text: str):
	frappe.get_doc({"doctype": "Comment", "comment_type": "Info", "reference_doctype": "Issue", "reference_name": name,
		"content": f"{frappe.utils.get_fullname(user)}: {text}"}).insert(ignore_permissions=True)


def accept(user: str, name: str, fix_by=None, note: str | None = None) -> dict:
	issue = _get(user, name)
	fix_by = getdate(fix_by) if fix_by else add_days(getdate(), FIX_DAYS)
	issue.db_set({"sk_stage": "Accepted", "sk_fix_by": fix_by, "sk_concerned_user": issue.sk_concerned_user or user, "status": "Replied"})
	_step(name, user, f"Accepted, fix by {fix_by}" + (f" · {note}" if note else ""))
	return {"name": name, "stage": "Accepted"}


def fixed(user: str, name: str, note: str | None = None, photo: str | None = None, cost=None) -> dict:
	issue = _get(user, name)
	if not (note or photo):
		frappe.throw(_("Please say what was done or add the after-fix photo"))
	issue.db_set({"sk_stage": "Fixed", "status": "Resolved", "resolution_details": note or "", **({"sk_fix_cost": cost} if cost else {})})
	attach(photo, "Issue", name, user)
	_step(name, user, f"Fixed: {note or 'photo added'}")
	frappe.db.set_value("ToDo", {"reference_type": "Issue", "reference_name": name, "status": "Open"}, "status", "Closed")
	if issue.sk_registered_by and issue.sk_registered_by != user:
		_todo(issue.sk_registered_by, "Issue", name, f"{TAG} fixed, ask the customer: {issue.subject}"[:140])
	return {"name": name, "stage": "Fixed"}


def customer_answer(user: str, name: str, ok, note: str | None = None, photo: str | None = None) -> dict:
	"""Closed only when the customer says OK (voice note or WhatsApp screenshot); not OK goes back to the fixer."""
	issue = _get(user, name)
	ok = str(ok) in ("1", "true", "True", "yes", "Yes")
	attach(photo, "Issue", name, user)
	frappe.db.set_value("ToDo", {"reference_type": "Issue", "reference_name": name, "allocated_to": user, "status": "Open"}, "status", "Closed")
	if ok:
		issue.db_set({"sk_stage": "Closed", "sk_customer_ok": "Yes", "status": "Closed"})
		_step(name, user, "Customer OK" + (f" · {note}" if note else ""))
		return {"name": name, "stage": "Closed"}
	issue.db_set({"sk_stage": "Not OK", "sk_customer_ok": "No", "status": "Open", "sk_fix_by": add_days(getdate(), FIX_DAYS)})
	_step(name, user, "Customer NOT OK: " + (note or "please fix again"))
	for u in {issue.sk_concerned_user} - {None}:
		_todo(u, "Issue", name, f"{TAG} customer not OK, fix again: {issue.subject}"[:140])
	return {"name": name, "stage": "Not OK"}


def on_nc_resolved(nc: str, user: str, action: str, photo: str | None = None):
	"""A factory fault fixed from My Fixes moves its complaint to Fixed as well."""
	if not frappe.db.has_column("Issue", "sk_non_conformance"):
		return
	name = frappe.db.get_value("Issue", {"sk_non_conformance": nc, "sk_stage": ["in", ["Registered", "Accepted", "Not OK"]]})
	if name:
		issue = frappe.get_doc("Issue", name)
		issue.db_set({"sk_stage": "Fixed", "status": "Resolved", "resolution_details": action})
		if photo:
			attach(photo, "Issue", name, user)
		_step(name, user, f"Fixed in the factory: {action}")
		if issue.sk_registered_by:
			_todo(issue.sk_registered_by, "Issue", name, f"{TAG} fixed, ask the customer: {issue.subject}"[:140])


def badge(user: str) -> dict:
	"""Red: complaints sent to me, or my complaints past their fix date; blue: fixed, waiting for the customer's OK."""
	if not frappe.db.exists("DocType", "Issue") or not frappe.db.has_column("Issue", "sk_stage"):
		return {}
	todo = frappe.db.count("ToDo", {"reference_type": "Issue", "allocated_to": user, "status": "Open", "description": ["like", f"{TAG}%"]})
	late = frappe.db.count("Issue", {"sk_registered_by": user, "sk_fix_by": ["<", nowdate()], "sk_stage": ["in", ["Registered", "Accepted", "Not OK"]]})
	n = todo + late
	return {"complaints": {"n": n, "c": "red"}} if n else {}


def late_for_management() -> list:
	if not frappe.db.exists("DocType", "Issue") or not frappe.db.has_column("Issue", "sk_stage"):
		return []
	return frappe.get_all("Issue", filters={"sk_fix_by": ["<", nowdate()], "sk_stage": ["in", ["Registered", "Accepted", "Not OK"]]},
		fields=["name", "subject", "sk_concerned_function", "sk_fix_by"], order_by="sk_fix_by asc", limit=0)
