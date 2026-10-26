"""Login with mobile number + SMS OTP (SK, 26-Oct-2026), next to the PIN login.

The SMS goes through ERPNext's own SMS Settings (any Indian gateway such as MSG91, with the DLT-approved OTP text).
Until a gateway is set there, the app shows only the PIN login. The OTP is kept hashed in the cache for 5 minutes,
at most 5 tries, and a number gets at most 5 OTPs an hour. The answer never says whether a number has a login.
"""

import hashlib
import secrets

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit

from sk_app.logins import clean_mobile

VALID_SECONDS = 5 * 60
MAX_TRIES = 5
MAX_SENDS_PER_HOUR = 5
# must match the OTP template approved on DLT; the site can change it with site config "sk_otp_message"
DEFAULT_MESSAGE = "{otp} is your SK App login OTP. Valid for 5 minutes. Do not share it. - SK Ind Tech"


def enabled() -> bool:
	return bool(frappe.db.get_single_value("SMS Settings", "sms_gateway_url")) or bool(frappe.get_hooks("send_sms"))


def _key(mobile: str) -> str:
	return f"sk_otp:{mobile}"


def _hash(mobile: str, otp: str) -> str:
	return hashlib.sha256(f"{mobile}:{otp}:{frappe.local.site}".encode()).hexdigest()


def _user_for(mobile: str) -> str | None:
	return frappe.db.get_value("User", {"mobile_no": mobile, "enabled": 1, "name": ["not in", ["Administrator", "Guest"]]}, "name")


@frappe.whitelist(allow_guest=True)
def status():
	return {"otp": enabled()}


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=20, seconds=60 * 60)
def send(mobile):
	if not enabled():
		frappe.throw(_("OTP is not switched on yet. Please use your PIN."))
	mobile = clean_mobile(mobile)
	sends_key = f"sk_otp_sends:{mobile}"
	sends = frappe.cache.get_value(sends_key) or 0
	if sends >= MAX_SENDS_PER_HOUR:
		frappe.throw(_("Too many OTPs. Please wait and try again, or use your PIN."))
	frappe.cache.set_value(sends_key, sends + 1, expires_in_sec=60 * 60)
	user = _user_for(mobile)
	if user:
		otp = f"{secrets.randbelow(10**6):06d}"
		frappe.cache.set_value(_key(mobile), {"hash": _hash(mobile, otp), "tries": 0}, expires_in_sec=VALID_SECONDS)
		from frappe.core.doctype.sms_settings.sms_settings import _send_sms

		message = (frappe.conf.get("sk_otp_message") or DEFAULT_MESSAGE).format(otp=otp)
		try:
			_send_sms([mobile], message, success_msg=False)
		except Exception:
			frappe.log_error("SK App OTP SMS failed")
			frappe.throw(_("SMS could not be sent. Please use your PIN."))
	# same answer whether or not the number has a login
	return {"sent": True, "valid_minutes": VALID_SECONDS // 60}


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=30, seconds=60 * 60)
def verify(mobile, otp):
	mobile = clean_mobile(mobile)
	saved = frappe.cache.get_value(_key(mobile))
	wrong = _("OTP is wrong or old. Please ask for a new OTP.")
	if not saved:
		frappe.throw(wrong, frappe.AuthenticationError)
	if saved["tries"] >= MAX_TRIES:
		frappe.cache.delete_value(_key(mobile))
		frappe.throw(wrong, frappe.AuthenticationError)
	if not secrets.compare_digest(saved["hash"], _hash(mobile, str(otp or "").strip())):
		saved["tries"] += 1
		frappe.cache.set_value(_key(mobile), saved, expires_in_sec=VALID_SECONDS)
		frappe.throw(wrong, frappe.AuthenticationError)
	frappe.cache.delete_value(_key(mobile))
	user = _user_for(mobile)
	if not user:
		frappe.throw(wrong, frappe.AuthenticationError)
	frappe.local.login_manager.login_as(user)
	return {"ok": True}
