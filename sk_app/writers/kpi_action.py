"""The KPI-action writer: the actions a person, their manager, the CEO or the AI add to lift a graph, and closing them with proof.
Plan A step 7 (SK 9-Nov): moved unchanged from home_kpi.py; names unchanged."""

from frappe.utils import add_days, getdate, nowdate
from sk_app.home_kpi import ACTION_MARK, PRIORITY, _check
import frappe


def add_action(user: str, member: str, text: str, priority="Medium", date=None) -> dict:
	member = member or user
	_check(user, member)
	text = (text or "").strip()
	if not text:
		frappe.throw(frappe._("Please write the action"))
	todo = frappe.get_doc({"doctype": "ToDo", "allocated_to": member, "assigned_by": user, "description": ACTION_MARK + text[:500],
		"priority": priority if priority in PRIORITY else "Medium", "date": getdate(date) if date else add_days(nowdate(), 7)})
	todo.insert(ignore_permissions=True)
	return {"name": todo.name}

def finish_action(user: str, name: str, note=None, photo=None) -> dict:
	from sk_app.store import attach

	todo = frappe.get_doc("ToDo", name)
	if not todo.description.startswith(ACTION_MARK) or todo.allocated_to != user:
		frappe.throw(frappe._("Only the person who has the action can close it"), frappe.PermissionError)
	todo.status = "Closed"
	todo.save(ignore_permissions=True)
	if note:
		todo.add_comment("Comment", note)
	attach(photo, "ToDo", todo.name, user)
	return {"ok": True}
