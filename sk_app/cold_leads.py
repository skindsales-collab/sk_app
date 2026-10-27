"""Cold Calling leads apart from current leads (SK 27-Oct-2026, Pranali: "all leads, including cold-calling data, are
displayed under My Leads; a separate Cold Calling option will make it easier to manage and call cold leads").

A lead is cold while its CRM Lead Source is one of the cold sources (SK App Settings "Cold Lead Sources"; by default
the marketing call list loaded on 19-Oct and "Cold Calling") and it is still at SK's first step, New. It stays a CRM
Lead in Frappe CRM: nothing is copied or bypassed. Once the salesperson moves it on (Qualified ...) in the CRM, it
leaves the cold list and shows in My Leads and the flow arrows like any other lead. Calls on cold leads count as
"Cold calls from marketing list" on the Day Report.
"""

import re

import frappe

from sk_app import lead_status
from sk_app.logic import parse_lines

DEFAULT_SOURCES = ["Marketing call", "Cold Calling"]


def _norm(source: str | None) -> str:
	"""Letters only, lower case, doubled letters once: "Marketingg call" and "marketing-call" are the same source."""
	return re.sub(r"(.)\1+", r"\1", re.sub(r"[^a-z]", "", (source or "").lower()))


def sources() -> set[str]:
	own = frappe.get_cached_doc("SK App Settings").get("cold_lead_sources") or ""
	return {_norm(s) for s in (parse_lines(own) or DEFAULT_SOURCES) if _norm(s)}


def is_cold(source: str | None, status: str | None, cold_sources: set[str] | None = None) -> bool:
	return bool(source) and _norm(source) in (sources() if cold_sources is None else cold_sources) \
		and lead_status.step_of(status) == "New"


def badge(user: str, functions) -> dict:
	"""Blue count on the Cold Calling icon: cold leads not called yet."""
	if not {"Sales", "Marketing"} & set(functions or []):
		return {}
	from sk_app import work

	n = sum(1 for i in work.open_leads(user, cold=True) if not i.extra.get("called"))
	return {"cold_leads": {"n": n, "c": "blue"}} if n else {}
