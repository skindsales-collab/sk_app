"""SK Phone, the free Android helper (SK 28-Oct-2026 review list Rev 1, points 17 and 18, approved).

A web app cannot read the phone's call list, so a small Android app ("SK Phone", installed from a file, not the Play
Store) sends the calls to ERPNext as CRM Call Logs, matched to the lead or deal, counted for the person's login.

- Linked once with the person's mobile + PIN; the phone gets its own token (only its hash is kept here). The CEO can
  unlink a phone (Logins → unlink SK Phone).
- Company phone: every incoming / outgoing / missed call is sent; calls of numbers not in CRM are counted too.
- Personal phone: the phone first downloads the hashes of the CRM numbers and sends only calls with those numbers;
  personal calls never leave the phone. The server checks again and drops any number not in CRM.
- No call recording, no contacts, no WhatsApp (WhatsApp stays the daily chat export; mail is already synced).
"""

import hashlib
import json
import re
import secrets
from datetime import datetime, timezone

import frappe
from frappe import _
from frappe.utils import add_to_date, cint, convert_utc_to_system_timezone, now_datetime

from sk_app import crm

FIELD = "sk_phone_devices"
MODES = ("company", "personal")
MAX_CALLS = 500


def ensure_setup():
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	create_custom_fields({"SK App User": [{"fieldname": FIELD, "label": "SK Phone devices", "fieldtype": "Small Text", "hidden": 1,
		"read_only": 1, "insert_after": "enabled", "description": "Phones linked to the SK Phone helper (token hashes only)"}]}, update=True)


def _hash(text: str) -> str:
	return hashlib.sha256(text.encode()).hexdigest()


def digits10(number: str | None) -> str:
	d = re.sub(r"\D", "", str(number or ""))
	return d[-10:] if len(d) >= 10 else ""


def _devices(user: str) -> list[dict]:
	raw = frappe.db.get_value("SK App User", {"user": user}, FIELD)
	try:
		return json.loads(raw) if raw else []
	except ValueError:
		return []


def _save_devices(user: str, devices: list[dict]):
	frappe.db.set_value("SK App User", {"user": user}, FIELD, json.dumps(devices, separators=(",", ":")), update_modified=False)


def link(mobile: str, pin: str, device: str | None = None, mode: str = "company") -> dict:
	"""The phone logs in once with mobile + PIN and gets its own token."""
	from frappe.utils.password import check_password

	from sk_app.logins import clean_mobile
	from sk_app.otp import _user_for

	wrong = _("Mobile number or PIN is wrong")
	try:
		user = _user_for(clean_mobile(mobile))
	except frappe.ValidationError:
		user = None
	if not user or not frappe.db.exists("SK App User", {"user": user, "enabled": 1}):
		frappe.throw(wrong, frappe.AuthenticationError)
	try:
		check_password(user, pin)
	except frappe.AuthenticationError:
		frappe.throw(wrong, frappe.AuthenticationError)
	token = secrets.token_urlsafe(32)
	mode = mode if mode in MODES else "company"
	devices = [d for d in _devices(user) if d.get("device") != (device or "")][:4]
	devices.append({"hash": _hash(token), "device": (device or "")[:80], "mode": mode, "linked": str(now_datetime())[:16], "last": None})
	_save_devices(user, devices)
	return {"token": token, "name": frappe.utils.get_fullname(user), "mode": mode}


def _user_of(token: str) -> tuple[str, dict]:
	h = _hash(str(token or ""))
	for r in frappe.get_all("SK App User", filters={"enabled": 1, FIELD: ["like", f"%{h}%"]}, fields=["user", FIELD]):
		for d in json.loads(r.get(FIELD) or "[]"):
			if secrets.compare_digest(d.get("hash") or "", h):
				return r.user, d
	frappe.throw(_("This phone is not linked any more. Open SK Phone and link it again."), frappe.AuthenticationError)


