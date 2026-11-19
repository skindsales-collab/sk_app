"""The one Attendance writer (linear flow map, Flow 6). On the New path of HR:

thumb machine (SK Thumb Sync, every 2 minutes) / Optick file / selfie -> Employee Checkin -> daily() at 10:30 AM makes one
ERPNext Attendance per person for YESTERDAY from its punches (HR uploads the Optick file by 10 AM, and late out-punches are
in by then), and sends HR ONE ToDo with yesterday's missed punches (no check-in, no out-punch). No manual attendance screen; HR's Fix stays for corrections.
The rules also run on every Attendance saved in ERPNext or through SK Hub (on_validate)."""

from datetime import datetime

import frappe
from frappe import _
from frappe.utils import add_days, get_datetime, getdate, nowdate

from sk_app.core.rules import report
from sk_app.writers.attendance_rules import attendance_problems, day_status, plan_day

MODULE = "HR"
TAG = "[Missed punch]"


def _use_new(user=None) -> bool:
	from sk_app.core.switch import use_new

	return use_new(MODULE, user if user is not None else frappe.session.user)


def make(e, day, ins: datetime, outs: datetime | None, cfg) -> tuple[str, bool]:
	"""(name, made_now): one posted Attendance for the day; an existing one (leave, HR fix) is never changed."""
	from sk_app.store import _company

	name = frappe.db.get_value("Attendance", {"employee": e.name, "attendance_date": day, "docstatus": ["<", 2]})
	if name:
		return name, False
	status, late = day_status(ins, outs, cfg["late_after"], cfg["half_day_below"])
	doc = frappe.get_doc({"doctype": "Attendance", "employee": e.name, "attendance_date": day, "status": status,
		"company": e.company or _company(), "in_time": ins, "out_time": outs, "late_entry": int(late)})
	doc.flags.ignore_permissions = True
	doc.flags.sk_from_punch = True
	doc.insert()
	doc.submit()
	return doc.name, True


def daily(day=None) -> dict:
	"""Scheduler 10:30 AM: yesterday's punches -> Attendance, missed punches -> one ToDo per HR person (checker 7-Nov: at
	night the Optick file is not in yet). Only when HR is New for everyone (a pilot list does not run the job)."""
	from sk_app import hr

	if not _use_new(""):
		return {"skipped": "HR is on the Old path"}
	day = getdate(day or add_days(nowdate(), -1))
	cfg = hr._settings()
	emps = [e for e in hr._employees() if not e.date_of_joining or getdate(e.date_of_joining) <= day]
	by_name = {e.name: e for e in emps}
	punches: dict = {}
	for c in frappe.get_all("Employee Checkin", filters={"time": ["between", [f"{day} 00:00:00", f"{day} 23:59:59"]],
			"employee": ["in", list(by_name) or [""]]}, fields=["employee", "time"]):
		punches.setdefault(c.employee, []).append(get_datetime(c.time))
	existing = set(frappe.get_all("Attendance", filters={"attendance_date": day, "docstatus": ["<", 2]}, pluck="employee"))
	leaves, holidays = hr._leaves(day, day), {}
	on_leave = {e.name for e in emps if hr._on_leave(leaves, e.name, day)}
	off = {e.name for e in emps if hr._off(e, day, cfg, holidays)}
	todo, missed = plan_day([{"name": e.name, "employee_name": e.employee_name} for e in emps], punches, existing, on_leave, off)
	made, errors = 0, []
	for t in todo:
		frappe.db.savepoint("sk_att_day")
		try:
			name, new = make(by_name[t["employee"]], day, t["in"], t["out"], cfg)
			made += 1 if new else 0
			# job J (9-Nov): the day's punches of any machine point to their Attendance
			frappe.db.sql("""update `tabEmployee Checkin` set attendance = %s where employee = %s and ifnull(attendance, '') = ''
				and time between %s and %s""", (name, t["employee"], f"{day} 00:00:00", f"{day} 23:59:59"))
		except Exception as ex:
			frappe.db.rollback(save_point="sk_att_day")
			frappe.clear_messages()
			errors.append(f"{by_name[t['employee']].employee_name}: {str(ex)[:120]}")
	# punches that arrived after the day's Attendance was made (thumb PC on again) still point to it
	frappe.db.sql("""update `tabEmployee Checkin` c join tabAttendance a on a.employee = c.employee and a.attendance_date = %s and a.docstatus = 1
		set c.attendance = a.name where ifnull(c.attendance, '') = '' and c.time between %s and %s""", (day, f"{day} 00:00:00", f"{day} 23:59:59"))
	if missed or errors:
		lines = [f"{m['name']}: {m['what']}" for m in missed] + [f"{x} (not saved)" for x in errors]
		text = f"{TAG} {day}: {len(missed)} to check<br>" + "<br>".join(lines[:60])
		for u in hr._hr_people():
			if not frappe.db.exists("ToDo", {"allocated_to": u, "status": "Open", "description": ["like", f"{TAG} {day}%"]}):
				frappe.get_doc({"doctype": "ToDo", "allocated_to": u, "description": text, "priority": "Medium", "date": nowdate(),
					"reference_type": "Attendance"}).insert(ignore_permissions=True)
	frappe.db.commit()
	return {"day": str(day), "made": made, "missed": len(missed), "errors": errors[:8]}


