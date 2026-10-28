"""Change list point 20: face / finger unlock (WebAuthn), PIN only until set up, CEO-only reset."""

import base64
import hashlib
import json
import struct
from unittest.mock import patch

import frappe
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from frappe.tests import IntegrationTestCase
from frappe.utils.password import update_password

from sk_app import applock
from sk_app.tests.test_change_list_a import _app_user

PERSON = "sk_test_lock_person@example.com"
CEO = "sk_test_lock_ceo@example.com"
HR = "sk_test_lock_hr@example.com"


def _enc(v) -> bytes:
	"""Tiny CBOR writer, only for building the phone's answer in the test."""
	def head(major, n):
		if n < 24:
			return bytes([major << 5 | n])
		for info, size in ((24, 1), (25, 2), (26, 4)):
			if n < 1 << (8 * size):
				return bytes([major << 5 | info]) + n.to_bytes(size, "big")
	if isinstance(v, bool):
		return bytes([0xF5 if v else 0xF4])
	if isinstance(v, int):
		return head(0, v) if v >= 0 else head(1, -1 - v)
	if isinstance(v, bytes):
		return head(2, len(v)) + v
	if isinstance(v, str):
		return head(3, len(v.encode())) + v.encode()
	if isinstance(v, dict):
		return head(5, len(v)) + b"".join(_enc(k) + _enc(x) for k, x in v.items())
	raise TypeError(v)


def b64(b: bytes) -> str:
	return base64.urlsafe_b64encode(b).decode().rstrip("=")


class Phone:
	"""A pretend phone with a fingerprint key in its secure chip."""

	def __init__(self):
		self.key = ec.generate_private_key(ec.SECP256R1())
		self.cid = b"sk-test-cred-" + hashlib.sha256(str(id(self)).encode()).digest()[:8]
		self.count = 0

	def _client(self, kind, challenge):
		return json.dumps({"type": kind, "challenge": challenge, "origin": f"https://{applock._rp_id()}"}).encode()

	def _auth(self, extra=b""):
		self.count += 1
		flags = 0x01 | 0x04 | (0x40 if extra else 0)
		return hashlib.sha256(applock._rp_id().encode()).digest() + bytes([flags]) + struct.pack(">I", self.count) + extra

	def create(self, o):
		n = self.key.public_key().public_numbers()
		cose = _enc({1: 2, 3: -7, -1: 1, -2: n.x.to_bytes(32, "big"), -3: n.y.to_bytes(32, "big")})
		auth = self._auth(b"\0" * 16 + struct.pack(">H", len(self.cid)) + self.cid + cose)
		return {"id": b64(self.cid), "rawId": b64(self.cid), "type": "public-key", "response": {
			"clientDataJSON": b64(self._client("webauthn.create", o["challenge"])),
			"attestationObject": b64(_enc({"fmt": "none", "attStmt": {}, "authData": auth}))}}

	def get(self, o, tamper=False):
		client = self._client("webauthn.get", o["challenge"])
		auth = self._auth()
		sig = self.key.sign(auth + hashlib.sha256(client).digest(), ec.ECDSA(hashes.SHA256()))
		if tamper:
			auth = auth[:-1] + bytes([auth[-1] ^ 1])
		return {"id": b64(self.cid), "rawId": b64(self.cid), "type": "public-key", "response": {
			"clientDataJSON": b64(client), "authenticatorData": b64(auth), "signature": b64(sig)}}


class TestAppLock(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		_app_user(PERSON, "Sales", ["Sales User"])
		_app_user(CEO, "Management", ["System Manager"])
		_app_user(HR, "HR", ["HR Manager"])
		update_password(PERSON, "4321")

	def setUp(self):
		frappe.db.delete("SK App Unlock Key", {"user": PERSON})

	def test_pin_until_face_set_up_then_face_only(self):
		self.assertTrue(applock.status(PERSON)["pin_ok"])
		self.assertRaises(frappe.ValidationError, applock.unlock_pin, PERSON, "0000")
		self.assertTrue(frappe.db.exists("SK App Lock Log", {"user": PERSON, "event": "Wrong PIN"}))
		applock.unlock_pin(PERSON, "4321")

		phone = Phone()
		st = applock.register(PERSON, phone.create(applock.options(PERSON, "setup")), "Test Android")
		self.assertTrue(st["has_key"])
		# SK 28-Oct (Rev 1 point 21, Swati "No passkeys available"): the PIN still opens when the phone loses its key
		self.assertTrue(st["pin_ok"])
		applock.unlock_pin(PERSON, "4321")
		applock.verify(PERSON, phone.get(applock.options(PERSON, "unlock")))
		self.assertTrue(frappe.db.exists("SK App Lock Log", {"user": PERSON, "event": "Unlock face / finger"}))
		# a changed answer, an old challenge or another phone never opens it
		self.assertRaises(frappe.ValidationError, applock.verify, PERSON, phone.get(applock.options(PERSON, "unlock"), tamper=True))
		old = applock.options(PERSON, "unlock")
		applock.verify(PERSON, phone.get(old))
		self.assertRaises(frappe.ValidationError, applock.verify, PERSON, phone.get(old))
		self.assertRaises(frappe.ValidationError, applock.verify, PERSON, Phone().get(applock.options(PERSON, "unlock")))

	def test_only_ceo_resets_face(self):
		phone = Phone()
		applock.register(PERSON, phone.create(applock.options(PERSON, "setup")))
		self.assertRaises(frappe.PermissionError, applock.reset, HR, PERSON)
		self.assertEqual(applock.reset(CEO, PERSON)["reset"], 1)
		self.assertTrue(applock.status(PERSON)["pin_ok"])
		self.assertTrue(frappe.db.exists("SK App Lock Log", {"user": PERSON, "event": "Reset by CEO", "by_user": CEO}))

	def test_locks_after_the_lock_time(self):
		with patch.object(applock, "applies", return_value=True), patch.object(applock, "_sid", return_value="sk-test-sid"):
			frappe.cache.delete_value(applock._key())
			self.assertTrue(applock.is_locked())
			self.assertRaises(frappe.PermissionError, applock.check)
			applock._unlock(PERSON, "Unlock PIN")
			self.assertFalse(applock.is_locked())
			frappe.cache.set_value(applock._key(), {"until": 1, "at": 1})
			self.assertTrue(applock.is_locked())
			applock.lock(PERSON)
			self.assertTrue(applock.is_locked())
