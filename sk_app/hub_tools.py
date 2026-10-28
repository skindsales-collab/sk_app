"""SK Hub tools (SK 28-Oct). Every tool runs as the signed-in person, with their own ERPNext permissions.

Rules built in, whatever the person's roles:
- read and create / change DRAFTS only: nothing is submitted, cancelled or deleted through the hub;
- system set-up records (users, roles, permissions, scripts, OAuth ...) are never changed, and
  token / secret records are never read;
- every write is logged in SK Hub Log, so any Project can see what another one changed.
"""

import json

import frappe
from frappe.utils import cint, flt, now_datetime

MAX_ROWS = 200
MAX_ANSWER_CHARS = 60000

# Never read through the hub (secrets and login tokens)
NO_READ = {
	"OAuth Bearer Token",
	"OAuth Authorization Code",
	"OAuth Client",
	"Social Login Key",
	"Connected App",
	"Token Cache",
	"User Social Login",
	"Integration Request",
}

# Never created or changed through the hub (system set-up; do it in ERPNext by an admin)
NO_WRITE = NO_READ | {
	"User",
	"Role",
	"Role Profile",
	"Module Profile",
	"Has Role",
	"User Permission",
	"DocPerm",
	"Custom DocPerm",
	"DocType",
	"DocField",
	"Custom Field",
	"Property Setter",
	"Customize Form",
	"Server Script",
	"Client Script",
	"System Settings",
	"OAuth Settings",
	"OAuth Provider Settings",
	"Scheduled Job Type",
	"Deleted Document",
	"Version",
	"Access Log",
	"Activity Log",
	"Error Log",
	"Data Import",
	"Data Export",
	"Bulk Update",
	"Auto Repeat",
	"Webhook",
	"Email Account",
	"SK Hub Log",
	"SK App Settings",
	"SK App User",
	"SK App Unlock Key",
}

# Fields Claude may not set: the hub decides these, ERPNext fills the rest
PROTECTED_FIELDS = {
	"docstatus",
	"owner",
	"creation",
	"modified",
	"modified_by",
	"idx",
	"amended_from",
	"doctype",
	"_user_tags",
	"_comments",
	"_assign",
	"_liked_by",
	"_seen",
}

TEAMS = (
	"Sales",
	"Marketing",
	"Production",
	"Subcontractor",
	"Quality",
	"Stores",
	"Purchase",
	"Accounts",
	"HR",
	"Machine Shifting",
	"Design",
	"AI",
	"IT / ERP",
	"Management",
)


# ---- helpers -------------------------------------------------------------------------------------
def _user() -> str:
	return frappe.session.user


def my_team(user: str | None = None) -> str | None:
	"""The person's team = their SK App home function (SK App User)."""
	return frappe.db.get_value("SK App User", {"user": user or _user()}, "home")


def _is_admin() -> bool:
	return "System Manager" in frappe.get_roles() or _user() == "Administrator"


def _doctype(doctype: str) -> str:
	if not doctype or not isinstance(doctype, str):
		frappe.throw("doctype is required, e.g. 'Quotation' or 'CRM Lead'")
	if not frappe.db.exists("DocType", doctype):
		frappe.throw(f"There is no document type called '{doctype}' in ERPNext.", frappe.DoesNotExistError)
	if frappe.get_meta(doctype).istable:
		frappe.throw(f"'{doctype}' is a child table. Read or change it through its parent document.")
	return doctype


def _can_read(doctype: str):
	_doctype(doctype)
	if doctype in NO_READ:
		frappe.throw(f"{doctype} holds login secrets and is never read through SK Hub.", frappe.PermissionError)


def _can_write(doctype: str):
	_doctype(doctype)
	if doctype in NO_WRITE:
		frappe.throw(
			f"{doctype} is system set-up and is not changed through SK Hub. Ask the ERPNext admin to do it in ERPNext.",
			frappe.PermissionError,
		)


