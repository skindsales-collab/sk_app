"""HR: attendance from Optick / thumb machine, leave and expenses (change list point 16 + HR draft F05 Rev 2, SK 26-Oct-2026).

Attendance: male staff check in on Optick (face), female office staff on the thumb machine. Step 1 (now, free): Aarti
downloads the day's Optick file (Excel / CSV) and uploads it in the app. Each row becomes an ERPNext Employee Checkin
(IN / OUT, device "Optick") and, while no ERPNext Shift Type does auto attendance, an Attendance (Present, late after
the SK App Settings time). People are matched once by Employee → Attendance Device ID, then mobile number, then name;
a person not found is picked once on the upload screen and remembered. "23:00:00 Auto Checkout" in the Optick file is a
missed out-punch: no OUT is made and HR sees it. Absent is never written from the file (a person on the thumb machine
or at a site would be marked absent by mistake); it is shown as "no check-in".

Selfie check-in (with location) is only the backup. Leave and expenses go through ERPNext Leave Application and
Expense Claim, approved on the phone by the person's manager; Accounts pays approved claims (Finance → Expenses).
"""

import re
from datetime import datetime, time, timedelta

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, get_datetime, get_first_day, get_last_day, getdate, now_datetime, nowdate

from sk_app import logins
from sk_app.logic import DAY_NAMES, parse_lines
from sk_app.store import _company, _todo, _users_with_function, attach

HR = "HR"
FIX_TAG = "[Attendance fix]"
AUTO_OUT = ("auto checkout", "auto check out", "auto-checkout")


def _is_hr(user: str) -> bool:
	return "System Manager" in frappe.get_roles(user) or bool({HR, "Management"} & set(logins.profile_functions(user)))


def _need_hr(user: str):
	if not _is_hr(user):
		frappe.throw(_("This screen is for HR"), frappe.PermissionError)


def _settings():
	s = frappe.get_cached_doc("SK App Settings")
	late = s.get("late_after") or "09:15:00"
	return {"late_after": _to_time(late) or time(9, 15), "half_day_below": flt(s.get("half_day_below")),
		"from_file": cint(s.get("attendance_from_file") if s.get("attendance_from_file") is not None else 1),
		"working": parse_lines((s.working_days or "").replace(",", "\n")) or DAY_NAMES[:6]}


def _to_time(v):
	if v in (None, "", "-"):
		return None
	if isinstance(v, time):
		return v
	if isinstance(v, datetime):
		return v.time()
	if isinstance(v, timedelta):
		return (datetime.min + v).time()
	if isinstance(v, (int, float)) and 0 <= v < 1:  # Excel time as a fraction of a day
		return (datetime.min + timedelta(seconds=round(v * 86400))).time()
	m = re.search(r"(\d{1,2}):(\d{2})(?::(\d{2}))?\s*([AaPp][Mm])?", str(v))
	if not m:
		return None
	h, mi, s = int(m.group(1)), int(m.group(2)), int(m.group(3) or 0)
	if m.group(4):
		h = h % 12 + (12 if m.group(4).lower() == "pm" else 0)
	return time(h, mi, s) if h < 24 else None


def _to_date(v):
	if v in (None, "", "-"):
		return None
	if isinstance(v, datetime):
		return v.date()
	try:
		s = str(v).strip()[:10]
		for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y", "%m/%d/%Y"):
			try:
				return datetime.strptime(s, fmt).date()
			except ValueError:
				continue
		return getdate(s)
	except Exception:
		return None


def _digits(v) -> str:
	d = re.sub(r"\D", "", str(v or ""))
	return d[-10:] if len(d) >= 10 else d


def _hm(t) -> str:
	return t.strftime("%H:%M") if t else ""


# ---------- matching people ----------

def _employees() -> list[dict]:
	rows = frappe.get_all("Employee", filters={"status": "Active"}, fields=["name", "employee_name", "attendance_device_id",
		"cell_number", "user_id", "company", "holiday_list", "gender", "date_of_joining"], order_by="employee_name asc")
	mobiles = {u.name: u.mobile_no for u in frappe.get_all("User", filters={"name": ["in", [r.user_id for r in rows if r.user_id] or [""]]},
		fields=["name", "mobile_no"])}
	for r in rows:
		r["mobile"] = _digits(r.cell_number) or _digits(mobiles.get(r.user_id))
	return rows


def _match(emps: list[dict], device_id: str, mobile: str, name: str):
	"""Attendance Device ID first (saved once), then the mobile number, then the exact name."""
	if device_id:
		for e in emps:
			if (e.attendance_device_id or "").strip() == device_id:
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


