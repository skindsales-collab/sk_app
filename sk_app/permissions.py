"""Record rules: people see and write only their own DSI and Work Book entries; managers see all."""

import frappe

MANAGER_ROLES = {"System Manager", "Sales Manager", "HR Manager"}


def _is_manager(user: str) -> bool:
	return bool(MANAGER_ROLES & set(frappe.get_roles(user)))


def stamp_user(doc, method=None):
	"""Ordinary users can only create entries for themselves."""
	user = frappe.session.user
	if not doc.user or not _is_manager(user) or user == "Guest":
		doc.user = user


def own_or_manager(doc, ptype=None, user=None):
	user = user or frappe.session.user
	if _is_manager(user):
		return True
	return doc.user == user or doc.owner == user


# ---------- CRM leads and deals per salesperson (SK 27-Oct: "lead is not yet segregated sales person wise") ----------

CRM_OWNER = {"CRM Lead": "lead_owner", "CRM Deal": "deal_owner"}
SALES_FUNCTIONS = {"Sales", "Marketing", "Machine Shifting"}


def _crm_owners(user: str) -> list[str] | None:
	"""None = sees all (CEO / Management / System Manager, and people outside Sales who only get ERPNext's own rights);
	else the salesperson's own records, and a sales manager's team too (Rushi sees Swati, Pranali and Rahul)."""
	from sk_app.logins import profile_functions

	if user == "Administrator" or "System Manager" in frappe.get_roles(user):
		return None
	functions = profile_functions(user)
	# SK 28-Oct: Marketing (Pranali) and Machine Shifting (Aditya) logins without Sales saw every lead in the CRM
	if "Management" in functions or not SALES_FUNCTIONS & set(functions):
		return None
	from sk_app.flows import _owners

	return _owners(user)


def _crm_condition(doctype: str, user: str | None) -> str:
	user = user or frappe.session.user
	owners = _crm_owners(user)
	if owners is None:
		return ""
	table, field = f"`tab{doctype}`", CRM_OWNER[doctype]
	people = ", ".join(frappe.db.escape(u) for u in owners)
	cond = f"{table}.`{field}` in ({people}) or {table}.`owner` = {frappe.db.escape(user)} or {table}.`_assign` like {frappe.db.escape('%' + user + '%')}"
	if len(owners) > 1:  # a manager also sees new leads nobody owns yet, to give them out
		cond += f" or ifnull({table}.`{field}`, '') = ''"
	return f"({cond})"


def crm_lead_query(user=None):
	return _crm_condition("CRM Lead", user)


def crm_deal_query(user=None):
	return _crm_condition("CRM Deal", user)


def crm_record(doc, ptype=None, user=None):
	"""Opening one lead / deal by its link follows the same rule as the lists."""
	user = user or frappe.session.user
	owners = _crm_owners(user)
	if owners is None:
		return True
	field = CRM_OWNER[doc.doctype]
	value = doc.get(field)
	if value in owners or doc.owner == user or user in (doc.get("_assign") or "") or (len(owners) > 1 and not value):
		return True
	return False


def ensure_crm_search():
	"""SK 27-Oct: find a lead in ERPNext by person, company, mobile or status (search box and link fields)."""
	from frappe.custom.doctype.property_setter.property_setter import make_property_setter

	for doctype, fields in (("CRM Lead", ["lead_name", "organization", "mobile_no", "lead_owner", "status"]),
			("CRM Deal", ["organization", "lead_name", "mobile_no", "deal_owner", "status"])):
		if not frappe.db.exists("DocType", doctype):
			continue
		meta = frappe.get_meta(doctype)
		have = [f for f in fields if meta.has_field(f)]
		make_property_setter(doctype, None, "search_fields", ",".join(have), "Data", validate_fields_for_doctype=False)
		for f in have[:3]:
			make_property_setter(doctype, f, "in_global_search", 1, "Check", validate_fields_for_doctype=False)