def today() -> dict:
	"""Scheduler 11:20 PM (job J, 9-Nov): today's punches -> Attendance at the end of the day, so a day is never lost when
	the thumb PC is off overnight; the 10:30 AM run back-fills yesterday."""
	return daily(nowdate())


def problems(doc) -> list:
	from sk_app import hr

	day = getdate(doc.attendance_date)
	joined = frappe.db.get_value("Employee", doc.employee, "date_of_joining")
	punches = frappe.db.count("Employee Checkin", {"employee": doc.employee, "time": ["between", [f"{day} 00:00:00", f"{day} 23:59:59"]]})
	leave = bool(hr._on_leave(hr._leaves(day, day), doc.employee, day))
	return attendance_problems(doc.status, day, getdate(joined) if joined else None, getdate(nowdate()), punches, leave)


def on_validate(doc, method=None):
	"""Every Attendance on the New path of HR (app, ERPNext, SK Hub)."""
	if doc.docstatus == 2 or doc.flags.get("sk_from_punch") or doc.flags.get("sk_hr_fix") or not _use_new(doc.owner):
		return
	report(MODULE, doc, problems(doc), title=_("Attendance check"))


# ---------- Plan A (SK 9-Nov): moved here unchanged from hr.py ----------
from datetime import datetime, time
from frappe import _
from frappe.utils import flt, getdate, now_datetime, nowdate
from sk_app.hr import AUTO_OUT, FIX_TAG, _digits, _employees, _hm, _hr_people, _need_hr, _settings, _to_date, _to_time
from sk_app.store import _company, _todo, attach
import frappe
import re


ID_FIELD = {"Optick": "attendance_device_id", "Office thumb": "thumb_id"}  # the two machines number people differently

def _match(emps: list[dict], device_id: str, mobile: str, name: str, device: str = "Optick"):
	"""The machine's own ID field first (saved once; thumb_id for the thumb machine, attendance_device_id for Optick),
	then the mobile number, then the exact name."""
	field = ID_FIELD.get(device, "attendance_device_id")
	if device_id:
		for e in emps:
			if str(e.get(field) or "").strip() == device_id:
				return e, "device id"
	if mobile:
		hits = [e for e in emps if e.mobile and e.mobile == mobile]
		if len(hits) == 1:
			return hits[0], "mobile"
	key = re.sub(r"\s+", " ", (name or "").strip().lower())
	if key:
		hits = [e for e in emps if re.sub(r"\s+", " ", (e.employee_name or "").strip().lower()) == key]
		if len(hits) == 1:
			return hits[0], "name"
	return None, None

COLUMNS = {
	"date": ("date", "attendance date", "punch date", "att. date", "att date", "log date", "logdate"),
	"id": ("emp id", "employee id", "emp code", "employee code", "user id", "userid", "id", "enroll no", "enrollno", "e. code", "card no"),
	"name": ("name", "employee name", "emp name", "emp. name"),
	"mobile": ("mobile no.", "mobile no", "mobile", "phone"),
	"in": ("in time", "intime", "punch in", "check in", "first in", "a. intime", "in"),
	"out": ("out time", "outtime", "punch out", "check out", "last out", "a. outtime", "out"),
	"work": ("total work", "work duration", "total hours", "duration", "work dur.", "work dur", "tot. dur."),
	"status": ("status",),
	# eSSL eTimeTrackLite: raw device logs (one row per punch) and the "Punch Records" cell of the daily report (job J, 9-Nov)
	"log": ("logdate", "log date", "punch time", "punch date time", "datetime", "date time"),
	"punches": ("punch records", "punches", "punch record"),
}

