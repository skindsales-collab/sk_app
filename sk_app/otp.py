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


# ---------- Forgot PIN: login code by email (SK 29-Oct: "if admin forgot then need to login with email", "for user" too) ----------
# Anyone whose login has a real e-mail gets a 6-digit code there; staff without an e-mail (…@staff.skind.local) still ask
# the CEO (logins.ask_new_pin). After the code, the app asks for a new PIN without the old one. The mail goes out from
# the default outgoing mailbox's own address: Hostinger refuses a "from" it does not own (ERPNext's reset mail failed so).
EMAIL_VALID_SECONDS = 10 * 60
PIN_FREE_SECONDS = 15 * 60


def has_real_email(email: str | None) -> bool:
	email = (email or "").strip().lower()
	return "@" in email and not email.endswith("@staff.skind.local") and not email.endswith("@example.com")


def _user_for_login(login: str) -> str | None:
	"""Mobile number, e-mail or user id → enabled user (never Administrator / Guest)."""
	login = (login or "").strip()
	if not login:
		return None
	skip = ["not in", ["Administrator", "Guest"]]
	if "@" not in login:
		return _user_for(clean_mobile(login))
	if login in ("Administrator", "Guest"):
		return None
	return frappe.db.get_value("User", {"name": login, "enabled": 1}, "name") \
		or frappe.db.get_value("User", {"email": login, "enabled": 1, "name": skip}, "name")


def _email_key(user: str) -> str:
	return f"sk_email_code:{user}"


def _sender() -> str | None:
	return frappe.db.get_value("Email Account", {"default_outgoing": 1, "enable_outgoing": 1}, "email_id")


def _send_code(user: str) -> None:
	email = frappe.db.get_value("User", user, "email") if user else None
	if not (user and has_real_email(email)):
		return
	sends_key = f"sk_email_sends:{user}"
	sends = frappe.cache.get_value(sends_key) or 0
	if sends >= MAX_SENDS_PER_HOUR:  # same answer as ever: never tells whether this login exists
		return
	frappe.cache.set_value(sends_key, sends + 1, expires_in_sec=60 * 60)
	code = f"{secrets.randbelow(10**6):06d}"
	frappe.cache.set_value(_email_key(user), {"hash": _hash(user, code), "tries": 0}, expires_in_sec=EMAIL_VALID_SECONDS)
	try:
		frappe.sendmail(recipients=[email], sender=_sender(), subject=_("SK App login code: {0}").format(code),
			message=_("Your SK App login code is <b>{0}</b>. It is valid for 10 minutes. After login, set a new PIN.<br>"
				"If you did not ask for it, ignore this mail.").format(code), now=True)
	except Exception:
		frappe.log_error("SK App e-mail login code failed")
		frappe.throw(_("E-mail could not be sent. Please ask the CEO for a new PIN."))


def _check_code(user: str | None, code) -> None:
	"""Right code: forgotten; the app then asks for a new PIN without the old one. Wrong: AuthenticationError."""
	wrong = _("Code is wrong or old. Please ask for a new code.")
	saved = frappe.cache.get_value(_email_key(user)) if user else None
	if not saved:
		frappe.throw(wrong, frappe.AuthenticationError)
	if saved["tries"] >= MAX_TRIES:
		frappe.cache.delete_value(_email_key(user))
		frappe.throw(wrong, frappe.AuthenticationError)
	if not secrets.compare_digest(saved["hash"], _hash(user, str(code or "").strip())):
		saved["tries"] += 1
		frappe.cache.set_value(_email_key(user), saved, expires_in_sec=EMAIL_VALID_SECONDS)
		frappe.throw(wrong, frappe.AuthenticationError)
	frappe.cache.delete_value(_email_key(user))
	frappe.cache.set_value(f"sk_pin_free:{user}", 1, expires_in_sec=PIN_FREE_SECONDS)
	if frappe.db.exists("SK App User", {"user": user}):
		frappe.db.set_value("SK App User", {"user": user}, "must_set_pin", 1)


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=10, seconds=60 * 60)
def email_code(login):
	"""Guest: send a login code to the e-mail of this mobile / e-mail. Same answer whether or not it has a login."""
	_send_code(_user_for_login(login))
	return {"sent": True, "valid_minutes": EMAIL_VALID_SECONDS // 60}


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=30, seconds=60 * 60)
def email_verify(login, code):
	user = _user_for_login(login)
	_check_code(user, code)
	frappe.local.login_manager.login_as(user)
	return {"ok": True}


# SK 29-Oct (CEO locked out on the lock screen): the same code opens the locked app for the logged-in person
def lock_email_code(user: str) -> dict:
	_send_code(user)
	return {"sent": True, "valid_minutes": EMAIL_VALID_SECONDS // 60}


def lock_email_verify(user: str, code) -> dict:
	from sk_app import applock

	try:
		_check_code(user, code)
	except frappe.AuthenticationError:
		# not an AuthenticationError to the browser: ERPNext would end the session on that
		frappe.throw(_("Code is wrong or old. Please ask for a new code."))
	applock._unlock(user, "Unlock e-mail code")
	return applock.status(user)


def pin_free(user: str) -> bool:
	return bool(frappe.cache.get_value(f"sk_pin_free:{user}"))
