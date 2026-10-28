"""SK 28-Oct review list Rev 1, points 17-18: SK Phone links with mobile + PIN, gets its own token, personal phones get
only hashes of CRM numbers; a wrong PIN or an unlinked phone gets nothing."""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils.password import update_password

from sk_app import crm, phone_sync
from sk_app.tests.test_change_list_a import _app_user

REP, CEO = "sk_test_phone_rep@example.com", "sk_test_phone_ceo@example.com"
MOBILE = "9876501234"


class TestPhoneSync(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		phone_sync.ensure_setup()
		_app_user(REP, "Sales", ["Sales User"])
		_app_user(CEO, "Management", ["System Manager"])
		frappe.db.set_value("User", REP, "mobile_no", MOBILE)
		update_password(REP, "2468")

	def test_link_token_numbers_and_unlink(self):
		self.assertRaises(frappe.AuthenticationError, phone_sync.link, MOBILE, "0000")
		r = phone_sync.link("+91 98765 01234", "2468", "Test Android", "personal")
		self.assertEqual(r["mode"], "personal")
		self.assertNotIn(r["token"], frappe.db.get_value("SK App User", {"user": REP}, phone_sync.FIELD))  # only its hash is kept
		self.assertEqual(phone_sync._user_of(r["token"])[0], REP)
		contact = frappe.get_doc({"doctype": "Contact", "first_name": "Phone Test Buyer"})
		contact.append("phone_nos", {"phone": "+91 99887 76655", "is_primary_mobile_no": 1})
		contact.insert(ignore_permissions=True)
		self.assertIn(phone_sync._hash("9988776655"), phone_sync.numbers(r["token"])["hashes"])
		self.assertEqual(phone_sync.phones(REP)[0]["device"], "Test Android")
		self.assertRaises(frappe.PermissionError, phone_sync.unlink, REP, REP)
		phone_sync.unlink(CEO, REP)
		self.assertRaises(frappe.AuthenticationError, phone_sync.numbers, r["token"])

	def test_calls_saved_for_crm_only_on_personal_phone(self):
		if not crm.installed():
			self.skipTest("Frappe CRM not installed")
		r = phone_sync.link(MOBILE, "2468", "Personal", "personal")
		out = phone_sync.upload(r["token"], [{"id": 1, "number": "9000000001", "type": "out", "start": 1761600000000, "duration": 30}])
		self.assertEqual((out["saved"], out["skipped"]), (0, 1))
