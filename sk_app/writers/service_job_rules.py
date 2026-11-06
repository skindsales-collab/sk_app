"""Pure rules of the subcontractor service job (Flow sheet, rate sheet 6-Nov-2026): a machine-shifting or other site job
we buy from a service subcontractor for a customer order. No frappe here; tests/test_service_job_rules.py runs them.

Steps (same for every service subcontractor): customer order + Project → service PO to the subcontractor at his final
rate with the payment term picked → advance if that term says so → his invoice as a draft bill from the PO → the
Non-Cabin owner approves the work → service GRN → the bill is payable, Accounts pay as per the term."""

TERMS = ("50% Advance - 50% After Invoice", "100% After Invoice - No Credit")  # Payment Terms Templates in ERPNext (SK 6-Nov)
OWNER_FUNCTION = "Machine Shifting"  # the Non-Cabin owner approves the work; taken from the SK App User function, no name
STAGES = ("ordered", "advance_paid", "billed", "approved", "paid")


def order_problems(rows: list[dict], supplier, payment_term, sales_order, project) -> list:
	"""rows = [{"item_code", "qty", "rate"}]."""
	found = []
	if not sales_order:
		found.append(("job_no_order", "Which customer order is this job for?"))
	if not project:
		found.append(("job_no_project", "The customer order has no Project; make the Project first so the cost is booked to it"))
	if not supplier:
		found.append(("job_no_supplier", "Which subcontractor does the job?"))
	if payment_term not in TERMS:
		found.append(("job_no_term", "Pick the payment term: 50% advance + 50% after invoice, or 100% after invoice"))
	good = [r for r in rows if float(r.get("qty") or 0) > 0]
	if not good:
		found.append(("job_no_items", "What work is ordered? Add at least one line with quantity"))
	if any(float(r.get("rate") or 0) <= 0 for r in good):
		found.append(("job_zero_rate", "Every line needs the subcontractor's final rate"))
	return found


def bill_problems(bill_no, bill_date, po_placed: bool, signed_report: bool = True) -> list:
	found = []
	if not signed_report:
		found.append(("bill_no_service_report", "The customer-signed service report is not on the PO yet; add it before the bill"))
	if not (bill_no or "").strip():
		found.append(("bill_no_number", "The subcontractor's invoice number is needed"))
	if not bill_date:
		found.append(("bill_no_date", "The subcontractor's invoice date is needed"))
	if not po_placed:
		found.append(("bill_po_not_placed", "The service PO is still a draft; place it before the bill"))
	return found


def submit_problems(rows: list[dict]) -> list:
	"""A service bill is posted only after the owner approved the work (every line has its service GRN)."""
	if any(not r.get("purchase_receipt") for r in rows):
		return [("bill_not_approved", "The Non-Cabin owner has not approved this work yet (no service GRN)")]
	return []


def advance_due(payment_term, grand_total: float) -> float:
	return round(float(grand_total or 0) * 0.5, 2) if payment_term == TERMS[0] else 0.0


def stage(*, placed: bool, advance_paid: bool, billed: bool, approved: bool, paid: bool) -> str:
	if paid:
		return "paid"
	if approved:
		return "approved"
	if billed:
		return "billed"
	if advance_paid:
		return "advance_paid"
	return "ordered" if placed else "draft"


def sale_rate(purchase_rate: float, margin: float) -> float:
	"""Our quote line = his rate x (1 + margin), rounded to the rupee (rate sheet note)."""
	return float(round(float(purchase_rate or 0) * (1 + float(margin or 0))))