def _filters(filters):
	if filters in (None, "", {}, []):
		return None
	if isinstance(filters, str):
		try:
			return json.loads(filters)
		except ValueError:
			frappe.throw("filters is not valid JSON")
	if isinstance(filters, (dict, list)):
		return filters
	frappe.throw("filters must be an object like {\"status\": \"Open\"} or a list of [field, operator, value]")


def _clean_data(data) -> dict:
	if isinstance(data, str):
		try:
			data = json.loads(data)
		except ValueError:
			frappe.throw("data must be an object of fieldname: value")
	if not isinstance(data, dict):
		frappe.throw("data must be an object of fieldname: value")

	def clean(d: dict) -> dict:
		out = {}
		for k, v in d.items():
			if k in PROTECTED_FIELDS:
				continue
			if isinstance(v, list):
				v = [clean(x) if isinstance(x, dict) else x for x in v]
			out[k] = v
		return out

	return clean(data)


def _log(action: str, doctype: str = "", name: str = "", detail=None, project: str | None = None):
	frappe.get_doc(
		{
			"doctype": "SK Hub Log",
			"user": _user(),
			"team": my_team(),
			"project": (project or "")[:140],
			"action": action,
			"reference_doctype": doctype or None,
			"reference_name": name or None,
			"detail": json.dumps(detail, default=str, ensure_ascii=False)[:5000] if detail is not None else None,
		}
	).insert(ignore_permissions=True)


def _plain(doc) -> dict:
	return json.loads(frappe.as_json(doc.as_dict(no_default_fields=False, convert_dates_to_str=True)))


# ---- tools: overview and reading ---------------------------------------------------------------
def hub_overview() -> dict:
	user = _user()
	team = my_team(user)
	open_for_team = frappe.db.count("SK Hub Handoff", {"to_team": team, "status": "Open"}) if team else 0
	return {
		"company": frappe.defaults.get_user_default("Company") or frappe.defaults.get_global_default("company"),
		"site": frappe.utils.get_url(),
		"user": user,
		"full_name": frappe.utils.get_fullname(user),
		"team": team or "(not set: ask the admin to set your SK App User home function)",
		"is_admin": _is_admin(),
		"roles": [r for r in frappe.get_roles(user) if r not in ("All", "Guest", "Desk User")],
		"open_handoffs_for_my_team": open_for_team,
		"teams": list(TEAMS),
		"rules": "Drafts only. Nothing is submitted, cancelled or deleted through SK Hub. Your own ERPNext permissions apply.",
	}


def describe_doctype(doctype: str) -> dict:
	_can_read(doctype)
	meta = frappe.get_meta(doctype)
	fields = []
	for f in meta.fields:
		if f.fieldtype in ("Section Break", "Column Break", "Tab Break", "HTML", "Button", "Fold"):
			continue
		entry = {"fieldname": f.fieldname, "label": f.label, "type": f.fieldtype}
		if f.options and f.fieldtype in ("Link", "Select", "Table", "Table MultiSelect", "Dynamic Link"):
			entry["options"] = f.options if f.fieldtype != "Select" else [o for o in f.options.split("\n") if o]
		if f.reqd:
			entry["required"] = True
		if f.read_only:
			entry["read_only"] = True
		if f.default not in (None, ""):
			entry["default"] = f.default
		fields.append(entry)
	return {
		"doctype": doctype,
		"submittable": bool(meta.is_submittable),
		"title_field": meta.title_field,
		"you_can": {
			"read": frappe.has_permission(doctype, "read"),
			"create": frappe.has_permission(doctype, "create") and doctype not in NO_WRITE,
			"write": frappe.has_permission(doctype, "write") and doctype not in NO_WRITE,
		},
		"fields": fields,
	}


def search_records(
	doctype: str,
	filters=None,
	fields: list | None = None,
	order_by: str | None = "modified desc",
	limit: int = 20,
	start: int = 0,
) -> list:
	_can_read(doctype)
	fields = fields or ["name"]
	if isinstance(fields, str):
		fields = [x.strip() for x in fields.split(",") if x.strip()]
	return frappe.get_list(
		doctype,
		filters=_filters(filters),
		fields=fields,
		order_by=order_by or "modified desc",
		offset=max(0, cint(start)),
		limit=max(1, min(cint(limit) or 20, MAX_ROWS)),
	)


