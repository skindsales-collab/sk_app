"""Dropdown choices from ERPNext, not fixed lists in the app screen (rebuild plan, Phase 0).

A Select field's choices come from the doctype as ERPNext has it today, including Customize Form changes, so a new
choice added in ERPNext shows in the app at once, with no deploy. Before 4-Nov the screen kept its own copies: the
problem types had already drifted ("Pay / leave" was in ERPNext but not in the app) and Net Banking was missing from the
payment modes.
"""

import frappe

# app key -> (doctype, Select field)
SELECTS = {
	"dsi_saving": ("SK DSI Entry", "saving_type"),
	"problem_type": ("SK Work Log", "problem_type"),
	"rating": ("SK Day Report", "manager_rating"),
}


def select(doctype: str, fieldname: str) -> list[str]:
	try:
		field = frappe.get_meta(doctype).get_field(fieldname)
	except Exception:
		return []
	if not field or field.fieldtype != "Select":
		return []
	return [o.strip() for o in (field.options or "").split("\n") if o.strip()]


def gst_states() -> list[str]:
	"""The GST state list of India Compliance when it is installed; else [] and the app keeps its own list."""
	try:
		from india_compliance.gst_india.constants import STATE_NUMBERS
	except Exception:
		return []
	return sorted(STATE_NUMBERS)


def app_options() -> dict:
	out = {key: select(dt, f) for key, (dt, f) in SELECTS.items()}
	out["gst_states"] = gst_states()
	return out