# ---------- reading the Optick / thumb file ----------

COLUMNS = {
	"date": ("date", "attendance date", "punch date"),
	"id": ("emp id", "employee id", "emp code", "employee code", "user id", "id", "enroll no", "card no"),
	"name": ("name", "employee name", "emp name"),
	"mobile": ("mobile no.", "mobile no", "mobile", "phone"),
	"in": ("in time", "punch in", "check in", "in"),
	"out": ("out time", "punch out", "check out", "out"),
	"work": ("total work", "work duration", "total hours", "duration"),
	"status": ("status",),
}


def _read(file_url: str) -> list[dict]:
	from sk_app.lead_sources import _rows_from_file

	rows = _rows_from_file(file_url) or []
	head_at, cols = None, {}
	for i, r in enumerate(rows[:15]):
		names = [str(c or "").strip().lower() for c in r]
		if "date" in names and any(n in names for n in COLUMNS["in"]):
			head_at = i
			for key, words in COLUMNS.items():
				for w in words:
					if w in names:
						cols[key] = names.index(w)
						break
			break
	if head_at is None:
		frappe.throw(_("This file has no Date / In Time columns. Please upload the Optick 'Basic Report' file."))
	out = []
	for r in rows[head_at + 1:]:
		get = lambda k: r[cols[k]] if k in cols and cols[k] < len(r) else None  # noqa: E731
		day = _to_date(get("date"))
		if not day:
			continue
		work = str(get("work") or "").strip().lower()
		in_t, out_t = _to_time(get("in")), _to_time(get("out"))
		missed = work in AUTO_OUT or (out_t == time(23, 0) and work in ("", "-"))
		out.append({"date": day, "id": str(get("id") or "").strip().removesuffix(".0"), "name": str(get("name") or "").strip(),
			"mobile": _digits(get("mobile")), "in": in_t, "out": None if missed else out_t, "missed_out": bool(in_t and missed),
			"status": str(get("status") or "").strip()})
	return out


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
		e, how = _match(emps, r["id"], r["mobile"], r["name"])
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
	for key, emp in (matches or {}).items():
		if not emp or emp not in by_name:
			continue
		r = next((x for x in rows if key in (x["id"], x["mobile"], x["name"])), None)
		if r and r["id"] and not by_name[emp].attendance_device_id:
			frappe.db.set_value("Employee", emp, "attendance_device_id", r["id"])
			by_name[emp]["attendance_device_id"] = r["id"]
			saved_ids += 1
	cfg = _settings()
	made = {"checkins": 0, "attendance": 0, "skipped": 0, "not_matched": 0, "missed_out": 0, "errors": []}
	for r in rows:
		if not r["in"]:
			continue
		key = r["id"] or r["mobile"] or r["name"]
		e, _how = _match(emps, r["id"], r["mobile"], r["name"])
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
	"""(name, made_now): Present (late after the settings time; half day only if SK set the hours and both punches
	are real). An existing Attendance (leave, HR fix) is never changed."""
	name = frappe.db.get_value("Attendance", {"employee": e.name, "attendance_date": day, "docstatus": ["<", 2]})
	if name:
		return name, False
	status = "Present"
	if cfg["half_day_below"] and outs and (outs - ins).total_seconds() / 3600 < cfg["half_day_below"]:
		status = "Half Day"
	doc = frappe.get_doc({"doctype": "Attendance", "employee": e.name, "attendance_date": day, "status": status,
		"company": e.company or _company(), "in_time": ins, "out_time": outs, "late_entry": int(ins.time() > cfg["late_after"])})
	doc.flags.ignore_permissions = True
	doc.insert()
	doc.submit()
	return doc.name, True


# ---------- who is in today, month ----------

def _off(e, day, cfg, holidays: dict) -> bool:
	if DAY_NAMES[day.weekday()] not in cfg["working"]:
		return True
	if e.name not in holidays:  # ERPNext v16: Holiday List Assignment (employee, else company); older: on the Employee
		hl = None
		try:
			from hrms.utils.holiday_list import get_holiday_list_for_employee

			hl = get_holiday_list_for_employee(e.name, raise_exception=False, as_on=day)
		except ImportError:
			pass
		holidays[e.name] = hl or e.holiday_list or frappe.get_cached_value("Company", e.company or _company(), "default_holiday_list")
	hl = holidays[e.name]
	if hl and hl not in holidays:
		holidays[hl] = set(getdate(d) for d in frappe.get_all("Holiday", filters={"parent": hl}, pluck="holiday_date"))
	return bool(hl and day in holidays[hl])


