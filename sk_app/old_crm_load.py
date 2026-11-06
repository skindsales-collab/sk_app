"""SK 6-Nov: load the old CRM data that never reached ERPNext (1,343 Biziverse junk / lost leads and 46 Common Sheet
quote parties with no lead), so every salesperson's Junk, Loss and Quote arrows count from 1-Apr.

SK uploads one private File named SK_Old_CRM_Load_*.csv (made by Claude from the Biziverse export and the Common Sheet,
duplicates merged). The hourly job loads it once: rows whose mobile is already a lead are skipped, each lead keeps its
old CRM dates, and the result is written to SK Rule Log. Rules: sk_app/old_crm_rules.py."""

import csv
import io
import json

import frappe

from sk_app import old_crm_rules as R

DONE_KEY = "sk_old_crm_loaded"


def hourly():
	for f in frappe.get_all("File", filters={"file_name": ["like", f"{R.FILE_PREFIX}%.csv"], "is_folder": 0},
			fields=["name", "file_name"], order_by="creation asc"):
		if f.file_name not in (frappe.db.get_global(DONE_KEY) or "").split("|"):
			# about 1,400 leads: the long queue, one job per file (a second hour does not start it twice; a rerun
			# skips every mobile already loaded anyway)
			frappe.enqueue("sk_app.old_crm_load.load", queue="long", timeout=3600, file_name=f.name,
				job_id=f"sk_old_crm_load_{f.name}", deduplicate=True)


@frappe.whitelist()
def run(file: str):
	frappe.only_for("System Manager")
	return load(file)


def _known() -> dict:
	mobiles = {R.mobile_key(m) for m in frappe.get_all("CRM Lead", pluck="mobile_no")} - {None}
	return {"mobiles": mobiles, "users": set(frappe.get_all("User", filters={"enabled": 1}, pluck="name")),
		"sources": set(frappe.get_all("CRM Lead Source", pluck="name")),
		"reasons": set(frappe.get_all("CRM Lost Reason", pluck="name"))}


def load(file_name: str) -> dict:
	f = frappe.get_doc("File", file_name)
	content = f.get_content()
	if isinstance(content, bytes):
		content = content.decode("utf-8-sig")
	rows = list(csv.DictReader(io.StringIO(content.lstrip("\ufeff"))))
	known = _known()
	made, skipped = [], {}
	frappe.flags.in_import = True  # the mandatory gate and the double guard skip a load (sk_app.gates / doubles)
	frappe.flags.mute_emails = True
	try:
		for row in rows:
			lead, why = R.lead_from_row(row, known)
			if not lead:
				skipped[why] = skipped.get(why, 0) + 1
				continue
			# a closed old lead is no work for anyone: it is inserted without an owner, so Frappe CRM makes no assignment
			# (6-Nov live check: each assignment queued an "assigned a new task" e-mail; 1,168 mails from one load), and the
			# owner is written straight after so the person's arrows still count it
			closed = lead.get("status") in R.CLOSED
			owner = lead.pop("lead_owner", None) if closed else None
			doc = frappe.get_doc({"doctype": "CRM Lead", **lead})
			doc.insert(ignore_permissions=True)
			if owner:
				frappe.db.set_value("CRM Lead", doc.name, "lead_owner", owner, update_modified=False)
			created, closed = R.dates_of(row)
			if created:
				frappe.db.set_value("CRM Lead", doc.name, {"creation": f"{created} 10:00:00",
					"modified": f"{closed or created} 18:00:00"}, update_modified=False)
			if lead.get("mobile_no"):
				known["mobiles"].add(lead["mobile_no"])
			made.append(doc.name)
		frappe.db.set_global(DONE_KEY, "|".join(filter(None, [(frappe.db.get_global(DONE_KEY) or ""), f.file_name])))
		frappe.db.commit()
	finally:
		frappe.flags.in_import = False
		frappe.flags.mute_emails = False
	result = {"file": f.file_name, "rows": len(rows), "loaded": len(made), "skipped": skipped,
		"first": made[:1], "last": made[-1:]}
	_log(result)
	_record(f.file_name, rows, made)
	return result


def _record(file_name: str, rows: list, made: list):
	"""SK 6-Nov import completeness: the load is an SK Import row, re-counted nightly (sk_app.core.imports)."""
	from sk_app.core import imports

	try:
		by_owner = {}
		for r in rows:
			by_owner[r.get("lead_owner") or ""] = by_owner.get(r.get("lead_owner") or "", 0) + 1
		filters = {"name": ["between", [made[0], made[-1]]]} if made else {"name": "none"}
		imports.record("Old CRM (Biziverse inactive + Common Sheet quotes)", "CRM Lead", len(rows), len(made), filters, file_name=file_name,
			record_type="Leads", by_salesperson=by_owner)
	except Exception:
		frappe.log_error(title="SK App import record")


def _log(result: dict):
	try:
		frappe.get_doc({"doctype": "SK Rule Log", "module": "Sales", "rule": "old CRM load", "mode": "Load",
			"detail": frappe.as_json(result)[:2000]}).insert(
			ignore_permissions=True)
	except Exception:
		frappe.log_error(frappe.as_json(result), "old CRM load")


def backfill():
	"""After migrate: the loads already done (SK Rule Log mode Load) get their SK Import row once."""
	from sk_app.core import imports

	if not frappe.db.table_exists(imports.DOCTYPE):
		return
	for log in frappe.get_all("SK Rule Log", filters={"mode": "Load", "rule": "old CRM load"}, fields=["detail"]):
		try:
			r = json.loads(log.detail)
		except ValueError:
			continue
		if not r.get("file") or frappe.db.exists(imports.DOCTYPE, {"file_name": r["file"]}):
			continue
		made = (r.get("first") or []) + (r.get("last") or [])
		filters = {"name": ["between", [made[0], made[-1]]]} if made else {"name": "none"}
		imports.record("Old CRM (Biziverse inactive + Common Sheet quotes)", "CRM Lead", r.get("rows", 0), r.get("loaded", 0), filters,
			file_name=r["file"], record_type="Leads")
