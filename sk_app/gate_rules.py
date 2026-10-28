"""Mandatory gate (SK 28-Oct-2026): "without processing mandatory things the screen will not process further, and all
data will be captured". Each screen has its must-have fields; the next step stays locked until they are filled.

Pure functions (no Frappe imports) so the rules can be unit tested anywhere. Each check returns the missing items as
(key, plain words) pairs; an empty list means the step may go on. gates.py applies them in the app and in ERPNext.
"""

import re

# names that say nothing about who the customer is (mail / portal imports often bring only "Enquiry")
PLACEHOLDER_WORDS = {"enquiry", "enquiries", "inquiry", "inquiries", "enq", "lead", "new lead", "customer", "client", "unknown",
	"na", "n/a", "none", "test", "sir", "madam", "mr", "ms", "mrs", "buyer", "requirement", "indiamart", "justdial", "tradeindia"}
REGISTERED_GST = ("Registered Regular", "Registered Composition", "SEZ", "Deemed Export", "UIN Holders", "Tax Deductor",
	"Tax Collector", "Input Service Distributor")
GSTIN_RE = re.compile(r"^[0-9]{2}[A-Z0-9]{10}[0-9A-Z]{3}$")

# what each screen needs (shown to SK and on the help card; the checks below are the same list)
RULES = {
	"Lead": ["Customer / company name (not 'Enquiry')", "Contact person", "Mobile number", "Segment (Cabin / Non-Cabin)",
		"Source", "Salesperson"],
	"Customer": ["Legal name", "GSTIN, or 'Unregistered' with the reason", "Billing address with state and PIN", "Mobile number"],
	"Quotation": ["Customer complete (above)", "Items with qty and rate", "GST applied", "Valid-till date", "Submitted in ERPNext"],
	"Deal: Quotation step": ["A quotation made for the deal"],
	"Deal: Negotiations step": ["The quotation submitted (sent to the customer)"],
	"Deal Won": ["Order date", "Order value", "Customer PO number or PO copy", "Promised delivery date", "Items",
		"Sales Order submitted"],
	"Sales Order": ["Customer complete", "Delivery date", "Items with rate", "Customer PO number or PO copy", "Submitted"],
	"Purchase request": ["Item and qty", "Required-by date", "Reason", "CEO approval before it moves on"],
	"Stock count": ["Store picked", "Counted qty on every line", "Store submits; manager OKs the differences"],
}


def blank(v) -> bool:
	return v is None or (isinstance(v, str) and not v.strip())


def is_placeholder_name(name) -> bool:
	"""True for 'Enquiry', 'Enquiry from IndiaMART', '9876543210', 'Lead 12' ..."""
	text = re.sub(r"[^a-z0-9/ ]", " ", str(name or "").lower()).strip()
	text = re.sub(r"\s+", " ", text)
	if not text or text.replace(" ", "").isdigit():
		return True
	words = [w for w in text.split(" ") if not w.isdigit()]
	if not words:
		return True
	if " ".join(words) in PLACEHOLDER_WORDS:
		return True
	# "enquiry from indiamart", "new enquiry", "lead for cabin": every word is a filler
	filler = PLACEHOLDER_WORDS | {"from", "for", "new", "via", "on", "of", "the", "a", "cabin", "website", "mail", "call", "portal"}
	return all(w in filler for w in words)


def mobile_ok(v) -> bool:
	digits = re.sub(r"\D", "", str(v or ""))
	return len(digits) >= 10


def gstin_ok(v) -> bool:
	return bool(GSTIN_RE.match(str(v or "").strip().upper()))


def lead_missing(d: dict) -> list[tuple[str, str]]:
	"""d: first_name, organization, mobile_no (or phone), sk_segment, source, lead_owner."""
	out = []
	company, person = d.get("organization"), d.get("first_name")
	if is_placeholder_name(company) and is_placeholder_name(person):
		out.append(("organization", "Real customer / company name (not 'Enquiry')"))
	if is_placeholder_name(person):
		out.append(("first_name", "Contact person's name"))
	if not (mobile_ok(d.get("mobile_no")) or mobile_ok(d.get("phone"))):
		out.append(("mobile_no", "Mobile number (10 digits)"))
	if blank(d.get("sk_segment")):
		out.append(("sk_segment", "Segment (Cabin / Non-Cabin)"))
	if blank(d.get("source")):
		out.append(("source", "Source (where the enquiry came from)"))
	if blank(d.get("lead_owner")) and blank(d.get("deal_owner")):
		out.append(("lead_owner", "Salesperson"))
	return out