def _leaves(day_from, day_to) -> dict:
	"""{employee: [(from, to, type, half)]} approved leave in the period."""
	out = {}
	if not frappe.db.exists("DocType", "Leave Application"):
		return out
	for l in frappe.get_all("Leave Application", filters={"status": "Approved", "docstatus": 1, "from_date": ["<=", day_to],
			"to_date": [">=", day_from]}, fields=["employee", "from_date", "to_date", "leave_type", "half_day"]):
		out.setdefault(l.employee, []).append(l)
	return out


def _on_leave(leaves, emp, day):
	return next((l for l in leaves.get(emp, []) if getdate(l.from_date) <= day <= getdate(l.to_date)), None)


def today(user: str, day=None) -> dict:
	"""HR / Management: today's Present (Optick / thumb / selfie), Late, No check-in, On leave, Off; fix requests."""
	_need_hr(user)
	day = getdate(day or nowdate())
	cfg = _settings()
	emps = _employees()
	logs = frappe.get_all("Employee Checkin", filters={"time": ["between", [f"{day} 00:00:00", f"{day} 23:59:59"]]},
		fields=["employee", "time", "log_type", "device_id"], order_by="time asc")
	first, last = {}, {}
	for x in logs:
		first.setdefault(x.employee, x)
		last[x.employee] = x
	att = {a.employee: a for a in frappe.get_all("Attendance", filters={"attendance_date": day, "docstatus": 1},
		fields=["name", "employee", "status", "late_entry"])}
	leaves, holidays = _leaves(day, day), {}
	groups = {"present": [], "late": [], "no_checkin": [], "on_leave": [], "off": []}
	for e in emps:
		f, a, lv = first.get(e.name), att.get(e.name), _on_leave(leaves, e.name, day)
		row = {"employee": e.name, "name": e.employee_name, "user": e.user_id, "mobile": e.mobile}
		if f:
			t = get_datetime(f.time).time()
			lo = last.get(e.name)
			row.update({"in": _hm(t), "out": _hm(get_datetime(lo.time).time()) if lo and lo.log_type == "OUT" else "",
				"source": f.device_id or "ERPNext"})
			groups["late" if t > cfg["late_after"] else "present"].append(row)
		elif lv or (a and a.status == "On Leave"):
			groups["on_leave"].append({**row, "leave_type": lv.leave_type if lv else "On Leave"})
		elif a and a.status in ("Present", "Work From Home", "Half Day"):
			groups["late" if a.late_entry else "present"].append({**row, "source": a.status})
		elif _off(e, day, cfg, holidays):
			groups["off"].append(row)
		else:
			groups["no_checkin"].append(row)
	return {"day": str(day), "late_after": _hm(cfg["late_after"]), "groups": groups,
		"counts": {k: len(v) for k, v in groups.items()}, "uploaded_today": any(x.device_id == "Optick" for x in logs),
		"by_source": {s: sum(1 for f in first.values() if (f.device_id or "ERPNext") == s) for s in {(f.device_id or "ERPNext") for f in first.values()}},
		"fix_requests": fix_requests(user)}


def month(user: str, month=None, employee=None) -> dict:
	"""Present / late / half day / leave / absent (= working day with no check-in) per person."""
	if employee:
		emp_user = frappe.db.get_value("Employee", employee, "user_id")
		if emp_user != user:
			_need_hr(user)
	else:
		_need_hr(user)
	start = get_first_day(getdate(month or nowdate()))
	end = min(get_last_day(start), getdate(nowdate()))
	cfg = _settings()
	emps = [e for e in _employees() if not employee or e.name == employee]
	att = {}
	for a in frappe.get_all("Attendance", filters={"attendance_date": ["between", [start, end]], "docstatus": 1,
			"employee": ["in", [e.name for e in emps] or [""]]}, fields=["employee", "attendance_date", "status", "late_entry"]):
		att[(a.employee, getdate(a.attendance_date))] = a
	ins = set()
	for c in frappe.get_all("Employee Checkin", filters={"time": ["between", [f"{start} 00:00:00", f"{end} 23:59:59"]],
			"employee": ["in", [e.name for e in emps] or [""]], "log_type": "IN"}, fields=["employee", "time"]):
		ins.add((c.employee, get_datetime(c.time).date()))
	leaves, holidays = _leaves(start, end), {}
	rows = []
	for e in emps:
		r = {"employee": e.name, "name": e.employee_name, "present": 0, "late": 0, "half_day": 0, "leave": 0, "absent": 0,
			"late_days": [], "leave_days": [], "absent_days": []}
		d = start
		while d <= end:
			a = att.get((e.name, d))
			if e.date_of_joining and d < getdate(e.date_of_joining):
				pass
			elif a and a.status == "On Leave" or (not a and _on_leave(leaves, e.name, d)):
				r["leave"] += 1
				r["leave_days"].append(d.day)
			elif a and a.status == "Absent":
				r["absent"] += 1
				r["absent_days"].append(d.day)
			elif a:
				r["half_day" if a.status == "Half Day" else "present"] += 1
				if a.late_entry:
					r["late"] += 1
					r["late_days"].append(d.day)
			elif (e.name, d) in ins:
				r["present"] += 1
			elif not _off(e, d, cfg, holidays) and d < getdate(nowdate()):
				r["absent"] += 1
				r["absent_days"].append(d.day)
			d = add_days(d, 1)
		rows.append(r)
	return {"month": str(start)[:7], "rows": rows}


