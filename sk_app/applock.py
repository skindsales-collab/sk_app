"""App lock with face / finger (change list point 20, SK 26-Oct-2026).

"Need some password to open this app every time ... auto close after every 30 min." · "Need to login with face or
finger only; after set-up the PIN option is removed from their screen; reset only with the CEO."

The phone's own fingerprint / face lock is linked once (WebAuthn platform authenticator: Android Chrome, iPhone
Safari). Only its public key is kept in ERPNext (SK App Unlock Key); no photo or fingerprint leaves the phone. Each
ERPNext session starts locked and locks again after SK App Settings → lock minutes without use (default 30). Until
face / finger is set up the PIN unlocks; after that only face / finger does. 5 wrong PINs end the session. Only the
CEO (Management) resets face / finger. Every unlock, lock, set-up and reset is kept in SK App Lock Log.
"""

import base64
import hashlib
import json
import secrets
import struct
import time
from urllib.parse import urlparse

import frappe
from frappe import _
from frappe.utils import cint, now_datetime

LOCKED = "SK_LOCKED"
WRONG_PIN_LIMIT = 5
CHALLENGE_SECONDS = 300


# ---------- lock state (per ERPNext session, in the cache) ----------

def minutes() -> int:
	value = frappe.db.get_single_value("SK App Settings", "lock_minutes")
	return 30 if value is None else cint(value)


def _sid() -> str:
	return frappe.session.sid or ""


def _key() -> str:
	return f"sk_unlocked:{_sid()}"


def applies() -> bool:
	"""Only phone / browser calls are locked (not background jobs, tests or the API key of the AI desk)."""
	if not minutes() or frappe.session.user in ("Guest", None):
		return False
	request = getattr(frappe.local, "request", None)
	if not request or not _sid() or _sid() == "Guest":
		return False
	return not (request.headers.get("Authorization") or "").startswith(("token ", "Bearer ", "Basic "))


def _state() -> dict:
	return frappe.cache.get_value(_key()) or {}


def _save(at: float):
	period = max(minutes(), 1) * 60
	frappe.cache.set_value(_key(), {"until": time.time() + period, "at": at}, expires_in_sec=period + 60)


def is_locked() -> bool:
	if not applies():
		return False
	return float(_state().get("until") or 0) < time.time()


def touch():
	"""Every app call while open keeps it open for another lock period (locks only after that long without use).
	The app's own minute check (X-SK-Background) does not count as use."""
	if applies() and not frappe.local.request.headers.get("X-SK-Background"):
		_save(_state().get("at") or time.time())


def on_login(login_manager=None):
	"""hooks on_session_creation: logging in with mobile + PIN (or OTP) opens the app at once, no second check."""
	if minutes() and getattr(frappe.local, "request", None) and frappe.session.sid:
		_save(time.time())


def check():
	"""Called by every app endpoint (sk_app.api._me)."""
	if is_locked():
		frappe.throw(LOCKED, frappe.PermissionError, title=_("Locked"))
	touch()


def _unlock(user: str, event: str, device: str | None = None):
	frappe.cache.delete_value(f"sk_wrong_pin:{user}")
	_save(time.time())
	log(user, event, device)


def lock(user: str) -> dict:
	frappe.cache.delete_value(_key())
	log(user, "Locked")
	return {"locked": True}


def log(user: str, event: str, device: str | None = None, by: str | None = None):
	frappe.get_doc({"doctype": "SK App Lock Log", "user": user, "event": event, "device": (device or _device())[:140],
		"by_user": by}).insert(ignore_permissions=True)


def _device() -> str:
	request = getattr(frappe.local, "request", None)
	agent = (request.headers.get("User-Agent") if request else "") or ""
	for name in ("iPhone", "iPad", "Android", "Windows", "Macintosh", "Linux"):
		if name in agent:
			model = ""
			if name == "Android" and ";" in agent:
				model = agent.split("Android", 1)[1].split(")", 1)[0].split(";")[-1].strip()
			return f"{name} {model}".strip()
	return agent[:60]


