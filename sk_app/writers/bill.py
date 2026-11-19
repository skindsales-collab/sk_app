"""The Bill writer (Purchase Invoice from a bill photo, Sales Invoice from a delivery, photo entries, month-close ticks).
Plan A step 5 (SK 9-Nov): moved unchanged from finance.py; names unchanged."""

from frappe import _
from frappe.utils import cint, flt, fmt_money, get_first_day, getdate, nowdate
from sk_app.finance import ACCOUNTS, MONTH_CLOSE, PHOTO_KINDS, _close_key
from sk_app.store import attach, draft_reason, need, try_submit
import frappe


def make_bill(user: str, purchase_order: str | None, bill_no: str, bill_date=None, todo=None, photo=None, purchase_receipt=None,
		items=None, supplier=None) -> dict:
	"""Purchase Invoice with the supplier's bill number, kept as draft to check: from the PO (ERPNext mapping) or from the
	store's receipt against that PO. No bill without a PO (SK 27-Oct purchase flow)."""
	need(user, ACCOUNTS)
	if not (bill_no or "").strip():
		frappe.throw(_("Please give the supplier's bill number"))
	if purchase_order:
		from erpnext.buying.doctype.purchase_order.purchase_order import get_mapped_purchase_invoice

		# Accounts may not read Purchase Orders in ERPNext; the bill is still made from the PO under her login
		pi = get_mapped_purchase_invoice(purchase_order, ignore_permissions=True)
	elif purchase_receipt:
		from erpnext.stock.doctype.purchase_receipt.purchase_receipt import make_purchase_invoice

		pi = make_purchase_invoice(purchase_receipt)
	else:
		# SK 27-Oct: no bill without a PO; material without a PO goes through an urgent requisition and its PO first
		frappe.throw(_("Pick the Purchase Order or the store's receipt. Material without PO: Store raises an urgent requisition first."))
	pi.bill_no = bill_no.strip()
	pi.bill_date = getdate(bill_date or nowdate())
	pi.flags.ignore_permissions = True
	pi.insert()
	attach(photo, "Purchase Invoice", pi.name, user)
	if todo:
		ref = frappe.db.get_value("ToDo", todo, ["allocated_to", "reference_name"], as_dict=True)
		file_url = frappe.db.get_value("File", {"attached_to_doctype": "Supplier", "attached_to_name": ref and ref.reference_name},
			"file_url", order_by="creation desc") if ref else None
		if file_url:
			frappe.get_doc({"doctype": "File", "file_url": file_url, "attached_to_doctype": "Purchase Invoice",
				"attached_to_name": pi.name}).insert(ignore_permissions=True)
		if ref and ref.allocated_to == user:
			frappe.db.set_value("ToDo", todo, "status", "Closed")
	return {"name": pi.name, "grand_total": pi.grand_total}

def done_bill_photo(user: str, todo: str) -> dict:
	"""Bill photo already handled in ERPNext (or not a bill): take it off the list."""
	need(user, ACCOUNTS)
	if frappe.db.get_value("ToDo", todo, "allocated_to") != user:
		frappe.throw(_("Not your task"), frappe.PermissionError)
	frappe.db.set_value("ToDo", todo, "status", "Closed")
	return {"ok": True}

def photo_entry(user: str, kind: str, photo: str, supplier=None, party=None, amount=None, ref_no=None, note=None) -> dict:
	"""Shraddha's photo of a bill / e-invoice / voucher / payment proof. A supplier bill joins Bills to Post (Make bill ->
	draft Purchase Invoice -> Post, as before); every other photo becomes her task with the ERPNext entry to make."""
	need(user, ACCOUNTS)
	if kind not in PHOTO_KINDS:
		frappe.throw(_("Please pick what the photo is"))
	if not photo:
		frappe.throw(_("Please take a photo or pick the PDF"))
	if kind == "supplier_bill":
		from sk_app.writers.purchase_order import send_bill

		if not supplier or not frappe.db.exists("Supplier", supplier):
			frappe.throw(_("Please pick the supplier"))
		send_bill(user, supplier, photo, amount, ref_no, None, note)
		return {"kind": kind, "go": "bills_to_post"}
	label = PHOTO_KINDS[kind][0]
	extra = [x for x in (party, amount and _("Rs {0}").format(fmt_money(flt(amount))), ref_no and _("Ref {0}").format(ref_no), note) if x]
	text = f"{PHOTO_TAG} [{kind}]: {_(label)}" + (" · " + " · ".join(extra) if extra else "")
	todo = frappe.get_doc({"doctype": "ToDo", "allocated_to": user, "description": text, "priority": "High", "date": nowdate()})
	todo.insert(ignore_permissions=True)
	attach(photo, "ToDo", todo.name, user)
	return {"kind": kind, "todo": todo.name, "go": "photo_entries"}

def make_invoice(user: str, delivery_note: str) -> dict:
	"""Sales Invoice from the Delivery Note (items, rates, taxes copied by ERPNext); a draft to check, then Post."""
	need(user, ACCOUNTS)
	from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice

	si = make_sales_invoice(delivery_note)
	si.flags.ignore_permissions = True
	si.insert()
	return {"name": si.name, "grand_total": si.grand_total}

def pay_expense(user: str, expense_claim: str) -> dict:
	need(user, ACCOUNTS)
	from hrms.hr.doctype.expense_claim.expense_claim import make_bank_entry

	je = frappe.get_doc(make_bank_entry("Expense Claim", expense_claim))
	je.cheque_no = je.get("cheque_no") or _("SK App {0}").format(nowdate())
	je.cheque_date = je.get("cheque_date") or nowdate()
	je.flags.ignore_permissions = True
	je.insert()
	posted = try_submit(je)
	return {"name": je.name, "posted": posted, "reason": draft_reason()}

def tick_close(user: str, key: str, done=1) -> dict:
	need(user, ACCOUNTS)
	if key not in dict(MONTH_CLOSE):
		frappe.throw(_("Unknown step"))
	desc = _close_key(get_first_day(nowdate()), key)
	name = frappe.db.get_value("ToDo", {"description": desc})
	status = "Closed" if cint(done) else "Open"
	if name:
		frappe.db.set_value("ToDo", name, {"status": status, "allocated_to": user})
	else:
		frappe.get_doc({"doctype": "ToDo", "allocated_to": user, "description": desc, "status": status, "date": nowdate()}).insert(ignore_permissions=True)
	return {"ok": True}