def my_line(user: str) -> dict | None:
	"""My Day top line: "In 9:02 (Optick)" green, late amber, or red "No check-in yet" after the late time on a working
	day once HR has uploaded today's file (before that it waits for the file, amber)."""
	emp = frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, ["name", "employee_name", "company", "holiday_list"], as_dict=True)
	if not emp:
		return None
	cfg = _settings()
	day = getdate(nowdate())
	first = frappe.get_all("Employee Checkin", filters={"employee": emp.name, "time": ["between", [f"{day} 00:00:00", f"{day} 23:59:59"]]},
		fields=["time", "log_type", "device_id"], order_by="time asc")
	out = {"employee": emp.name, "late_after": _hm(cfg["late_after"]), "month": month(user, day, emp.name)["rows"][0]}
	if first:
		t = get_datetime(first[0].time).time()
		last_out = next((get_datetime(x.time).time() for x in reversed(first) if x.log_type == "OUT"), None)
		return {**out, "state": "amber" if t > cfg["late_after"] else "green", "in": _hm(t), "out": _hm(last_out),
			"source": first[0].device_id or "ERPNext", "next": "OUT" if first[-1].log_type == "IN" else "IN"}
	lv = _on_leave(_leaves(day, day), emp.name, day)
	if lv:
		return {**out, "state": "green", "leave": lv.leave_type, "next": "IN"}
	if _off(emp, day, cfg, {}):
		return {**out, "state": "green", "off": True, "next": "IN"}
	if now_datetime().time() <= cfg["late_after"]:
		return {**out, "state": None, "next": "IN"}
	uploaded = frappe.db.exists("Employee Checkin", {"device_id": "Optick", "time": ["between", [f"{day} 00:00:00", f"{day} 23:59:59"]]})
	return {**out, "state": "red" if uploaded else "amber", "waiting_file": not uploaded, "next": "IN"}


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


def _hr_people() -> list[str]:
	return _users_with_function(HR) or _users_with_function("Management")


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
	doc.insert()
	doc.submit()
	doc.add_comment("Comment", _("Fixed in SK App by {0}: {1}").format(frappe.utils.get_fullname(user), reason.strip()[:300]))
	if todo and frappe.db.get_value("ToDo", todo, "allocated_to") == user:
		frappe.db.set_value("ToDo", todo, "status", "Closed")
	return {"name": doc.name, "status": status}


# ---------- leave and expenses ----------

def _my_employee(user: str):
	emp = frappe.db.get_value("Employee", {"user_id": user, "status": "Active"},
		["name", "employee_name", "company", "leave_approver", "expense_approver", "reports_to"], as_dict=True)
	if not emp:
		frappe.throw(_("Your login is not linked to an ERPNext Employee. Please ask HR."))
	return emp


def _approver(emp, user: str, field: str) -> str | None:
	"""Employee's leave / expense approver, else the manager they report to, else their app manager, else HR."""
	a = emp.get(field)
	if not a and emp.reports_to:
		a = frappe.db.get_value("Employee", emp.reports_to, "user_id")
	if not a:
		a = frappe.db.get_value("SK App User", {"user": user}, "manager")
	if not a or a == user:
		a = next((u for u in _hr_people() if u != user), a)
	return a


def _may_decide(user: str, approver: str | None) -> bool:
	return approver == user or _is_hr(user)


