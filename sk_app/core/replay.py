"""Replay check (SK 4-Nov rebuild): every record since 1-Apr goes through the new shared rules, nothing is changed.

Each gap is one SK Rule Log row (mode "Replay") with its link, so the 7 PM report and SK see exactly what the new path
would have stopped, before any user is switched to it. Run: CEO taps it in the app / opens
/api/method/sk_app.api.replay_check, or bench execute sk_app.core.replay.run. Old replay rows are cleared first.
"""

import frappe
from frappe.utils import now_datetime

LOG = "SK Rule Log"
MODE = "Replay"
START = "2026-04-01"


def _log(module: str, rule: str, doctype: str, name: str, detail: str):
	frappe.get_doc({"doctype": LOG, "module": module, "rule": rule, "mode": MODE, "reference_doctype": doctype,
		"reference_name": name, "user": frappe.session.user, "detail": str(detail)[:1000]}).insert(ignore_permissions=True)


def _sales(since: str) -> dict:
	from sk_app import gates
	from sk_app.gate_rules import is_placeholder_po, words
	from sk_app.won_deals import deals_by_customer, refs

	out = {"po_placeholder": 0, "order_not_won": 0, "order_without_deal": 0, "lead_data": 0}
	won = set(frappe.get_all("CRM Deal Status", filters={"type": "Won"}, pluck="name") or ["Won"]) \
		if frappe.db.exists("DocType", "CRM Deal Status") else {"Won"}
	for name in frappe.get_all("Sales Order", filters={"docstatus": 1, "transaction_date": [">=", since]}, pluck="name", limit=0):
		so = frappe.get_doc("Sales Order", name)
		if is_placeholder_po(so.po_no) and not gates._has_file("Sales Order", so.name):
			out["po_placeholder"] += 1
			_log("Sales", "po_placeholder", "Sales Order", so.name, f"PO no '{so.po_no}' is not a customer PO number")
		if not frappe.db.exists("DocType", "CRM Deal"):
			continue
		found = refs(so)
		problem = None
		if not found:
			found, problem = deals_by_customer(so)
		if problem:
			out[problem[0] if problem[0] in out else "order_without_deal"] += 1
			_log("Sales", problem[0], "Sales Order", so.name, problem[1])
		for ref in found:
			deal = ref if ref.startswith("CRM-DEAL-") else frappe.db.get_value("CRM Deal", {"lead": ref})
			status = frappe.db.get_value("CRM Deal", deal, "status") if deal else None
			if status not in won:
				out["order_not_won"] += 1
				_log("Sales", "order_not_won", "Sales Order", so.name,
					f"Order submitted but {deal or ref} is {status or 'not a deal yet'}, not Won")
	# S4: orders that look unbilled while the customer has invoices made without the order (Tally invoices): the match
	# is only suggested here; Shraddha links them after SK's OK
	out["invoice_not_linked"] = 0
	for so in frappe.get_all("Sales Order", filters={"docstatus": 1, "per_billed": 0, "transaction_date": [">=", since]},
			fields=["name", "customer", "grand_total"], limit=0):
		free = frappe.db.sql("""select si.name, si.grand_total from `tabSales Invoice` si where si.docstatus = 1 and si.customer = %s
			and si.is_return = 0 and not exists (select 1 from `tabSales Invoice Item` i where i.parent = si.name and ifnull(i.sales_order, '') != '')
			order by abs(si.grand_total - %s) limit 3""", (so.customer, so.grand_total), as_dict=True)
		if free:
			out["invoice_not_linked"] += 1
			_log("Sales", "invoice_not_linked", "Sales Order", so.name, "0% billed; invoices of this customer made without the order: "
				+ ", ".join(f"{r.name} ({r.grand_total:,.0f})" for r in free))
	if frappe.db.exists("DocType", "CRM Lead"):
		for doctype in ("CRM Lead", "CRM Deal"):
			for name in frappe.get_all(doctype, filters={"modified": [">=", since]}, pluck="name", limit=0):
				doc = frappe.get_doc(doctype, name)
				missing = gates.status_missing(doctype, doc, doc.get("status"))
				if missing:
					out["lead_data"] += 1
					_log("Sales", "lead_data", doctype, name, f"{doc.get('status')}: missing " + words(missing).replace("\n", "; "))
	return out


def _finance(since: str) -> dict:
	from sk_app import doubles

	found = doubles.possible_doubles(since)
	out = {"possible_double": 0, "bank_in_cash": 0, "no_reference": 0, "kept_draft": 0}
	for p in found["pairs"]:
		a, b = p.get("first") or {}, p.get("second") or {}
		out["possible_double"] += 1
		_log("Finance", "possible_double", a.get("doctype") or "Payment Entry", a.get("name"),
			f"Possible double of {b.get('doctype') or ''} {b.get('name') or ''}: {p.get('why') or ''}")
	for r in found["bank_in_cash"]:
		out["bank_in_cash"] += 1
		_log("Finance", "bank_in_cash", "Payment Entry", r.name, f"{r.mode_of_payment or r.reference_no} booked through Cash")
	for r in frappe.get_all("Payment Entry", filters={"docstatus": 1, "posting_date": [">=", since], "reference_no": ["in", ["", None]]},
			fields=["name", "party", "paid_amount"], limit=0):
		out["no_reference"] += 1
		_log("Finance", "no_reference", "Payment Entry", r.name, f"{r.party} {r.paid_amount}: no UTR / reference")
	for doctype in ("Payment Entry", "Journal Entry", "Purchase Invoice", "Sales Invoice"):
		for r in frappe.get_all(doctype, filters={"docstatus": 0, "creation": [">=", since]}, fields=["name"], limit=0):
			reason = frappe.db.get_value("Comment", {"reference_doctype": doctype, "reference_name": r.name,
				"content": ["like", "Kept as draft by SK App%"]}, "content", order_by="creation desc")
			out["kept_draft"] += 1
			_log("Finance", "kept_draft", doctype, r.name, reason or "Draft not posted")
	return out


def run(since: str = START) -> dict:
	frappe.db.delete(LOG, {"mode": MODE})
	started = now_datetime()
	result = {"since": since, "Sales": _sales(since), "Finance": _finance(since)}
	result["total"] = sum(sum(v.values()) for k, v in result.items() if isinstance(v, dict))
	result["accuracy_check"] = "passed" if not result["total"] else "gaps listed in SK Rule Log (mode Replay)"
	result["seconds"] = (now_datetime() - started).seconds
	frappe.db.commit()
	return result


def run_and_tell(since: str = START, user: str | None = None) -> dict:
	result = run(since)
	if user:
		lines = [f"{m}: " + ", ".join(f"{k} {v}" for k, v in result[m].items()) for m in ("Sales", "Finance")]
		frappe.get_doc({"doctype": "Notification Log", "for_user": user, "type": "Alert", "subject":
			f"Replay check since {since}: {result['total']} gaps ({result['accuracy_check']})",
			"email_content": "<br>".join(lines) + "<br><a href='/app/sk-rule-log?mode=Replay'>SK Rule Log</a>"}).insert(ignore_permissions=True)
		frappe.db.commit()
	return result