def get_record(doctype: str, name: str) -> dict:
	_can_read(doctype)
	doc = frappe.get_doc(doctype, name)
	doc.check_permission("read")
	return _plain(doc)


def count_records(doctype: str, filters=None) -> int:
	"""Counted through get_list, so the person's permissions (e.g. own leads only) apply."""
	_can_read(doctype)
	flt_ = _filters(filters)
	total, page = 0, 5000
	while total < 500000:
		names = frappe.get_list(doctype, filters=flt_, pluck="name", order_by="name asc", offset=total, limit=page)
		total += len(names)
		if len(names) < page:
			break
	return total


def item_stock(item_code: str) -> dict:
	_can_read("Bin")
	rows = frappe.get_list(
		"Bin",
		filters={"item_code": item_code},
		fields=["warehouse", "actual_qty", "reserved_qty", "ordered_qty", "projected_qty", "stock_uom"],
		limit=500,
	)
	return {
		"item_code": item_code,
		"item_name": frappe.db.get_value("Item", item_code, "item_name"),
		"warehouses": rows,
		"total_actual": sum(flt(r.actual_qty) for r in rows),
		"total_projected": sum(flt(r.projected_qty) for r in rows),
	}


# ---- tools: drafts ---------------------------------------------------------------------------------
def create_draft(doctype: str, data: dict, project: str | None = None) -> dict:
	_can_write(doctype)
	values = _clean_data(data)
	values["doctype"] = doctype
	doc = frappe.get_doc(values)
	if doc.meta.is_submittable:
		doc.docstatus = 0
	doc.insert()  # checks the person's create permission and runs ERPNext's own validations
	_log("create", doctype, doc.name, values, project)
	return {
		"created": doc.name,
		"doctype": doctype,
		"status": "Draft" if doc.meta.is_submittable else "Saved",
		"open": frappe.utils.get_url_to_form(doctype, doc.name),
		"next_step": "The responsible person checks it and submits it in ERPNext / SK App."
		if doc.meta.is_submittable
		else "Saved in ERPNext.",
	}


def update_draft(doctype: str, name: str, changes: dict, project: str | None = None) -> dict:
	_can_write(doctype)
	doc = frappe.get_doc(doctype, name)
	if doc.docstatus != 0:
		frappe.throw(
			f"{doctype} {name} is already submitted or cancelled. Change it in ERPNext (Cancel and Amend) - not through SK Hub.",
			frappe.PermissionError,
		)
	values = _clean_data(changes)
	values.pop("name", None)
	doc.update(values)
	doc.save()  # checks the person's write permission
	_log("update", doctype, name, values, project)
	return {"updated": doc.name, "doctype": doctype, "fields": sorted(values), "open": frappe.utils.get_url_to_form(doctype, doc.name)}


def add_comment(doctype: str, name: str, text: str, project: str | None = None) -> dict:
	_can_read(doctype)
	doc = frappe.get_doc(doctype, name)
	doc.check_permission("read")
	comment = doc.add_comment("Comment", frappe.utils.escape_html(text))
	_log("comment", doctype, name, text, project)
	return {"comment": comment.name, "on": f"{doctype} {name}"}


# ---- tools: coordination between Projects / teams ----------------------------------------------------
def post_handoff(
	to_team: str,
	subject: str,
	details: str = "",
	reference_doctype: str | None = None,
	reference_name: str | None = None,
	project: str | None = None,
) -> dict:
	if to_team not in TEAMS:
		frappe.throw(f"Unknown team '{to_team}'. Teams: {', '.join(TEAMS)}")
	if reference_doctype:
		_can_read(reference_doctype)
	doc = frappe.get_doc(
		{
			"doctype": "SK Hub Handoff",
			"from_user": _user(),
			"from_team": my_team(),
			"from_project": (project or "")[:140],
			"to_team": to_team,
			"subject": subject[:140],
			"details": details,
			"reference_doctype": reference_doctype or None,
			"reference_name": reference_name or None,
			"status": "Open",
		}
	).insert()
	_log("handoff", "SK Hub Handoff", doc.name, {"to": to_team, "subject": subject}, project)
	return {"handoff": doc.name, "to_team": to_team, "status": "Open"}


