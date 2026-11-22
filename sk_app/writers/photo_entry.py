"""Photo Entry makes ERPNext drafts (SK approved 21-Nov, Shraddha list D).

Before: a photo only became a ToDo, so nothing reached the books (16-18 Nov: 5 bill photos stayed tasks, 7 photos were
uploaded and attached to nothing because the save failed silently). Now:
- the phone reads the photo itself (bundled tesseract, no outside or paid API) and sends only the text read;
  read() picks the facts (photo_entry_rules) and matches the party by GSTIN (or what she chose before for that text);
- save() makes the DRAFT in ERPNext with the photo attached: Purchase Invoice (from the PO / receipt, or without PO to an
  expense head, flagged to SK), Sales Invoice (from the Sales Order / Delivery Note), Payment Entry (UTR, allocated by
  the KF-04447 rule), Journal Entry (expense head + Cabin / Non-Cabin cost centre), or a ToDo for "Other";
- a double (same party + bill no, or same UTR) is refused with a link to the earlier record;
- the photo is uploaded first; a photo left attached to nothing shows in "Not saved" with Retry, so none is lost;
- Shraddha posts each draft with Post (the existing gates in try_submit).
"""

import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate

from sk_app.finance import ACCOUNTS, PHOTO_TAG
from sk_app.photo_entry_rules import KINDS, parse, problems
from sk_app.store import _company, attach, need

NO_PO_FIELD = "sk_no_po"
OWN_GSTINS = ("27ABBCS4285J1ZZ",)
DOCTYPES = ("Purchase Invoice", "Sales Invoice", "Payment Entry", "Journal Entry")


def ensure_fields():
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	create_custom_fields({"Purchase Invoice": [{"fieldname": NO_PO_FIELD, "label": "Bill without PO (SK to see)", "fieldtype": "Check",
		"insert_after": "bill_date", "read_only": 1, "no_copy": 1, "in_standard_filter": 1}]}, update=True)


def _gstin_field(doctype: str) -> str | None:
	return "gstin" if frappe.db.has_column(doctype, "gstin") else None


def _party_by_gstin(doctype: str, gstin: str) -> str | None:
	field = _gstin_field(doctype)
	if not gstin or not field:
		return None
	return frappe.db.get_value(doctype, {field: gstin, "disabled": 0}, "name")


def _sbi_account(company: str) -> str | None:
	"""SK: payments are net banking from STATE BANK OF INDIA by default."""
	abbr = frappe.get_cached_value("Company", company, "abbr")
	name = f"STATE BANK OF INDIA - {abbr}"
	if frappe.db.exists("Account", name):
		return name
	from sk_app.finance import bank_account

	return bank_account(company, "Net Banking")


def expense_heads(company: str, supplier: str | None = None) -> list[str]:
	"""Expense ledgers; the heads used before for this supplier come first (last used on top)."""
	heads = frappe.get_all("Account", filters={"company": company, "is_group": 0, "root_type": "Expense", "disabled": 0},
		pluck="name", order_by="account_name asc")
	used = []
	if supplier:
		used = [r[0] for r in frappe.db.sql("""select pii.expense_account from `tabPurchase Invoice Item` pii
			join `tabPurchase Invoice` pi on pi.name = pii.parent where pi.supplier = %s and pi.docstatus < 2 and pii.expense_account is not null
			group by pii.expense_account order by max(pi.posting_date) desc limit 5""", supplier)]
	return list(dict.fromkeys([h for h in used if h in heads] + heads))


def _open_docs(kind: str, party: str | None) -> dict:
	if not party:
		return {}
	from sk_app.store import material_pos

	if kind == "supplier_bill":
		return {"orders": frappe.get_all("Purchase Order", filters={"supplier": party, "docstatus": 1, "per_billed": ["<", 100], **material_pos()},
				fields=["name", "grand_total", "transaction_date"], order_by="creation desc", limit=10),
			"receipts": frappe.get_all("Purchase Receipt", filters={"supplier": party, "docstatus": 1, "per_billed": ["<", 100], "is_return": 0},
				fields=["name", "grand_total", "posting_date"], order_by="creation desc", limit=10)}
	if kind == "sales_invoice":
		return {"orders": frappe.get_all("Sales Order", filters={"customer": party, "docstatus": 1, "per_billed": ["<", 100], "status": ["not in", ["Closed"]]},
				fields=["name", "grand_total", "transaction_date"], order_by="creation desc", limit=10),
			"deliveries": frappe.get_all("Delivery Note", filters={"customer": party, "docstatus": 1, "per_billed": ["<", 100], "is_return": 0},
				fields=["name", "grand_total", "posting_date"], order_by="creation desc", limit=10)}
	if kind in ("money_in", "money_out"):
		from sk_app.writers.payment_allocate import open_invoices

		return {"bills": open_invoices("Customer" if kind == "money_in" else "Supplier", party, _company())}
	return {}


