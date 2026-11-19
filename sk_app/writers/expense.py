"""The Expense writer (cash voucher / expense claim): claim, CEO decision, voucher fields. Plan A step 4 (SK 9-Nov): moved
unchanged from hr.py; names unchanged."""

from frappe import _
from frappe.utils import cint, flt, getdate, nowdate
from sk_app.hr import _ceos, _close_todos, _is_ceo, _my_employee
from sk_app.store import _company, _todo, _users_with_function, attach
import frappe


def ensure_voucher_fields():
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	if not frappe.db.exists("DocType", "Expense Claim"):
		return
	create_custom_fields({"Expense Claim": [
		{"fieldname": "sk_paid_to", "label": "Paid to", "fieldtype": "Data", "insert_after": "expense_approver"},
		{"fieldname": "sk_cabin", "label": "Project / cabin code", "fieldtype": "Data", "insert_after": "sk_paid_to", "in_standard_filter": 1},
		{"fieldname": "sk_no_bill", "label": "No bill: reason", "fieldtype": "Small Text", "insert_after": "sk_cabin"},
	]}, update=True)

def claim_expense(user: str, expense_type: str, amount, expense_date=None, note: str | None = None, photo: str | None = None,
		paid_to: str | None = None, cabin: str | None = None, no_bill: str | None = None) -> dict:
	"""Cash voucher filled by the person who spent it, with the details the CEO needs; every voucher goes to the CEO."""
	emp = _my_employee(user)
	if flt(amount) <= 0:
		frappe.throw(_("Please give the amount"))
	if not (note or "").strip():
		frappe.throw(_("Please say what the money was spent on"))
	if not photo and not (no_bill or "").strip():
		frappe.throw(_("Please take the bill photo, or say why there is no bill"))
	ceos = [u for u in _ceos() if u != user] or _ceos()
	approver = ceos[0] if ceos else None
	cabin = (cabin or "").strip()
	doc = frappe.get_doc({"doctype": "Expense Claim", "employee": emp.name, "company": emp.company or _company(),
		"expense_approver": approver, "approval_status": "Draft", "posting_date": nowdate(), "remark": (note or "").strip()[:500],
		"expenses": [{"expense_date": getdate(expense_date or nowdate()), "expense_type": expense_type, "amount": flt(amount),
			"description": (note or expense_type).strip()[:300]}]})
	if doc.meta.has_field("sk_paid_to"):
		doc.update({"sk_paid_to": (paid_to or "").strip()[:140], "sk_cabin": cabin[:140], "sk_no_bill": (no_bill or "").strip()[:300] if not photo else None})
	if cabin and frappe.db.exists("Project", cabin):
		doc.project = cabin
	doc.flags.ignore_permissions = True
	doc.flags.ignore_mandatory = True  # payable account and expense accounts are set by Accounts before posting
	doc.insert()
	attach(photo, "Expense Claim", doc.name, user)
	for ceo in ceos:
		_todo(ceo, "Expense Claim", doc.name, f"Cash voucher: {emp.employee_name} Rs {flt(amount):,.0f} ({expense_type}"
			f"{' · ' + cabin if cabin else ''}). Please approve.")
	return {"name": doc.name, "approver": frappe.utils.get_fullname(approver) if approver else None}

def decide_expense(user: str, name: str, ok, note: str | None = None) -> dict:
	"""CEO approves (sanctioned = claimed) or rejects with a reason. ERPNext posts it if the accounts are set; Accounts pays it."""
	from sk_app.store import draft_reason, try_submit

	doc = frappe.get_doc("Expense Claim", name)
	if not _is_ceo(user):
		frappe.throw(_("Only the CEO approves cash vouchers"), frappe.PermissionError)
	if doc.docstatus != 0:
		frappe.throw(_("Already decided"))
	if not cint(ok) and not (note or "").strip():
		frappe.throw(_("Please say why it is rejected"))
	doc.approval_status = "Approved" if cint(ok) else "Rejected"
	for row in doc.expenses:
		row.sanctioned_amount = row.amount if cint(ok) else 0
	doc.flags.ignore_permissions = True
	doc.flags.ignore_mandatory = True
	doc.save()
	posted = try_submit(doc)
	reason = draft_reason()
	if note:
		doc.add_comment("Comment", note.strip()[:300])
	_close_todos("Expense Claim", name)
	if cint(ok):
		for acc in _users_with_function("Accounts"):
			_todo(acc, "Expense Claim", name, f"Approved cash voucher {doc.employee_name} Rs {flt(doc.total_claimed_amount):,.0f}: "
				+ ("pay it in ERPNext" if posted else "set accounts, post and pay in ERPNext"))
	emp_user = frappe.db.get_value("Employee", doc.employee, "user_id")
	if emp_user and emp_user != user:
		_todo(emp_user, "Expense Claim", name, f"Your cash voucher Rs {flt(doc.total_claimed_amount):,.0f}: {doc.approval_status}{' · ' + note if note else ''}")
	return {"status": doc.approval_status, "posted": posted, "reason": reason}
