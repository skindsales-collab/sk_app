"""SK's lead status flow (SK 27-Oct-2026): 1) New 2) Qualified 3) Drawing 4) Quotation 5) Negotiations 6) Deal Won
7) Junk Lead 8) Deal Loss. The app's status buttons and the Sales 3D arrows follow these steps."""

import frappe

# (status, CRM type, colour)
FLOW = [("New", "Open", "gray"), ("Qualified", "Ongoing", "blue"), ("Drawing", "Ongoing", "purple"), ("Quotation", "Ongoing", "orange"),
	("Negotiations", "Ongoing", "amber"), ("Deal Won", "Won", "green"), ("Junk Lead", "Junk", "red"), ("Deal Loss", "Lost", "red")]
NAMES = [n for n, _t, _c in FLOW]
# arrow steps (open work only)
STEPS = ["New", "Qualified", "Drawing", "Quotation", "Negotiations"]
# old Frappe CRM statuses, until SK's mapping moves them: which arrow they count in
OLD_STEP = {"Contacted": "New", "Nurture": "Qualified"}
# SK's choice 27-Oct: where the leads in the old CRM statuses go
MOVE = {"Contacted": "New", "Nurture": "Qualified", "Unqualified": "Junk Lead", "Converted": "Deal Won"}
# deal statuses (when a lead was converted) by words in their name
DEAL_WORDS = [("Negotiations", ("negotiat", "ready to close")), ("Quotation", ("quot", "proposal")), ("Drawing", ("draw", "demo", "making"))]


def step_of(status: str | None, deal: bool = False) -> str:
	if status in STEPS:
		return status
	if deal:
		low = (status or "").lower()
		return next((step for step, words in DEAL_WORDS if any(w in low for w in words)), "Qualified")
	return OLD_STEP.get(status, "New")


def ensure_statuses():
	"""Create SK's statuses in the CRM and put them first, in SK's order."""
	if not frappe.db.exists("DocType", "CRM Lead Status"):
		return
	meta = frappe.get_meta("CRM Lead Status")
	df = meta.get_field("type")
	types = set((df.options or "").split("\n")) if df else set()
	for pos, (name, typ, colour) in enumerate(FLOW, start=1):
		if not frappe.db.exists("CRM Lead Status", name):
			doc = frappe.new_doc("CRM Lead Status")
			doc.lead_status = name
			if df and typ in types:
				doc.type = typ
			cf = meta.get_field("color")
			if cf and (cf.fieldtype != "Select" or colour in (cf.options or "").split("\n")):
				doc.color = colour
			doc.position = pos
			try:
				doc.insert(ignore_permissions=True)
			except Exception:
				frappe.log_error(f"SK lead status {name}")  # never stop a deploy for this
				continue
		elif meta.get_field("position"):
			frappe.db.set_value("CRM Lead Status", name, "position", pos, update_modified=False)
	for old, new in MOVE.items():
		if frappe.db.exists("CRM Lead Status", new):
			frappe.db.sql("update `tabCRM Lead` set status = %s where status = %s", (new, old))
	if meta.get_field("position"):
		for i, name in enumerate(n for n in frappe.get_all("CRM Lead Status", pluck="name") if n not in NAMES):
			frappe.db.set_value("CRM Lead Status", name, "position", 20 + i, update_modified=False)


def app_statuses() -> list[dict]:
	"""Status buttons in the app: SK's 8 when the CRM has them, otherwise whatever the CRM has."""
	rows = frappe.get_all("CRM Lead Status", fields=["name", "type"], order_by="position asc")
	mine = [r for r in rows if r.name in NAMES]
	return sorted(mine, key=lambda r: NAMES.index(r.name)) if len(mine) == len(NAMES) else rows
