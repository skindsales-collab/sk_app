"""Cabin / Non-Cabin segment, two levels like Tally (change list point 2, SK 26-Oct-2026).

Customer Group is the segment in ERPNext: All Customer Groups → Cabin (Standard Cabin, LGSF, Modular) and Non-Cabin
(Machine Shifting, Job Work, Other). ERPNext copies it into every Quotation, Sales Order, Delivery Note and Sales
Invoice. CRM Lead / Deal keep the sub-segment in sk_segment and the app fills sk_main_segment. The cabin team sees
only Cabin customers, Aditya only Non-Cabin ones; Management, Accounts and the AI desk see both. A customer with no
segment yet is seen by Management only, and by Rushi / Aditya on the "Segment not set" tab to tag it with one tap.
"""

import frappe
from frappe import _

CABIN, NON_CABIN, BOTH = "Cabin", "Non-Cabin", "Both"
TREE = {
	CABIN: ["Standard Cabin (GI / ACP)", "LGSF", "Modular / Labour Camp"],
	NON_CABIN: ["Machine Shifting", "Job Work", "Other"],
}
SUB_SEGMENTS = [s for subs in TREE.values() for s in subs]
LEGACY = {"Cabin": "Standard Cabin (GI / ACP)"}  # the old flat list had a plain "Cabin"
# Customer Group names are unique in ERPNext, so "Other" gets its main segment in the name
GROUP_OF = {s: ("Other Non-Cabin" if s == "Other" else s) for s in SUB_SEGMENTS}
SEGMENT_OF_GROUP = {g: s for s, g in GROUP_OF.items()}
OLD_GROUPS = {"Commercial": "Company", "Government": "Company", "Individual": "Individual", "Non Profit": "Company"}
BOTH_FUNCTIONS = {"Management", "Accounts", "AI", "IT / ERP"}


def sub_of(segment: str | None) -> str | None:
	segment = LEGACY.get(segment, segment)
	return segment if segment in SUB_SEGMENTS else None


def main_of(segment: str | None) -> str | None:
	if segment in TREE:
		return segment
	sub = sub_of(segment) or SEGMENT_OF_GROUP.get(segment)
	return next((main for main, subs in TREE.items() if sub in subs), None)


def groups_of(main: str) -> list[str]:
	"""Customer Groups of a main segment (the group itself and its sub-groups)."""
	return [main] + [GROUP_OF[s] for s in TREE.get(main, [])]


def all_groups() -> list[str]:
	return [g for main in TREE for g in groups_of(main)]


def user_main(user: str) -> str:
	"""Cabin, Non-Cabin or Both for a person: set on SK App User, otherwise from the function."""
	if user == "Administrator":
		return BOTH
	set_on = frappe.db.get_value("SK App User", {"user": user}, "sk_main_segment")
	if set_on in (CABIN, NON_CABIN, BOTH):
		return set_on
	from sk_app.logins import profile_functions

	functions = set(profile_functions(user))
	if functions & BOTH_FUNCTIONS:
		return BOTH
	if "Machine Shifting" in functions and not functions & {"Sales", "Marketing"}:
		return NON_CABIN
	if functions & {"Sales", "Marketing"}:
		return CABIN
	return BOTH


def can_tag(user: str) -> bool:
	"""Management, Rushi (a manager of a sales team) and Aditya tag the customers that have no segment yet."""
	from sk_app.day_report import _team

	main = user_main(user)
	return main == BOTH or main == NON_CABIN or bool(_team(user))


def ensure_customer_groups():
	"""Add Cabin / Non-Cabin and their sub-groups under All Customer Groups (old groups stay, nothing is removed)."""
	if not frappe.db.exists("DocType", "Customer Group"):
		return
	root = frappe.db.get_value("Customer Group", {"is_group": 1, "parent_customer_group": ["in", ["", None]]}) or "All Customer Groups"
	if not frappe.db.exists("Customer Group", root):
		return
	for main, subs in TREE.items():
		if not frappe.db.exists("Customer Group", main):
			frappe.get_doc({"doctype": "Customer Group", "customer_group_name": main, "parent_customer_group": root,
				"is_group": 1}).insert(ignore_permissions=True)
		for sub in subs:
			if not frappe.db.exists("Customer Group", GROUP_OF[sub]):
				frappe.get_doc({"doctype": "Customer Group", "customer_group_name": GROUP_OF[sub], "parent_customer_group": main,
					"is_group": 0}).insert(ignore_permissions=True)


def ensure_fields():
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	if not frappe.db.exists("DocType", "CRM Lead"):
		return
	# "Cabin" stays in the list so leads saved before the two levels still open; the app turns it into Standard Cabin
	sub = {"fieldname": "sk_segment", "label": "Segment", "fieldtype": "Select",
		"options": "\n" + "\n".join(SUB_SEGMENTS + ["Cabin"]), "insert_after": "source", "in_standard_filter": 1}
	main = {"fieldname": "sk_main_segment", "label": "Main segment", "fieldtype": "Select", "options": f"\n{CABIN}\n{NON_CABIN}",
		"insert_after": "sk_segment", "read_only": 1, "in_standard_filter": 1}
	create_custom_fields({"CRM Lead": [sub, main], "CRM Deal": [sub, main]}, update=True)