def keys(user: str) -> list:
	return frappe.get_all("SK App Unlock Key", filters={"user": user, "enabled": 1},
		fields=["name", "credential_id", "public_key", "alg", "sign_count", "device", "creation"], order_by="creation asc")


def status(user: str) -> dict:
	have = keys(user)
	at = float(_state().get("at") or 0)
	return {"locked": is_locked(), "minutes": minutes(), "has_key": bool(have), "pin_ok": True,
		"just_unlocked": bool(at) and time.time() - at < 90,
		"phones": [k.device for k in have], "name": frappe.utils.get_fullname(user)}


# ---------- PIN (always works; face / finger is the quick way once set up) ----------

def unlock_pin(user: str, pin) -> dict:
	from frappe.utils.password import check_password

	# SK 28-Oct (Swati: "No passkeys available"): the phone can lose its face / finger key, so the PIN always opens too
	try:
		check_password(user, str(pin or ""))
	except frappe.AuthenticationError:
		wrong = cint(frappe.cache.get_value(f"sk_wrong_pin:{user}")) + 1
		frappe.cache.set_value(f"sk_wrong_pin:{user}", wrong, expires_in_sec=3600)
		log(user, "Wrong PIN")
		if wrong >= WRONG_PIN_LIMIT:
			frappe.cache.delete_value(f"sk_wrong_pin:{user}")
			log(user, "Logged out (wrong PINs)")
			frappe.local.login_manager.logout()
			frappe.db.commit()  # the session is gone even though this call ends with an error
			frappe.throw(_("5 wrong PINs: please log in again with your mobile number"), frappe.PermissionError)
		frappe.throw(_("Wrong PIN ({0} of {1} tries)").format(wrong, WRONG_PIN_LIMIT))
	_unlock(user, "Unlock PIN")
	return status(user)


# ---------- face / finger (WebAuthn) ----------

def _b64d(s: str) -> bytes:
	s = str(s or "")
	return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _b64e(b: bytes) -> str:
	return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _rp_id() -> str:
	request = getattr(frappe.local, "request", None)
	host = (request.host if request else "") or urlparse(frappe.utils.get_url()).netloc
	return host.split(":")[0]


def options(user: str, purpose: str) -> dict:
	"""Challenge for the phone: purpose "setup" (link face / finger) or "unlock"."""
	challenge = secrets.token_bytes(32)
	frappe.cache.set_value(f"sk_webauthn:{user}:{purpose}", _b64e(challenge), expires_in_sec=CHALLENGE_SECONDS)
	out = {"challenge": _b64e(challenge), "rpId": _rp_id(), "timeout": 60000, "userVerification": "required"}
	if purpose == "setup":
		out.update({"rp": {"id": _rp_id(), "name": "SK App"},
			"user": {"id": _b64e(hashlib.sha256(user.encode()).digest()[:16]), "name": user, "displayName": frappe.utils.get_fullname(user)},
			"pubKeyCredParams": [{"type": "public-key", "alg": -7}, {"type": "public-key", "alg": -257}],
			"authenticatorSelection": {"authenticatorAttachment": "platform", "userVerification": "required", "residentKey": "discouraged"},
			"attestation": "none", "excludeCredentials": [{"type": "public-key", "id": k.credential_id} for k in keys(user)]})
	else:
		have = keys(user)
		if not have:
			frappe.throw(_("Face / finger is not set up on this login yet"))
		out["allowCredentials"] = [{"type": "public-key", "id": k.credential_id} for k in have]
	return out


def _client_data(raw_b64: str, kind: str, user: str, purpose: str, cache_key: str | None = None) -> bytes:
	raw = _b64d(raw_b64)
	data = json.loads(raw)
	cache_key = cache_key or f"sk_webauthn:{user}:{purpose}"
	want = frappe.cache.get_value(cache_key)
	frappe.cache.delete_value(cache_key)
	if data.get("type") != kind:
		frappe.throw(_("Face / finger check failed (type)"))
	if not want or not secrets.compare_digest(str(data.get("challenge") or ""), str(want)):
		frappe.throw(_("Face / finger check took too long. Please try again."))
	if (urlparse(data.get("origin") or "").hostname or "") != _rp_id():
		frappe.throw(_("Face / finger check failed (site)"))
	return raw


