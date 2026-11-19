"""Pure rules of the nightly data check (SK 14-Nov "approve": SK App tests all data every night and sends each person
their open items with a link, what is wrong and one action; SK gets the summary).

No frappe here: the check module (core/night_check.py) reads ERPNext and hands plain dicts to these rules, so the
rules are tested without a site. Nothing salary-related is ever checked (SK's limit 8)."""

MODULE = "Night check"  # the SK Rule Log module every night's rows are written under

# kind -> (words for the mail heading, the one action the owner takes, function that owns it unless the record says otherwise)
KINDS = {
	"double": ("Possible double entry", "Cancel the wrong one, or tick 'Not a double (checked)' if both are right", "Accounts"),
	"two_deals": ("Lead with more than one deal", "Keep one deal, mark the other Lost or delete the draft", "Sales"),
	"bank_in_cash": ("Bank payment booked through Cash", "Cancel, amend and choose the bank account", "Accounts"),
	"missing": ("Data missing", "Fill the missing data", "Sales"),
	"customer_gst": ("Customer billed without GST / address data", "Fill GSTIN (or tick unregistered) and the billing address", "Accounts"),
	"no_login": ("Person without an app login", "Make the login (People) or set the mobile number", "Management"),
	"late": ("Late item", "Update it, or close it if it is over", None),
	"draft": ("Draft not submitted", "Check and Submit it, or delete it if it is wrong", None),
	"unlinked_payment": ("Payment not linked to a bill", "Link the payment to its bill(s)", "Accounts"),
	"import_gap": ("Import gap (source rows not in ERPNext)", "Load the missing rows or correct the SK Import count", "Management"),
	"approval": ("Purchase request waiting for CEO", "Approve or reject it", "Management"),
	"won_no_order": ("Deal Won without a Sales Order", "Make the Sales Order from the deal, or move the deal back to Negotiations", "Sales"),
	"applicant_untouched": ("Candidate not touched for 24 hours", "Open the candidate: read the resume, book Round 1 or put on Hold", "HR"),
	"shortlisted_waiting": ("Shortlisted candidate not seen by the CEO for 48 hours", "Open the Round 2 list and book the candidate or decide", "Management"),
}
ORDER = list(KINDS)

# drafts a person must submit or delete (never Salary Slip / Payroll Entry; Job Cards stay open by design)
DRAFT_DOCTYPES = {
	"Quotation": "Sales", "Sales Order": "Sales", "Sales Invoice": "Accounts", "Payment Entry": "Accounts", "Journal Entry": "Accounts",
	"Purchase Invoice": "Accounts", "Purchase Order": "Purchase", "Material Request": "Stores", "Stock Entry": "Stores", "Purchase Receipt": "Stores",
}
DRAFT_GRACE_DAYS = 1  # a draft made or edited today is still being worked on


def item(kind: str, doctype: str, name: str, what: str, user: str, function: str | None = None, days: int = 0, action: str | None = None) -> dict:
	"""One open item. user = who must act (an app login); function = the module the item belongs to."""
	words, do, fn = KINDS[kind]
	return {"kind": kind, "doctype": doctype, "name": str(name), "what": (what or words)[:300], "action": action or do,
		"user": user, "function": function or fn or "", "days": int(days or 0)}


def key(it: dict) -> tuple:
	return (it["kind"], it["doctype"], it["name"])


def dedupe(items: list[dict]) -> list[dict]:
	"""The same record found through two people (a manager and a member) is one item, owned by the first found."""
	seen, out = set(), []
	for it in items:
		k = key(it)
		if k in seen:
			continue
		seen.add(k)
		out.append(it)
	return out


def diff(last: list[dict], now: list[dict]) -> tuple[set, set]:
	"""(new keys = found tonight and not last night, fixed keys = found last night and gone tonight)."""
	a, b = {key(i) for i in last}, {key(i) for i in now}
	return b - a, a - b


def by_user(items: list[dict]) -> dict[str, list[dict]]:
	out: dict[str, list[dict]] = {}
	for it in sorted(items, key=lambda i: (ORDER.index(i["kind"]), -i["days"], i["doctype"], i["name"])):
		out.setdefault(it["user"], []).append(it)
	return out


def detail_text(it: dict) -> str:
	"""The Rule Log 'detail' line: function · what · Do: action · N days (read back by parse_detail)."""
	parts = [it["function"] or "-", it["what"], f"Do: {it['action']}"]
	if it["days"]:
		parts.append(f"{it['days']} days")
	return " · ".join(parts)[:1000]


def parse_detail(detail: str) -> dict:
	parts = [p.strip() for p in (detail or "").split(" · ")]
	fn = parts[0] if parts and parts[0] != "-" else ""
	what = parts[1] if len(parts) > 1 else ""
	action = next((p[4:] for p in parts if p.startswith("Do: ")), "")
	days = next((int(p.split()[0]) for p in parts if p.endswith(" days") and p.split()[0].isdigit()), 0)
	return {"function": fn, "what": what, "action": action, "days": days}


def draft_is_stale(modified_days_ago: int) -> bool:
	return modified_days_ago > DRAFT_GRACE_DAYS


def person_summary(items: list[dict], new: set, fixed_count: int) -> dict:
	return {"open": len(items), "new": sum(1 for i in items if key(i) in new), "fixed": fixed_count}


def module_lines(items: list[dict]) -> list[tuple[str, int, int]]:
	"""(function, open, late-kind count) one line per module, biggest first; the CEO's one-line-per-module view."""
	tot: dict[str, list[int]] = {}
	for it in items:
		t = tot.setdefault(it["function"] or "Other", [0, 0])
		t[0] += 1
		t[1] += 1 if it["kind"] == "late" else 0
	return sorted(((fn, o, l) for fn, (o, l) in tot.items()), key=lambda r: (-r[1], r[0]))


def subject(count: int, new: int) -> str:
	if not count:
		return "SK App night check: all clear"
	return f"SK App night check: {count} item{'s' if count != 1 else ''} to fix" + (f" ({new} new)" if new else "")
