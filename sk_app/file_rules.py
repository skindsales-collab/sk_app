"""Pure rules for files on customer-facing records (PR H, SK rule 16-Nov KF-05549).

Case: Cabin 53 (CRM-DEAL-2026-00125) got the BOM / costing Excel on the deal, and the app task told the salesperson to
open it. A deal, lead, quotation, order, invoice or customer record is what the customer may see: only PDFs (drawing,
quote) and photos go there; the costing Excel stays on the internal Project record. Customer file names carry the
customer's name and date, never the internal cabin number (skill sk-customer-drawing-no-cabin-number)."""

import re

CUSTOMER_FACING = {"CRM Lead", "CRM Deal", "Quotation", "Sales Order", "Sales Invoice", "Customer"}
ALLOWED = {".pdf", ".jpg", ".jpeg", ".png", ".webp", ".heic"}  # drawings and quotes as PDF; site / card photos
INTERNAL_WORDS = ("bom", "costing", "cost_sheet", "cost sheet", "manufacturing", "internal", "job_card", "rate card", "ratecard")
CABIN_NO = re.compile(r"(?i)(?<![A-Za-z0-9])(?:cabin|cab)[ _\-]*(?:no\.?)?[ _\-]*\d{1,4}(?=[ _\-.]|$)[ _\-]*|(?<![A-Za-z0-9])C[ _\-]?\d{2,4}(?=[ _\-.])[ _\-]*")


def ext_of(file_name: str | None) -> str:
	name = (file_name or "").strip().lower()
	return name[name.rfind("."):] if "." in name else ""


def allowed_on(doctype: str | None, file_name: str | None) -> tuple[bool, str | None]:
	"""(ok, reason) for a file going onto a record. Internal records take anything."""
	if doctype not in CUSTOMER_FACING:
		return True, None
	ext = ext_of(file_name)
	low = (file_name or "").lower()
	if ext not in ALLOWED:
		return False, f"Only PDF (drawing, quote) and photos go on a {doctype}; the costing Excel stays on the internal Project record"
	if ext == ".pdf" and any(w in low for w in INTERNAL_WORDS):
		return False, f"'{file_name}' looks internal (BOM / costing): it stays on the Project record, not on the {doctype}"
	return True, None


def customer_file_name(file_name: str | None) -> str:
	"""The name the customer sees: the internal cabin number taken out ('Cabin 53 Godrej quote.pdf' -> 'Godrej quote.pdf')."""
	name = (file_name or "").strip()
	ext = ext_of(name)
	stem = name[: -len(ext)] if ext else name
	stem = CABIN_NO.sub("", stem)
	stem = re.sub(r"[ _\-]{2,}", " ", stem).strip(" _-")
	return (stem or "Document") + ext


def is_quote_file(file_name: str | None) -> bool:
	"""SK 16-Nov: only a PDF is the quote; the design bot's '..._BOM_Costing_Quote_Rev0.xlsx' is the internal costing."""
	name = (file_name or "").lower()
	return "quot" in name and name.endswith(".pdf")
