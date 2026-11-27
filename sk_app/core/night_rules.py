"""Pure rules of the nightly data check (SK 14-Nov "approve": SK App tests all data every night and sends each person
their open items with a link, what is wrong and one action; SK gets the summary).

No frappe here: the check module (core/night_check.py) reads ERPNext and hands plain dicts to these rules, so the
rules are tested without a site. Nothing salary-related is ever checked (SK's limit 8)."""

import re
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
	"email_typo": ("Login e-mail with a mistyped domain", "Correct the e-mail in the User record (e.g. @skind.tech, @gmail.com)", "Management"),
	"service_sac": ("Service item with a goods HSN instead of a SAC", "Set the SAC (manpower 998519, shifting / installation 998719, transport 996511; CA confirms)", "Accounts"),
	"po_placeholder": ("Sales Order without the customer's real PO number", "Type the real PO number and PO date, or attach the PO copy", "Sales"),
	"draft_late": ("Quote / expense still a draft after 5 days", "Ask the owner to submit it or delete it", "Management"),
	"unlinked_payment": ("Payment not linked to a bill", "Link the payment to its bill(s)", "Accounts"),
	"import_gap": ("Import gap (source rows not in ERPNext)", "Load the missing rows or correct the SK Import count", "Management"),
	"approval": ("Purchase request waiting for CEO", "Approve or reject it", "Management"),
	"quote_not_in_erp": ("Quote not in ERPNext (design's PDF only)", "Fill the missing customer details on the deal, then Make quotation in the app", "Sales"),
	"won_no_order": ("Deal Won without a Sales Order", "Make the Sales Order from the deal, or move the deal back to Negotiations", "Sales"),
	"applicant_untouched": ("Candidate not touched for 24 hours", "Open the candidate: read the resume, book Round 1 or put on Hold", "HR"),
	"shortlisted_waiting": ("Shortlisted candidate not seen by the CEO for 48 hours", "Open the Round 2 list and book the candidate or decide", "Management"),
}
ORDER = list(KINDS)

# drafts a person must submit or delete (never Salary Slip / Payroll Entry; Job Cards stay open by design)
DRAFT_DOCTYPES = {
	"Quotation": "Sales", "Sales Order": "Sales", "Sales Invoice": "Accounts", "Payment Entry": "Accounts", "Journal Entry": "Accounts",
	"Purchase Invoice": "Accounts", "Purchase Order": "Purchase", "Material Request": "Stores", "Stock Entry": "Stores", "Purchase Receipt": "Stores",
	"Expense Claim": "Accounts", "Delivery Note": "Stores", "Work Order": "Production",  # SK 27-Nov gate: every step's draft
}
DRAFT_GRACE_DAYS = 1  # a draft made or edited today is still being worked on
# SK 23-Nov (approved): quotes and expenses left as drafts: on the owner's list after 2 days, also on SK's list after 5
DRAFT_WATCH = {"Quotation": "Sales", "Expense Claim": "Accounts", "Purchase Invoice": "Accounts"}
DRAFT_OWNER_DAYS, DRAFT_CEO_DAYS = 2, 5
# SK 23-Nov checker: a purchase bill waits 3 days (the supplier's copy, the GRN), then goes on the owner's list; never to SK
OWNER_DAYS = {"Purchase Invoice": 3}
TO_CEO = {"Quotation", "Expense Claim"}


def draft_due(doctype: str, days_old: int) -> tuple[bool, bool]:
	"""(on the owner's list, also on the CEO's list) for a draft this many days old."""
	if doctype in DRAFT_WATCH:
		return days_old > OWNER_DAYS.get(doctype, DRAFT_OWNER_DAYS), doctype in TO_CEO and days_old > DRAFT_CEO_DAYS
	return days_old > DRAFT_GRACE_DAYS, False


SAC = re.compile(r"^99\d{4}(00)?$")  # 6-digit SAC (some masters carry it padded to 8 with 00)


TYPO_DOMAINS = ("gmial.", "gamil.", "gmal.", "gmail.co$", "gmai.com", "yaho.", "hotmial.", "rediff.co$")


def _distance(a: str, b: str) -> int:
	prev = list(range(len(b) + 1))
	for i, ca in enumerate(a, 1):
		cur = [i]
		for j, cb in enumerate(b, 1):
			cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
		prev = cur
	return prev[-1]


def email_typo(email: str | None) -> bool:
	"""SK 23-Nov checker: a login's e-mail with a mistyped domain (skind.tech misspelt, gmial.com ...) gets no mail."""
	e = (email or "").strip().lower()
	if "@" not in e:
		return False
	dom = e.split("@", 1)[1]
	if dom.endswith(".local") or dom == "skind.tech":
		return False
	if "skind" in dom or _distance(dom, "skind.tech") <= 2:  # skinf.tech, skind.tec, skindtech.com ...
		return True
	return any(re.search(t.replace(".", r"\.") if not t.endswith("$") else t.replace(".", r"\."), dom) for t in TYPO_DOMAINS)


def bad_sac(hsn: str | None) -> bool:
	"""A service item whose code is not a service (SAC 99xxxx), e.g. the cabin goods code 940600 on manpower."""
	return not SAC.match(str(hsn or "").strip())


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


# SK 21-Nov: alert mails go to the person / team box concerned, read from SK App Settings "alert_routes" (no address in code)
AREA_OF_FUNCTION = {"Accounts": "accounts", "Finance": "accounts", "Purchase": "purchase", "Stores": "stores", "Store": "stores",
	"Production": "production", "HR": "hr", "Machine Shifting": "machine_shifting"}
SALES_FUNCTIONS = ("Sales", "Marketing")


def parse_routes(text: str | None) -> dict:
	"""'accounts: acc@x.com, other@x.com' lines -> {'accounts': ['acc@x.com', 'other@x.com']}; blank / bad lines skipped."""
	out = {}
	for line in (text or "").splitlines():
		area, sep, who = line.partition(":")
		emails = [w.strip() for w in who.replace(";", ",").split(",") if "@" in w]
		if sep and area.strip() and emails:
			out[area.strip().lower().replace(" ", "_")] = emails
	return out


# SK 21-Nov: the default routes (SK named prod@skind.tech for purchase drafts and store items); a line already set is kept
DEFAULT_ROUTES = (("accounts", "acc@skind.tech"), ("cabin_sales", "cabin@skind.tech"), ("machine_shifting", "service@skind.tech"),
	("purchase", "prod@skind.tech"), ("stores", "prod@skind.tech"))


def with_default_routes(text: str | None) -> str:
	"""Adds the default line for every area that has none; never changes a line SK set."""
	have = parse_routes(text)
	lines = [ln for ln in (text or "").splitlines() if ln.strip()]
	lines += [f"{area}: {email}" for area, email in DEFAULT_ROUTES if area not in have]
	return "\n".join(lines)


def area_of(function: str | None, segment: str | None = None) -> str | None:
	"""Which alert area an item belongs to: sales by the record's segment (Non-Cabin = machine shifting / job work)."""
	if function in SALES_FUNCTIONS:
		return "machine_shifting" if (segment or "").lower().startswith("non") else "cabin_sales"
	return AREA_OF_FUNCTION.get(function or "")

