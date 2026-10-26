"""Change list point 16 + HR step: Optick file upload, attendance, leave and expenses."""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, getdate, nowdate

from sk_app import hr
from sk_app.tests.test_crm_day_report import app_user
from sk_app.tests.test_sk_app_api import make_user
from sk_app.tests.test_store_purchase import run

HR_U = "sk_test_hr_aarti@example.com"
STAFF = "sk_test_hr_ranjit@example.com"
BOSS = "sk_test_hr_boss@example.com"


def employee(first, mobile=None, user=None, **kw):
	name = frappe.db.get_value("Employee", {"first_name": first})
	if name:
		return name
	company = frappe.db.get_value("Company", {}, "name")
	doc = frappe.get_doc({"doctype": "Employee", "first_name": first, "gender": "Male", "date_of_birth": "1990-01-01",
		"date_of_joining": "2020-01-01", "company": company, "cell_number": mobile, "user_id": user, "status": "Active", **kw})
	doc.insert(ignore_permissions=True)
	return doc.name


class TestHr(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		if not frappe.db.get_value("Company", {}, "name"):
			raise cls.skipTest(cls, "needs an ERPNext company")
		for u, roles in ((HR_U, ["HR User", "HR Manager"]), (STAFF, ["Employee"]), (BOSS, ["Employee"])):
			make_user(u, roles)
		app_user(HR_U, "HR")
		app_user(BOSS, "Production")
		app_user(STAFF, "Production", manager=BOSS)
		cls.boss = employee("SKTestBoss", "9876511110", BOSS)
		cls.staff = employee("SKTestRanjit", "9876511111", STAFF, reports_to=cls.boss)
		cls.other = employee("SKTestBabu", None)
		cls.d1, cls.d2 = add_days(nowdate(), -2), add_days(nowdate(), -1)
		csv = "\n".join([
			"Basic Report — test,,,,,,,,,",
			"Date,Day,Emp ID,Name,Mobile No.,In Time,Out Time,Total Work,Overtime Duration,Status",
			f"{cls.d1},x,901,SKTestRanjit,9876511111,09:02:10,18:05:00,9h 3m,-,Present",
			f"{cls.d2},x,901,SKTestRanjit,9876511111,09:41:00,23:00:00,Auto Checkout,-,Present",
			f"{cls.d1},x,902,Babu,0000000000,08:55:00,17:00:00,8h 5m,-,Present",
			f"{cls.d2},x,902,Babu,0000000000,-,-,-,-,Absent",
		])
		f = frappe.get_doc({"doctype": "File", "file_name": "optick_test.csv", "content": csv.encode(), "is_private": 1})
		f.insert(ignore_permissions=True)
		cls.file_url = f.file_url

	def test_upload_today_month(self):
		p = run(HR_U, hr.upload_preview, self.file_url)
		self.assertEqual(p["rows"], 4)
		self.assertEqual([m["employee"] for m in p["matched"]], [self.staff])
		self.assertEqual(p["matched"][0]["how"], "mobile")
		self.assertEqual(len(p["not_found"]), 1)
		self.assertEqual(len(p["missed_out"]), 1)
		self.assertEqual(p["late"], 1)

		r = run(HR_U, hr.upload_save, self.file_url, {"902": self.other})
		self.assertEqual(r["errors"], [])
		self.assertEqual(r["ids_saved"], 1)
		self.assertEqual(frappe.db.get_value("Employee", self.other, "attendance_device_id"), "902")
		self.assertEqual(r["checkins"], 5)  # Ranjit IN+OUT, IN only (missed out), Babu IN+OUT; Babu's absent day makes nothing
		self.assertEqual(r["missed_out"], 1)
		self.assertFalse(frappe.db.exists("Attendance", {"employee": self.other, "attendance_date": self.d2}))
		late = frappe.db.get_value("Attendance", {"employee": self.staff, "attendance_date": self.d2}, ["status", "late_entry"], as_dict=True)
		self.assertEqual((late.status, late.late_entry), ("Present", 1))
		self.assertEqual(run(HR_U, hr.upload_save, self.file_url, {})["checkins"], 0)  # never twice

		day = run(HR_U, hr.today, self.d2)
		self.assertIn(self.staff, [x["employee"] for x in day["groups"]["late"]])
		m = {x["employee"]: x for x in run(HR_U, hr.month, self.d2)["rows"]}
		self.assertGreaterEqual(m[self.staff]["present"], 2)
		self.assertIn(getdate(self.d2).day, m[self.staff]["late_days"])
		with self.assertRaises(frappe.PermissionError):
			run(STAFF, hr.today)
		self.assertTrue(run(STAFF, hr.my_line))

	def test_fix_request_and_selfie(self):
		run(STAFF, hr.ask_fix, self.d1, "Optick did not read me")
		req = run(HR_U, hr.fix_requests)
		self.assertTrue(any("Optick did not read me" in x["text"] for x in req))
		x = next(x for x in req if "Optick did not read me" in x["text"])
		r = run(HR_U, hr.fix_attendance, self.staff, self.d1, "Half Day", "came late, told HR", x["todo"])
		self.assertEqual(frappe.db.get_value("Attendance", r["name"], "status"), "Half Day")
		self.assertEqual(frappe.db.get_value("ToDo", x["todo"], "status"), "Closed")
		photo = frappe.get_doc({"doctype": "File", "file_name": "selfie.txt", "content": b"x", "is_private": 1, "owner": STAFF}).insert(ignore_permissions=True)
		frappe.db.set_value("File", photo.name, "owner", STAFF)
		s = run(STAFF, hr.selfie_checkin, photo.file_url, 18.52, 73.85)
		self.assertEqual(frappe.db.get_value("Employee Checkin", s["name"], "device_id"), "App selfie")
		self.assertEqual(frappe.db.get_value("File", photo.name, "attached_to_name"), s["name"])

	def test_leave_and_expense(self):
		if not frappe.db.exists("Leave Type", "SK Test LWP"):
			frappe.get_doc({"doctype": "Leave Type", "leave_type_name": "SK Test LWP", "is_lwp": 1}).insert(ignore_permissions=True)
		hl = "SK Test HL"
		if not frappe.db.exists("Holiday List", hl):
			frappe.get_doc({"doctype": "Holiday List", "holiday_list_name": hl, "from_date": "2020-01-01",
				"to_date": "2030-12-31"}).insert(ignore_permissions=True)
		if frappe.db.exists("DocType", "Holiday List Assignment") and not frappe.db.exists("Holiday List Assignment", {"assigned_to": self.staff, "docstatus": 1}):
			frappe.get_doc({"doctype": "Holiday List Assignment", "applicable_for": "Employee", "assigned_to": self.staff,
				"holiday_list": hl, "from_date": "2020-01-01"}).insert(ignore_permissions=True).submit()
		frappe.db.set_value("Employee", self.staff, "holiday_list", hl)
		day = add_days(nowdate(), 30)
		while frappe.db.exists("Holiday", {"parent": hl, "holiday_date": day}):
			day = add_days(day, 1)
		r = run(STAFF, hr.apply_leave, "SK Test LWP", day, day, 0, "family function")
		self.assertTrue(frappe.db.exists("ToDo", {"allocated_to": BOSS, "reference_name": r["name"], "status": "Open"}))
		self.assertIn(r["name"], [x.name for x in run(BOSS, hr.listing)["leave_to_approve"]])
		self.assertNotIn(r["name"], [x.name for x in run(STAFF, hr.listing)["leave_to_approve"]])
		with self.assertRaises(frappe.PermissionError):
			run(STAFF, hr.decide_leave, r["name"], 1)
		self.assertEqual(run(BOSS, hr.decide_leave, r["name"], 1)["status"], "Approved")
		self.assertEqual(frappe.db.get_value("Leave Application", r["name"], "docstatus"), 1)

		company = frappe.db.get_value("Employee", self.staff, "company")
		account = frappe.db.get_value("Account", {"company": company, "root_type": "Expense", "is_group": 0}, "name")
		if not frappe.db.exists("Expense Claim Type", "SK Test Travel"):
			frappe.get_doc({"doctype": "Expense Claim Type", "expense_type": "SK Test Travel",
				"accounts": [{"company": company, "default_account": account}]}).insert(ignore_permissions=True)
		c = run(STAFF, hr.claim_expense, "SK Test Travel", 450, nowdate(), "auto to site")
		self.assertIn(c["name"], [x.name for x in run(BOSS, hr.listing)["claims_to_approve"]])
		d = run(BOSS, hr.decide_expense, c["name"], 1)
		self.assertEqual(d["status"], "Approved")
		self.assertEqual(frappe.db.get_value("Expense Claim", c["name"], "approval_status"), "Approved")
