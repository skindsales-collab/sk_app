"""One-time (SK 7-Nov): the 9 "possible double" pairs in the 7-Nov mail were all two real entries with their own Tally
voucher numbers (PAY/526 vs PAY/527, J329 vs J330, bill 305 vs 306). The guard now skips such pairs; this ticks
"Not a double (checked)" on those records so the decision is on the record too. Submitted documents: set_value only.
Checker 7-Nov: only pairs whose two numbers are of the same kind (two Tally numbers, two bill numbers) are ticked; a pair
with a bank number (Oxford PE-00012 / PE-00206, Babasaheb JE-01769 / PE-00202) stays in the morning list."""

import frappe

from sk_app.double_rules import find_pairs
from sk_app.doubles import OK_FIELD, _money_rows


PATCH_RULE = "double pair ticked by patch"


def execute():
	since = "2026-04-01"
	rows = _money_rows(since)
	with_refs = {(p["first"]["doctype"], p["first"]["name"], p["second"]["doctype"], p["second"]["name"]) for p in find_pairs(rows)}
	blind = find_pairs([{**r, "ref": None} for r in rows])  # the guard before this change
	by_name = {(r["doctype"], r["name"]): r for r in rows}
	ticked = 0
	for p in blind:
		key = (p["first"]["doctype"], p["first"]["name"], p["second"]["doctype"], p["second"]["name"])
		if key in with_refs:
			continue
		a, b = by_name.get(key[:2], {}), by_name.get(key[2:], {})
		why = "Not a double: {0} {1} ({2}) and {3} {4} ({5}) have their own numbers of the same kind, Rs {6:,.0f}".format(
			key[0], key[1], a.get("ref") or "", key[2], key[3], b.get("ref") or "", float(a.get("amount") or 0))
		for r in (p["first"], p["second"]):
			if frappe.get_meta(r["doctype"]).has_field(OK_FIELD) and not frappe.db.get_value(r["doctype"], r["name"], OK_FIELD):
				frappe.db.set_value(r["doctype"], r["name"], OK_FIELD, 1, update_modified=False)
				# checker 7-Nov: every tick is reported, on the record and in SK Rule Log (listed in the next morning mail)
				frappe.get_doc(r["doctype"], r["name"]).add_comment("Comment", "Ticked 'Not a double (checked)' by SK App patch 7-Nov. " + why)
				frappe.get_doc({"doctype": "SK Rule Log", "module": "Finance", "rule": PATCH_RULE, "mode": "Patch",
					"reference_doctype": r["doctype"], "reference_name": r["name"], "detail": why}).insert(ignore_permissions=True)
				ticked += 1
	if ticked:
		frappe.db.commit()
	print(f"tick_pairs_with_own_voucher_numbers: {ticked} records ticked (SK Rule Log rule '{PATCH_RULE}')")
