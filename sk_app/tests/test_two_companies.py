"""SK 28-Oct review list Rev 1 point 5: SK Ind Tech and SK Enterprises: each person's entries go to their company, every
dashboard shows one company or both."""

import frappe
from frappe.tests import IntegrationTestCase

from sk_app import dashboards, logins, store
from sk_app.tests.test_change_list_a import _app_user

PERSON = "sk_test_co_person@example.com"


class TestTwoCompanies(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		_app_user(PERSON, "Sales", ["Sales User"])
		cls.company = frappe.db.get_value("Company", {}, "name")

	def test_person_company_default_and_dashboard_filter(self):
		app = frappe.get_doc("SK App User", {"user": PERSON})
		app.company = self.company
		app.save(ignore_permissions=True)
		self.assertEqual(frappe.defaults.get_user_default("Company", PERSON), self.company)
		frappe.flags.sk_company = "Some Other Co"
		try:
			self.assertEqual(store._company(), "Some Other Co")
			self.assertEqual(dashboards._seg_filter("Cabin")["company"], "Some Other Co")
			self.assertNotIn("company", dashboards._seg_filter("Cabin", company=False))
			self.assertEqual(dashboards.companies(), ["Some Other Co"])
		finally:
			frappe.flags.sk_company = None
		self.assertIn(self.company, dashboards.companies())
		d = dashboards.page("Administrator", "overview", company=self.company)
		self.assertEqual(d["company"], self.company)
		self.assertIsNone(frappe.flags.get("sk_company"))
		self.assertEqual(dashboards.page("Administrator", "overview", company="Not A Company")["company"], "")
		self.assertIn("company", logins.people("Administrator")[0])
