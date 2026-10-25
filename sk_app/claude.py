"""Server-side Claude calls. The API key lives only in site_config (anthropic_api_key), never on the phone."""

import frappe
from frappe.utils import getdate

from sk_app.logic import GUIDE_SYSTEM

FALLBACK_BETA = "server-side-fallback-2026-07-01"


def _api_key() -> str | None:
	return frappe.conf.get("anthropic_api_key")


def _under_cap(settings) -> bool:
	"""Monthly call cap set by the CEO; the counter resets when the month changes."""
	month = f"{getdate():%Y-%m}"
	if settings.claude_calls_month != month:
		frappe.db.set_single_value("SK App Settings", {"claude_calls_month": month, "claude_calls_this_month": 0})
		settings.claude_calls_this_month = 0
	return (settings.claude_calls_this_month or 0) < (settings.monthly_call_cap or 0)


def _count_call():
	frappe.db.sql(
		"""update `tabSingles` set value = cast(value as unsigned) + 1
		where doctype='SK App Settings' and field='claude_calls_this_month'"""
	)
	frappe.clear_document_cache("SK App Settings", "SK App Settings")


def available() -> bool:
	settings = frappe.get_cached_doc("SK App Settings")
	return bool(settings.guide_enabled and _api_key() and _under_cap(settings))


def guide_text(prompt: str) -> str | None:
	"""One short 'what to do now' line from Claude, or None so the caller uses the rule-based card."""
	if not available():
		return None
	import anthropic

	settings = frappe.get_cached_doc("SK App Settings")
	client = anthropic.Anthropic(api_key=_api_key(), timeout=30.0, max_retries=1)
	try:
		response = client.beta.messages.create(
			model=settings.claude_model or "claude-opus-5-5",
			max_tokens=1024,
			system=GUIDE_SYSTEM,
			messages=[{"role": "user", "content": prompt}],
			output_config={"effort": settings.claude_effort or "low"},
			betas=[FALLBACK_BETA],
			fallbacks="default",
		)
	except anthropic.APIConnectionError:
		frappe.log_error("SK App: Claude not reachable", "SK App Claude")
		return None
	except anthropic.RateLimitError:
		frappe.log_error("SK App: Claude rate limited", "SK App Claude")
		return None
	except anthropic.APIStatusError as e:
		frappe.log_error(f"SK App: Claude error {e.status_code}: {e.message}", "SK App Claude")
		return None
	finally:
		_count_call()

	if response.stop_reason == "refusal":
		return None
	text = " ".join(b.text for b in response.content if b.type == "text").strip()
	return text[:500] or None
