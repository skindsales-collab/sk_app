"""SK 26-Nov (approved): staff advances, one balance per person. Read only; for SK (Management) and Accounts.
Advances paid and recovered are the GL rows of the "Staff and Labour Advances" / "Employee Advances" accounts. A row
tagged with the employee (party) counts on that person; a row without a party is listed as "not tagged yet" with its
remark, so Accounts can tag it. No salary is read or shown."""

import frappe
from frappe.utils import flt

WORDS = ("staff and labour advance", "employee advance")


def accounts() -> list[str]:
	return [a.name for a in frappe.get_all("Account", filters={"is_group": 0}, fields=["name", "account_name"])
		if any(w in (a.account_name or "").lower() for w in WORDS)]


def summary(user: str) -> dict:
	from sk_app.store import need

	need(user, "Management", "Accounts")
	accs = accounts()
	rows = frappe.get_all("GL Entry", filters={"account": ["in", accs or ["-"]], "is_cancelled": 0},
		fields=["posting_date", "voucher_type", "voucher_no", "party_type", "party", "debit", "credit", "remarks", "company"],
		order_by="posting_date asc", limit=0)
	people, untagged = {}, []
	for r in rows:
		amount = flt(r.debit) - flt(r.credit)
		if r.party:
			p = people.setdefault((r.party_type, r.party), {"party_type": r.party_type, "party": r.party, "balance": 0.0, "entries": 0, "last": None})
			p["balance"] += amount
			p["entries"] += 1
			p["last"] = str(r.posting_date)
		else:
			untagged.append({"date": str(r.posting_date), "voucher": r.voucher_no, "doctype": r.voucher_type, "amount": amount,
				"remark": (r.remarks or "")[:160], "company": r.company})
	# SK 26-Nov: what each person spent against the advance = their expense claims (Leave & Expense → Expense, approved by SK)
	if frappe.db.exists("DocType", "Expense Claim"):
		for c in frappe.get_all("Expense Claim", filters={"docstatus": ["<", 2], "approval_status": ["!=", "Rejected"]},
				fields=["employee", "approval_status", "docstatus", "total_claimed_amount", "total_sanctioned_amount"], limit=0):
			p = people.setdefault(("Employee", c.employee), {"party_type": "Employee", "party": c.employee, "balance": 0.0, "entries": 0, "last": None})
			if c.approval_status == "Approved" and c.docstatus == 1:
				p["claimed"] = p.get("claimed", 0.0) + flt(c.total_sanctioned_amount or c.total_claimed_amount)
			else:
				p["waiting"] = p.get("waiting", 0.0) + flt(c.total_claimed_amount)
	for p in people.values():
		p["name"] = frappe.db.get_value(p["party_type"], p["party"], "employee_name" if p["party_type"] == "Employee" else "name") or p["party"]
		p["claimed"], p["waiting"] = round(p.get("claimed", 0.0), 2), round(p.get("waiting", 0.0), 2)
		p["left"] = round(p["balance"] - p["claimed"], 2)  # advance still with the person after the approved bills
	out = sorted(people.values(), key=lambda p: -abs(p["left"]))
	return {"people": out, "untagged": untagged[::-1], "untagged_total": sum(u["amount"] for u in untagged),
		"total": sum(p["balance"] for p in out) + sum(u["amount"] for u in untagged), "accounts": accs}
