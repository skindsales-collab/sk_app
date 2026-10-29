"""Check & Submit (SK 29-Oct: "Yogesh doesn't have submit option in app hence pending, pl give option in app & make in
such a way that it can use to low skill person"). Each function sees the drafts it owns in ERPNext, checks the big
numbers and submits with one tap. ERPNext's own submit runs (the mandatory gate and stock / account checks stay);
it runs as the system because many app users may not read accounts (store.as_system), after the app's own check of
who may submit what."""

import frappe
from frappe import _
from frappe.utils import flt

from sk_app import logins
from sk_app.store import submit_for

# function -> doctypes its people submit; own=True: only drafts the person made
SUBMITS = {
	"Stores": [("Stock Reconciliation", False), ("Stock Entry", False), ("Purchase Receipt", False), ("Delivery Note", False)],
	"Production": [("Work Order", False), ("Stock Entry", False)],
	"Purchase": [("Purchase Order", True), ("Material Request", True)],
	"Accounts": [("Sales Invoice", False), ("Purchase Invoice", False), ("Payment Entry", False), ("Journal Entry", False)],
	"Sales": [("Quotation", True), ("Sales Order", True)],
	"Marketing": [("Quotation", True)],
	"Machine Shifting": [("Quotation", True), ("Sales Order", True)],
	"Management": [("Sales Order", False), ("Purchase Order", False), ("Quotation", False)],
}
AMOUNT = {"Stock Reconciliation": "difference_amount", "Stock Entry": "total_outgoing_value", "Work Order": "qty",
	"Material Request": None, "Journal Entry": "total_debit", "Payment Entry": "paid_amount"}
PARTY = {"Quotation": "customer_name", "Sales Order": "customer_name", "Sales Invoice": "customer_name", "Delivery Note": "customer_name",
	"Purchase Order": "supplier_name", "Purchase Invoice": "supplier_name", "Purchase Receipt": "supplier_name", "Payment Entry": "party_name",
	"Work Order": "production_item", "Stock Entry": "stock_entry_type", "Stock Reconciliation": "purpose", "Journal Entry": "voucher_type",
	"Material Request": "material_request_type"}


def _allowed(user: str) -> dict:
	if "System Manager" in frappe.get_roles(user):
		fns = list(SUBMITS)
	else:
		fns = [f for f in logins.profile_functions(user) if f in SUBMITS]
	out = {}
	for f in fns:
		for doctype, own in SUBMITS[f]:
			out[doctype] = out.get(doctype, True) and own  # one function that may submit all of them wins
	return out


def my_drafts(user: str) -> list[dict]:
	rows = []
	for doctype, own in _allowed(user).items():
		if not frappe.db.exists("DocType", doctype):
			continue
		amount = AMOUNT.get(doctype, "grand_total")
		fields = ["name", "owner", "modified", PARTY[doctype]] + ([amount] if amount else [])
		filters = {"docstatus": 0, **({"owner": user} if own else {})}
		for r in frappe.get_all(doctype, filters=filters, fields=fields, order_by="modified desc", limit=50):
			rows.append({"doctype": doctype, "name": r.name, "party": r.get(PARTY[doctype]) or "", "amount": flt(r.get(amount)) if amount else None,
				"by": frappe.utils.get_fullname(r.owner), "modified": str(r.modified)[:16]})
	return sorted(rows, key=lambda r: r["modified"], reverse=True)


def lines(user: str, doctype: str, name: str) -> dict:
	"""The draft's lines in big numbers to check before submitting (stock count: book qty, counted qty, difference)."""
	_check(user, doctype, name)
	doc = frappe.get_doc(doctype, name)
	out = []
	for r in doc.get("items") or doc.get("accounts") or doc.get("references") or []:
		row = {"item": r.get("item_name") or r.get("item_code") or r.get("account") or r.get("reference_name") or "",
			"qty": flt(r.get("qty")), "uom": r.get("uom") or r.get("stock_uom") or "", "amount": flt(r.get("amount") or r.get("debit") or r.get("allocated_amount"))}
		if doctype == "Stock Reconciliation":
			row.update({"old": flt(r.get("current_qty")), "new": flt(r.get("qty")), "diff": flt(r.get("qty")) - flt(r.get("current_qty"))})
		out.append(row)
	return {"doctype": doctype, "name": name, "lines": out, "party": doc.get(PARTY.get(doctype, "name")) or "",
		"total": flt(doc.get("grand_total") or doc.get("total_debit") or doc.get("paid_amount") or doc.get("difference_amount"))}


def _check(user: str, doctype: str, name: str):
	allowed = _allowed(user)
	if doctype not in allowed:
		frappe.throw(_("You may not submit {0}").format(_(doctype)), frappe.PermissionError)
	if allowed[doctype] and frappe.db.get_value(doctype, name, "owner") != user:
		frappe.throw(_("Only the person who made {0} submits it").format(name), frappe.PermissionError)


def submit(user: str, doctype: str, name: str) -> dict:
	_check(user, doctype, name)
	doc = frappe.get_doc(doctype, name)
	if doc.docstatus == 1:
		return {"submitted": True, "name": name}
	if doc.docstatus != 0:
		frappe.throw(_("{0} is cancelled").format(name))
	if not submit_for(doc, user):
		# the reason ERPNext gave is on the draft as a comment (store.try_submit)
		why = frappe.get_all("Comment", filters={"reference_doctype": doctype, "reference_name": name, "comment_type": "Comment"},
			fields=["content"], order_by="creation desc", limit=1)
		frappe.throw(_("{0} could not be submitted: {1}").format(name, frappe.utils.strip_html(why[0].content) if why else _("check it in ERPNext")))
	return {"submitted": True, "name": name}