def list_handoffs(team: str | None = None, status: str = "Open", limit: int = 30) -> list:
	team = team or my_team()
	filters = {}
	if status and status != "All":
		filters["status"] = status
	or_filters = {"to_team": team, "from_team": team} if team else None
	return frappe.get_list(
		"SK Hub Handoff",
		filters=filters,
		or_filters=or_filters,
		fields=[
			"name", "creation", "from_user", "from_team", "from_project", "to_team", "subject", "details",
			"reference_doctype", "reference_name", "status", "closed_by", "closed_on", "close_note",
		],
		order_by="creation desc",
		limit=max(1, min(cint(limit) or 30, MAX_ROWS)),
	)


def close_handoff(handoff: str, note: str = "", project: str | None = None) -> dict:
	doc = frappe.get_doc("SK Hub Handoff", handoff)
	team = my_team()
	if not _is_admin() and team not in (doc.to_team, doc.from_team):
		frappe.throw("Only the receiving or sending team can close this handoff.", frappe.PermissionError)
	doc.status = "Done"
	doc.closed_by = _user()
	doc.closed_on = now_datetime()
	doc.close_note = note
	doc.save()
	_log("close_handoff", "SK Hub Handoff", doc.name, note, project)
	return {"handoff": doc.name, "status": "Done"}


def recent_activity(limit: int = 30, user: str | None = None, team: str | None = None, reference_doctype: str | None = None) -> list:
	filters = {}
	if user:
		filters["user"] = user
	if team:
		filters["team"] = team
	if reference_doctype:
		filters["reference_doctype"] = reference_doctype
	return frappe.get_all(  # the log is shared on purpose: every Project sees what the others changed
		"SK Hub Log",
		filters=filters,
		fields=["creation", "user", "team", "project", "action", "reference_doctype", "reference_name", "detail"],
		order_by="creation desc",
		limit=max(1, min(cint(limit) or 30, MAX_ROWS)),
	)


# ---- tool list for MCP ---------------------------------------------------------------------------
_PROJECT = {
	"type": "string",
	"description": "Name of the Claude Project you are working in (e.g. 'Sales', 'Design Cabin'), for the activity log.",
}
_FILTERS = {
	"description": 'Frappe filters: {"status": "Open"} or [["grand_total", ">", 100000], ["status", "=", "Draft"]]',
	"anyOf": [{"type": "object"}, {"type": "array"}, {"type": "string"}],
}
READ = {"readOnlyHint": True, "openWorldHint": False}
WRITE = {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False, "openWorldHint": False}


def _tool(fn, title, description, properties=None, required=(), annotations=READ):
	return {
		"fn": fn,
		"spec": {
			"name": fn.__name__,
			"title": title,
			"description": description,
			"inputSchema": {"type": "object", "properties": properties or {}, "required": list(required)},
			"annotations": {"title": title, **annotations},
		},
	}


