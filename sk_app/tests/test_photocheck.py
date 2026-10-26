"""Change list point 1: check before saving."""

import frappe
from frappe.tests import IntegrationTestCase

from sk_app import photocheck

USER = "sk_test_p_user@example.com"


class TestPhotoCheck(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		from sk_app.tests.test_sk_app_api import make_user

		make_user(USER, ["Purchase User"])

	def test_checks_and_learning(self):
		rows = {r["field"]: r for r in photocheck.check(USER, "lead", {"first_name": "", "mobile_no": "98220 4123", "email": "x@y"})["rows"]}
		self.assertEqual(rows["first_name"]["state"], "red")
		self.assertEqual(rows["mobile_no"]["state"], "red")
		self.assertEqual(rows["email"]["state"], "red")
		self.assertEqual(rows["sk_segment"]["state"], "red")
		g = photocheck.check_gstin("27ABCDE1234F1Z5")
		self.assertEqual(g["state"], "green")
		self.assertIn("ABCDE1234F", g["note"])
		self.assertEqual(photocheck.check_gstin("27ABCDE1234").get("state"), "red")
		plate = photocheck.check_plate({"vehicle_no": "mh12ab1234"})[0]
		self.assertEqual((plate["state"], plate["options"]), ("amber", ["MH 12 AB 1234"]))
		self.assertEqual(photocheck.check_plate({"vehicle_no": "MH 12 AB 1234"})[0]["state"], "green")
		supplier = frappe.db.get_value("Supplier", {}, "name")
		if supplier:
			photocheck.learn(USER, "supplier", "Jay Mataji Elect.", supplier)
			bill = {r["field"]: r for r in photocheck.check(USER, "bill", {"supplier": "Jay Mataji Elect.", "bill_no": "", "amount": 0})["rows"]}
			self.assertEqual(bill["supplier"]["options"][0], supplier)
			self.assertEqual(bill["bill_no"]["state"], "red")