def duplicate(kind: str, v: dict) -> str | None:
	"""The earlier record of the same bill (party + bill no) or the same payment (UTR)."""
	if kind == "supplier_bill" and v.get("supplier") and (v.get("bill_no") or "").strip():
		return frappe.db.get_value("Purchase Invoice", {"supplier": v["supplier"], "bill_no": v["bill_no"].strip(), "docstatus": ["<", 2]}, "name")
	if kind in ("money_in", "money_out") and (v.get("utr") or "").strip():
		return frappe.db.get_value("Payment Entry", {"reference_no": v["utr"].strip(), "docstatus": ["<", 2]}, "name")
	return None


def read(user: str, kind: str, text: str, party: str | None = None) -> dict:
	"""Facts from the text the phone read, the party found by GSTIN, and what to pick from (orders, bills, heads)."""
	need(user, ACCOUNTS)
	from sk_app.photocheck import learned

	facts = parse(text or "", OWN_GSTINS)
	ptype = "Customer" if kind in ("sales_invoice", "money_in") else "Supplier" if kind in ("supplier_bill", "money_out") else None
	given, party, how = party, None, None
	if ptype and party_given_ok(ptype, given):
		party, how = given, "picked"
	elif ptype:
		for g in facts["gstins"]:
			party = _party_by_gstin(ptype, g)
			if party:
				how = f"GSTIN {g}"
				break
		if not party and facts["gstin"]:
			party = learned(ptype.lower(), facts["gstin"])
			how = "chosen before for this GSTIN" if party else None
	facts.update({"party_type": ptype, "party": party or "", "party_found_by": how or ""})
	if ptype:
		facts[ptype.lower()] = party or ""
	company = _company()
	out = {"facts": facts, **_open_docs(kind, party)}
	if kind in ("supplier_bill", "expense"):
		out["expense_heads"] = expense_heads(company, party if kind == "supplier_bill" else None)
	if kind == "expense":
		out["cost_centers"] = frappe.get_all("Cost Center", filters={"company": company, "is_group": 0, "disabled": 0}, pluck="name", order_by="name asc")
		out["money_accounts"] = frappe.get_all("Account", filters={"company": company, "is_group": 0, "account_type": ["in", ["Bank", "Cash"]], "disabled": 0},
			pluck="name", order_by="account_type asc, account_name asc")
	dup = duplicate(kind, {**facts, "supplier": party})
	if dup:
		out["duplicate"] = dup
	return out


def party_given_ok(ptype: str, party: str | None) -> bool:
	return bool(party) and bool(frappe.db.exists(ptype, party))


def _flag_no_po(pi, user: str):
	"""SK decided 21-Nov: a bill without PO is allowed as a draft but SK sees each one."""
	from sk_app.store import _todo, _users_with_function

	pi.db_set(NO_PO_FIELD, 1)
	text = _("Bill without PO: {0} {1} Rs {2} (by {3})").format(pi.supplier_name or pi.supplier, pi.bill_no or "", frappe.utils.fmt_money(pi.grand_total),
		frappe.utils.get_fullname(user))
	pi.add_comment("Comment", text)
	for boss in _users_with_function("Management")[:1] or ["Administrator"]:
		_todo(boss, "Purchase Invoice", pi.name, text)