TOOLS = {
	t["spec"]["name"]: t
	for t in (
		_tool(hub_overview, "Who am I / my team", "Who you are signed in as, your team and roles, and how many handoffs are open for your team. Call this first."),
		_tool(
			describe_doctype,
			"Fields of a document type",
			"Field names, types, options and required fields of an ERPNext document type, and whether you may read / create / change it. Use before create_draft.",
			{"doctype": {"type": "string", "description": "e.g. Quotation, CRM Lead, Material Request"}},
			["doctype"],
		),
		_tool(
			search_records,
			"Search records",
			"List ERPNext / CRM records you are allowed to see. Returns only the fields you ask for (max 200 rows per call; page with start).",
			{
				"doctype": {"type": "string"},
				"filters": _FILTERS,
				"fields": {"type": "array", "items": {"type": "string"}, "description": 'e.g. ["name","customer_name","grand_total","status"]'},
				"order_by": {"type": "string", "default": "modified desc"},
				"limit": {"type": "integer", "default": 20, "maximum": MAX_ROWS},
				"start": {"type": "integer", "default": 0},
			},
			["doctype"],
		),
		_tool(get_record, "Get one record", "One full record including its child tables (items, taxes ...).", {"doctype": {"type": "string"}, "name": {"type": "string"}}, ["doctype", "name"]),
		_tool(count_records, "Count records", "How many records match the filters.", {"doctype": {"type": "string"}, "filters": _FILTERS}, ["doctype"]),
		_tool(item_stock, "Stock of an item", "Stock of one item in every warehouse: actual, reserved, ordered and projected qty.", {"item_code": {"type": "string"}}, ["item_code"]),
		_tool(
			create_draft,
			"Create a draft",
			"Create a record as a DRAFT (e.g. Quotation, Material Request, CRM Lead, Task, BOM). It is never submitted here: the responsible person submits it in ERPNext / SK App. Child tables go in as lists, e.g. {\"items\": [{\"item_code\": \"X\", \"qty\": 2}]}.",
			{"doctype": {"type": "string"}, "data": {"type": "object", "description": "fieldname: value"}, "project": _PROJECT},
			["doctype", "data"],
			WRITE,
		),
		_tool(
			update_draft,
			"Change a draft",
			"Change fields on a record that is still a draft (or a master such as Customer, Item, CRM Lead). Submitted or cancelled documents cannot be changed here.",
			{"doctype": {"type": "string"}, "name": {"type": "string"}, "changes": {"type": "object"}, "project": _PROJECT},
			["doctype", "name", "changes"],
			WRITE,
		),
		_tool(
			add_comment,
			"Add a comment",
			"Add a comment to a record's timeline, visible to staff in ERPNext / CRM.",
			{"doctype": {"type": "string"}, "name": {"type": "string"}, "text": {"type": "string"}, "project": _PROJECT},
			["doctype", "name", "text"],
			WRITE,
		),
		_tool(
			post_handoff,
			"Hand work to another team",
			"Pass work to another team's Claude Project, e.g. Sales -> Design: 'Drawing needed for CRM-DEAL-2026-00044'. The other team sees it in list_handoffs.",
			{
				"to_team": {"type": "string", "enum": list(TEAMS)},
				"subject": {"type": "string"},
				"details": {"type": "string"},
				"reference_doctype": {"type": "string", "description": "optional, e.g. CRM Deal"},
				"reference_name": {"type": "string", "description": "optional, e.g. CRM-DEAL-2026-00044"},
				"project": _PROJECT,
			},
			["to_team", "subject"],
			WRITE,
		),
		_tool(
			list_handoffs,
			"Handoffs for my team",
			"Handoffs sent to or from a team (default: your team). status: Open, Done or All.",
			{"team": {"type": "string", "enum": list(TEAMS)}, "status": {"type": "string", "enum": ["Open", "Done", "All"], "default": "Open"}, "limit": {"type": "integer", "default": 30}},
		),
		_tool(
			close_handoff,
			"Close a handoff",
			"Mark a handoff done with a short note of what was done.",
			{"handoff": {"type": "string", "description": "e.g. HO-2026-000012"}, "note": {"type": "string"}, "project": _PROJECT},
			["handoff"],
			WRITE,
		),
		_tool(
			recent_activity,
			"What changed through SK Hub",
			"Latest creates, changes, comments and handoffs made through SK Hub by any Project. Check this before any bulk change so two Projects never change the same records at once.",
			{"limit": {"type": "integer", "default": 30}, "user": {"type": "string"}, "team": {"type": "string"}, "reference_doctype": {"type": "string"}},
		),
	)
}


def tool_list() -> list:
	return [t["spec"] for t in TOOLS.values()]
