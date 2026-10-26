"""Quality screens (SK, 26-Oct-2026 draft F04): checks waiting (incoming from Store receipts, stage from Job Cards
marked done, final before dispatch), the checklist from the real Quality Inspection Templates with OK / Not OK taps,
photos and spoken readings, and Non-Conformance sent to the person who must fix it.
"""

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, nowdate

from sk_app.store import _todo, _users_with_function, attach, need, try_submit

QUALITY = "Quality"
FINAL_WORDS = ("final", "inspection", "qc")


def _is_final(operation: str | None) -> bool:
	return any(w in (operation or "").lower() for w in FINAL_WORDS)


def pending(user: str) -> dict:
	"""Checks waiting, oldest first, in three groups."""
	need(user, QUALITY)
	checked = lambda dt: set(frappe.get_all("Quality Inspection", filters={"reference_type": dt, "docstatus": ["<", 2]}, pluck="reference_name"))
	done_pr = checked("Purchase Receipt")
	incoming = []
	for pr in frappe.get_all("Purchase Receipt", filters={"docstatus": ["<", 2], "creation": [">=", add_days(nowdate(), -14)]},
			fields=["name", "supplier_name", "creation", "docstatus"], order_by="creation asc"):
		if pr.name in done_pr:
			continue
		for i in frappe.get_all("Purchase Receipt Item", filters={"parent": pr.name}, fields=["item_code", "item_name", "qty", "uom"]):
			incoming.append({"reference_type": "Purchase Receipt", "reference_name": pr.name, "item_code": i.item_code, "item_name": i.item_name,
				"qty": i.qty, "uom": i.uom, "from": pr.supplier_name, "since": str(pr.creation), "inspection_type": "Incoming"})
	done_jc = checked("Job Card")
	stage, final = [], []
	for jc in frappe.get_all("Job Card", filters={"docstatus": ["<", 2], "modified": [">=", add_days(nowdate(), -30)],
			"status": "Completed"}, fields=["name", "operation", "workstation", "production_item", "item_name", "for_quantity", "modified", "work_order"],
			order_by="modified asc"):
		if jc.name in done_jc:
			continue
		row = {"reference_type": "Job Card", "reference_name": jc.name, "item_code": jc.production_item, "item_name": jc.item_name,
			"qty": jc.for_quantity, "operation": jc.operation, "from": jc.workstation, "since": str(jc.modified), "work_order": jc.work_order,
			"inspection_type": "In Process"}
		(final if _is_final(jc.operation) else stage).append(row)
	for r in final:
		r["inspection_type"] = "Outgoing"
	return {"incoming": incoming, "stage": stage, "final": final}


def templates(user: str) -> list[str]:
	need(user, QUALITY)
	return frappe.get_all("Quality Inspection Template", pluck="name", order_by="name asc")


def guess_template(reference_type: str, operation=None, item_code=None) -> str | None:
	"""QIT-OP-<operation> for a stage, the item's own template for incoming material."""
	if reference_type == "Job Card" and operation:
		for name in frappe.get_all("Quality Inspection Template", pluck="name"):
			if operation.lower() in name.lower():
				return name
	if item_code:
		return frappe.db.get_value("Item", item_code, "quality_inspection_template")
	return None


def checklist(user: str, template: str) -> list[dict]:
	need(user, QUALITY)
	return frappe.get_all("Item Quality Inspection Parameter", filters={"parent": template, "parenttype": "Quality Inspection Template"},
		fields=["specification", "value", "numeric", "min_value", "max_value"], order_by="idx asc")


def save(user: str, reference_type: str, reference_name: str, item_code: str, points: list[dict], template=None,
		sample_size=1, accepted_qty=None, rejected_qty=None, photos=None, remark=None, inspection_type=None) -> dict:
	"""One tap per point (OK / Not OK + spoken reading). Any Not OK makes the inspection Rejected; for a stage that
	opens a Non-Conformance for the workstation's subcontractor and the Production owner."""
	need(user, QUALITY)
	if reference_type not in ("Purchase Receipt", "Job Card", "Delivery Note"):
		frappe.throw(_("Unknown check"))
	points = [p for p in points or [] if p.get("specification")]
	if not points:
		frappe.throw(_("Please tick the checklist"))
	bad = [p for p in points if not cint(p.get("ok"))]
	for p in bad:
		if not (p.get("note") or "").strip():
			frappe.throw(_("Please say what is wrong for: {0}").format(p["specification"]))
	qi = frappe.new_doc("Quality Inspection")
	qi.report_date = nowdate()
	qi.inspection_type = inspection_type or {"Purchase Receipt": "Incoming", "Job Card": "In Process", "Delivery Note": "Outgoing"}[reference_type]
	qi.reference_type = reference_type
	qi.reference_name = reference_name
	qi.item_code = item_code
	qi.sample_size = flt(sample_size) or 1
	qi.inspected_by = user
	qi.manual_inspection = 1
	if template and frappe.db.exists("Quality Inspection Template", template):
		qi.quality_inspection_template = template
	for p in points:
		_spec(p["specification"])
		qi.append("readings", {"specification": p["specification"], "manual_inspection": 1, "reading_value": (p.get("note") or "")[:140],
			"value": p.get("value"), "status": "Accepted" if cint(p.get("ok")) else "Rejected"})
	qi.status = "Rejected" if bad else "Accepted"
	lines = [x for x in (remark, accepted_qty not in (None, "") and _("Accepted qty: {0}").format(flt(accepted_qty)),
		rejected_qty not in (None, "") and _("Rejected qty: {0}").format(flt(rejected_qty))) if x]
	qi.remarks = "\n".join(lines) or None
	qi.flags.ignore_permissions = True
	qi.flags.ignore_mandatory = True
	qi.insert()
	for p in photos or []:
		attach(p, "Quality Inspection", qi.name, user)
	posted = try_submit(qi)
	out = {"name": qi.name, "status": qi.status, "posted": posted}
	if reference_type == "Job Card" and bad:
		out["non_conformance"] = raise_nc(user, _("Rework: {0}").format(", ".join(p["specification"] for p in bad)),
			"\n".join(f"{p['specification']}: {p.get('note')}" for p in bad), job_card=reference_name, photos=photos)["name"]
	if reference_type == "Purchase Receipt" and (bad or flt(rejected_qty)):
		for who in _users_with_function("Stores") + _users_with_function("Purchase"):
			_todo(who, "Purchase Receipt", reference_name, _("Incoming check {0}: {1} rejected. {2}").format(qi.status, flt(rejected_qty), remark or ""))
	return out


