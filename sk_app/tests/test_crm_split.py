"""SK 27-Oct: leads were not split salesperson-wise in ERPNext / CRM. Each salesperson sees only their own leads and
deals; the sales manager also sees the team's and unassigned ones; CEO / System Manager see all."""

import frappe
from frappe.tests import IntegrationTestCase

from sk_app import permissions
from sk_app.tests.test_crm_day_report import app_user, make_user

REP, BOSS, STRANGER = "sk_split_rep@example.com", "sk_split_mgr@example.com", "sk_split_other@example.com"


class TestCrmSplit(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		from sk_app.install import after_install

		after_install()
		for u in (REP, BOSS, STRANGER):
			make_user(u, ["Sales User", "Employee"])
		app_user(BOSS, "Sales")
		app_user(REP, "Sales", BOSS)
		app_user(STRANGER, "Sales")

	def test_rep_sees_only_own(self):
		cond = permissions.crm_lead_query(REP)
		self.assertIn(frappe.db.escape(REP), cond)
		self.assertNotIn(STRANGER, cond)
		self.assertNotIn("ifnull", cond)  # a rep does not see unassigned leads

	def test_manager_sees_team_and_unassigned(self):
		cond = permissions.crm_deal_query(BOSS)
		self.assertIn(REP, cond)
		self.assertIn("deal_owner", cond)
		self.assertIn("ifnull", cond)
		self.assertNotIn(STRANGER, cond)

	def test_admin_sees_all(self):
		self.assertEqual(permissions.crm_lead_query("Administrator"), "")

	def test_one_record(self):
		lead = frappe._dict(doctype="CRM Lead", lead_owner=STRANGER, owner=STRANGER, _assign=None)
		self.assertFalse(permissions.crm_record(lead, "read", REP))
		self.assertTrue(permissions.crm_record(lead, "read", STRANGER))
		self.assertFalse(permissions.crm_record(lead, "read", BOSS))
		lead.lead_owner = REP
		self.assertTrue(permissions.crm_record(lead, "read", BOSS))
