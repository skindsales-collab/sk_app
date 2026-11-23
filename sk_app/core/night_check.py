"""Nightly data check (SK 14-Nov "approve"): at night SK App tests all data since 1-Apr and writes every open item to
SK Rule Log (module "Night check"); at 7 AM each owner gets one mail (link, what is wrong, one action) and the same
list under "Data missing" on their Home; SK gets the summary (per person open / new / fixed, one line per module).

Reuses what exists: the double guard (doubles.possible_doubles), the mandatory-gate list (gates.pending), the flow
boxes' late rows (flows), payment linking (writers/payment_allocate) and the import check (core/imports).
Nothing salary-related is read. Mails go only to enabled app logins with a real e-mail."""

import frappe
from frappe import _
from frappe.utils import date_diff, get_url_to_form, getdate, nowdate

from sk_app.core import night_rules as R

LOG = "SK Rule Log"
ROWS_IN_MAIL = 60


# ---------- who owns what ----------

def _app_users() -> list[dict]:
	return frappe.get_all("SK App User", filters={"enabled": 1}, fields=["user", "full_name"], order_by="full_name asc")


def _function_owner(function: str | None) -> str:
	"""The first login with that function; Management (the CEO) when nobody has it."""
	from sk_app.core.people import ceo_users, users_with_function

	users = [u for u in (users_with_function(function) if function else []) if u != "Administrator"]
	return next(iter(users), None) or next(iter(u for u in ceo_users() if u != "Administrator"), "Administrator")


def _owner_or(user: str | None, function: str | None, logins: set) -> str:
	"""The record's own person when they have an app login; else the function's person. Never Administrator (nobody reads its mail)."""
	return user if user and user in logins and user != "Administrator" else _function_owner(function)


# ---------- the checks ----------

def _doubles(logins: set) -> list[dict]:
	from sk_app import doubles

	found = doubles.possible_doubles()
	out = []
	for p in found.get("pairs") or []:
		a, b = p["first"], p["second"]
		out.append(R.item("double", a["doctype"], a["name"], f"{a.get('party') or ''} ₹{float(a.get('total') or a.get('amount') or 0):,.0f} looks like "
			f"{b['doctype']} {b['name']} ({p['why']})", _function_owner("Accounts")))
	for d in found.get("deals") or []:
		owner = frappe.db.get_value("CRM Deal", d.names.split(",")[0], "deal_owner")
		out.append(R.item("two_deals", "CRM Lead", d.lead, f"deals {d.names}", _owner_or(owner, "Sales", logins)))
	for r in found.get("bank_in_cash") or []:
		out.append(R.item("bank_in_cash", "Payment Entry", r.name, f"{r.party or ''} ₹{float(r.amount or 0):,.0f} · {r.date}", _function_owner("Accounts")))
	return out


def _missing(logins: set) -> list[dict]:
	from sk_app import gates
	from sk_app.core.people import ceo_users

	ceo = next(iter(ceo_users()), "Administrator")
	out = []
	for g in gates.pending(ceo, rows=True)["groups"]:
		if g["key"] == "leads":
			for r in g["rows"]:
				owner = frappe.db.get_value("CRM Lead", r["name"], "lead_owner")
				out.append(R.item("missing", "CRM Lead", r["name"], f"{r['title']} · {r['meta']}", _owner_or(owner, "Sales", logins)))
		elif g["key"] == "requests":
			for r in g["rows"]:
				out.append(R.item("approval", "Material Request", r["name"], r["meta"], ceo))
	# customers billed since 1-Apr whose GST / address data is missing (the invoice cannot be right without it)
	for c in frappe.get_all("Sales Invoice", filters={"docstatus": 1, "posting_date": [">=", _since()]}, distinct=True, pluck="customer"):
		miss = gates.customer_missing(c)
		if miss:
			out.append(R.item("customer_gst", "Customer", c, ", ".join(t for _k, t in miss), _function_owner("Accounts")))
	from sk_app import won_deals

	for d in won_deals.won_without_order():  # SK 14-Nov KF-05180: Won = order exists
		out.append(R.item("won_no_order", "CRM Deal", d.name, f"{d.get('organization') or d.name} · Won since {str(d.modified)[:10]}",
			_owner_or(d.get("deal_owner"), "Sales", logins)))
	from sk_app.writers import app_user

	for p in app_user.missing():
		out.append(R.item("no_login", p["kind"], p["name"],  # kind is the doctype: Employee / Supplier
			f"{p['full_name']} · " + ("mobile known, login not made" if p["can_make"] else "no mobile number"), ceo))
	return out