def _spec(name: str):
	"""Checklist points typed on the phone that are not yet parameters in ERPNext are added once."""
	if not frappe.db.exists("Quality Inspection Parameter", name):
		frappe.get_doc({"doctype": "Quality Inspection Parameter", "parameter": name}).insert(ignore_permissions=True)


def _procedure() -> str:
	name = frappe.db.get_value("Quality Procedure", {}, "name", order_by="creation asc")
	if name:
		return name
	return frappe.get_doc({"doctype": "Quality Procedure", "quality_procedure_name": "Cabin Manufacturing Quality"}).insert(ignore_permissions=True).name


def raise_nc(user: str, subject: str, details: str, job_card=None, fixer=None, by_when=None, photos=None) -> dict:
	"""Non Conformance to the person who fixes it (the workstation's subcontractor, or the person picked)."""
	need(user, QUALITY, "Production")
	if not (subject or "").strip():
		frappe.throw(_("Please say what is wrong"))
	nc = frappe.new_doc("Non Conformance")
	nc.subject = subject[:140]
	nc.procedure = _procedure()
	nc.status = "Open"
	ref = ""
	if job_card:
		jc = frappe.db.get_value("Job Card", job_card, ["operation", "workstation", "item_name", "work_order"], as_dict=True) or {}
		ref = f"{job_card} · {jc.get('operation') or ''} · {jc.get('item_name') or ''}"
		if not fixer and jc.get("workstation"):
			fixer = frappe.db.get_value("SK App User", {"workstation": jc["workstation"], "enabled": 1}, "user")
	# process owner comes from the Quality Procedure in ERPNext, so the person who fixes it is named in the
	# details and gets the ToDo; the ToDo is what puts it on his phone
	nc.details = "\n".join(x for x in (ref, details, fixer and _("Who fixes: {0}").format(frappe.utils.get_fullname(fixer)),
		by_when and _("Fix by {0}").format(by_when)) if x)
	nc.flags.ignore_permissions = True
	nc.insert()
	for p in photos or []:
		attach(p, "Non Conformance", nc.name, user)
	for who in {fixer, *_users_with_function("Production")} - {None, user}:
		_todo(who, "Non Conformance", nc.name, _("Fix: {0}").format(subject))
	return {"name": nc.name, "fixer": fixer}


def _fixer_of(name: str) -> set[str]:
	return set(frappe.get_all("ToDo", filters={"reference_type": "Non Conformance", "reference_name": name, "status": ["!=", "Cancelled"]},
		pluck="allocated_to"))


def open_ncs(user: str) -> list[dict]:
	need(user, QUALITY, "Production", "Subcontractor")
	filters = {"status": "Open"}
	from sk_app.production import _is_sub_only

	if _is_sub_only(user):
		filters["name"] = ["in", frappe.get_all("ToDo", filters={"reference_type": "Non Conformance", "allocated_to": user,
			"status": "Open"}, pluck="reference_name") or [""]]
	return [{**r, "creation": str(r.creation)} for r in frappe.get_all("Non Conformance", filters=filters,
		fields=["name", "subject", "details", "creation"], order_by="creation asc")]


def close_nc(user: str, name: str, action: str, photo=None) -> dict:
	"""Fixed: the person says what was done and adds an after photo; Quality sees it closed."""
	need(user, QUALITY, "Production", "Subcontractor")
	nc = frappe.get_doc("Non Conformance", name)
	from sk_app.production import _is_sub_only

	if _is_sub_only(user) and user not in _fixer_of(nc.name):
		frappe.throw(_("This is not your job"), frappe.PermissionError)
	if not (action or "").strip():
		frappe.throw(_("Please say what was done"))
	nc.corrective_action = action
	nc.status = "Resolved"
	nc.flags.ignore_permissions = True
	nc.save()
	attach(photo, "Non Conformance", nc.name, user)
	frappe.db.set_value("ToDo", {"reference_type": "Non Conformance", "reference_name": nc.name, "status": "Open"}, "status", "Closed")
	from sk_app.complaints import on_nc_resolved

	on_nc_resolved(nc.name, user, action, photo)  # point 5: a customer complaint fixed in the factory
	return {"name": nc.name, "status": nc.status}


def badges(user: str, functions: list[str]) -> dict:
	out = {}
	if QUALITY in functions:
		p = pending(user)
		out["inspect"] = len(p["incoming"]) + len(p["stage"])
		out["final_check"] = len(p["final"])
		out["non_conformance"] = frappe.db.count("Non Conformance", {"status": "Open"})
	if "Subcontractor" in functions:
		out["my_fixes"] = frappe.db.count("ToDo", {"reference_type": "Non Conformance", "allocated_to": user, "status": "Open"})
	return {k: v for k, v in out.items() if v}