_DATE_IN_TEXT = re.compile(r"(\d{1,2}[-/.](?:\d{1,2}|[A-Za-z]{3})[-/.]\d{2,4}|\d{4}-\d{2}-\d{2})")

_TIME_IN_TEXT = re.compile(r"(\d{1,2}:\d{2}(?::\d{2})?)")

def _header(rows: list[list]) -> tuple[int | None, dict]:
	"""The header row and the column of each known field. A header needs an In Time column, or a log date-time column
	(raw device logs), or a Punch Records column; a Date column is not needed (eSSL daily report: date in the title)."""
	for i, r in enumerate(rows[:15]):
		names = [str(c or "").strip().lower() for c in r]
		cols = {}
		for key, words in COLUMNS.items():
			for w in words:
				if w in names:
					cols[key] = names.index(w)
					break
		if "in" in cols or "log" in cols or "punches" in cols:
			if "date" in cols and cols.get("log") == cols["date"]:  # "logdate" is a date-time, not a plain date
				cols.pop("date")
			return i, cols
	return None, {}

def _title_date(rows: list[list]):
	"""eSSL daily report: 'Attendance Date : 06-Nov-2026' in a row above the header."""
	for r in rows:
		for c in r:
			m = _DATE_IN_TEXT.search(str(c or ""))
			if m and "date" in " ".join(str(x or "") for x in r).lower():
				d = _to_date(m.group(1))
				if d:
					return d
	return None

def _punch_times(cell) -> tuple:
	"""'09:01:00(in),13:02:00(out),18:02:00(out)' -> (first time, last time)."""
	times = [_to_time(t) for t in _TIME_IN_TEXT.findall(str(cell or ""))]
	times = [t for t in times if t]
	return (times[0], times[-1] if len(times) > 1 else None) if times else (None, None)

def _read(file_url: str) -> list[dict]:
	from sk_app.lead_sources import _rows_from_file

	rows = _rows_from_file(file_url) or []
	head_at, cols = _header(rows)
	if head_at is None:
		frappe.throw(_("This file has no In Time / punch columns. Please upload the Optick 'Basic Report' or the eSSL attendance export."))
	fixed_day = _title_date(rows[:head_at]) if "date" not in cols and "log" not in cols else None
	out, by_key = [], {}
	for r in rows[head_at + 1:]:
		get = lambda k: r[cols[k]] if k in cols and cols[k] < len(r) else None  # noqa: E731
		pid, pname = str(get("id") or "").strip().removesuffix(".0"), str(get("name") or "").strip()
		if "log" in cols:  # raw device logs: one row per punch, grouped per person and day
			when = _to_datetime(get("log"))
			if not when or not (pid or pname):
				continue
			key = (pid or pname, when.date())
			row = by_key.get(key)
			if not row:
				row = by_key[key] = {"date": when.date(), "id": pid, "name": pname, "mobile": _digits(get("mobile")), "in": when.time(),
					"out": None, "missed_out": False, "status": ""}
				out.append(row)
			else:
				lo, hi = min(row["in"], when.time()), max(row["in"], row["out"] or row["in"], when.time())
				row["in"], row["out"] = lo, hi if hi > lo else None
			continue
		day = _to_date(get("date")) if "date" in cols else fixed_day
		if not day:
			continue
		work = str(get("work") or "").strip().lower()
		in_t, out_t = _to_time(get("in")), _to_time(get("out"))
		if not in_t and "punches" in cols:
			in_t, out_t = _punch_times(get("punches"))
		missed = work in AUTO_OUT or (out_t == time(23, 0) and work in ("", "-"))
		out.append({"date": day, "id": pid, "name": pname, "mobile": _digits(get("mobile")), "in": in_t, "out": None if missed else out_t,
			"missed_out": bool(in_t and missed), "status": str(get("status") or "").strip()})
	return out

def _to_datetime(v):
	if isinstance(v, datetime):
		return v
	s = str(v or "").strip()
	for fmt in ("%d-%m-%Y %H:%M:%S", "%d-%m-%Y %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M",
			"%d-%b-%Y %H:%M:%S", "%d-%b-%Y %H:%M", "%m/%d/%Y %H:%M:%S", "%m/%d/%Y %H:%M"):
		try:
			return datetime.strptime(s, fmt)
		except ValueError:
			continue
	return None