def _purchase_bill(user: str, v: dict):
	from sk_app.writers.bill import make_bill

	if v.get("purchase_order") or v.get("purchase_receipt"):
		r = make_bill(user, v.get("purchase_order"), v["bill_no"], v.get("bill_date"), photo=None, purchase_receipt=v.get("purchase_receipt"))
		return frappe.get_doc("Purchase Invoice", r["name"])
	from erpnext.controllers.accounts_controller import get_taxes_and_charges

	company = _company()
	pi = frappe.new_doc("Purchase Invoice")
	pi.company = company
	pi.supplier = v["supplier"]
	pi.bill_no = v["bill_no"].strip()
	pi.bill_date = getdate(v.get("bill_date") or nowdate())
	pi.append("items", {"item_name": (v.get("what") or _("Bill without PO"))[:140], "description": v.get("what") or _("As per supplier bill {0}").format(pi.bill_no),
		"qty": 1, "rate": flt(v.get("taxable")), "uom": "Nos", "expense_account": v["expense_account"],
		**({"cost_center": v["cost_center"]} if v.get("cost_center") else {})})
	gst = flt(v.get("cgst")) + flt(v.get("sgst")) + flt(v.get("igst"))
	gstin = frappe.db.get_value("Supplier", pi.supplier, "gstin") if _gstin_field("Supplier") else None
	if gst > 0:
		abbr = frappe.get_cached_value("Company", company, "abbr")
		out_state = flt(v.get("igst")) > 0 or (gstin and not gstin.startswith("27"))
		tmpl = f"Input GST {'Out' if out_state else 'In'}-state - {abbr}"
		if frappe.db.exists("Purchase Taxes and Charges Template", tmpl):
			pi.taxes_and_charges = tmpl
			for t in get_taxes_and_charges("Purchase Taxes and Charges Template", tmpl):
				pi.append("taxes", t)
	pi.flags.ignore_permissions = True
	pi.insert()
	_flag_no_po(pi, user)
	return pi


def _sales_invoice(user: str, v: dict):
	if v.get("delivery_note"):
		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice

		si = make_sales_invoice(v["delivery_note"])
	else:
		from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice

		si = make_sales_invoice(v["sales_order"], ignore_permissions=True)
	si.flags.ignore_permissions = True
	si.insert()  # its name comes from the running Tally series (invoice_naming)
	return si


def _payment(user: str, kind: str, v: dict):
	from sk_app.writers.payment_allocate import open_invoices
	from sk_app.writers.payment_allocate_rules import allocate

	company = _company()
	ptype, party = ("Customer", v["customer"]) if kind == "money_in" else ("Supplier", v["supplier"])
	amount = flt(v["amount"])
	pe = frappe.new_doc("Payment Entry")
	pe.update({"company": company, "payment_type": "Receive" if kind == "money_in" else "Pay", "party_type": ptype, "party": party,
		"posting_date": getdate(v.get("bill_date") or nowdate()), "paid_amount": amount, "received_amount": amount,
		"mode_of_payment": "Net Banking" if frappe.db.exists("Mode of Payment", "Net Banking") else None,
		"reference_no": (v.get("utr") or "").strip() or _("Photo entry {0}").format(nowdate()), "reference_date": getdate(v.get("bill_date") or nowdate())})
	bank = _sbi_account(company)
	if kind == "money_in":
		pe.paid_to = bank
	else:
		pe.paid_from = bank
	pe.setup_party_account_field()
	pe.set_missing_values()
	pe.source_exchange_rate = pe.source_exchange_rate or 1  # INR both sides
	pe.target_exchange_rate = pe.target_exchange_rate or 1
	bills = open_invoices(ptype, party, company)
	rows, why = allocate(amount, bills, " ".join(str(v.get(k) or "") for k in ("bill_no", "note", "text")))
	dt = "Sales Invoice" if ptype == "Customer" else "Purchase Invoice"
	for r in rows:
		pe.append("references", {"reference_doctype": dt, "reference_name": r["name"], "allocated_amount": r["amount"]})
	if rows:
		pe.set_missing_ref_details()
	pe.set_amounts()
	pe.flags.ignore_permissions = True
	pe.insert()
	pe.add_comment("Comment", _("Photo entry. Bills allocated: {0}").format(why))  # KF-04447 rule, so she sees why
	return pe


def _journal(user: str, v: dict):
	from sk_app.writers.journal import write

	money = v.get("money_account") or _sbi_account(_company())
	je, _posted = write(user, v["expense_account"], money, v["amount"], cost_center=v.get("cost_center"),
		narration=v.get("note") or v.get("what") or _("Photo entry"))
	return je


