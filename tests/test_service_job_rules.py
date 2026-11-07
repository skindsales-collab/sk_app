from sk_app.writers.purchase_order_rules import problems as po_problems
from sk_app.writers.service_job_rules import TERMS, advance_due, bill_problems, order_problems, sale_rate, stage, submit_problems

keys = lambda found: [k for k, _w in found]


def test_order_problems():
	rows = [{"item_code": "SR-04", "qty": 1, "rate": 140000}]
	assert order_problems(rows, "Technomech", TERMS[0], "SO-1", "PROJ-1") == []
	assert keys(order_problems([{"item_code": "SR-04", "qty": 0, "rate": 0}], None, "cash", None, None)) == [
		"job_no_order", "job_no_project", "job_no_supplier", "job_no_term", "job_no_items"]
	assert keys(order_problems([{"item_code": "SR-01", "qty": 20, "rate": 0}], "T", TERMS[1], "SO-1", "P")) == ["job_zero_rate"]


def test_bill_and_submit_problems():
	assert bill_problems("PUR/NC/070", "2026-11-06", True) == []
	assert keys(bill_problems("", None, False)) == ["bill_no_number", "bill_no_date", "bill_po_not_placed"]
	assert keys(bill_problems("PUR/NC/070", "2026-11-06", True, signed_report=False)) == ["bill_no_service_report"]
	assert submit_problems([{"purchase_receipt": "PR-1"}]) == []
	assert keys(submit_problems([{"purchase_receipt": "PR-1"}, {"purchase_receipt": None}])) == ["bill_not_approved"]


def test_advance_stage_and_sale_rate():
	assert advance_due(TERMS[0], 118000) == 59000.0
	assert advance_due(TERMS[1], 118000) == 0.0
	assert stage(placed=False, advance_paid=False, billed=False, approved=False, paid=False) == "draft"
	assert stage(placed=True, advance_paid=False, billed=False, approved=False, paid=False) == "ordered"
	assert stage(placed=True, advance_paid=True, billed=False, approved=False, paid=False) == "advance_paid"
	assert stage(placed=True, advance_paid=True, billed=True, approved=False, paid=False) == "billed"
	assert stage(placed=True, advance_paid=True, billed=True, approved=True, paid=False) == "approved"
	assert stage(placed=True, advance_paid=True, billed=True, approved=True, paid=True) == "paid"
	assert sale_rate(1864, 0.529) == 2850.0
	assert sale_rate(140000, 0.3) == 182000.0


def test_service_po_needs_no_requisition():
	rows = [{"item_code": "SR-04", "qty": 1, "rate": 140000, "material_request": None, "approved": False}]
	assert keys(po_problems(rows, "Technomech", "2026-11-10", False)) == ["po_without_request"]
	assert po_problems(rows, "Technomech", "2026-11-10", False, True) == []
