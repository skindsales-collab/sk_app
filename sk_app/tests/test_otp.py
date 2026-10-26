import re
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests import IntegrationTestCase

from sk_app import logins, otp

MOBILE = "9876500061"


class TestOtp(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		u = frappe.db.get_value("User", {"mobile_no": MOBILE})
		cls.user = u or logins.make_login("Administrator", MOBILE, ["Sales"], full_name="OTP Test")["user"]

	def setUp(self):
		for k in (f"sk_otp:{MOBILE}", f"sk_otp_sends:{MOBILE}"):
			frappe.cache.delete_value(k)

	def test_off_until_sms_gateway_is_set(self):
		frappe.db.set_single_value("SMS Settings", "sms_gateway_url", "")
		self.assertFalse(otp.status()["otp"])
		self.assertRaises(frappe.ValidationError, otp.send, MOBILE)

	def test_send_and_login(self):
		frappe.db.set_single_value("SMS Settings", "sms_gateway_url", "https://sms.example.com/send")
		sent = []
		with patch("frappe.core.doctype.sms_settings.sms_settings._send_sms", lambda to, msg, **kw: sent.append((to, msg))):
			self.assertTrue(otp.send("+91 98765 00061")["sent"])
			otp.send("9876500099")  # no login: same answer, nothing sent
		self.assertEqual(len(sent), 1)
		self.assertEqual(sent[0][0], [MOBILE])
		code = re.search(r"\d{6}", sent[0][1]).group()
		frappe.local.login_manager = MagicMock()
		wrong = "000000" if code != "000000" else "111111"
		self.assertRaises(frappe.AuthenticationError, otp.verify, MOBILE, wrong)
		self.assertTrue(otp.verify(MOBILE, code)["ok"])
		frappe.local.login_manager.login_as.assert_called_once_with(self.user)
		# used once only
		self.assertRaises(frappe.AuthenticationError, otp.verify, MOBILE, code)

	def test_five_wrong_tries_kill_the_otp(self):
		frappe.db.set_single_value("SMS Settings", "sms_gateway_url", "https://sms.example.com/send")
		sent = []
		with patch("frappe.core.doctype.sms_settings.sms_settings._send_sms", lambda to, msg, **kw: sent.append(msg)):
			otp.send(MOBILE)
		code = re.search(r"\d{6}", sent[0]).group()
		wrong = "000000" if code != "000000" else "111111"
		for _ in range(otp.MAX_TRIES):
			self.assertRaises(frappe.AuthenticationError, otp.verify, MOBILE, wrong)
		frappe.local.login_manager = MagicMock()
		self.assertRaises(frappe.AuthenticationError, otp.verify, MOBILE, code)

	def tearDown(self):
		frappe.db.set_single_value("SMS Settings", "sms_gateway_url", "")
