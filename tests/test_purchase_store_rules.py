from sk_app.writers.purchase_order_rules import ceo_reason, problems as po_problems
from sk_app.writers.receipt_rules import problems as receipt_problems, received_rows
from sk_app.writers.stock_entry_rules import TO_JOB, issue_rows, problems as issue_problems


def test_po_ceo_reason():
	assert ceo_reason(1, 0, 0, 0, 25000) == "no approved requisition for some items"
	assert ceo_reason(0, 0, 30000, 35400, 25000) == "no estimate on the requisition"
	assert ceo_reason(0, 0, 10000, 11800, 25000) is None
	assert ceo_reason(0, 10000, 11500, 13570, 25000) == "15% above the approved value"
	assert ceo_reason(0, 10000, 10500, 12390, 25000) is None


def test_po_problems():
	ok = [{"item_code": "GP", "qty": 2, "rate": 100, "material_request": "MR-1", "approved": True}]
	assert po_problems(ok, "Tata", "2026-11-10", False) == []
	keys = lambda *a: [k for k, _w in po_problems(*a)]
	bad = [{"item_code": "GP", "qty": 0, "rate": 0, "material_request": None, "approved": False}]
	assert keys(bad, None, None, False) == ["po_no_supplier", "po_no_date", "po_no_items", "po_zero_rate", "po_without_request"]
	assert keys(bad, "Tata", "2026-11-10", True) == ["po_no_items", "po_zero_rate"]


def test_receipt_rows_and_problems():
	po_rows = [{"name": "r1", "item_code": "GP", "qty": 10}, {"name": "r2", "item_code": "BOLT", "qty": 100}]
	assert received_rows(po_rows, {"r1": 4, "r2": 0}) == [{"name": "r1", "item_code": "GP", "qty": 4.0}]
	assert received_rows(po_rows, {}) == [{"name": "r1", "item_code": "GP", "qty": 10.0}, {"name": "r2", "item_code": "BOLT", "qty": 100.0}]
	assert received_rows(po_rows, {"BOLT": 50}) == [{"name": "r1", "item_code": "GP", "qty": 10.0}, {"name": "r2", "item_code": "BOLT", "qty": 50.0}]
	rows = [{"item_code": "GP", "qty": 4, "purchase_order": "PO-1"}]
	assert receipt_problems(rows, False, False, "CH-77") == []
	keys = lambda *a: [k for k, _w in receipt_problems(*a)]
	assert keys([{"item_code": "GP", "qty": 0, "purchase_order": None}], False, False, "") == ["receipt_no_qty", "receipt_no_po", "receipt_no_challan"]
	assert keys([{"item_code": "GP", "qty": 1, "purchase_order": None}], True, False, "x") == []
	assert keys([{"item_code": "GP", "qty": 1, "purchase_order": None}], False, True, "x") == []


def test_issue_rows_and_problems():
	items = [{"item_code": "GP", "qty": 2}, {"item_code": "BOLT", "qty": 10, "warehouse": "Rack - SK"}]
	rows, use_card = issue_rows(items, {"GP": "Store - SK"}, "Main - SK", "WIP - SK", {"GP": "jc1", "BOLT": "jc2"})
	assert use_card and rows[0] == {"item_code": "GP", "qty": 2.0, "s_warehouse": "Store - SK", "t_warehouse": "WIP - SK", "job_card_item": "jc1"}
	assert rows[1]["s_warehouse"] == "Rack - SK"
	rows, use_card = issue_rows(items, {}, "Main - SK", "WIP - SK", {"GP": "jc1"})
	assert not use_card and "job_card_item" not in rows[0] and rows[0]["s_warehouse"] == "Main - SK"
	assert issue_problems(TO_JOB, rows, "WO-1", "Issued to Satish") == []
	keys = lambda *a: [k for k, _w in issue_problems(*a)]
	assert keys(TO_JOB, [{"item_code": "GP", "qty": 0, "s_warehouse": None, "t_warehouse": "WIP"}], None, "") == [
		"issue_no_items", "issue_no_job", "issue_no_store", "issue_no_taker"]
	assert keys("Material Receipt", [{"item_code": "GP", "qty": 1}], None, None) == []