def _late(users: list[dict]) -> list[dict]:
	"""Every red row of every person's flow boxes, the member before the manager (dedupe keeps the first owner)."""
	from sk_app import flows
	from sk_app.core.people import is_ceo
	from sk_app.logins import profile_functions

	out = []
	frappe.flags.sk_flow_all = True
	try:
		people = [(u["user"], profile_functions(u["user"]) or []) for u in users if not is_ceo(u["user"])]
		people.sort(key=lambda p: len(flows._owners(p[0]) or []))
		for user, functions in people:
			for f in flows.for_user(user, functions, flows.CUMULATIVE)["flows"]:
				for st in f["stages"]:
					for r in st["rows"]:
						if r.get("c") == "red" and r.get("doctype") and r.get("name"):
							out.append(R.item("late", r["doctype"], r["name"], f"{st['label']}: {r['title']} · {r.get('meta') or ''}", user,
								function=f["function"], days=r.get("days") or 0))
	finally:
		frappe.flags.sk_flow_all = False
	return out


def _drafts(logins: set) -> list[dict]:
	from sk_app.core.people import ceo_users

	ceos = [u for u in ceo_users() if u in logins]
	out = []
	for doctype, function in R.DRAFT_DOCTYPES.items():
		if not frappe.db.table_exists(doctype):
			continue
		title = next((f for f in ("customer_name", "supplier_name", "title") if frappe.get_meta(doctype).has_field(f)), "name")
		for d in frappe.get_all(doctype, filters={"docstatus": 0, "creation": [">=", _since()]}, fields=["name", "owner", "modified", "creation", title], limit=0):
			age = date_diff(nowdate(), getdate(d.modified))
			days = date_diff(nowdate(), getdate(d.creation))
			to_owner, to_ceo = R.draft_due(doctype, age if doctype not in R.DRAFT_WATCH else days)
			if not to_owner:
				continue
			owner = _owner_or(d.owner, function, logins)
			what = f"{d.get(title) or d.name} · draft since {str(d.creation)[:10]}"
			out.append(R.item("draft", doctype, d.name, what, owner, function=function, days=days))
			if to_ceo:  # SK 23-Nov: a quote / expense still a draft after 5 days also goes to SK
				for ceo in ceos:
					if ceo != owner:
						out.append(R.item("draft_late", doctype, d.name, f"{what} · owner {frappe.db.get_value('User', owner, 'full_name') or owner} · {days} days",
							ceo, function="Management", days=days))
	return out


def _unlinked_payments() -> list[dict]:
	acc = _function_owner("Accounts")
	return [R.item("unlinked_payment", "Payment Entry", p.name, f"{p.party_name or p.party} ₹{float(p.unallocated_amount):,.0f} not against any bill · {p.posting_date}",
		acc, days=date_diff(nowdate(), p.posting_date))
		for p in frappe.get_all("Payment Entry", filters={"docstatus": 1, "unallocated_amount": [">", 0.5], "posting_date": [">=", _since()]},
			fields=["name", "party", "party_name", "unallocated_amount", "posting_date"], order_by="posting_date asc", limit=0)]


def _import_gaps() -> list[dict]:
	from sk_app.core import imports

	if not frappe.db.table_exists("SK Import"):
		return []
	ceo = _function_owner("Management")
	out = []
	for name in frappe.get_all("SK Import", pluck="name"):
		doc = frappe.get_doc("SK Import", name)
		gap = imports._check_one(doc)
		if gap:
			out.append(R.item("import_gap", "SK Import", name, f"{doc.source}: {gap} rows missing", ceo))
	return out


def _hiring(logins: set) -> list[dict]:
	"""SK 17-Nov hiring: a new candidate untouched 24 h -> HR; a shortlisted one not seen by the CEO 48 h -> CEO."""
	if not frappe.db.exists("DocType", "Job Applicant"):
		return []
	from frappe.utils import add_to_date

	out = []
	hr = _function_owner("HR")
	for a in frappe.get_all("Job Applicant", filters={"status": ["in", ["Open", "Replied"]], "modified": ["<", add_to_date(nowdate(), hours=-24)]},
			fields=["name", "applicant_name", "job_title", "modified"], limit=0):
		out.append(R.item("applicant_untouched", "Job Applicant", a.name, f"{a.applicant_name} · {a.job_title or 'no job yet'}", hr, days=date_diff(nowdate(), a.modified)))
	ceo = _function_owner("Management")
	for a in frappe.get_all("Job Applicant", filters={"status": "Shortlisted", "sk_sk_seen_on": ["is", "not set"], "modified": ["<", add_to_date(nowdate(), hours=-48)]},
			fields=["name", "applicant_name", "job_title", "modified"], limit=0):
		out.append(R.item("shortlisted_waiting", "Job Applicant", a.name, f"{a.applicant_name} · {a.job_title or ''}", ceo, days=date_diff(nowdate(), a.modified)))
	return out


