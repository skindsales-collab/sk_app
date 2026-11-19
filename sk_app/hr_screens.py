"""HR screens (reads only; the HR writers are writers/attendance.py, writers/leave.py, writers/employee.py, writers/expense.py).
Today's attendance, the month, My Day line, leave / expense options and listing, badges.
Plan A step 4 (SK 9-Nov): split out of hr.py; names unchanged. hr.py keeps the helpers the HR writers share."""

from datetime import time
from frappe.utils import add_days, flt, get_datetime, get_first_day, get_last_day, getdate, now_datetime, nowdate
from sk_app.hr import HR, LEAVE_FIELDS, _claim_fields, _employees, _hm, _is_ceo, _is_hr, _leaves, _need_hr, _off, _on_leave, _settings, _stage
from sk_app.writers.attendance import fix_requests
import frappe


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
	from sk_app.purchase_screens import cabin_codes

	return {"leave_types": types, "expense_types": exp, "employee": emp, "is_hr": _is_hr(user), "is_ceo": _is_ceo(user),
		"cabins": cabin_codes()}  # SK 28-Oct: cash voucher project / cabin code

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
