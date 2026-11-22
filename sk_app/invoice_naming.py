"""SK 21-Nov: Sales Invoice number SK/IND/MMYY/### - "SK" and "IND" fixed, MMYY = month and year of the invoice date,
### = ONE running number that goes on across months and years (848, 849, ...), never back to 001 in a new month.

The ERPNext naming series "SK/IND/.MM.YY./.###." counts per month (it restarted at 001 in November), so the app names
these invoices itself: a single counter (tabSeries key COUNTER), started from the higher of SK App Settings
"invoice_running_last" (the last number already used, e.g. 848) and the highest number found in existing invoices.
Amended invoices take the next number too (GST allows 16 characters; SK/IND/1126/849 is 15). Other series (SINV-…)
are not touched."""

import re

import frappe
from frappe.utils import cint, getdate

PREFIX = "SK/IND/"
COUNTER = "SK/IND/RUNNING/"
NAME_RE = re.compile(r"^SK/IND/\d{4}/(\d+)$")


def name_for(posting_date, number: int) -> str:
	d = getdate(posting_date)
	return f"{PREFIX}{d:%m}{d:%y}/{int(number):03d}"


def number_of(name: str | None) -> int:
	m = NAME_RE.match(name or "")
	return int(m.group(1)) if m else 0


def autoname(doc, method=None):
	"""Sales Invoice autoname hook: only for the SK/IND/ series."""
	if not (doc.get("naming_series") or "").startswith(PREFIX):
		return
	from frappe.model.naming import getseries

	ensure_counter()
	doc.name = name_for(doc.posting_date or frappe.utils.nowdate(), cint(getseries(COUNTER, 3)))


def _highest_used() -> int:
	names = frappe.get_all("Sales Invoice", filters={"name": ["like", f"{PREFIX}%"]}, pluck="name")
	return max([number_of(n) for n in names] + [0])


def ensure_counter() -> int:
	"""The counter is never below the last number used (setting or existing invoices). Returns the counter value."""
	last = cint(frappe.db.get_single_value("SK App Settings", "invoice_running_last")) if frappe.get_meta("SK App Settings").has_field(
		"invoice_running_last") else 0
	start = max(last, _highest_used())
	current = cint(frappe.db.get_value("Series", COUNTER, "current", order_by="name"))
	if not frappe.db.exists("Series", COUNTER):
		frappe.db.sql("insert into `tabSeries` (`name`, `current`) values (%s, %s)", (COUNTER, start))
		return start
	if current < start:
		frappe.db.sql("update `tabSeries` set `current` = %s where `name` = %s", (start, COUNTER))
		return start
	return current


def ensure_amend_naming():
	"""An amended Sales Invoice takes the next running number (SK/IND/1126/849-1 would be 17 characters, over GST's 16):
	"Default Naming" for Sales Invoice in Document Naming Settings. Only added when missing, never changed if set."""
	if not frappe.db.exists("DocType", "Amended Document Naming Settings"):
		return
	if frappe.db.exists("Amended Document Naming Settings", {"document_type": "Sales Invoice", "parenttype": "Document Naming Settings"}):
		return
	s = frappe.get_single("Document Naming Settings")
	s.append("amend_naming_override", {"document_type": "Sales Invoice", "action": "Default Naming"})
	s.flags.ignore_permissions = True
	s.save()

