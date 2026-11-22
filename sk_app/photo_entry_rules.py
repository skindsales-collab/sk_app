"""Pure rules for Photo Entry (SK approved 21-Nov, Shraddha list D). The phone reads the photo itself (bundled
tesseract, nothing leaves the phone); these rules pick the facts out of the text it read: GSTIN, bill no, bill date,
taxable value, CGST / SGST / IGST, grand total, UTR and payment amount. No frappe import, so it is unit tested."""

import re

GSTIN = re.compile(r"\b(\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z])\b")
NUM = r"(\d{1,3}(?:,\d{2,3})*(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)"
MONTHS = {m: i for i, m in enumerate(("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"), 1)}


def money(text) -> float:
	try:
		return round(float(str(text).replace(",", "").replace("₹", "").strip()), 2)
	except ValueError:
		return 0.0


def gstins(text: str, own=()) -> list[str]:
	"""Every GSTIN in the text except the company's own (OCR often reads O for 0: fixed in the digit places)."""
	found, own = [], {g.upper() for g in own or ()}
	for raw in re.findall(r"\b[0-9OIS]{2}[A-Z0-9]{13}\b", (text or "").upper()):
		g = raw[:2].replace("O", "0").replace("I", "1").replace("S", "5") + raw[2:]
		if GSTIN.match(g) and g not in own and g not in found:
			found.append(g)
	return found


def iso_date(text: str) -> str | None:
	"""21/11/2026, 21-11-26, 21.11.2026, 21-Nov-2026, 21 Nov 26 -> 2026-11-21."""
	m = re.search(r"\b(\d{1,2})[\/\-. ](\d{1,2}|[A-Za-z]{3,9})[\/\-. ,]+(\d{4}|\d{2})\b", text or "")
	if not m:
		return None
	d, mo, y = m.groups()
	mon = int(mo) if mo.isdigit() else MONTHS.get(mo[:3].lower())
	if not mon or not 1 <= mon <= 12 or not 1 <= int(d) <= 31:
		return None
	year = int(y) + (2000 if len(y) == 2 else 0)
	return f"{year:04d}-{mon:02d}-{int(d):02d}"


def _after(text: str, label: str) -> str | None:
	m = re.search(label + r"[^\n\d]{0,25}?" + NUM, text, re.I)
	return m.group(1) if m else None


def _tax(text: str, head: str) -> float:
	"""The amount on a CGST / SGST / IGST line: the last number on it that is not the rate."""
	best = 0.0
	for line in (text or "").splitlines():
		if re.search(r"\b" + head + r"\b", line, re.I) and not re.search(r"total\s+tax|tax\s+amount\s+\(in", line, re.I):
			nums = [money(n) for n in re.findall(NUM, line.split(head.upper())[-1] if head.upper() in line else line)]
			nums = [n for n in nums if n not in (2.5, 6, 9, 14, 18, 28, 5, 12)]
			if nums:
				best = max(best, nums[-1])
	return best


def bill_no(text: str) -> str | None:
	m = re.search(r"(?:invoice|bill|inv)\s*(?:no\.?|number|#)\s*[:\-.]?\s*([A-Z0-9][A-Z0-9\/\-]*\d[A-Z0-9\/\-]*)", text or "", re.I)
	return m.group(1).strip("-/") if m else None


def utr(text: str) -> str | None:
	"""UTR / reference of a bank payment: labelled first, else a bare 12-digit IMPS / UPI ref or a 16-22 NEFT / RTGS ref."""
	m = re.search(r"(?:utr|u\.t\.r|ref(?:erence)?\.?\s*(?:no|number)|transaction\s*(?:id|ref(?:erence)?)|txn\s*(?:id|no))\s*[:\-.#]?\s*([A-Z0-9]{10,22})",
		text or "", re.I)
	if m:
		return m.group(1).upper()
	m = re.search(r"\b([A-Z]{4}[A-Z0-9]{12,18}|\d{12})\b", (text or "").upper())
	return m.group(1) if m else None


def parse(text: str, own_gstins=()) -> dict:
	"""Facts of a bill / invoice / payment slip from the text the phone read."""
	t = text or ""
	g = gstins(t, own_gstins)
	total = money(_after(t, r"(?:grand\s*total|total\s*amount|invoice\s*(?:value|total)|net\s*amount|amount\s*payable|total\s*(?:rs\.?|inr|₹))") or 0)
	taxable = money(_after(t, r"(?:taxable\s*(?:value|amount)|sub\s*-?\s*total|assessable\s*value)") or 0)
	cgst, sgst, igst = _tax(t, "CGST"), _tax(t, "SGST"), _tax(t, "IGST")
	if not taxable and total and (cgst or igst):
		taxable = round(total - cgst - sgst - igst, 2)
	if not total and taxable:
		total = round(taxable + cgst + sgst + igst, 2)
	date_m = re.search(r"(?:invoice|bill|inv|voucher|txn|transaction|payment)?\s*date[d]?\s*[:\-.]?\s*([^\n]{6,20})", t, re.I)
	amount = total or money(_after(t, r"(?:\bamount\b|\bpaid\b|\bcredited\b|\bdebited\b|\brs\b\.?|\binr\b|₹)") or 0)
	return {"gstin": g[0] if g else "", "gstins": g, "bill_no": bill_no(t) or "", "bill_date": (iso_date(date_m.group(1)) if date_m else None) or iso_date(t) or "",
		"taxable": taxable, "cgst": cgst, "sgst": sgst, "igst": igst, "total": total, "utr": utr(t) or "", "amount": amount}


KINDS = ("supplier_bill", "sales_invoice", "money_in", "money_out", "expense", "other")
INTERNAL_PREFIX = ("From CRM", "Tally", "Common Sheet")


def problems(kind: str, v: dict) -> list[str]:
	"""What is still missing before the draft can be made (the person fixes these on the screen)."""
	out = []
	if kind not in KINDS:
		return ["Pick what the photo is"]
	if kind in ("supplier_bill", "money_out") and not v.get("supplier"):
		out.append("Pick the supplier")
	if kind in ("sales_invoice", "money_in") and not v.get("customer"):
		out.append("Pick the customer")
	if kind == "supplier_bill":
		if not (v.get("bill_no") or "").strip():
			out.append("Bill no is needed (stops double entry)")
		if not (v.get("purchase_order") or v.get("purchase_receipt")):
			if not v.get("expense_account"):
				out.append("Bill without PO: pick the expense head")
			if money(v.get("taxable") or 0) <= 0:
				out.append("Give the taxable value")
	if kind == "sales_invoice" and not (v.get("sales_order") or v.get("delivery_note")):
		out.append("Pick the Sales Order or Delivery Note")
	if kind in ("money_in", "money_out", "expense") and money(v.get("amount") or 0) <= 0:
		out.append("Give the amount")
	if kind == "expense" and not v.get("expense_account"):
		out.append("Pick the expense head")
	return out
