"""Voice note to text for the hiring bot (R5 item 13): Bhashini (Government of India) first, Google as backup; None when
no provider is set, and the bot then asks the candidate to type. Keys live in site_config, never in the app."""

import base64

import frappe

LANG = {"Marathi": "mr", "Hindi": "hi", "English": "en"}


def provider() -> str:
	return (frappe.get_cached_doc("SK App Settings").get("stt_provider") or "None") if frappe.db.exists("DocType", "SK App Settings") else "None"


def transcribe(content: bytes, language: str | None, media_type: str = "audio/ogg") -> str | None:
	which = provider()
	lang = LANG.get(language or "Marathi", "mr")
	try:
		if which == "Whisper":
			return _whisper(content, lang, media_type)
		if which == "Bhashini" and frappe.conf.get("bhashini_key"):
			return _bhashini(content, lang)  # test only (R9.3)
		if which == "Google" and frappe.conf.get("google_stt_key"):
			return _google(content, lang, media_type)
	except Exception:
		frappe.log_error("SK hiring speech to text")
	return None


def _whisper(content: bytes, lang: str, media_type: str) -> str | None:
	"""Open-source Whisper on the Mac / own server for saved clips (R9.3 fallback): used when the 'whisper' package is installed."""
	import importlib.util
	import os
	import tempfile

	if importlib.util.find_spec("whisper") is None:
		return None
	import importlib

	whisper = importlib.import_module("whisper")
	ext = ".webm" if "webm" in (media_type or "") else ".ogg"
	with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
		f.write(content)
		path = f.name
	try:
		model = whisper.load_model(frappe.conf.get("whisper_model") or "small")
		out = model.transcribe(path, language=lang)
		return (out.get("text") or "").strip() or None
	finally:
		os.unlink(path)


def _bhashini(content: bytes, lang: str) -> str | None:
	"""Bhashini ASR (ULCA pipeline). Endpoint and service ids come from site_config so they can change without code."""
	import requests

	url = frappe.conf.get("bhashini_url") or "https://dhruva-api.bhashini.gov.in/services/inference/pipeline"
	body = {"pipelineTasks": [{"taskType": "asr", "config": {"language": {"sourceLanguage": lang}, "serviceId": frappe.conf.get("bhashini_asr_service_id") or "",
		"audioFormat": "ogg", "samplingRate": 16000}}], "inputData": {"audio": [{"audioContent": base64.b64encode(content).decode()}]}}
	r = requests.post(url, json=body, headers={"Authorization": frappe.conf.get("bhashini_key"), "Content-Type": "application/json"}, timeout=60)
	r.raise_for_status()
	out = r.json().get("pipelineResponse") or []
	for task in out:
		for o in task.get("output") or []:
			if o.get("source"):
				return o["source"]
	return None


def _google(content: bytes, lang: str, media_type: str) -> str | None:
	import requests

	code = {"mr": "mr-IN", "hi": "hi-IN", "en": "en-IN"}[lang]
	enc = "OGG_OPUS" if "ogg" in media_type else "MP3" if "mp" in media_type else "LINEAR16"
	r = requests.post(f"https://speech.googleapis.com/v1/speech:recognize?key={frappe.conf.get('google_stt_key')}",
		json={"config": {"encoding": enc, "languageCode": code, "alternativeLanguageCodes": ["hi-IN", "en-IN", "mr-IN"]}, "audio": {"content": base64.b64encode(content).decode()}}, timeout=60)
	r.raise_for_status()
	results = r.json().get("results") or []
	return " ".join(alt["transcript"] for res in results for alt in res.get("alternatives", [])[:1]) or None
