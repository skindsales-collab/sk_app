"""SK 27-Oct: potential customers (not leads) on a Marketing list for festival greetings and promotions; greetings sent
one by one on WhatsApp and counted per login; the same mobile is not made twice."""

import frappe
from frappe.tests import IntegrationTestCase

from sk_app import comms, marketing_list as ml
from sk_app.tests.test_crm_day_report import app_user, make_user
from sk_app.tests.test_store_purchase import run

REP, STORE = "sk_mk_rep@example.com", "sk_mk_store@example.com"


class TestMarketingList(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		ml.ensure_setup()
		make_user(REP, ["Sales User", "Employee"])
		make_user(STORE, ["Stock User", "Employee"])
		app_user(REP, "Marketing")
		app_user(STORE, "Stores")

	def test_add_greet_and_count(self):
		r = run(REP, ml.add, "Anil Patil", "+91 98220 11223", "Patil Infra", "Pune", "anil.mk@example.com")
		self.assertFalse(r["existing"])
		self.assertEqual(frappe.db.get_value("Contact", r["name"], "owner"), REP)
		self.assertTrue(frappe.db.exists("Email Group Member", {"email_group": ml.GROUP, "email": "anil.mk@example.com"}))
		again = run(REP, ml.add, "Anil", "9822011223")
		self.assertEqual(again["name"], r["name"])
		self.assertTrue(again["existing"])
		before = run(REP, ml.people)["today"]
		g = run(REP, ml.greet, r["name"], "diwali")
		self.assertIn("Diwali", g["message"])
		self.assertIn("SK Ind Tech", g["message"])
		d = run(REP, ml.people, "patil")
		row = next(x for x in d["rows"] if x["name"] == r["name"])
		self.assertEqual(row["greetings"], 1)
		self.assertEqual(d["today"], before + 1)
		if frappe.db.exists("DocType", "CRM Call Log"):
			self.assertGreaterEqual(comms.call_totals(REP, frappe.utils.getdate())["whatsapp"], 1)
		with self.assertRaises(frappe.ValidationError):
			run(REP, ml.greet, r["name"], "promotion")

	def test_only_sales_and_marketing(self):
		with self.assertRaises(frappe.PermissionError):
			run(STORE, ml.people)
		with self.assertRaises(frappe.ValidationError):
			run(REP, ml.add, "No Number")
