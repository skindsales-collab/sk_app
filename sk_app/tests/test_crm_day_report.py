import frappe
from frappe.tests import IntegrationTestCase
from frappe.tests.classes.context_managers import set_user
from frappe.utils import add_to_date, now_datetime

from sk_app import api, day_report

REP = "sk_test_rep@example.com"
BOSS = "sk_test_boss@example.com"
STRANGER = "sk_test_stranger@example.com"


def make_user(email, roles):
	if not frappe.db.exists("User", email):
		frappe.get_doc({"doctype": "User", "email": email, "first_name": email.split("@")[0], "send_welcome_email": 0,
			"roles": [{"role": r} for r in roles]}).insert(ignore_permissions=True)
	return email


def app_user(email, home, manager=None):
	if not frappe.db.exists("SK App User", email):
		frappe.get_doc({"doctype": "SK App User", "user": email, "home": home, "manager": manager}).insert()


class TestCrmAndDayReport(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		from sk_app.install import after_install

		after_install()
		make_user(REP, ["Sales User", "Employee"])
		make_user(BOSS, ["Sales User", "Employee"])
		make_user(STRANGER, ["Sales User", "Employee"])
		app_user(BOSS, "Sales")
		app_user(REP, "Sales", BOSS)
		app_user(STRANGER, "Sales")
		cls.crm = bool(frappe.db.exists("DocType", "CRM Lead"))

	def test_training_lessons_seeded_and_done(self):
		with set_user(REP):
			rows = api.training_lessons()
			self.assertGreaterEqual(len(rows), 7)
			api.training_done(rows[0].name)
			self.assertTrue(api.training_lessons()[0]["done"])

	def test_day_report_one_per_day_and_manager_review(self):
		with set_user(REP):
			api.add_work("Visited site at Taloja")
			name = api.send_day_report("Two site visits, one quote", problems="Need drawing", plan_tomorrow="Call ABC")
			again = api.send_day_report("Two site visits, one quote, updated")
			self.assertEqual(name, again)
			doc = frappe.get_doc("SK Day Report", name)
			self.assertEqual(doc.manager, BOSS)
			self.assertGreaterEqual(doc.work_entries, 1)
			self.assertIn("Taloja", doc.auto_summary)
			self.assertTrue(api.home()["day_report_sent"])
		with set_user(BOSS):
			team = api.team_day_reports()
			self.assertEqual(team["sent"], 1)
			self.assertIn("team_reports", api.home()["home"]["tiles"])
			api.review_day_report(name, "Good", "Well done")
		self.assertEqual(frappe.db.get_value("SK Day Report", name, "manager_rating"), "Good")
		with set_user(STRANGER):
			self.assertRaises(frappe.PermissionError, api.review_day_report, name, "OK")
			self.assertEqual(api.team_day_reports()["total"], 0)

	def test_day_report_needs_text(self):
		with set_user(REP):
			self.assertRaises(frappe.ValidationError, api.send_day_report, "  ")

	def test_reminder_only_near_work_end_and_until_sent(self):
		due = day_report.due_at()
		self.assertEqual(day_report.reminder(STRANGER, add_to_date(due, hours=-3)), [])
		self.assertEqual(len(day_report.reminder(STRANGER, add_to_date(due, minutes=-30))), 1)

	def test_crm_new_lead_follow_up_and_call_log(self):
		if not self.crm:
			self.skipTest("Frappe CRM not installed")
		with set_user(REP):
			name = api.new_lead("Ramesh", mobile_no="9876543210", organization="SK Test Cabins Ltd", segment="Cabin",
				requirement="2 site cabins 20x10")
			rows = [r for r in api.follow_up() if r["name"] == name]
			self.assertTrue(rows and rows[0]["new"])
			api.log_contact("CRM Lead", name, "Call", "Talked", "Wants quote by Monday")
			d = api.crm_detail("CRM Lead", name)
			self.assertEqual(d["doc"]["sk_segment"], "Cabin")
			self.assertEqual(len(d["calls"]), 1)
			self.assertTrue(any("Requirement" in n["title"] for n in d["notes"]))
			self.assertTrue(frappe.db.get_value("CRM Lead", name, "first_responded_on"))
			self.assertEqual(day_report.captured(REP)["calls_made"], 1)
		with set_user(STRANGER):
			self.assertRaises(frappe.PermissionError, api.crm_detail, "CRM Lead", name)

	def test_share_link_only_for_quotation_and_sales_order(self):
		with set_user(REP):
			self.assertRaises(frappe.ValidationError, api.share_link, "User", REP)