def save(user: str, kind: str, photo: str, v: dict) -> dict:
	"""Make the draft for the photo. The photo must already be uploaded (it is never lost: unattached ones show in Not saved)."""
	need(user, ACCOUNTS)
	v = frappe._dict(v or {})
	if not photo:
		frappe.throw(_("Please take a photo or pick the PDF"))
	missing = problems(kind, v)
	if missing:
		frappe.throw("<br>".join(_(m) for m in missing), title=_("Please check"))
	dup = duplicate(kind, v)
	if dup:
		dt = "Purchase Invoice" if kind == "supplier_bill" else "Payment Entry"
		frappe.throw(_("Already entered: <a href='/app/{0}/{1}'>{1}</a>").format(frappe.scrub(dt).replace("_", "-"), dup), title=_("Double entry"))
	if kind == "other":
		todo = frappe.get_doc({"doctype": "ToDo", "allocated_to": user, "priority": "High", "date": nowdate(),
			"description": f"{PHOTO_TAG} [other]: " + (v.get("note") or _("Other document"))}).insert(ignore_permissions=True)
		attach(photo, "ToDo", todo.name, user)
		return {"doctype": "ToDo", "name": todo.name}
	doc = {"supplier_bill": lambda: _purchase_bill(user, v), "sales_invoice": lambda: _sales_invoice(user, v),
		"money_in": lambda: _payment(user, kind, v), "money_out": lambda: _payment(user, kind, v), "expense": lambda: _journal(user, v)}[kind]()
	attach(photo, doc.doctype, doc.name, user)
	if v.get("read_party_text") and v.get("party_chosen"):  # her correction is kept: next time the same GSTIN finds it
		from sk_app.photocheck import learn

		learn(user, ("customer" if kind in ("sales_invoice", "money_in") else "supplier"), v.read_party_text, v.party_chosen)
	return {"doctype": doc.doctype, "name": doc.name, "grand_total": flt(doc.get("grand_total") or doc.get("paid_amount") or doc.get("total_debit")),
		"no_po": bool(doc.get(NO_PO_FIELD)), "url": f"/app/{frappe.scrub(doc.doctype).replace('_', '-')}/{doc.name}"}


def not_saved(user: str) -> list[dict]:
	"""Photos she uploaded in the last 30 days that are attached to nothing (a save that failed): Retry from here."""
	need(user, ACCOUNTS)
	return frappe.get_all("File", filters={"owner": user, "is_folder": 0, "attached_to_name": ["is", "not set"],
		"creation": [">=", frappe.utils.add_days(nowdate(), -30)]}, fields=["name", "file_name", "file_url", "creation"], order_by="creation desc", limit=50)


def drop_photo(user: str, file: str) -> dict:
	"""Not needed (a wrong photo): removed from the Not saved list."""
	need(user, ACCOUNTS)
	f = frappe.get_doc("File", file)
	if f.owner != user or f.attached_to_name:
		frappe.throw(_("Not your photo"), frappe.PermissionError)
	f.delete(ignore_permissions=True)
	return {"ok": True}


def drafts(user: str) -> list[dict]:
	"""Her drafts of the last 30 days (made here or in ERPNext), each with Post."""
	need(user, ACCOUNTS)
	out = []
	since = frappe.utils.add_days(nowdate(), -30)
	for dt, title, amt in (("Purchase Invoice", "supplier_name", "grand_total"), ("Sales Invoice", "customer_name", "grand_total"),
			("Payment Entry", "party_name", "paid_amount"), ("Journal Entry", "user_remark", "total_debit")):
		extra = [NO_PO_FIELD] if dt == "Purchase Invoice" and frappe.db.has_column(dt, NO_PO_FIELD) else []
		for r in frappe.get_all(dt, filters={"owner": user, "docstatus": 0, "creation": [">=", since]},
				fields=["name", f"{title} as title", f"{amt} as amount", "creation"] + extra, order_by="creation desc", limit=30):
			r.update({"doctype": dt, "creation": str(r.creation), "no_po": bool(r.get(NO_PO_FIELD)),
				"url": f"/app/{frappe.scrub(dt).replace('_', '-')}/{r.name}"})
			out.append(r)
	return sorted(out, key=lambda r: r["creation"], reverse=True)