def _since():
	from erpnext.accounts.utils import get_fiscal_year

	return get_fiscal_year(nowdate())[1]


def _safe(fn, *args) -> list[dict]:
	try:
		return fn(*args) or []
	except Exception:
		frappe.log_error(f"SK night check {getattr(fn, '__name__', fn)}")
		return []


def collect() -> list[dict]:
	"""Every open item tonight, one owner each."""
	users = _app_users()
	logins = {u["user"] for u in users}
	items = _safe(_doubles, logins) + _safe(_missing, logins) + _safe(_late, users) + _safe(_drafts, logins) + _safe(_unlinked_payments) + _safe(_import_gaps) + _safe(_hiring, logins)
	return R.dedupe(items)


# ---------- the log: tonight's rows and last night's ----------

def _run_dates(n: int = 2) -> list:
	return [r[0] for r in frappe.db.sql("select date(creation) d from `tabSK Rule Log` where module=%s group by d order by d desc limit %s", (R.MODULE, n))]


def _rows_on(day) -> list[dict]:
	if not day:
		return []
	out = []
	for r in frappe.get_all(LOG, filters={"module": R.MODULE, "creation": ["between", [f"{day} 00:00:00", f"{day} 23:59:59"]]},
			fields=["rule", "reference_doctype", "reference_name", "user", "detail", "name"], limit=0):
		d = R.parse_detail(r.detail)
		out.append({"kind": r.rule, "doctype": r.reference_doctype or "", "name": r.reference_name or "", "user": r.user, "log": r.name, **d})
	return out


def nightly() -> dict:
	"""Scheduler, every night: write tonight's open items to SK Rule Log (the morning mail and the Home list read them)."""
	if not frappe.db.table_exists(LOG):
		return {}
	today = nowdate()
	frappe.db.delete(LOG, {"module": R.MODULE, "creation": [">=", f"{today} 00:00:00"]})  # a second run the same night replaces the first
	items = collect()
	for it in items:
		frappe.get_doc({"doctype": LOG, "module": R.MODULE, "rule": it["kind"], "mode": "Warn only", "reference_doctype": it["doctype"] or None,
			"reference_name": it["name"] if it["doctype"] and frappe.db.exists(it["doctype"], it["name"]) else None, "user": it["user"],
			"detail": R.detail_text(it)}).insert(ignore_permissions=True)
	frappe.db.commit()
	return {"date": today, "items": len(items), "people": len({i["user"] for i in items})}


def open_items(user: str | None = None) -> list[dict]:
	"""Last night's open items (for one person, or all) with link, what, action, days and new/old."""
	if not frappe.db.table_exists(LOG):
		return []
	dates = _run_dates(2)
	if not dates:
		return []
	now = _rows_on(dates[0])
	last = _rows_on(dates[1]) if len(dates) > 1 else []
	new, _fixed = R.diff(last, now)
	out = []
	for r in now:
		if user and r["user"] != user:
			continue
		r["new"] = R.key(r) in new
		r["link"] = get_url_to_form(r["doctype"], r["name"]) if r["doctype"] and r["name"] else "/app/sk-rule-log?module=Night%20check"
		out.append(r)
	return sorted(out, key=lambda i: (R.ORDER.index(i["kind"]) if i["kind"] in R.ORDER else 99, -i["days"]))


def home_rows(user: str) -> list[dict]:
	"""The Home "Data missing" group: one row per item in the app's row shape."""
	return [{"doctype": r["doctype"] or "SK Rule Log", "name": r["name"] or r["log"], "title": r["what"] or R.KINDS.get(r["kind"], ("", "", ""))[0],
		"meta": f"Do: {r['action']}" + (f" · {r['days']} days" if r["days"] else "") + (" · new" if r["new"] else "")} for r in open_items(user)]


# ---------- the 7 AM mails ----------

def _line(r: dict) -> str:
	return (f'<li><a href="{r["link"]}">{r["doctype"]} {r["name"]}</a> · {frappe.utils.escape_html(r["what"])} · <b>Do:</b> '
		f'{frappe.utils.escape_html(r["action"])}' + (f" · {r['days']} days" if r["days"] else "") + (" · <i>new</i>" if r.get("new") else "") + "</li>")


