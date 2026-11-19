"""WhatsApp Cloud API transport (Rev 1, R3): the webhook Meta calls and the send calls. Token and verify token live in
site_config (whatsapp_token, whatsapp_verify_token); the phone number id in SK App Settings. Off until SK turns
'WhatsApp bot on' after the hosting move and Meta verification. Media from candidates is saved as a private File."""

import json

import frappe
from frappe.utils import now_datetime

GRAPH = "https://graph.facebook.com/v21.0"


def on() -> bool:
	s = frappe.get_cached_doc("SK App Settings")
	return bool(s.get("whatsapp_bot_on") and s.get("whatsapp_phone_id") and frappe.conf.get("whatsapp_token"))


def verify(mode: str | None, token: str | None, challenge: str | None):
	"""GET from Meta when the webhook is set up."""
	if mode == "subscribe" and token and token == frappe.conf.get("whatsapp_verify_token"):
		frappe.local.response.update({"type": "text", "data": challenge or ""})
		return
	frappe.throw("Webhook verification failed", frappe.PermissionError)


def receive(payload: dict) -> int:
	"""POST from Meta: every text / audio / image / document message goes to the bot engine."""
	from sk_app import hiring_bot

	n = 0
	for entry in payload.get("entry") or []:
		for change in entry.get("changes") or []:
			value = change.get("value") or {}
			for m in value.get("messages") or []:
				mobile = (m.get("from") or "")[-10:]
				if not mobile:
					continue
				incoming = {"text": "", "media": None}
				kind = m.get("type")
				if kind == "text":
					incoming["text"] = (m.get("text") or {}).get("body") or ""
				elif kind == "interactive":
					i = m.get("interactive") or {}
					incoming["text"] = ((i.get("button_reply") or i.get("list_reply") or {}).get("id") or (i.get("button_reply") or i.get("list_reply") or {}).get("title") or "")
				elif kind in ("audio", "image", "document"):
					media = m.get(kind) or {}
					url, media_type = _download(media.get("id"), media.get("mime_type"), mobile)
					incoming["media"] = {"kind": kind, "url": url, "media_type": media_type}
					incoming["text"] = media.get("caption") or ""
				else:
					continue
				try:
					hiring_bot.handle(mobile, incoming, hiring_bot._send_free)
					frappe.db.commit()
					n += 1
				except Exception:
					frappe.db.rollback()
					frappe.log_error(f"SK hiring bot {mobile}")
	return n


def _headers() -> dict:
	return {"Authorization": f"Bearer {frappe.conf.get('whatsapp_token')}", "Content-Type": "application/json"}


def _download(media_id: str | None, mime: str | None, mobile: str) -> tuple[str | None, str | None]:
	"""A candidate's media: fetched from Meta and kept as a private File (resume photo / PDF, voice note, test photo)."""
	if not media_id or not on():
		return None, mime
	import requests

	try:
		meta = requests.get(f"{GRAPH}/{media_id}", headers=_headers(), timeout=30).json()
		data = requests.get(meta.get("url"), headers=_headers(), timeout=60).content
		ext = {"application/pdf": "pdf", "image/jpeg": "jpg", "image/png": "png", "audio/ogg": "ogg", "audio/mpeg": "mp3", "audio/ogg; codecs=opus": "ogg"}.get(mime or "", "bin")
		f = frappe.get_doc({"doctype": "File", "file_name": f"wa_{mobile}_{str(now_datetime())[:19].replace(':', '').replace(' ', '_')}.{ext}", "is_private": 1, "content": data}).insert(ignore_permissions=True)
		return f.file_url, mime
	except Exception:
		frappe.log_error("SK WhatsApp media download")
		return None, mime


def month_count() -> int:
	s = frappe.get_cached_doc("SK App Settings")
	month = str(frappe.utils.nowdate())[:7]
	return int(s.get("whatsapp_month_count") or 0) if s.get("whatsapp_month") == month else 0


def _count_reply():
	s = frappe.get_cached_doc("SK App Settings")
	month = str(frappe.utils.nowdate())[:7]
	n = (int(s.get("whatsapp_month_count") or 0) + 1) if s.get("whatsapp_month") == month else 1
	frappe.db.set_value("SK App Settings", None, {"whatsapp_month": month, "whatsapp_month_count": n}, update_modified=False)
	frappe.clear_document_cache("SK App Settings", "SK App Settings")


def send_text(mobile: str, text: str, applicant: str | None = None) -> bool:
	"""A free service reply (R11): only inside the candidate's 24-hour window and under 950 replies this month; never a template."""
	from sk_app import hiring_rules as R

	if not on():
		return False
	last = frappe.db.get_value("Job Applicant", applicant, "sk_last_message_on") if applicant else None
	ok, why = R.may_reply_free(frappe.utils.get_datetime(last) if last else None, now_datetime(), month_count())
	if not ok:
		frappe.log_error(f"SK WhatsApp not sent ({why}): {mobile}", "SK WhatsApp free window")
		return False
	import requests

	s = frappe.get_cached_doc("SK App Settings")
	body = {"messaging_product": "whatsapp", "to": f"91{mobile[-10:]}", "type": "text", "text": {"body": text[:4000]}}
	try:
		r = requests.post(f"{GRAPH}/{s.whatsapp_phone_id}/messages", headers=_headers(), data=json.dumps(body), timeout=30)
		if r.status_code >= 400:
			frappe.log_error(f"SK WhatsApp send {r.status_code}: {r.text[:500]}")
			return False
		_count_reply()
		return True
	except Exception:
		frappe.log_error("SK WhatsApp send")
		return False


# R11 (SK 17-Nov 'free only'): no template sending. Business-started messages (W0, W4, W5, W6, W7, W9) are never sent by
# the bot; the app shows a 'Send by WhatsApp' button that opens wa.me/<mobile>?text=<message> on the HR phone.