def options(user: str) -> dict:
	emp = frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, "name")
	types = []
	if frappe.db.exists("DocType", "Leave Type"):
		from hrms.hr.doctype.leave_application.leave_application import get_leave_balance_on

		for lt in frappe.get_all("Leave Type", fields=["name", "is_lwp"], order_by="name asc"):
			bal = None
			if emp and not lt.is_lwp:
				try:
					bal = flt(get_leave_balance_on(emp, lt.name, nowdate()))
				except Exception:
					bal = None
			types.append({"name": lt.name, "balance": bal, "lwp": bool(lt.is_lwp)})
	exp = frappe.get_all("Expense Claim Type", pluck="name", order_by="name asc") if frappe.db.exists("DocType", "Expense Claim Type") else []
	from sk_app.requisition import cabin_codes

	return {"leave_types": types, "expense_types": exp, "employee": emp, "is_hr": _is_hr(user), "is_ceo": _is_ceo(user),
		"cabins": cabin_codes()}  # SK 28-Oct: cash voucher project / cabin code


LEAVE_FIELDS = ["name", "employee", "employee_name", "leave_type", "from_date", "to_date", "total_leave_days", "half_day",
	"description", "status", "docstatus", "leave_approver", "posting_date"]
CLAIM_FIELDS = ["name", "employee", "employee_name", "posting_date", "total_claimed_amount", "approval_status", "status",
	"docstatus", "expense_approver", "remark"]


def _claim_fields() -> list[str]:
	extra = ["sk_paid_to", "sk_cabin", "sk_no_bill", "project"] if frappe.get_meta("Expense Claim").has_field("sk_paid_to") else []
	return CLAIM_FIELDS + extra


def listing(user: str) -> dict:
	"""Mine (leave + expenses) and To approve (where I am the approver; HR / Management see all waiting)."""
	emp = frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, "name")
	hr = _is_hr(user)
	wait_leave = {"status": "Open", "docstatus": 0, **({} if hr else {"leave_approver": user})}
	wait_claim = {"approval_status": "Draft", "docstatus": 0}  # SK 28-Oct: every cash voucher waits for the CEO
	out = {"my_leave": [], "my_claims": [], "leave_to_approve": [], "claims_to_approve": []}
	if frappe.db.exists("DocType", "Leave Application"):
		if emp:
			out["my_leave"] = frappe.get_all("Leave Application", filters={"employee": emp}, fields=LEAVE_FIELDS, order_by="from_date desc", limit=20)
		out["leave_to_approve"] = [l for l in frappe.get_all("Leave Application", filters=wait_leave, fields=LEAVE_FIELDS, order_by="from_date asc", limit=50)
			if l.employee != emp]
	if frappe.db.exists("DocType", "Expense Claim"):
		if emp:
			out["my_claims"] = frappe.get_all("Expense Claim", filters={"employee": emp}, fields=_claim_fields(), order_by="posting_date desc", limit=20)
		if _is_ceo(user):
			out["claims_to_approve"] = frappe.get_all("Expense Claim", filters=wait_claim, fields=_claim_fields(), order_by="posting_date asc", limit=50)
		for c in out["my_claims"] + out["claims_to_approve"]:
			c["type"] = frappe.db.get_value("Expense Claim Detail", {"parent": c.name}, "expense_type")
			c["stage"] = _stage(c)
			c["photos"] = frappe.get_all("File", filters={"attached_to_doctype": "Expense Claim", "attached_to_name": c.name}, pluck="file_url")
	out["to_approve"] = len(out["leave_to_approve"]) + len(out["claims_to_approve"])
	return out


def apply_leave(user: str, leave_type: str, from_date, to_date=None, half_day=0, reason: str | None = None) -> dict:
	emp = _my_employee(user)
	approver = _approver(emp, user, "leave_approver")
	doc = frappe.get_doc({"doctype": "Leave Application", "employee": emp.name, "leave_type": leave_type, "from_date": getdate(from_date),
		"to_date": getdate(to_date or from_date), "half_day": cint(half_day), "half_day_date": getdate(from_date) if cint(half_day) else None,
		"description": (reason or "").strip()[:500], "leave_approver": approver, "status": "Open", "company": emp.company,
		"posting_date": nowdate(), "follow_via_email": 0})
	doc.flags.ignore_permissions = True
	try:
		doc.insert()
	except frappe.ValidationError as e:
		frappe.clear_messages()
		msg = str(e)
		if "balance" in msg.lower():
			msg = _("No {0} left for you. Ask HR to give leave, or pick Leave Without Pay.").format(leave_type)
		elif "holiday list" in msg.lower():
			msg = _("HR has not set your holiday list in ERPNext yet (Holiday List Assignment). Please ask HR.")
		frappe.throw(re.sub(r"<[^>]*>", "", msg))
	if approver:
		_todo(approver, "Leave Application", doc.name, f"Leave: {emp.employee_name} {doc.from_date} to {doc.to_date} ({leave_type}). Please approve.")
	return {"name": doc.name, "approver": frappe.utils.get_fullname(approver) if approver else None, "days": doc.total_leave_days}


