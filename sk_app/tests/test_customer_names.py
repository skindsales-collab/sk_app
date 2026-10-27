"""SK 27-Oct points 14 / 19: CUS- customers renamed to their name."""

import frappe
from frappe.tests import IntegrationTestCase

from sk_app import customer_names


class TestCustomerNames(IntegrationTestCase):
	def test_rename_cus_customers(self):
		for code, name in (("CUS-SKT-91", "SK Test Rename Buyer"), ("CUS-SKT-92", "SK Test Rename Buyer"), ("CUS-SKT-93", "SK Test A/B Buyer")):
			if not frappe.db.exists("Customer", code):
				frappe.get_doc({"doctype": "Customer", "customer_name": name, "customer_type": "Company"}).insert(set_name=code, ignore_permissions=True)
		self.assertEqual(customer_names.new_name("X  Y/Z", {"X Y-Z"}), "X Y-Z - 2")
		customer_names.rename_all()
		self.assertFalse(frappe.db.exists("Customer", "CUS-SKT-91"))
		self.assertTrue(frappe.db.exists("Customer", "SK Test Rename Buyer"))
		self.assertTrue(frappe.db.exists("Customer", "SK Test Rename Buyer - 2"))
		self.assertTrue(frappe.db.exists("Customer", "SK Test A-B Buyer"))
		self.assertEqual(frappe.db.get_default(customer_names.DONE_KEY), "1")
		customer_names.ensure()
		self.assertEqual(frappe.db.get_single_value("Selling Settings", "cust_master_name"), "Customer Name")