def crm_numbers() -> dict:
	"""{last 10 digits: (doctype, name)} of every lead, deal and customer contact number; newest record wins."""
	out = {}
	for doctype, fields in (("Contact", ["mobile_no", "phone"]), ("CRM Lead", ["mobile_no", "phone"]), ("CRM Deal", ["mobile_no", "phone"])):
		if not frappe.db.exists("DocType", doctype):
			continue
		meta = frappe.get_meta(doctype)
		have = [f for f in fields if meta.has_field(f)]
		filters = {"converted": 0} if doctype == "CRM Lead" and meta.has_field("converted") else {}
		for r in frappe.get_all(doctype, filters=filters, fields=["name", *have], order_by="modified asc", limit=0):
			for f in have:
				d = digits10(r.get(f))
				if d:
					out[d] = (doctype, r.name)
	if frappe.db.exists("DocType", "Contact Phone"):
		for r in frappe.get_all("Contact Phone", filters={"parenttype": "Contact"}, fields=["parent", "phone"], limit=0):
			d = digits10(r.phone)
			if d and d not in out:
				out[d] = ("Contact", r.parent)
	return out


def numbers(token: str) -> dict:
	"""Personal phones: hashes of the CRM numbers, so the phone sends only business calls."""
	_user_of(token)
	return {"hashes": sorted({_hash(d) for d in crm_numbers()})}


def _reference(doctype: str, name: str) -> tuple[str | None, str | None]:
	"""A Contact of a customer is logged on its open deal (CRM Call Log belongs to a lead or deal)."""
	if doctype in crm.CRM_DOCTYPES:
		return doctype, name
	org = frappe.db.get_value("Contact", name, "company_name")
	deal = frappe.db.get_value("CRM Deal", {"organization": org}, "name", order_by="modified desc") \
		if org and frappe.db.exists("DocType", "CRM Deal") else None
	return ("CRM Deal", deal) if deal else (None, None)


def _from_epoch(ms) -> datetime:
	"""The phone's call time (epoch milliseconds, UTC) in the site's time zone, as ERPNext keeps times."""
	if not cint(ms):
		return now_datetime()
	return convert_utc_to_system_timezone(datetime.fromtimestamp(cint(ms) / 1000, tz=timezone.utc)).replace(tzinfo=None)


def upload(token: str, calls) -> dict:
	"""Calls from the phone: [{id, number, type: in / out / missed, start: epoch ms, duration: seconds}]."""
	user, device = _user_of(token)
	if not crm.installed():
		frappe.throw(_("Frappe CRM is not installed"))
	calls = json.loads(calls) if isinstance(calls, str) else (calls or [])
	known = crm_numbers()
	saved = skipped = 0
	me = digits10(frappe.db.get_value("User", user, "mobile_no")) or user
	for c in calls[:MAX_CALLS]:
		number = digits10(c.get("number"))
		kind = c.get("type")
		if not number or kind not in ("in", "out", "missed"):
			skipped += 1
			continue
		ref = known.get(number)
		if device.get("mode") == "personal" and not ref:
			skipped += 1  # a personal call: never stored
			continue
		call_id = f"skp-{_hash(user)[:8]}-{cint(c.get('id'))}-{cint(c.get('start'))}"[:140]
		if frappe.db.exists("CRM Call Log", {"id": call_id}):
			continue
		seconds = max(0, cint(c.get("duration")))
		start = _from_epoch(c.get("start"))
		doctype, name = _reference(*ref) if ref else (None, None)
		direction = "Outgoing" if kind == "out" else "Incoming"
		status = "Completed" if seconds else "No Answer"
		log = frappe.get_doc({"doctype": "CRM Call Log", "id": call_id, "type": direction, "status": status,
			"from": me if direction == "Outgoing" else number, "to": number if direction == "Outgoing" else me,
			"telephony_medium": "Manual", "start_time": start, "end_time": add_to_date(start, seconds=seconds), "duration": seconds,
			"reference_doctype": doctype, "reference_docname": name})
		log.set("caller" if direction == "Outgoing" else "receiver", user)
		log.flags.ignore_permissions = True
		log.insert()
		saved += 1
	devices = _devices(user)
	for d in devices:
		if d.get("hash") == device.get("hash"):
			d["last"] = str(now_datetime())[:16]
	_save_devices(user, devices)
	return {"saved": saved, "skipped": skipped}


def unlink(by: str, user: str) -> dict:
	"""CEO / HR: a phone lost or changed hands."""
	from sk_app.logins import _check_manager

	_check_manager(by)
	n = len(_devices(user))
	_save_devices(user, [])
	return {"user": user, "unlinked": n}


def phones(user: str) -> list[dict]:
	return [{k: d.get(k) for k in ("device", "mode", "linked", "last")} for d in _devices(user)]