def decide_leave(user: str, name: str, ok, note: str | None = None) -> dict:
	doc = frappe.get_doc("Leave Application", name)
	if not _may_decide(user, doc.leave_approver):
		frappe.throw(_("Only the approver or HR can do this"), frappe.PermissionError)
	if doc.docstatus != 0:
		frappe.throw(_("Already decided"))
	doc.status = "Approved" if cint(ok) else "Rejected"
	doc.flags.ignore_permissions = True
	doc.save()
	doc.submit()
	if note:
		doc.add_comment("Comment", note.strip()[:300])
	_close_todos("Leave Application", name)
	emp_user = frappe.db.get_value("Employee", doc.employee, "user_id")
	if emp_user:
		_todo(emp_user, "Leave Application", name, f"Your leave {doc.from_date} to {doc.to_date}: {doc.status}{' · ' + note if note else ''}")
	return {"status": doc.status}


# ---------- cash vouchers (SK 28-Oct): filled by the person, every one approved by the CEO, paid by Accounts ----------

def _stage(c) -> str:
	"""Waiting CEO → Approved → Paid (or Rejected), as the person sees it."""
	if c.approval_status == "Rejected":
		return "Rejected"
	if c.approval_status != "Approved":
		return "Waiting CEO"
	return "Paid" if c.docstatus == 1 and c.status == "Paid" else "Approved"


def ensure_voucher_fields():
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	if not frappe.db.exists("DocType", "Expense Claim"):
		return
	create_custom_fields({"Expense Claim": [
		{"fieldname": "sk_paid_to", "label": "Paid to", "fieldtype": "Data", "insert_after": "expense_approver"},
		{"fieldname": "sk_cabin", "label": "Project / cabin code", "fieldtype": "Data", "insert_after": "sk_paid_to", "in_standard_filter": 1},
		{"fieldname": "sk_no_bill", "label": "No bill: reason", "fieldtype": "Small Text", "insert_after": "sk_cabin"},
	]}, update=True)


def _ceos() -> list[str]:
	from sk_app.requisition import _ceos

	return _ceos()


def _is_ceo(user: str) -> bool:
	from sk_app.requisition import _is_ceo

	return _is_ceo(user)


def claim_expense(user: str, expense_type: str, amount, expense_date=None, note: str | None = None, photo: str | None = None,
		paid_to: str | None = None, cabin: str | None = None, no_bill: str | None = None) -> dict:
	"""Cash voucher filled by the person who spent it, with the details the CEO needs; every voucher goes to the CEO."""
	emp = _my_employee(user)
	if flt(amount) <= 0:
		frappe.throw(_("Please give the amount"))
	if not (note or "").strip():
		frappe.throw(_("Please say what the money was spent on"))
	if not photo and not (no_bill or "").strip():
		frappe.throw(_("Please take the bill photo, or say why there is no bill"))
	ceos = [u for u in _ceos() if u != user] or _ceos()
	approver = ceos[0] if ceos else None
	cabin = (cabin or "").strip()
	doc = frappe.get_doc({"doctype": "Expense Claim", "employee": emp.name, "company": emp.company or _company(),
		"expense_approver": approver, "approval_status": "Draft", "posting_date": nowdate(), "remark": (note or "").strip()[:500],
		"expenses": [{"expense_date": getdate(expense_date or nowdate()), "expense_type": expense_type, "amount": flt(amount),
			"description": (note or expense_type).strip()[:300]}]})
	if doc.meta.has_field("sk_paid_to"):
		doc.update({"sk_paid_to": (paid_to or "").strip()[:140], "sk_cabin": cabin[:140], "sk_no_bill": (no_bill or "").strip()[:300] if not photo else None})
	if cabin and frappe.db.exists("Project", cabin):
		doc.project = cabin
	doc.flags.ignore_permissions = True
	doc.flags.ignore_mandatory = True  # payable account and expense accounts are set by Accounts before posting
	doc.insert()
	attach(photo, "Expense Claim", doc.name, user)
	for ceo in ceos:
		_todo(ceo, "Expense Claim", doc.name, f"Cash voucher: {emp.employee_name} Rs {flt(amount):,.0f} ({expense_type}"
			f"{' · ' + cabin if cabin else ''}). Please approve.")
	return {"name": doc.name, "approver": frappe.utils.get_fullname(approver) if approver else None}


