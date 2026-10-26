"""Change list point 5: customer complaints from the Sales app."""

import frappe
from frappe.tests import IntegrationTestCase

from sk_app import complaints
from sk_app.tests.test_change_list_a import _app_user
from sk_app.tests.test_segments import _customer

SELLER = "sk_test_c_seller@example.com"
STORE = "sk_test_c_store@example.com"
OTHER = "sk_test_c_other@example.com"


class TestComplaints(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		complaints.ensure_setup()
		_app_user(SELLER, "Sales", ["Sales User"])
		_app_user(STORE, "Stores", ["Stock User"])
		_app_user(OTHER, "Sales", ["Sales User"])
		frappe.db.delete("SK App User", {"home": "Stores", "user": ["!=", STORE]})

	def test_register_fix_and_customer_ok(self):
		cust = _customer("SK Test Complaint Co", "LGSF")
		r = complaints.register(SELLER, cust, "Two wall panels damaged in transit", "Item missing / short / damaged in transit")
		self.assertEqual(r["function"], "Stores")
		issue = frappe.get_doc("Issue", r["name"])
		self.assertEqual((issue.sk_stage, issue.sk_concerned_user, issue.sk_segment), ("Registered", STORE, "LGSF"))
		self.assertTrue(frappe.db.exists("ToDo", {"reference_name": issue.name, "allocated_to": STORE, "status": "Open"}))
		self.assertEqual(complaints.badge(STORE)["complaints"]["c"], "red")
		self.assertIn(issue.name, [x["name"] for x in complaints.listing(STORE, "to_fix")["rows"]])
		self.assertIn(issue.name, [x["name"] for x in complaints.listing(SELLER)["rows"]])
		self.assertRaises(frappe.PermissionError, complaints.detail, OTHER, issue.name)
		complaints.accept(STORE, issue.name)
		complaints.fixed(STORE, issue.name, "Sent two new panels")
		self.assertEqual(frappe.db.get_value("Issue", issue.name, "sk_stage"), "Fixed")
		complaints.customer_answer(SELLER, issue.name, 0, "Still one panel bent")
		self.assertEqual(frappe.db.get_value("Issue", issue.name, "sk_stage"), "Not OK")
		complaints.fixed(STORE, issue.name, "Replaced the bent panel")
		complaints.customer_answer(SELLER, issue.name, 1)
		d = complaints.detail(SELLER, issue.name)
		self.assertEqual((d["sk_stage"], d["status"], d["sk_customer_ok"]), ("Closed", "Closed", "Yes"))
		self.assertTrue(len(d["steps"]) >= 4)

	def test_factory_fault_makes_a_non_conformance(self):
		if not frappe.db.exists("DocType", "Non Conformance"):
			self.skipTest("Quality module not installed")
		cust = _customer("SK Test Complaint Co", "LGSF")
		r = complaints.register(SELLER, cust, "Roof leaking near AC point", "Leakage / roof / door / window / glass")
		nc = frappe.db.get_value("Issue", r["name"], "sk_non_conformance")
		self.assertTrue(nc)
		complaints.on_nc_resolved(nc, STORE, "Sealed the AC point")
		self.assertEqual(frappe.db.get_value("Issue", r["name"], "sk_stage"), "Fixed")
		self.assertRaises(frappe.ValidationError, complaints.register, SELLER, cust, "x", "Not a type")
