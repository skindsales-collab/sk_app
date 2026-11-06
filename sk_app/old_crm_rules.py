"""Pure rules for the one-time load of old CRM data (SK 6-Nov: Biziverse junk / lost leads and the Common Sheet
quotes never reached ERPNext). No frappe import, so the rules are tested in CI.

The data itself never sits in this repository (it holds customer names and mobiles, and the repo is public):
it is a private ERPNext File that SK uploads, see sk_app/old_crm_load.py."""

import re
from datetime import date

FILE_PREFIX = "SK_Old_CRM_Load_"  # SK uploads e.g. SK_Old_CRM_Load_6Nov2026.csv as a private File
MARKER = "[old CRM load]"         # written into lost_notes, so a second run skips rows already loaded
CLOSED = ("Junk Lead", "Deal Loss")
OPEN = ("Quotation",)
FIELDS = ("first_name", "organization", "mobile_no", "source", "lead_owner", "status", "lost_reason", "lost_notes",
	"sk_product", "sk_segment")


def mobile_key(mobile) -> str | None:
	"""Last 10 digits (+91 98220 12345 and 9822012345 are the same person); 0000000000 is no number."""
	digits = re.sub(r"\D", "", str(mobile or ""))
	key = digits[-10:] if len(digits) >= 10 else None
	return None if key == "0000000000" else key


def parse_date(text) -> date | None:
	try:
		return date.fromisoformat(str(text or "").strip()[:10])
	except ValueError:
		return None


def lead_from_row(row: dict, known: dict) -> tuple[dict | None, str]:
	"""One CSV row -> the CRM Lead fields to insert, or (None, why it is skipped).
	known: {"mobiles": set of mobile keys already in ERPNext, "users": set, "sources": set, "reasons": set}."""
	key = mobile_key(row.get("mobile_no"))
	if key and key in known["mobiles"]:
		return None, "already in ERPNext (same mobile)"
	status = (row.get("status") or "").strip()
	if status not in CLOSED + OPEN:
		return None, f"status {status or '(blank)'} is not loaded"
	name = (row.get("first_name") or row.get("organization") or "").strip() or "Old CRM lead"
	lead = {
		"first_name": name[:60],
		"organization": (row.get("organization") or "").strip()[:140] or None,
		"mobile_no": key,
		"source": row.get("source") if row.get("source") in known["sources"] else None,
		"lead_owner": row.get("lead_owner") if row.get("lead_owner") in known["users"] else None,
		"status": status,
		"sk_product": (row.get("sk_product") or "").strip()[:140] or None,
		"sk_segment": row.get("sk_segment") or "Cabin",
	}
	notes = (row.get("lost_notes") or "").strip()
	if row.get("quote_no"):
		notes += f" | quote no {row['quote_no']}" + (f", Rs {row['quote_amount']}" if row.get("quote_amount") else "")
	lead["lost_notes"] = f"{MARKER} {notes}".strip()[:1000]
	if status in CLOSED:
		reason = row.get("lost_reason")
		lead["lost_reason"] = reason if reason in known["reasons"] else ("Other" if "Other" in known["reasons"] else None)
	return lead, ""


def dates_of(row: dict) -> tuple[date | None, date | None]:
	"""(created, closed): the old CRM date the lead came in, and the day it was closed (falls back to created), so the
	month-wise arrows put the lead in its own month and not in the month it was loaded."""
	created = parse_date(row.get("date"))
	closed = parse_date(row.get("closed_date")) or created
	return created, closed
