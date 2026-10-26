import frappe
from frappe.tests import IntegrationTestCase
from frappe.tests.classes.context_managers import set_user
from frappe.utils.password import check_password

from sk_app import api, logins
from sk_app.functions import function_list, sections_for
from sk_app.tests.test_sk_app_api import make_user

HR = "sk_test_hr@example.com"
CLERK = "sk_test_clerk@example.com"
MOBILE = "9876500011"


class TestLogins(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		logins.setup_site()
		for email, roles in ((HR, ["HR Manager", "Employee"]), (CLERK, ["Sales User", "Employee"])):
			make_user(email, roles)
			if not frappe.db.exists("SK App User", email):
				frappe.get_doc({"doctype": "SK App User", "user": email, "home": "HR" if email == HR else "Sales"}).insert()
		if not frappe.db.exists("Workstation", "SK Test Fabrication"):
			frappe.get_doc({"doctype": "Workstation", "workstation_name": "SK Test Fabrication"}).insert()

	def setUp(self):
		for u in frappe.get_all("User", filters={"mobile_no": ["in", [MOBILE, "9876500012"]]}, pluck="name"):
			frappe.db.delete("SK App User", {"user": u})
			frappe.delete_doc("User", u, force=True, ignore_permissions=True)

	def test_clean_mobile(self):
		for typed in ("+91 98765 00011", "098765-00011", "9876500011"):
			self.assertEqual(logins.clean_mobile(typed), MOBILE)
		for bad in ("12345", "5876500011", ""):
			self.assertRaises(frappe.ValidationError, logins.clean_mobile, bad)

	def test_sections_put_both_functions_on_one_home(self):
		self.assertEqual(function_list({"home": "Sales", "functions": [{"function": "Purchase"}, {"function": "Sales"}, {"function": "Nope"}]}),
			["Sales", "Purchase"])
		s = sections_for(["Sales", "Purchase"])
		self.assertEqual([x["function"] for x in s["sections"]], ["Sales", "Purchase"])
		self.assertIn("my_leads", s["sections"][0]["tiles"])
		self.assertEqual(s["shared"][0], "my_day")
		self.assertEqual(s["shared"][-1], "day_report")
		own = [t for x in s["sections"] for t in x["tiles"]]
		self.assertFalse(set(own) & set(s["shared"]))
		self.assertEqual(len(own), len(set(own)))

	def test_hr_makes_login_from_mobile_and_person_sets_pin(self):
		with set_user(HR):
			r = api.hr_make_login("+91 98765 00011", '["Sales", "Purchase"]', full_name="Test Worker", language="Marathi")
		self.assertEqual(r["user"], f"{MOBILE}@{logins.HIDDEN_DOMAIN}")
		self.assertEqual(len(r["pin"]), 6)
		self.assertEqual(frappe.db.get_value("User", r["user"], "mobile_no"), MOBILE)
		check_password(r["user"], r["pin"])
		roles = set(frappe.get_roles(r["user"]))
		self.assertTrue({"Sales User", "Purchase User"} <= roles)
		with set_user(r["user"]):
			h = api.home()
			self.assertTrue(h["must_set_pin"])
			self.assertEqual(h["functions"], ["Sales", "Purchase"])
			self.assertEqual(len(h["sections"]["sections"]), 2)
			api.set_pin(r["pin"], "4321")
			self.assertFalse(api.home()["must_set_pin"])
		check_password(r["user"], "4321")
		self.assertRaises(frappe.AuthenticationError, check_password, r["user"], r["pin"])

	def test_same_mobile_twice_is_blocked(self):
		with set_user(HR):
			api.hr_make_login(MOBILE, ["Sales"], full_name="First")
			self.assertRaises(frappe.ValidationError, logins.make_login, HR, MOBILE, ["Sales"], None, "Second")

	def test_subcontractor_needs_workstation_and_gets_no_employee_role(self):
		with set_user(HR):
			self.assertRaises(frappe.ValidationError, api.hr_make_login, "9876500012", ["Subcontractor"], full_name="Ranjit T")
			r = api.hr_make_login("9876500012", ["Subcontractor"], full_name="Ranjit T", workstation="SK Test Fabrication")
		roles = set(frappe.get_roles(r["user"]))
		self.assertIn("SK Subcontractor", roles)
		self.assertNotIn("Employee", roles)
		self.assertEqual(frappe.db.get_value("SK App User", {"user": r["user"]}, "workstation"), "SK Test Fabrication")

	def test_only_hr_makes_logins_and_hr_cannot_give_admin(self):
		with set_user(CLERK):
			self.assertRaises(frappe.PermissionError, api.hr_people)
			self.assertRaises(frappe.PermissionError, api.hr_make_login, MOBILE, ["Sales"], None, "X")
		if logins.ADMIN_FUNCTIONS:
			with set_user(HR):
				self.assertRaises(frappe.PermissionError, api.hr_make_login, MOBILE, [next(iter(logins.ADMIN_FUNCTIONS))], None, "X")

	def test_reset_and_close(self):
		with set_user(HR):
			r = api.hr_make_login(MOBILE, ["Sales"], full_name="Leaver")
			again = api.hr_reset_pin(r["user"])
			self.assertNotEqual(again["pin"], "")
			check_password(r["user"], again["pin"])
			people = {p["user"]: p for p in api.hr_people() if p["user"]}
			self.assertEqual(people[r["user"]]["state"], "active")
			api.hr_close_login(r["user"])
			people = {p["user"]: p for p in api.hr_people() if p["user"]}
			self.assertEqual(people[r["user"]]["state"], "closed")
		self.assertEqual(frappe.db.get_value("User", r["user"], "enabled"), 0)

	def test_login_with_mobile_number(self):
		with set_user(HR):
			r = api.hr_make_login(MOBILE, ["Sales"], full_name="Phone Login")
		self.assertTrue(frappe.db.get_single_value("System Settings", "allow_login_using_mobile_number"))
		from frappe.core.doctype.user.user import User

		found = User.find_by_credentials(MOBILE, r["pin"])
		self.assertEqual(found["name"], r["user"])
		self.assertTrue(found["is_authenticated"])
		self.assertFalse(User.find_by_credentials(MOBILE, "000000")["is_authenticated"])