def person_html(rows: list[dict]) -> str:
	parts = ["<p>" + _("Your open data items from last night's SK App check. Open each link, do the one action, and it drops off tomorrow. "
		"The same list is under Data missing on your Home.") + "</p>"]
	for kind in R.ORDER:
		group = [r for r in rows if r["kind"] == kind]
		if group:
			parts.append(f"<p><b>{R.KINDS[kind][0]} ({len(group)})</b></p><ol>" + "".join(_line(r) for r in group[:ROWS_IN_MAIL]) +
				(f"<li>… {len(group) - ROWS_IN_MAIL} more on your Home</li>" if len(group) > ROWS_IN_MAIL else "") + "</ol>")
	return "".join(parts)


def summary_html(by_user: dict, new: set, fixed_by_user: dict, names: dict, all_rows: list[dict]) -> str:
	head = "<tr><th align=left>Person</th><th>Open</th><th>New</th><th>Fixed yesterday</th></tr>"
	people = sorted(set(by_user) | set(fixed_by_user), key=lambda u: -len(by_user.get(u, [])))
	rows = "".join("<tr><td>{0}</td><td align=center>{1}</td><td align=center>{2}</td><td align=center>{3}</td></tr>".format(
		names.get(u, u), *R.person_summary(by_user.get(u, []), new, fixed_by_user.get(u, 0)).values()) for u in people)
	modules = "".join(f"<li>{fn}: {o} open" + (f", {l} late" if l else "") + "</li>" for fn, o, l in R.module_lines(all_rows))
	return (f"<p>SK App night check of {nowdate()}: {len(all_rows)} open items with {len(people)} people"
		f"{' (all clear)' if not all_rows else ''}. Each person got their own list with links.</p>"
		f"<table border=1 cellpadding=4 style='border-collapse:collapse'>{head}{rows}</table><p><b>By module</b></p><ul>{modules}</ul>"
		"<p><a href='/app/sk-rule-log?module=Night%20check'>All rows in SK Rule Log</a></p>")


def _mail(users: list[str], subject: str, html: str) -> int:
	from sk_app.mailbox import _notify
	from sk_app.otp import _sender, has_real_email

	users = [u for u in set(users) if u not in ("Administrator", "Guest")]
	_notify(users, subject)
	emails = [e for e in (frappe.db.get_value("User", u, "email") for u in users) if has_real_email(e)]
	if emails:
		frappe.sendmail(recipients=emails, sender=_sender(), subject=subject, message=html, now=False)
	return len(emails)


def _has_routes() -> bool:
	return frappe.get_meta("SK App Settings").has_field("alert_routes")


def _segment(item: dict) -> str | None:
	"""Cabin / Non-Cabin of the item's record (sales items only need it)."""
	dt, name = item.get("doctype"), item.get("name")
	if not dt or not name or not frappe.db.exists(dt, name):
		return None
	meta = frappe.get_meta(dt)
	if meta.has_field("sk_main_segment"):
		return frappe.db.get_value(dt, name, "sk_main_segment")
	if meta.has_field("customer_group"):
		group = frappe.db.get_value(dt, name, "customer_group") or ""
		return "Non-Cabin" if "non" in group.lower() else ("Cabin" if group else None)
	return None


def _mail_to(emails: list[str], subject: str, html: str) -> int:
	"""Mail to addresses from the settings (a person or a team box); app logins with that address also get the bell."""
	from sk_app.mailbox import _notify
	from sk_app.otp import _sender

	emails = sorted({e.strip() for e in emails or [] if "@" in e})
	if not emails:
		return 0
	users = frappe.get_all("User", filters={"email": ["in", emails], "enabled": 1}, pluck="name")
	if users:
		_notify(users, subject)
	frappe.sendmail(recipients=emails, sender=_sender(), subject=subject, message=html, now=False)
	return len(emails)


AREA_TITLE = {"accounts": "Accounts", "cabin_sales": "Cabin sales", "machine_shifting": "Machine shifting / Non-Cabin",
	"purchase": "Purchase", "stores": "Stores", "production": "Production", "hr": "HR"}


def area_html(items: list[dict], names: dict) -> str:
	"""All open items of one area, person by person (the team box sees its whole team's list)."""
	parts = []
	for user in sorted({i["user"] for i in items}, key=lambda u: -sum(1 for i in items if i["user"] == u)):
		mine = [i for i in items if i["user"] == user]
		parts.append(f"<p><b>{frappe.utils.escape_html(names.get(user, user))} ({len(mine)})</b></p><ol>"
			+ "".join(_line(r) for r in mine[:ROWS_IN_MAIL]) + (f"<li>… {len(mine) - ROWS_IN_MAIL} more on their Home</li>" if len(mine) > ROWS_IN_MAIL else "") + "</ol>")
	return "".join(parts)