def set_main(doc, method=None):
	"""CRM Lead / Deal validate: two-level segment kept in step."""
	if not doc.meta.has_field("sk_segment"):
		return
	if doc.sk_segment in LEGACY:
		doc.sk_segment = LEGACY[doc.sk_segment]
	if doc.meta.has_field("sk_main_segment"):
		doc.sk_main_segment = main_of(doc.sk_segment)


def customer_group_from_deal(doc, method=None):
	"""Customer before_insert: a customer made from a won deal gets the deal's segment as its Customer Group."""
	deal = doc.get("crm_deal")
	if not deal or (doc.customer_group and doc.customer_group in all_groups()):
		return
	segment = frappe.db.get_value("CRM Deal", deal, "sk_segment") if frappe.db.exists("DocType", "CRM Deal") else None
	sub = sub_of(segment)
	if sub and frappe.db.exists("Customer Group", GROUP_OF[sub]):
		doc.customer_group = GROUP_OF[sub]


def _order_totals(names: list[str]) -> dict:
	if not names:
		return {}
	rows = frappe.db.sql("""select customer, sum(base_grand_total) from `tabSales Order`
		where docstatus < 2 and customer in %(names)s group by customer""", {"names": names})
	return dict(rows)


def customers(user: str, tab: str = "mine", q: str | None = None, segment: str | None = None) -> dict:
	"""Customers of the person's segment. tab "not_set": customers with no segment yet, to tag them."""
	main = user_main(user)
	tagger = can_tag(user)
	filters = {"disabled": 0}
	if tab == "not_set":
		if not tagger:
			frappe.throw(_("Only Management, the sales manager and Aditya tag customers"), frappe.PermissionError)
		filters["customer_group"] = ["not in", all_groups()]
	elif main == BOTH:
		filters["customer_group"] = ["in", groups_of(segment) if segment in TREE else all_groups()]
	else:
		filters["customer_group"] = ["in", groups_of(main)]
	or_filters = None
	if (q or "").strip():
		like = f"%{q.strip()}%"
		or_filters = [["customer_name", "like", like], ["mobile_no", "like", like], ["name", "like", like]]
	rows = frappe.get_all("Customer", filters=filters, or_filters=or_filters,
		fields=["name", "customer_name", "customer_group", "mobile_no", "territory"], order_by="modified desc", limit=100)
	totals = _order_totals([r.name for r in rows])
	for r in rows:
		r["segment"] = SEGMENT_OF_GROUP.get(r.customer_group) or (r.customer_group if r.customer_group in TREE else None)
		r["main"] = main_of(r.customer_group)
		r["orders"] = totals.get(r.name) or 0
	not_set = frappe.db.count("Customer", {"disabled": 0, "customer_group": ["not in", all_groups()]}) if tagger else 0
	return {"main": main, "tree": TREE, "rows": rows, "not_set": not_set, "can_tag": tagger}


def tag(user: str, customer: str, segment: str) -> dict:
	"""One tap: put a customer under its segment. An old group (Commercial / Government / Individual) moves to
	Customer Type and is noted on the customer, so nothing is lost."""
	if not can_tag(user):
		frappe.throw(_("Only Management, the sales manager and Aditya tag customers"), frappe.PermissionError)
	sub = sub_of(segment)
	if not sub:
		frappe.throw(_("Pick a segment"))
	ensure_customer_groups()
	old = frappe.db.get_value("Customer", customer, ["customer_group", "customer_type"], as_dict=True)
	if not old:
		frappe.throw(_("Customer not found"))
	values = {"customer_group": GROUP_OF[sub]}
	if old.customer_group in OLD_GROUPS:
		values["customer_type"] = OLD_GROUPS[old.customer_group]
	frappe.db.set_value("Customer", customer, values)
	frappe.get_doc({"doctype": "Comment", "comment_type": "Info", "reference_doctype": "Customer", "reference_name": customer,
		"content": f"Segment set to {sub} in SK App by {frappe.utils.get_fullname(user)}"
		+ (f" (old group: {old.customer_group})" if old.customer_group else "")}).insert(ignore_permissions=True)
	return {"customer": customer, "group": GROUP_OF[sub], "main": main_of(sub)}


def sync_user_permissions():
	"""Optional (SK App Settings → segment user permissions): the same rule on the ERPNext desk with User Permission on
	Customer Group, so the cabin team cannot open Non-Cabin customers there either. Off until SK says so."""
	if not frappe.db.get_single_value("SK App Settings", "segment_user_permissions"):
		return
	for user in frappe.get_all("SK App User", filters={"enabled": 1}, pluck="user"):
		main = user_main(user)
		have = frappe.get_all("User Permission", filters={"user": user, "allow": "Customer Group"}, fields=["name", "for_value"])
		want = main if main in TREE else None
		for p in have:
			if p.for_value != want:
				frappe.delete_doc("User Permission", p.name, ignore_permissions=True)
		if want and not any(p.for_value == want for p in have) and frappe.db.exists("Customer Group", want):
			frappe.get_doc({"doctype": "User Permission", "user": user, "allow": "Customer Group", "for_value": want,
				"apply_to_all_doctypes": 1}).insert(ignore_permissions=True)


def on_app_user_update(doc, method=None):
	if frappe.db.get_single_value("SK App Settings", "segment_user_permissions"):
		sync_user_permissions()
