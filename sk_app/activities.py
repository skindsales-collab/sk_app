"""Sales daily activity counters (SK 27-Oct-2026, improvement list point 11, from SK's sheet) and the phone call list
upload (point 4: "phone not connected with app", calls were not captured).

Each activity is a counter with a daily target on the Day Report / My Day. Where ERPNext already has the facts the
count is read from it (calls logged against leads in each step, quotations made, revised quotations); the rest is one
tap (+1) by the salesperson. Targets are proposals until SK sets his own (site config "sk_activity_targets").

A browser cannot read the phone's call list, so (free) the salesperson exports the call history from the phone as a
CSV / Excel once a day and uploads it: every call to or from a lead's or deal's number becomes a CRM Call Log on it.
At 12 noon a salesperson with 0 calls logged gets a red reminder.
"""

import csv
import io
import re

import frappe
from frappe import _
from frappe.utils import add_to_date, cint, get_datetime, getdate, now_datetime, nowdate

from sk_app import crm, lead_status

# (key, English, Marathi, proposed daily target)
ACTIVITIES = [
	("raw_calls", "Raw leads calling", "नवीन लीडना कॉल", 20),
	("cold_calls", "Cold calls from marketing list", "मार्केटिंग यादीतून कोल्ड कॉल", 20),
	("mql", "MQLs (marketing qualified leads)", "MQL (पात्र लीड)", 3),
	("visits", "Physical visits done", "प्रत्यक्ष भेटी", 1),
	("new_company", "New companies searched", "नवीन कंपन्या शोधल्या", 5),
	("qualified_followup", "Qualified lead follow-up calls", "पात्र लीड फॉलो-अप कॉल", 10),
	("quote_followup", "Quotation follow-up calls", "कोटेशन फॉलो-अप कॉल", 5),
	("quotes_sent", "Quotations sent", "कोटेशन पाठवली", 2),
	("revised_quotes", "Revised quotations", "सुधारित कोटेशन", 1),
	("drawings", "Drawings done", "ड्रॉइंग केली", 1),
	("gmb", "Google My Business posts", "Google My Business पोस्ट", 1),
]
# calls logged in the app / uploaded against a lead in this step count for the activity
CALL_STEPS = {"raw_calls": ("New",), "qualified_followup": ("Qualified", "Drawing"), "quote_followup": ("Quotation", "Negotiations")}
NOON_MARK = "[No calls by noon]"


def targets() -> dict:
	own = frappe.conf.get("sk_activity_targets") or {}
	return {k: cint(own.get(k, t)) for k, _en, _mr, t in ACTIVITIES}


def _calls_by_step(user: str, day) -> dict:
	"""Calls by the lead's step; calls on cold-calling leads (sk_app.cold_leads) count as cold calls (SK 27-Oct)."""
	from sk_app import cold_leads

	out = {k: 0 for k in (*CALL_STEPS, "cold_calls")}
	if not crm.installed():
		return out
	cold_sources = cold_leads.sources()
	rows = frappe.get_all("CRM Call Log", filters={"creation": ["between", [f"{day} 00:00:00", f"{day} 23:59:59"]]},
		or_filters={"caller": user, "receiver": user}, fields=["reference_doctype", "reference_docname"], limit=0)
	for r in rows:
		if not r.reference_docname:
			continue
		doc = frappe.db.get_value(r.reference_doctype, r.reference_docname, ["status", "source"], as_dict=True) or {} \
			if r.reference_doctype in crm.CRM_DOCTYPES else {}
		status = doc.get("status")
		if r.reference_doctype == "CRM Lead" and cold_leads.is_cold(doc.get("source"), status, cold_sources):
			out["cold_calls"] += 1
			continue
		step = lead_status.step_of(status, deal=r.reference_doctype == "CRM Deal")
		for k, steps in CALL_STEPS.items():
			if step in steps:
				out[k] += 1
	return out


def _auto(user: str, day) -> dict:
	"""The counts ERPNext already has."""
	out = _calls_by_step(user, day)
	span = ["between", [f"{day} 00:00:00", f"{day} 23:59:59"]]
	out["quotes_sent"] = frappe.db.count("Quotation", {"owner": user, "creation": span, "docstatus": ["<", 2], "amended_from": ["is", "not set"]})
	out["revised_quotes"] = frappe.db.count("Quotation", {"owner": user, "creation": span, "docstatus": ["<", 2], "amended_from": ["is", "set"]})
	return out


def today(user: str, day=None) -> dict:
	day = getdate(day or nowdate())
	auto = _auto(user, day)
	manual = {r.activity: cint(r.qty) for r in frappe.get_all("SK Activity Count", filters={"user": user, "date": day},
		fields=["activity", "qty"])}
	tg = targets()
	rows = []
	for k, en, mr, _t in ACTIVITIES:
		done = auto.get(k, 0) + manual.get(k, 0)
		rows.append({"key": k, "label": en, "label_mr": mr, "target": tg[k], "done": done, "auto": auto.get(k, 0),
			"tap": manual.get(k, 0), "c": "green" if done >= tg[k] else "amber" if done else "red"})
	hit = sum(1 for r in rows if r["done"] >= r["target"])
	return {"date": str(day), "rows": rows, "hit": hit, "total": len(rows)}


def tap(user: str, key: str, step: int = 1, day=None) -> dict:
	if key not in targets():
		frappe.throw(_("Unknown activity"))
	day = getdate(day or nowdate())
	name = frappe.db.get_value("SK Activity Count", {"user": user, "date": day, "activity": key})
	if name:
		qty = max(0, cint(frappe.db.get_value("SK Activity Count", name, "qty")) + cint(step))
		frappe.db.set_value("SK Activity Count", name, "qty", qty)
	elif cint(step) > 0:
		frappe.get_doc({"doctype": "SK Activity Count", "user": user, "date": day, "activity": key, "qty": cint(step)}).insert(ignore_permissions=True)
	return today(user, day)