def decide_expense(user: str, name: str, ok, note: str | None = None) -> dict:
	"""CEO approves (sanctioned = claimed) or rejects with a reason. ERPNext posts it if the accounts are set; Accounts pays it."""
	from sk_app.store import try_submit

	doc = frappe.get_doc("Expense Claim", name)
	if not _is_ceo(user):
		frappe.throw(_("Only the CEO approves cash vouchers"), frappe.PermissionError)
	if doc.docstatus != 0:
		frappe.throw(_("Already decided"))
	if not cint(ok) and not (note or "").strip():
		frappe.throw(_("Please say why it is rejected"))
	doc.approval_status = "Approved" if cint(ok) else "Rejected"
	for row in doc.expenses:
		row.sanctioned_amount = row.amount if cint(ok) else 0
	doc.flags.ignore_permissions = True
	doc.flags.ignore_mandatory = True
	doc.save()
	posted = try_submit(doc)
	if note:
		doc.add_comment("Comment", note.strip()[:300])
	_close_todos("Expense Claim", name)
	if cint(ok):
		for acc in _users_with_function("Accounts"):
			_todo(acc, "Expense Claim", name, f"Approved cash voucher {doc.employee_name} Rs {flt(doc.total_claimed_amount):,.0f}: "
				+ ("pay it in ERPNext" if posted else "set accounts, post and pay in ERPNext"))
	emp_user = frappe.db.get_value("Employee", doc.employee, "user_id")
	if emp_user and emp_user != user:
		_todo(emp_user, "Expense Claim", name, f"Your cash voucher Rs {flt(doc.total_claimed_amount):,.0f}: {doc.approval_status}{' · ' + note if note else ''}")
	return {"status": doc.approval_status, "posted": posted}


def _close_todos(doctype: str, name: str):
	for t in frappe.get_all("ToDo", filters={"reference_type": doctype, "reference_name": name, "status": "Open"}, pluck="name"):
		frappe.db.set_value("ToDo", t, "status", "Closed")


SK_HOLIDAYS = "SK Holidays {0}-{1}"


def ensure_holiday_setup():
	"""Trial 26-Oct: leave could not be applied on sk-dev: HRMS needs a Holiday List assigned to the company, and the
	holidays were made as one small list per festival with nothing assigned. Once, after deploy: one list for the
	financial year with every festival from those lists plus Sunday weekly off (Optick shows Sunday as Week_off),
	assigned to the company. Nothing is made when the company already has a holiday list."""
	if not frappe.db.exists("DocType", "Holiday List"):
		return
	try:
		company = _company()
		if not company:
			return
		if frappe.db.exists("DocType", "Holiday List Assignment"):
			if frappe.db.exists("Holiday List Assignment", {"assigned_to": company, "docstatus": 1}):
				return
		elif frappe.db.get_value("Company", company, "default_holiday_list"):
			return
		today = getdate()
		fy = today.year if today.month >= 4 else today.year - 1
		start, end = getdate(f"{fy}-04-01"), getdate(f"{fy + 1}-03-31")
		name = SK_HOLIDAYS.format(fy, str(fy + 1)[2:])
		if not frappe.db.exists("Holiday List", name):
			festivals = frappe.get_all("Holiday", filters={"parenttype": "Holiday List", "holiday_date": ["between", [start, end]], "weekly_off": 0},
				fields=["holiday_date", "description"], order_by="holiday_date")
			seen, rows = set(), []
			for h in festivals:
				if h.holiday_date not in seen:
					seen.add(h.holiday_date)
					rows.append({"holiday_date": h.holiday_date, "description": h.description})
			day = start + timedelta(days=(6 - start.weekday()) % 7)
			while day <= end:
				if day not in seen:
					rows.append({"holiday_date": day, "description": "Sunday", "weekly_off": 1})
				day += timedelta(days=7)
			frappe.get_doc({"doctype": "Holiday List", "holiday_list_name": name, "from_date": start, "to_date": end,
				"holidays": sorted(rows, key=lambda r: r["holiday_date"])}).insert(ignore_permissions=True)
		if frappe.db.exists("DocType", "Holiday List Assignment"):
			frappe.get_doc({"doctype": "Holiday List Assignment", "applicable_for": "Company", "assigned_to": company,
				"holiday_list": name, "from_date": start}).insert(ignore_permissions=True).submit()
		if not frappe.db.get_value("Company", company, "default_holiday_list"):
			frappe.db.set_value("Company", company, "default_holiday_list", name)
	except Exception:
		frappe.log_error("SK App holiday list setup")


