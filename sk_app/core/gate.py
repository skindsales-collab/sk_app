"""Switch gate (SK 6-Nov "no missing after rebuild"). When SK flips a module Old → New on SK Path Switch, the counts per
doctype and per person are saved on that row. Nightly, and on demand (api.gate_check), the counts now (minus records made
after the switch) are compared with the saved ones; any record missing is written to SK Rule Log (mode Gate), a ToDo
goes to the CEO, and the result shows on the switch row. The same check runs for every module before old code removal."""

import json

import frappe
from frappe import _
from frappe.utils import now_datetime, nowdate

from sk_app.core.gate_rules import compare

SWITCH = "SK Path Switch"
MODE = "Gate"
# the records each module's flow makes; the owner field is the person whose arrows count them
DOCTYPES = {
	"Sales": {"CRM Lead": "lead_owner", "CRM Deal": "deal_owner", "Quotation": "owner", "Sales Order": "owner", "Customer": "owner"},
	"Finance": {"Sales Invoice": "owner", "Purchase Invoice": "owner", "Payment Entry": "owner", "Journal Entry": "owner"},
	"Purchase": {"Material Request": "owner", "Purchase Order": "owner", "Supplier": "owner"},
	"Store": {"Purchase Receipt": "owner", "Stock Entry": "owner", "Item": "owner"},
	"Production": {"Work Order": "owner", "Job Card": "owner", "Project": "owner"},
	"HR": {"Employee": "owner", "Attendance": "owner", "Leave Application": "owner", "Employee Checkin": "owner"},
	"Home": {"SK App User": "owner", "ToDo": "allocated_to"},
}


def counts(module: str, since=None) -> dict:
	"""{doctype: {"total", "by_owner"}} of records not cancelled (docstatus < 2), optionally only those made since a time."""
	out = {}
	for dt, owner in DOCTYPES.get(module, {}).items():
		if not frappe.db.exists("DocType", dt):
			continue
		filters = {}
		if frappe.get_meta(dt).is_submittable:
			filters["docstatus"] = ["<", 2]
		if since:
			filters["creation"] = [">", since]
		rows = frappe.get_all(dt, filters=filters, fields=[f"`{owner}` as o", "count(name) as n"], group_by=owner, as_list=True)
		out[dt] = {"total": sum(int(r[1]) for r in rows), "by_owner": {str(r[0] or ""): int(r[1]) for r in rows}}
	return out


def on_switch(doc, method=None):
	"""SK Path Switch saved: a flip to New saves the before-counts; a flip back to Old clears the gate."""
	if not doc.meta.has_field("gate_snapshot") or not doc.has_value_changed("path"):
		return
	if doc.path == "New":
		doc.gate_snapshot = json.dumps(counts(doc.module))
		doc.switched_on = now_datetime()
		doc.gate_result = _("Switched to New: counts saved, checked nightly")
	else:
		doc.gate_result = _("Back on Old since {0}").format(nowdate())


def check(module: str, tell: bool = True) -> dict:
	row = frappe.db.get_value(SWITCH, module, ["path", "gate_snapshot", "switched_on"], as_dict=True) if frappe.db.table_exists(SWITCH) else None
	if not row or not row.gate_snapshot:
		return {"module": module, "ok": True, "note": "no switch snapshot"}
	before = json.loads(row.gate_snapshot)
	result = compare(before, counts(module), counts(module, since=row.switched_on))
	result["module"] = module
	frappe.db.set_value(SWITCH, module, "gate_result", (("OK " if result["ok"] else "MISSING ") + str(now_datetime())[:16] + " " +
		", ".join(f"{r['doctype']} {r['before']}→{r['now']} (+{r['new']}, missing {r['missing']})" for r in result["rows"]))[:1000], update_modified=False)
	if not result["ok"]:
		for dt, m in result["missing"].items():
			frappe.get_doc({"doctype": "SK Rule Log", "module": module, "rule": "gate_missing_records", "mode": MODE, "reference_doctype": dt,
				"detail": json.dumps(m)[:1000]}).insert(ignore_permissions=True)
		if tell:
			from sk_app.core.people import ceo_users

			text = _("Switch gate {0}: records missing since the switch to New: {1}. The module must not go further until this is explained.").format(
				module, "; ".join(f"{dt} {m['total']}" + (f" ({', '.join(f'{o}: {n}' for o, n in m['by_owner'].items())})" if m["by_owner"] else "")
				for dt, m in result["missing"].items())) + " <a href='/app/sk-path-switch'>SK Path Switch</a>"
			for u in ceo_users():
				frappe.get_doc({"doctype": "ToDo", "allocated_to": u, "description": text, "priority": "High", "date": nowdate(),
					"reference_type": SWITCH, "reference_name": module}).insert(ignore_permissions=True)
	return result


def nightly() -> dict:
	"""Every module on New, before the scorecard. Also the gate before old code removal (all modules must be OK)."""
	if not frappe.db.table_exists(SWITCH):
		return {}
	frappe.db.delete("SK Rule Log", {"mode": MODE})
	return {m: check(m) for m in frappe.get_all(SWITCH, filters={"path": "New"}, pluck="module")}