def morning() -> dict:
	"""Scheduler, 7 AM. SK 23-Nov: ONE mail per inbox per day with the full summary: a person's own items, the team box's
	whole area (all its people's items), the possible doubles for Accounts and the CEO's count summary are joined into
	one mail when they go to the same address. Nothing open, only the summary says 'all clear'."""
	from sk_app.core.people import ceo_users
	from sk_app.otp import _sender, has_real_email

	dates = _run_dates(2)
	if not dates or str(dates[0]) < str(getdate(frappe.utils.add_days(nowdate(), -1))):
		return {"skipped": "no check last night"}
	rows = open_items()
	last = _rows_on(dates[1]) if len(dates) > 1 else []
	new, fixed = R.diff(last, rows)
	fixed_by_user: dict = {}
	for r in last:
		if R.key(r) in fixed:
			fixed_by_user[r["user"]] = fixed_by_user.get(r["user"], 0) + 1
	logins = {u["user"] for u in _app_users()}
	names = {u["user"]: u["full_name"] for u in _app_users()}
	by = R.by_user([r for r in rows if r["user"] in logins])
	ceos = list(ceo_users())
	routes = R.parse_routes(frappe.db.get_single_value("SK App Settings", "alert_routes") if _has_routes() else "")
	mails: dict = {}  # address -> {"sections": [(title, html)], "count": n, "users": set()}

	def add(emails, title, html, count, user=None):
		for e in {x.strip().lower() for x in emails or [] if x and "@" in x}:
			m = mails.setdefault(e, {"sections": [], "count": 0, "users": set()})
			m["sections"].append((title, html))
			m["count"] += count
			if user:
				m["users"].add(user)

	# 1. each person's own items (the CEO's own items only when no team box takes them)
	area_of = {}
	for i in rows:
		area_of[R.key(i)] = R.area_of(i.get("function"), _segment(i)) if routes else None
	for user, items in by.items():
		if user in ceos and routes:
			items = [i for i in items if not (area_of.get(R.key(i)) and routes.get(area_of[R.key(i)]))]
		if not items:
			continue
		email = frappe.db.get_value("User", user, "email")
		if has_real_email(email):
			add([email], _("Your open items ({0})").format(len(items)), person_html(items), len(items), user)
	# 2. each team box: all open items of its area
	for area, emails in routes.items():
		if area == "summary":
			continue
		items = [i for i in rows if area_of.get(R.key(i)) == area]
		if items:
			add(emails, _("{0}: all open items ({1})").format(_(AREA_TITLE.get(area, area)), len(items)), area_html(items, names), len(items))
	# 3. possible doubles (Accounts)
	try:
		from sk_app import doubles

		found = doubles.possible_doubles()
		dcount = sum(len(found.get(k) or []) for k in ("pairs", "deals", "bank_in_cash", "masters", "master_problems", "auto_ticked"))
		if dcount:
			to = routes.get("accounts") or [frappe.db.get_value("User", u, "email") for u in doubles._recipients()]
			add(to, _("Possible double / wrong entries ({0})").format(dcount), doubles.report_html(found), dcount)
	except Exception:
		frappe.log_error("SK App morning mail: doubles section")
	# 4. the CEO's count summary
	summary_to = routes.get("summary") or [frappe.db.get_value("User", u, "email") for u in ceos]
	add(summary_to, _("Summary: {0} open items, {1} people").format(len(rows), len(by)), summary_html(by, new, fixed_by_user, names, rows), 0)
	from sk_app.mailbox import _notify

	sent = 0
	for email, m in mails.items():
		subject = _("SK App morning check: {0} items to act on").format(m["count"]) if m["count"] else R.subject(0, 0)
		body = "".join(f"<h3 style='color:#2A6EB4'>{t}</h3>{h}" for t, h in m["sections"])
		users = list(m["users"]) or frappe.get_all("User", filters={"email": email, "enabled": 1}, pluck="name")
		if users:
			_notify(users, subject)
		frappe.sendmail(recipients=[email], sender=_sender(), subject=subject, message=body, now=False)
		sent += 1
	return {"people": len(by), "open": len(rows), "new": len(new), "fixed": len(fixed), "mails": sent, "inboxes": sorted(mails)}