def _auth_data(data: bytes, need_uv=True) -> dict:
	if len(data) < 37:
		frappe.throw(_("Face / finger check failed (data)"))
	if data[:32] != hashlib.sha256(_rp_id().encode()).digest():
		frappe.throw(_("Face / finger check failed (site)"))
	flags = data[32]
	if not flags & 0x01 or (need_uv and not flags & 0x04):
		frappe.throw(_("The phone did not check your face / finger. Please try again."))
	out = {"flags": flags, "sign_count": struct.unpack(">I", data[33:37])[0]}
	if flags & 0x40:  # attested credential data (set-up only)
		cred_len = struct.unpack(">H", data[53:55])[0]
		out["credential_id"] = data[55:55 + cred_len]
		out["cose"], _end = _cbor(data, 55 + cred_len)
		out["cose_raw"] = data[55 + cred_len:_end]
	return out


def register(user: str, credential: dict | str, device: str | None = None) -> dict:
	"""Set-up: the phone made a key pair inside its secure chip; keep the public half."""
	cred = frappe.parse_json(credential) if isinstance(credential, str) else credential
	resp = cred.get("response") or {}
	_client_data(resp.get("clientDataJSON"), "webauthn.create", user, "setup")
	att, _end = _cbor(_b64d(resp.get("attestationObject")), 0)
	auth = _auth_data(att.get("authData") or b"")
	if "cose" not in auth:
		frappe.throw(_("Face / finger set-up failed (no key)"))
	alg = auth["cose"].get(3)
	if alg not in (-7, -257):
		frappe.throw(_("This phone's lock type is not supported"))
	doc = frappe.get_doc({"doctype": "SK App Unlock Key", "user": user, "device": (device or _device())[:140], "enabled": 1,
		"credential_id": _b64e(auth["credential_id"]), "public_key": _b64e(auth["cose_raw"]), "alg": alg,
		"sign_count": auth["sign_count"], "last_used": now_datetime()}).insert(ignore_permissions=True)
	log(user, "Set up face / finger", doc.device)
	_unlock(user, "Unlock face / finger", doc.device)
	return status(user)


def verify(user: str, credential: dict | str) -> dict:
	"""Unlock: the phone signed our challenge after checking the face / finger."""
	cred = frappe.parse_json(credential) if isinstance(credential, str) else credential
	cid = _b64e(_b64d(cred.get("rawId") or cred.get("id")))
	key = next((k for k in keys(user) if k.credential_id == cid), None)
	if not key:
		frappe.throw(_("This phone's face / finger is not linked to your login. Ask the CEO to reset it, then set it up again."))
	_check_signature(key, cred, user, "unlock")
	_unlock(user, "Unlock face / finger", key.device)
	return status(user)


def _check_signature(key, cred: dict, user: str, purpose: str, cache_key: str | None = None):
	resp = cred.get("response") or {}
	client = _client_data(resp.get("clientDataJSON"), "webauthn.get", user, purpose, cache_key)
	auth_raw = _b64d(resp.get("authenticatorData"))
	auth = _auth_data(auth_raw)
	signed = auth_raw + hashlib.sha256(client).digest()
	if not _signature_ok(_cbor(_b64d(key.public_key), 0)[0], _b64d(resp.get("signature")), signed):
		frappe.throw(_("Face / finger check failed. Please try again."))
	if auth["sign_count"] and key.sign_count and auth["sign_count"] <= key.sign_count:
		frappe.throw(_("This face / finger key looks copied. Ask the CEO to reset it."))
	frappe.db.set_value("SK App Unlock Key", key.name, {"sign_count": auth["sign_count"], "last_used": now_datetime()})


# ---------- log in with face / finger (SK 28-Oct, Rev 1 point 1: "Fingerprint / Face ID login") ----------
# The phone keeps which face / finger keys were linked on it; the login screen asks the phone to sign a fresh challenge
# with one of them, and the key's owner is logged in. The mobile + PIN login stays as the backup.

