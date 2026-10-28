"""Segment on every sales entry (SK 28-Oct-2026): "all future data separate in sub group (machine shifting / job work /
maintenance)". The customer's group gives the segment (see segments.py). On a Sales Order / Sales Invoice the app sets
the income ledger (Cabin Sales or Non Cabin Sales) and, for Non-Cabin, the sub-group's cost centre, so the Segment
P&L splits Non-Cabin into Machine Shifting, Job Work and Maintenance. Entries up to now stay "Non-Cabin (combined)".
"""

import frappe

from sk_app import segments

# Non-Cabin sub-group → cost centre group and the leaf used on new entries
SUB_COST_CENTRE = {"Machine Shifting": ("Machine Shifting", "Project Execution"), "Job Work": ("Job Work", "Job Work Execution"),
	"Maintenance": ("Machine Maintenance", "Maintenance Execution")}
INCOME = {segments.CABIN: "Cabin Sales", segments.NON_CABIN: "Non Cabin Sales"}
# income ledgers the app may replace: ERPNext's default and the other segment's ledger
GENERIC_INCOME = ("Sales", "Cabin Sales", "Non Cabin Sales")


def _abbr(company: str) -> str:
	return frappe.get_cached_value("Company", company, "abbr")


def ensure_cost_centres():
	"""Job Work cost centre (group + leaf) next to Machine Shifting and Machine Maintenance, for every company."""
	for company in frappe.get_all("Company", pluck="name"):
		abbr = _abbr(company)
		root = frappe.db.get_value("Cost Center", {"company": company, "is_group": 1, "parent_cost_center": ["in", ["", None]]})
		if not root:
			continue
		for group, leaf in SUB_COST_CENTRE.values():
			if not frappe.db.exists("Cost Center", f"{group} - {abbr}"):
				frappe.get_doc({"doctype": "Cost Center", "cost_center_name": group, "parent_cost_center": root, "company": company,
					"is_group": 1}).insert(ignore_permissions=True)
			if not frappe.db.exists("Cost Center", f"{leaf} - {abbr}"):
				frappe.get_doc({"doctype": "Cost Center", "cost_center_name": leaf, "parent_cost_center": f"{group} - {abbr}",
					"company": company, "is_group": 0}).insert(ignore_permissions=True)


def set_segment(doc, method=None):
	"""Sales Order / Sales Invoice validate: income ledger and cost centre from the customer's segment."""
	if doc.docstatus or not doc.get("customer_group") or not doc.company:
		return
	sub = segments.sub_of(segments.SEGMENT_OF_GROUP.get(doc.customer_group, doc.customer_group))
	main = segments.main_of(sub or doc.customer_group)
	if main not in INCOME:
		return
	abbr = _abbr(doc.company)
	income = f"{INCOME[main]} - {abbr}"
	cost_centre = None
	if main == segments.NON_CABIN and sub in SUB_COST_CENTRE:
		leaf = f"{SUB_COST_CENTRE[sub][1]} - {abbr}"
		cost_centre = leaf if frappe.db.exists("Cost Center", leaf) else None
	if cost_centre and doc.meta.has_field("cost_center"):
		doc.cost_center = cost_centre
	has_income = frappe.db.exists("Account", income)
	for item in doc.get("items") or []:
		if cost_centre and item.meta.has_field("cost_center"):
			item.cost_center = cost_centre
		if has_income and item.meta.has_field("income_account") and \
				(item.income_account or "").rsplit(" - ", 1)[0] in GENERIC_INCOME:
			item.income_account = income