def upload_preview(user: str, file_url: str, device: str = "Optick") -> dict:
	"""What the file holds before anything is saved: matched, not found (pick once), missed out-punches, already saved."""
	_need_hr(user)
	rows = _read(file_url)
	emps = _employees()
	people, not_found = {}, {}
	for r in rows:
		key = r["id"] or r["mobile"] or r["name"]
		if key in people or key in not_found:
			(people.get(key) or not_found[key])["rows"] += 1
			continue
		e, how = _match(emps, r["id"], r["mobile"], r["name"], device)
		entry = {"id": r["id"], "name": r["name"], "mobile": r["mobile"], "rows": 1}
		if e:
			people[key] = {**entry, "employee": e.name, "employee_name": e.employee_name, "how": how}
		else:
			near = [x.name for x in emps if r["name"] and r["name"].split()[0].lower() in (x.employee_name or "").lower()]
			not_found[key] = {**entry, "options": near[:5]}
	days = sorted({r["date"] for r in rows})
	punches = [r for r in rows if r["in"]]
	already = 0
	matched_emps = {p["employee"] for p in people.values()}
	if punches and matched_emps:
		already = frappe.db.count("Employee Checkin", {"employee": ["in", list(matched_emps)], "device_id": device,
			"time": ["between", [f"{days[0]} 00:00:00", f"{days[-1]} 23:59:59"]]})
	return {"rows": len(rows), "punches": len(punches), "from": str(days[0]) if days else None, "to": str(days[-1]) if days else None,
		"matched": sorted(people.values(), key=lambda x: x["employee_name"]), "not_found": list(not_found.values()),
		"missed_out": [{"name": r["name"], "date": str(r["date"]), "in": _hm(r["in"])} for r in rows if r["missed_out"]],
		"late": sum(1 for r in punches if r["in"] > _settings()["late_after"]), "already": already,
		"employees": [{"name": e.name, "employee_name": e.employee_name} for e in emps], "device": device}

def upload_save(user: str, file_url: str, matches: dict | None = None, device: str = "Optick") -> dict:
	"""Make the Employee Checkins (and Attendance) from the file. matches = {file id / mobile / name: Employee} for the
	people HR picked; their Optick ID is saved on the Employee so next time it is automatic."""
	_need_hr(user)
	if device not in ("Optick", "Office thumb"):
		device = "Optick"
	rows = _read(file_url)
	emps = _employees()
	by_name = {e.name: e for e in emps}
	saved_ids = 0
	field = ID_FIELD.get(device, "attendance_device_id")  # the file's ID goes to that machine's own field, never crossed
	for key, emp in (matches or {}).items():
		if not emp or emp not in by_name:
			continue
		r = next((x for x in rows if key in (x["id"], x["mobile"], x["name"])), None)
		if r and r["id"] and not by_name[emp].get(field) and frappe.get_meta("Employee").has_field(field):
			frappe.db.set_value("Employee", emp, field, r["id"])
			by_name[emp][field] = r["id"]
			saved_ids += 1
	cfg = _settings()
	made = {"checkins": 0, "attendance": 0, "skipped": 0, "not_matched": 0, "missed_out": 0, "errors": []}
	for r in rows:
		if not r["in"]:
			continue
		key = r["id"] or r["mobile"] or r["name"]
		e, _how = _match(emps, r["id"], r["mobile"], r["name"], device)
		if not e and (matches or {}).get(key) in by_name:
			e = by_name[matches[key]]
		if not e:
			made["not_matched"] += 1
			continue
		made["missed_out"] += 1 if r["missed_out"] else 0
		frappe.db.savepoint("sk_att_row")
		try:
			ins = datetime.combine(r["date"], r["in"])
			outs = datetime.combine(r["date"], r["out"]) if r["out"] and r["out"] > r["in"] else None
			logs = [x for x in (_checkin(e.name, ins, "IN", device), outs and _checkin(e.name, outs, "OUT", device)) if x]
			made["checkins"] += sum(1 for _n, new in logs if new)
			if not logs or not any(new for _n, new in logs):
				made["skipped"] += 1
			if cfg["from_file"]:
				att = _attendance(e, r["date"], ins, outs, cfg)
				if att:
					made["attendance"] += 1 if att[1] else 0
					for name, _new in logs:
						frappe.db.set_value("Employee Checkin", name, "attendance", att[0], update_modified=False)
		except Exception as ex:
			frappe.db.rollback(save_point="sk_att_row")
			frappe.clear_messages()
			made["errors"].append(f"{e.employee_name} {r['date']}: {str(ex)[:120]}")
	made["errors"] = made["errors"][:8]
	made["ids_saved"] = saved_ids
	return made