def login_options() -> dict:
	token = secrets.token_urlsafe(18)
	challenge = secrets.token_bytes(32)
	frappe.cache.set_value(f"sk_webauthn_login:{token}", _b64e(challenge), expires_in_sec=CHALLENGE_SECONDS)
	return {"token": token, "challenge": _b64e(challenge), "rpId": _rp_id(), "timeout": 60000, "userVerification": "required"}


def login_verify(token: str, credential: dict | str) -> str:
	cred = frappe.parse_json(credential) if isinstance(credential, str) else credential
	failed = _("Face / finger login did not work. Please log in with your PIN.")
	try:
		cid = _b64e(_b64d(cred.get("rawId") or cred.get("id") or ""))
	except Exception:
		frappe.throw(failed, frappe.AuthenticationError)
	key = frappe.db.get_value("SK App Unlock Key", {"credential_id": cid, "enabled": 1},
		["name", "user", "credential_id", "public_key", "alg", "sign_count", "device"], as_dict=True)
	if not key or not frappe.db.get_value("User", key.user, "enabled"):
		frappe.throw(failed, frappe.AuthenticationError)
	if frappe.db.exists("SK App User", {"user": key.user, "enabled": 0}):
		frappe.throw(failed, frappe.AuthenticationError)
	if not frappe.cache.get_value(f"sk_webauthn_login:{token}"):
		frappe.throw(_("Face / finger check took too long. Please try again."), frappe.AuthenticationError)
	_check_signature(key, cred, key.user, "login", f"sk_webauthn_login:{token}")
	frappe.local.login_manager.login_as(key.user)
	log(key.user, "Login face / finger", key.device)
	return key.user


def reset(by: str, user: str) -> dict:
	"""CEO only: new phone, finger not working, phone without face / finger: the person sets it up again."""
	from sk_app.logins import _check_manager

	_check_manager(by)
	n = 0
	for k in keys(user):
		frappe.db.set_value("SK App Unlock Key", k.name, "enabled", 0)
		n += 1
	log(user, "Reset by CEO", by=by)
	return {"user": user, "reset": n}


def _signature_ok(cose: dict, signature: bytes, data: bytes) -> bool:
	from cryptography.exceptions import InvalidSignature
	from cryptography.hazmat.primitives import hashes
	from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa

	try:
		if cose.get(3) == -7:
			pub = ec.EllipticCurvePublicNumbers(int.from_bytes(cose[-2], "big"), int.from_bytes(cose[-3], "big"), ec.SECP256R1()).public_key()
			pub.verify(signature, data, ec.ECDSA(hashes.SHA256()))
		elif cose.get(3) == -257:
			pub = rsa.RSAPublicNumbers(int.from_bytes(cose[-2], "big"), int.from_bytes(cose[-1], "big")).public_key()
			pub.verify(signature, data, padding.PKCS1v15(), hashes.SHA256())
		else:
			return False
		return True
	except (InvalidSignature, KeyError, ValueError, TypeError):
		return False


def _cbor(data: bytes, i: int):
	"""Small CBOR reader for WebAuthn (attestation object and COSE keys). Returns (value, next index)."""
	first = data[i]
	major, info = first >> 5, first & 0x1F
	i += 1
	if info < 24:
		n = info
	elif info in (24, 25, 26, 27):
		size = 1 << (info - 24)
		n = int.from_bytes(data[i:i + size], "big")
		i += size
	else:
		raise ValueError("unsupported CBOR")
	if major == 0:
		return n, i
	if major == 1:
		return -1 - n, i
	if major == 2:
		return bytes(data[i:i + n]), i + n
	if major == 3:
		return data[i:i + n].decode(), i + n
	if major == 4:
		out = []
		for _x in range(n):
			v, i = _cbor(data, i)
			out.append(v)
		return out, i
	if major == 5:
		out = {}
		for _x in range(n):
			k, i = _cbor(data, i)
			v, i = _cbor(data, i)
			out[k] = v
		return out, i
	if major == 7:
		return {20: False, 21: True, 22: None}.get(info), i
	raise ValueError("unsupported CBOR")
