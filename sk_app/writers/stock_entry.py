"""The one Stock Entry writer (linear flow map, Flow 4 Store). Material given to a job from the app is one Stock Entry
(Material Transfer for Manufacture) from the store to the job's WIP, tied to the job card's rows when it can be. Used
on the New path of Store; the rules also run on every Stock Entry saved in ERPNext or through SK Hub."""

import frappe
from frappe import _
from frappe.utils import flt

from sk_app.core.rules import report
from sk_app.writers.stock_entry_rules import TO_JOB, issue_rows, problems


def issue(user: str, wo, items: list[dict], *, taken_by=None, job_card=None, photo=None, default_store, uom, insert_for, attach,
		submit_for) -> dict:
	source = {r.item_code: r.source_warehouse for r in wo.required_items}
	card_rows = {r.item_code: r.name for r in frappe.get_all("Job Card Item", filters={"parent": job_card, "parenttype": "Job Card"},
		fields=["name", "item_code"])} if job_card else {}
	rows, use_card = issue_rows(items, source, wo.source_warehouse, wo.wip_warehouse, card_rows)
	se = frappe.new_doc("Stock Entry")
	se.stock_entry_type = se.purpose = TO_JOB
	se.work_order = wo.name
	se.company = wo.company
	se.from_bom = 0
	se.to_warehouse = wo.wip_warehouse
	if use_card:
		se.job_card = job_card
	for r in rows:
		r["s_warehouse"] = r["s_warehouse"] or default_store(r["item_code"], wo.company)
		se.append("items", {**r, **uom(r["item_code"])})
	se.remarks = _("Issued from SK App to {0}").format(taken_by or "-") + (f" · {_('Job card')} {job_card}" if job_card and not use_card else "")
	insert_for(se, user)  # on_validate checks it; accounts filled by ERPNext (as_system)
	attach(photo, "Stock Entry", se.name, user)
	return {"name": se.name, "posted": submit_for(se, user)}


def on_validate(doc, method=None):
	"""Every Stock Entry on the New path of Store: lines complete, job named on an issue to a job, who took it."""
	from sk_app.core.switch import use_new

	if doc.docstatus == 1 or not use_new("Store", doc.owner or frappe.session.user):
		return
	rows = [{"item_code": r.item_code, "qty": flt(r.qty), "s_warehouse": r.s_warehouse, "t_warehouse": r.t_warehouse} for r in doc.get("items") or []]
	found = problems(doc.purpose, rows, doc.get("work_order"), doc.get("remarks"))
	report("Store", doc, found, title=_("Issue data missing"))