def _checkin(employee: str, when: datetime, log_type: str, device: str, lat=None, lng=None):
	"""(name, made_now). The same person and time is never saved twice."""
	name = frappe.db.get_value("Employee Checkin", {"employee": employee, "time": when})
	if name:
		return name, False
	doc = frappe.get_doc({"doctype": "Employee Checkin", "employee": employee, "time": when, "log_type": log_type,
		"device_id": device, **({"latitude": flt(lat), "longitude": flt(lng)} if lat and lng else {})})
	doc.insert(ignore_permissions=True)
	return doc.name, True

def _attendance(e, day, ins, outs, cfg):
	"""(name, made_now): the one Attendance writer (rebuild Flow 6, writers/attendance.py)."""
	from sk_app.writers.attendance import make

	return make(e, day, ins, outs, cfg)

def selfie_checkin(user: str, photo: str, lat=None, lng=None) -> dict:
	"""Backup only (machine down, at a customer site): selfie + location, IN or OUT by the last punch of today."""
	if not photo:
		frappe.throw(_("Please take a selfie first"))
	emp = frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, "name")
	if not emp:
		frappe.throw(_("Your login is not linked to an ERPNext Employee. Please ask HR."))
	day = getdate(nowdate())
	last = frappe.get_all("Employee Checkin", filters={"employee": emp, "time": ["between", [f"{day} 00:00:00", f"{day} 23:59:59"]]},
		fields=["log_type"], order_by="time desc", limit=1)
	log_type = "OUT" if last and last[0].log_type == "IN" else "IN"
	name, _new = _checkin(emp, now_datetime().replace(microsecond=0), log_type, "App selfie", lat, lng)
	attach(photo, "Employee Checkin", name, user)
	return {"name": name, "log_type": log_type, "time": _hm(now_datetime().time())}

def ask_fix(user: str, day, text: str) -> dict:
	"""'Optick missed me': a ToDo to HR with the date and the person's words."""
	if not (text or "").strip():
		frappe.throw(_("Please say what to fix"))
	emp = frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, ["name", "employee_name"], as_dict=True)
	if not emp:
		frappe.throw(_("Your login is not linked to an ERPNext Employee. Please ask HR."))
	day = getdate(day or nowdate())
	for hr in _hr_people():
		_todo(hr, "Employee", emp.name, f"{FIX_TAG} {emp.employee_name} {day}: {text.strip()[:300]}")
	return {"ok": True}

def fix_requests(user: str) -> list[dict]:
	return [{"todo": t.name, "employee": t.reference_name, "text": t.description.replace(FIX_TAG, "").strip(), "date": _fix_date(t.description)}
		for t in frappe.get_all("ToDo", filters={"allocated_to": user, "status": "Open", "description": ["like", f"{FIX_TAG}%"]},
			fields=["name", "reference_name", "description"], order_by="creation asc")]

def _fix_date(text: str):
	m = re.search(r"\d{4}-\d{2}-\d{2}", text or "")
	return m.group(0) if m else None

def fix_attendance(user: str, employee: str, day, status: str, reason: str, todo: str | None = None) -> dict:
	"""HR corrects a day: the old Attendance is cancelled and a new one made with the reason as a comment."""
	_need_hr(user)
	if status not in ("Present", "Absent", "Half Day", "Work From Home"):
		frappe.throw(_("Unknown status"))
	if not (reason or "").strip():
		frappe.throw(_("Please say the reason"))
	day = getdate(day)
	old = frappe.db.get_value("Attendance", {"employee": employee, "attendance_date": day, "docstatus": 1})
	if old:
		o = frappe.get_doc("Attendance", old)
		o.flags.ignore_permissions = True
		o.cancel()
	frappe.db.delete("Attendance", {"employee": employee, "attendance_date": day, "docstatus": 0})
	doc = frappe.get_doc({"doctype": "Attendance", "employee": employee, "attendance_date": day, "status": status,
		"company": frappe.db.get_value("Employee", employee, "company") or _company()})
	doc.flags.ignore_permissions = True
	doc.flags.sk_hr_fix = True  # HR's correction carries its reason (comment): not a rule gap
	doc.insert()
	doc.submit()
	doc.add_comment("Comment", _("Fixed in SK App by {0}: {1}").format(frappe.utils.get_fullname(user), reason.strip()[:300]))
	if todo and frappe.db.get_value("ToDo", todo, "allocated_to") == user:
		frappe.db.set_value("ToDo", todo, "status", "Closed")
	return {"name": doc.name, "status": status}