def team_today(users: list[str], day=None) -> dict:
	return {u: today(u, day) for u in users}


# ---------- the phone's call list (point 4) ----------

def _digits(v) -> str:
	d = re.sub(r"\D", "", str(v or ""))
	return d[-10:] if len(d) >= 10 else ""


def _rows(content: bytes, filename: str) -> list[dict]:
	if filename.lower().endswith((".xlsx", ".xls")):
		from frappe.utils.xlsxutils import read_xlsx_file_from_attached_file

		table = read_xlsx_file_from_attached_file(fcontent=content)
	else:
		text = content.decode("utf-8-sig", errors="replace")
		table = list(csv.reader(io.StringIO(text)))
	if not table:
		return []
	head = [str(h or "").strip().lower() for h in table[0]]

	def col(*words):
		return next((i for i, h in enumerate(head) if any(w in h for w in words)), None)
	num, when, dur, typ = col("number", "phone", "mobile"), col("date", "time"), col("duration", "seconds"), col("type", "direction")
	if num is None or when is None:
		frappe.throw(_("The file needs a phone number column and a date / time column"))
	out = []
	for r in table[1:]:
		if len(r) <= max(num, when):
			continue
		out.append({"number": _digits(r[num]), "when": r[when], "duration": r[dur] if dur is not None and dur < len(r) else 0,
			"type": str(r[typ]).lower() if typ is not None and typ < len(r) else "outgoing"})
	return out


def _seconds(v) -> int:
	s = str(v or "").strip()
	if re.match(r"^\d+:\d{1,2}(:\d{1,2})?$", s):
		parts = [int(x) for x in s.split(":")]
		return parts[0] * 3600 + parts[1] * 60 + parts[2] if len(parts) == 3 else parts[0] * 60 + parts[1]
	m = re.findall(r"(\d+)\s*(h|m|s)", s.lower())
	if m:
		return sum(int(n) * {"h": 3600, "m": 60, "s": 1}[u] for n, u in m)
	return cint(float(s)) if re.match(r"^\d+(\.\d+)?$", s) else 0


def upload_calls(user: str, file_url: str) -> dict:
	"""Every call in the phone's exported call list to or from a lead / deal number becomes a CRM Call Log on it."""
	if not crm.installed():
		frappe.throw(_("Frappe CRM is not installed"))
	f = frappe.get_doc("File", {"file_url": file_url})
	rows = _rows(f.get_content() if isinstance(f.get_content(), bytes) else f.get_content().encode(), f.file_name or file_url)
	index = {}
	for dt, owner in (("CRM Lead", "lead_owner"), ("CRM Deal", "deal_owner")):
		for r in frappe.get_all(dt, filters={owner: user}, fields=["name", "mobile_no", "phone"], limit=0):
			for n in (r.mobile_no, r.phone):
				if _digits(n):
					index.setdefault(_digits(n), (dt, r.name))
	me = _digits(frappe.db.get_value("User", user, "mobile_no")) or "0"
	made = skipped = unknown = 0
	for r in rows:
		ref = index.get(r["number"])
		if not ref:
			unknown += 1
			continue
		try:
			start = get_datetime(r["when"])
		except Exception:
			skipped += 1
			continue
		incoming = any(w in r["type"] for w in ("in", "receiv", "missed", "reject"))
		missed = any(w in r["type"] for w in ("miss", "reject", "not answer"))
		seconds = _seconds(r["duration"])
		if frappe.db.exists("CRM Call Log", {"reference_docname": ref[1], "start_time": start}):
			skipped += 1
			continue
		log = frappe.get_doc({"doctype": "CRM Call Log", "id": frappe.generate_hash(length=16), "type": "Incoming" if incoming else "Outgoing",
			"status": "No Answer" if missed or not seconds else "Completed", "from": r["number"] if incoming else me,
			"to": me if incoming else r["number"], "telephony_medium": "Manual", "start_time": start,
			"end_time": add_to_date(start, seconds=seconds), "duration": seconds, "reference_doctype": ref[0], "reference_docname": ref[1]})
		log.set("receiver" if incoming else "caller", user)
		log.insert(ignore_permissions=True)
		if seconds:
			crm._mark_first_response(ref[0], ref[1])
		made += 1
	return {"made": made, "already": skipped, "not_customers": unknown, "rows": len(rows)}


def noon_nudge(now=None):
	"""Scheduler (hourly): at 12 noon, a red ToDo for each salesperson with no call logged today."""
	now = now or now_datetime()
	if now.hour != 12 or not crm.installed():
		return
	from sk_app.comms import call_totals
	from sk_app.logins import profile_functions

	day = getdate(now)
	for p in frappe.get_all("SK App User", filters={"enabled": 1}, pluck="user"):
		if not {"Sales", "Marketing"} & set(profile_functions(p)):
			continue
		if call_totals(p, day)["calls"]:
			continue
		if frappe.db.exists("ToDo", {"allocated_to": p, "description": ["like", f"{NOON_MARK}%"], "date": day}):
			continue
		frappe.get_doc({"doctype": "ToDo", "allocated_to": p, "date": day, "priority": "High", "status": "Open",
			"description": f"{NOON_MARK} 0 calls logged by 12 noon. Call your new leads now, or upload today's call list (Calls → Upload call list)."}).insert(ignore_permissions=True)
