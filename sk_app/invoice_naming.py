"""SK 21-Nov: Sales Invoice number SK/IND/MMYY/### - "SK" and "IND" fixed, MMYY = month and year of the invoice date,
### = ONE running number that goes on across months and years (848, 849, ...), never back to 001 in a new month.

The ERPNext naming series "SK/IND/.MM.YY./.###." counts per month (it restarted at 001 in November), so the app names
these invoices itself: a single counter (tabSeries key COUNTER), started from the higher of SK App Settings
"invoice_running_last" (the last number already used, e.g. 848) and the highest number found in existing invoices.
SK 27-Nov ("invoice number changes, this should not happen"): a corrected (cancelled + amended) invoice keeps EXACTLY its
number. The cancelled copy is kept as "<number>-CXL" (its accounts already reversed; it never goes to GST) and the
amendment takes the number itself. Only when the cancelled copy had an IRN or e-way bill (the GST portal already holds
that number) does the amendment take the same number with a letter (850A), within GST's 16 characters.
Other series (SINV-…) are not touched."""

import re

import frappe
from frappe.utils import cint, getdate

PREFIX = "SK/IND/"
COUNTER = "SK/IND/RUNNING/"
NAME_RE = re.compile(r"^SK/IND/\d{4}/(\d+)[A-Z]?$")
ROOT_RE = re.compile(r"^(SK/IND/\d{4}/\d+)[A-Z]?$")


def name_for(posting_date, number: int) -> str:
	d = getdate(posting_date)
	return f"{PREFIX}{d:%m}{d:%y}/{int(number):03d}"


def amended_name(amended_from: str | None, taken) -> str | None:
	"""The amendment's name: the same number with the next free letter (taken(name) -> bool)."""
	m = ROOT_RE.match(amended_from or "")
	if not m:
		return None
	for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
		if not taken(m.group(1) + letter):
			return m.group(1) + letter
	return None


def cxl_name(name: str, taken) -> str:
	"""Where the cancelled copy is kept: 850-CXL, then 850-CXL2 ..."""
	n, i = f"{name}-CXL", 2
	while taken(n):
		n, i = f"{name}-CXL{i}", i + 1
	return n


def keep_on_amend(doc) -> bool:
	"""The amendment takes its cancelled original's exact number (the original moves to -CXL)."""
	src = doc.get("amended_from")
	if not ROOT_RE.match(src or ""):
		return False
	row = frappe.db.get_value("Sales Invoice", src, ["docstatus", "irn", "ewaybill"], as_dict=True) if frappe.db.exists("Sales Invoice", src) else None
	if not row or row.docstatus != 2 or row.get("irn") or row.get("ewaybill"):
		return False
	keep = cxl_name(src, lambda n: bool(frappe.db.exists("Sales Invoice", n)))
	frappe.rename_doc("Sales Invoice", src, keep, force=True)
	doc.amended_from = keep
	doc.name = src
	return True


def number_of(name: str | None) -> int:
	m = NAME_RE.match(name or "")
	return int(m.group(1)) if m else 0


def autoname(doc, method=None):
	"""Sales Invoice autoname hook: only for the SK/IND/ series."""
	if not (doc.get("naming_series") or "").startswith(PREFIX):
		return
	from frappe.model.naming import getseries

	if frappe.flags.sk_invoice_name:  # the one-time "keep this number" fix (keep_number below)
		doc.name = frappe.flags.sk_invoice_name
		return
	if keep_on_amend(doc):
		return
	amend = amended_name(doc.get("amended_from"), lambda n: bool(frappe.db.exists("Sales Invoice", n)))
	if amend:
		doc.name = amend
		return
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



def keep_number(keep: str, cancelled: list[str], copy_from: str, counter: int) -> str | None:
	"""One-time admin fix (SK 27-Nov "keep 850, no change"): the cancelled invoices get "-CXL" (their accounts are already
	reversed; none had an IRN / e-way bill), the running counter goes back, and a DRAFT with the kept number is made as a copy
	of the last cancelled one, for Accounts to check and submit. Does nothing unless every named invoice is cancelled."""
	if frappe.db.exists("Sales Invoice", keep) and frappe.db.get_value("Sales Invoice", keep, "docstatus") != 2:
		return None
	for n in cancelled:
		row = frappe.db.get_value("Sales Invoice", n, ["docstatus", "irn", "ewaybill"], as_dict=True)
		if not row or row.docstatus != 2 or row.get("irn") or row.get("ewaybill"):
			return None
	for n in cancelled:
		frappe.rename_doc("Sales Invoice", n, n + "-CXL", force=True)
	src = frappe.get_doc("Sales Invoice", copy_from + "-CXL")
	new = frappe.copy_doc(src)
	new.amended_from = None
	new.docstatus = 0
	new.flags.sk_no_double = True  # it replaces the cancelled copy on purpose
	frappe.flags.sk_invoice_name = keep
	try:
		new.insert(ignore_permissions=True)
	finally:
		frappe.flags.sk_invoice_name = None
	frappe.db.sql("update `tabSeries` set `current` = %s where `name` = %s", (counter, COUNTER))
	if frappe.get_meta("SK App Settings").has_field("invoice_running_last"):
		frappe.db.set_single_value("SK App Settings", "invoice_running_last", counter)
	return new.name


ROTHE_850 = ("SK/IND/1126/850", ["SK/IND/1126/850", "SK/IND/1126/856", "SK/IND/1126/857"], "SK/IND/1126/857", 855)


def hourly():
	"""SK 27-Nov "keep 850 / no 857": once Accounts has cancelled 857, the Rothe invoice gets back its number 850 as a draft.
	Runs only while 850, 856 and 857 all exist and are all cancelled; afterwards it finds 850 as a draft and does nothing."""
	keep, names, src, counter = ROTHE_850
	if not all(frappe.db.get_value("Sales Invoice", n, "docstatus") == 2 for n in names):
		return
	try:
		made = keep_number(keep, names, src, counter)
		if made:
			frappe.get_doc("Sales Invoice", made).add_comment("Comment", "SK 27-Nov: invoice number 850 kept for Rothe (already sent to the "
				"customer). The cancelled 850 / 856 / 857 are kept as -CXL. Check and Submit this draft.")
			frappe.db.commit()
	except Exception:
		frappe.db.rollback()
		frappe.log_error("SK App keep invoice 850")
