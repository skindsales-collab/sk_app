import frappe
from frappe.tests import IntegrationTestCase
from frappe.tests.classes.context_managers import set_user

from sk_app import api
from sk_app.functions import home_for
from sk_app.tests.test_sk_app_api import make_user

BOSS = "sk_test_rushi@example.com"
REP = "sk_test_swati@example.com"
OUT = "sk_test_outsider@example.com"


class TestTeam(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		for email, manager in ((BOSS, None), (REP, BOSS), (OUT, None)):
			make_user(email, ["Sales User"])
			if not frappe.db.exists("SK App User", {"user": email}):
				frappe.get_doc({"doctype": "SK App User", "user": email, "home": "Sales", "manager": manager}).insert(ignore_permissions=True)

	def test_manager_sees_team_with_own(self):
		self.assertIn("team_leads", home_for("Sales", has_team=True)["tiles"])
		self.assertNotIn("team_leads", home_for("Sales")["tiles"])
		with set_user(BOSS):
			d = api.team_follow_up()
			self.assertEqual([p["user"] for p in d["people"]][:1], [BOSS])
			self.assertIn(REP, [p["user"] for p in d["people"]])
			api.team_follow_up(person=REP)
			self.assertRaises(frappe.PermissionError, api.team_follow_up, person=OUT)

	def test_member_cannot_see_manager(self):
		with set_user(REP):
			self.assertRaises(frappe.PermissionError, api.team_follow_up, person=BOSS)
			self.assertEqual([p["user"] for p in api.team_follow_up()["people"]], [REP])