def customer_missing(d: dict) -> list[tuple[str, str]]:
	"""d: customer_name, gst_category, gstin, sk_gst_note, address_state, address_pincode, mobile_no."""
	out = []
	if is_placeholder_name(d.get("customer_name")):
		out.append(("customer_name", "Customer's legal name"))
	cat = d.get("gst_category") or "Unregistered"
	if cat in REGISTERED_GST or not blank(d.get("gstin")):
		if not gstin_ok(d.get("gstin")):
			out.append(("gstin", "GSTIN (15 letters / digits)"))
	elif blank(d.get("sk_gst_note")):
		out.append(("gstin", "GSTIN, or tick 'Unregistered' and say why"))
	if blank(d.get("address_state")):
		out.append(("address", "Billing address with state"))
	elif blank(d.get("address_pincode")):
		out.append(("address", "PIN code of the billing address"))
	if not mobile_ok(d.get("mobile_no")):
		out.append(("mobile_no", "Customer's mobile number"))
	return out


def quotation_missing(d: dict) -> list[tuple[str, str]]:
	"""d: party_name, valid_till, items [{qty, rate}], taxes (count), total_taxes_and_charges."""
	out = []
	if blank(d.get("party_name")):
		out.append(("party_name", "Customer"))
	items = d.get("items") or []
	if not items:
		out.append(("items", "At least one item"))
	elif any(not (float(i.get("qty") or 0) > 0 and float(i.get("rate") or 0) > 0) for i in items):
		out.append(("items", "Qty and rate on every item"))
	if not (d.get("taxes") or float(d.get("total_taxes_and_charges") or 0) > 0):
		out.append(("taxes", "GST (pick the GST template)"))
	if blank(d.get("valid_till")):
		out.append(("valid_till", "Valid-till date"))
	return out


def order_missing(d: dict) -> list[tuple[str, str]]:
	"""Sales Order / Deal Won. d: transaction_date, delivery_date, po_no, po_file (bool), items [{qty, rate}], grand_total."""
	out = []
	if blank(d.get("transaction_date")):
		out.append(("transaction_date", "Order date"))
	if blank(d.get("delivery_date")):
		out.append(("delivery_date", "Promised delivery date"))
	if blank(d.get("po_no")) and not d.get("po_file"):
		out.append(("po_no", "Customer PO number or PO copy"))
	items = d.get("items") or []
	if not items:
		out.append(("items", "Items"))
	elif any(not (float(i.get("qty") or 0) > 0 and float(i.get("rate") or 0) > 0) for i in items):
		out.append(("items", "Qty and rate on every item"))
	if not float(d.get("grand_total") or 0) > 0:
		out.append(("grand_total", "Order value"))
	return out


def request_missing(d: dict) -> list[tuple[str, str]]:
	"""Purchase request. d: items [{item_code, qty}], schedule_date, reason."""
	out = []
	items = d.get("items") or []
	if not items or any(blank(i.get("item_code")) or not float(i.get("qty") or 0) > 0 for i in items):
		out.append(("items", "Item and qty on every line"))
	if blank(d.get("schedule_date")):
		out.append(("schedule_date", "Required-by date"))
	if blank(d.get("reason")):
		out.append(("reason", "Reason (why it is needed)"))
	return out


def count_missing(warehouse, book: list[str], counted: dict) -> list[tuple[str, str]]:
	"""Stock count: every item the store holds in ERPNext must get a counted qty (0 is a count)."""
	out = []
	if blank(warehouse):
		out.append(("warehouse", "Store"))
	left = [code for code in book if blank(counted.get(code)) and counted.get(code) != 0]
	if left:
		out.append(("counts", f"Counted qty on every line ({len(left)} left)"))
	return out


def deal_step_needs(step: str, quotations: list[dict], orders: list[dict]) -> list[tuple[str, str]]:
	"""Lead / deal status gate. step: New, Qualified, Drawing, Quotation, Negotiations, Won.
	quotations / orders: [{docstatus}] linked to the deal."""
	if step == "Quotation" and not quotations:
		return [("quotation", "Make the quotation first")]
	if step == "Negotiations" and not any(q.get("docstatus") == 1 for q in quotations):
		return [("quotation", "Submit the quotation first (sent to the customer)")]
	if step == "Won" and not any(o.get("docstatus") == 1 for o in orders):
		return [("sales_order", "Order received: Sales Order with PO, value and delivery date, submitted")]
	return []


def words(missing: list[tuple[str, str]]) -> str:
	return "\n".join("• " + text for _key, text in missing)
