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
	for p in people.values():
		p["name"] = frappe.db.get_value(p["party_type"], p["party"], "employee_name" if p["party_type"] == "Employee" else "name") or p["party"]
	out = sorted(people.values(), key=lambda p: -abs(p["balance"]))
	return {"people": out, "untagged": untagged[::-1], "untagged_total": sum(u["amount"] for u in untagged),
		"total": sum(p["balance"] for p in out) + sum(u["amount"] for u in untagged), "accounts": accs}
