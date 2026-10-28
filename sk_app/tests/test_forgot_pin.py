"""SK 28-Oct: forgot PIN / password. The person asks (login page by mobile, or lock screen), only the CEO approves, a new
temporary PIN is given and must be changed at the next login; the request never tells whether a number has a login."""

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from sk_app import logins
from sk_app.tests.test_change_list_a import _app_user

STAFF = "sk_test_fp_staff@example.com"
CEO = "sk_test_fp_ceo@example.com"
MOBILE = "9876500011"


class TestForgotPin(IntegrationTestCase):
	def setUp(self):
		_app_user(STAFF, "Stores", ["Stock User"])
		_app_user(CEO, "Management", ["Sales Manager"])
		frappe.db.set_value("User", STAFF, "mobile_no", MOBILE)
		frappe.db.delete("ToDo", {"reference_type": "User", "reference_name": STAFF})

	def _open(self):
		return frappe.get_all("ToDo", filters={"reference_type": "User", "reference_name": STAFF, "status": "Open",
			"description": ["like", f"{logins.PIN_TAG}%"]}, pluck="name")

	def test_request_once_and_same_answer_for_unknown_number(self):
		with patch("sk_app.logins._ceos", return_value=[CEO]):
			self.assertEqual(logins.forgot_pin(MOBILE), {"sent": True})
			self.assertEqual(logins.forgot_pin(MOBILE), {"sent": True})
			self.assertEqual(logins.forgot_pin("9000000000"), {"sent": True})
		self.assertEqual(len(self._open()), 1)

	def test_only_ceo_approves_and_pin_must_be_changed(self):
		with patch("sk_app.logins._ceos", return_value=[CEO]):
			logins.ask_new_pin(STAFF, "lock screen")
		todo = self._open()[0]
		with self.assertRaises(frappe.PermissionError):
			logins.pin_request_done(STAFF, todo, 1)
		out = logins.pin_request_done(CEO, todo, 1)
		self.assertTrue(out["pin"])
		self.assertEqual(frappe.db.get_value("SK App User", {"user": STAFF}, "must_set_pin"), 1)
		self.assertFalse(self._open())

	def test_reject_closes_without_new_pin(self):
		with patch("sk_app.logins._ceos", return_value=[CEO]):
			logins.ask_new_pin(STAFF)
		out = logins.pin_request_done(CEO, self._open()[0], 0)
		self.assertNotIn("pin", out)
		self.assertFalse(self._open())
