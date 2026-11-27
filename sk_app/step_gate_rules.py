"""Essential-field gate for every function (SK 27-Nov "approve all": SK_App_Essential_Field_Gate_All_Functions_Rev0.xlsx).

A step cannot go further while its essential data is missing; the stop says what is missing, who fills it and why, so the
person understands. Pure rules here (tested without a site); sk_app/step_gates.py reads the ERPNext record and stops it.
Every function returns [(key, plain words)], empty = may go on.
"""

from __future__ import annotations

import re

SIZE = re.compile(r"\d+(?:\.\d+)?\s*(?:ft|feet|'|’)?\s*[x×*]\s*\d+", re.I)

# who fills each step (the function; the person is looked up from it) and what comes next
WHO = {
	"send_to_design": "Sales", "design_status": "Design", "work_order": "Design", "purchase_order": "Purchase",
	"purchase_invoice": "Accounts", "purchase_receipt": "Stores", "stock_issue": "Stores", "delivery_note": "Stores",
	"project_close": "Production", "payment": "Accounts", "expense_claim": "Accounts", "employee_login": "HR",
}
WHY = "All the data of this step must be in ERPNext before the next step (SK 27-Nov)."


def blank(v) -> bool:
	return v is None or str(v).strip() in ("", "0", "0.0", "None")


def send_to_design(requirement: str | None, length=None, width=None) -> list[tuple[str, str]]:
	"""Row 3: design starts only on a full enquiry: what the customer wants, and its size."""
	out = []
	text = (requirement or "").strip()
	if not text:
		out.append(("requirement", "Requirement: what the customer wants (office, toilet, security cabin ...)"))
	if not ((not blank(length) and not blank(width)) or SIZE.search(text)):
		out.append(("size", "Size: length x width (e.g. 20 x 10 ft) in the requirement"))
	return out


def design_status(new_status: str | None, drawing_pdfs: int, quote_value) -> list[tuple[str, str]]:
	"""Rows 8-9: 'Drawing Sent' only with the customer drawing PDF on the deal; 'BOM & Quote Sent' only with the quote value."""
	s = (new_status or "").lower()
	out = []
	if s == "drawing sent" and drawing_pdfs < 1:
		out.append(("drawing", "Customer drawing PDF attached to the deal"))
	if s == "bom & quote sent" and blank(quote_value):
		out.append(("quote_value", "Design quote value (before GST) on the deal"))
	return out


def work_order(drawing_pdfs: int) -> list[tuple[str, str]]:
	"""Row 10: production starts from the manufacturing drawing."""
	return [] if drawing_pdfs else [("drawing", "Manufacturing drawing (mm) PDF on the Sales Order, Project or Work Order")]


def purchase_order(gst_category: str | None, gstin: str | None, has_address: bool, no_date_rows: int) -> list[tuple[str, str]]:
	"""Row 13."""
	out = []
	if (gst_category or "Unregistered") != "Unregistered" and blank(gstin):
		out.append(("gstin", "Supplier GSTIN (or set the supplier as Unregistered)"))
	if not has_address:
		out.append(("address", "Supplier address"))
	if no_date_rows:
		out.append(("schedule_date", "Delivery (required-by) date on every line"))
	return out


def purchase_invoice(bill_no, bill_date, stock_rows_unlinked: int) -> list[tuple[str, str]]:
	"""Row 14: the supplier's own bill number and date; stock lines come through the receipt / PO."""
	out = []
	if blank(bill_no):
		out.append(("bill_no", "Supplier bill number"))
	if blank(bill_date):
		out.append(("bill_date", "Supplier bill date"))
	if stock_rows_unlinked:
		out.append(("receipt", "Stock lines against their Purchase Receipt or Purchase Order"))
	return out


def purchase_receipt(challan_no, files: int) -> list[tuple[str, str]]:
	"""Row 15."""
	out = []
	if blank(challan_no):
		out.append(("challan", "Supplier challan / delivery note number"))
	if files < 1:
		out.append(("photo", "Photo of the supplier challan"))
	return out


ISSUE_PURPOSES = ("Material Issue", "Material Transfer for Manufacture")


def stock_issue(purpose: str | None, work_order, project) -> list[tuple[str, str]]:
	"""Row 16 (ERPNext itself refuses more than the stock): every issue to production names its cabin."""
	if purpose in ISSUE_PURPOSES and blank(work_order) and blank(project):
		return [("cabin", "Cabin: the Work Order or Project the material is issued for")]
	return []


def delivery_note(vehicle_no, transport, qc_passed: bool) -> list[tuple[str, str]]:
	"""Rows 20-21 (the e-way bill comes from the invoice after submit; the night check follows it)."""
	out = []
	if not qc_passed:
		out.append(("qc", "Final quality check passed (Quality Inspection submitted)"))
	if blank(vehicle_no):
		out.append(("vehicle_no", "Vehicle number"))
	if blank(transport):
		out.append(("transport", "Transporter or driver name"))
	return out


def project_close(new_status: str | None, files: int) -> list[tuple[str, str]]:
	"""Row 22."""
	if new_status == "Completed" and files < 1:
		return [("handover", "Handover photo / customer sign-off on the Project")]
	return []


def payment(payment_type: str | None, party_type: str | None, references: int) -> list[tuple[str, str]]:
	"""Rows 24-25: a customer receipt / supplier payment is linked to its bill or order (an advance to its order)."""
	if payment_type in ("Receive", "Pay") and party_type in ("Customer", "Supplier") and references < 1:
		what = "invoice, or the Sales Order for an advance" if party_type == "Customer" else "bill, or the Purchase Order for an advance"
		return [("references", f"Link the payment to its {what}")]
	return []


def expense_claim(employee, files: int, no_bill) -> list[tuple[str, str]]:
	"""Row 26."""
	out = []
	if blank(employee):
		out.append(("employee", "Employee"))
	if files < 1 and blank(no_bill):
		out.append(("bill", "Bill photo (or tick 'No bill' with the reason)"))
	return out


def employee_login(d: dict) -> list[tuple[str, str]]:
	"""Row 28 (no salary in the app)."""
	labels = {"cell_number": "Mobile number", "date_of_joining": "Joining date", "department": "Department", "designation": "Designation"}
	return [(k, v) for k, v in labels.items() if blank(d.get(k))]


def notice(record: str, missing: list[tuple[str, str]], who: str, person: str | None = None) -> str:
	"""The one message every stop shows: what is missing, who fills it, why."""
	lines = [f"{record} cannot go further. Missing:"] + ["• " + w for _k, w in missing]
	lines.append(f"Who fills it: {person + ' (' + who + ')' if person else who}")
	lines.append(WHY)
	return "\n".join(lines)