def badges(user: str, functions: list[str]) -> dict:
	out = {}
	try:
		n = listing(user)["to_approve"]
		if n:
			out["leave_expense"] = n
		if HR in functions or "Management" in functions:
			fixes = len(fix_requests(user))
			if fixes:
				out["attendance"] = fixes
	except Exception:
		frappe.log_error("SK App HR badges")
	return out


# ---------- New joiner from a photo of the joining form / PAN / Aadhaar (SK 27-Oct improvement list point 10) ----------
# HR photographs the papers, the phone reads them, HR checks every box and saves: an ERPNext Employee. Bank details are
# never read or kept in the app (confidential); pay is not in the app at all.

def ensure_joiner_fields():
	"""Aadhaar has no standard Employee field: one Custom Field (HR may photograph Aadhaar, SK 26-Oct)."""
	if not frappe.db.exists("DocType", "Employee") or frappe.get_meta("Employee").has_field("sk_aadhaar"):
		return
	from frappe.custom.doctype.custom_field.custom_field import create_custom_field

	create_custom_field("Employee", {"fieldname": "sk_aadhaar", "label": "Aadhaar No", "fieldtype": "Data", "length": 12,
		"insert_after": "pan_number" if frappe.get_meta("Employee").has_field("pan_number") else "date_of_birth"})


def _date(value):
	if not value:
		return None
	v = str(value).strip()
	m = re.match(r"^(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2}|\d{4})$", v)
	if m:
		d, mth, y = m.groups()
		y = int(y) + (2000 if int(y) < 50 else 1900) if len(y) == 2 else int(y)
		return getdate(f"{y}-{int(mth):02d}-{int(d):02d}")
	return getdate(v)


def new_joiner(user: str, data: dict, photos: list | None = None) -> dict:
	_need_hr(user)
	name = " ".join((data.get("name") or "").split())
	if not name:
		frappe.throw(_("Please give the name"))
	gender = data.get("gender") or ""
	if gender not in ("Male", "Female"):
		frappe.throw(_("Please pick Male or Female"))
	dob, joined = _date(data.get("dob")), _date(data.get("joining")) or getdate()
	if not dob:
		frappe.throw(_("Please give the date of birth"))
	aadhaar = re.sub(r"\D", "", data.get("aadhaar") or "")
	if aadhaar and len(aadhaar) != 12:
		frappe.throw(_("Aadhaar must have 12 digits"))
	pan = (data.get("pan") or "").strip().upper()
	if pan and not re.match(r"^[A-Z]{5}\d{4}[A-Z]$", pan):
		frappe.throw(_("PAN looks wrong: 5 letters, 4 digits, 1 letter"))
	mobile = re.sub(r"\D", "", data.get("mobile") or "")[-10:]
	if mobile and frappe.db.exists("Employee", {"cell_number": mobile, "status": "Active"}):
		frappe.throw(_("An employee with mobile {0} already exists").format(mobile))
	first, _sp, last = name.partition(" ")
	doc = frappe.get_doc({"doctype": "Employee", "first_name": first, "last_name": last or None, "gender": gender,
		"date_of_birth": dob, "date_of_joining": joined, "company": _company(), "status": "Active",
		"cell_number": mobile or None, "personal_email": (data.get("email") or "").strip() or None,
		"current_address": (data.get("address") or "").strip() or None,
		"person_to_be_contacted": (data.get("emergency_name") or "").strip() or None,
		"emergency_phone_number": re.sub(r"\D", "", data.get("emergency_mobile") or "")[-10:] or None})
	if pan and doc.meta.has_field("pan_number"):
		doc.pan_number = pan
	if aadhaar and doc.meta.has_field("sk_aadhaar"):
		doc.sk_aadhaar = aadhaar
	if data.get("designation") and frappe.db.exists("Designation", data["designation"]):
		doc.designation = data["designation"]
	doc.insert()
	for p in photos or []:
		attach(p, "Employee", doc.name, user)
	return {"name": doc.name, "employee_name": doc.employee_name}
