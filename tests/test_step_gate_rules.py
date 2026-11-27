from sk_app import step_gate_rules as R


def keys(x):
	return [k for k, _w in x]


def test_send_to_design_needs_requirement_and_size():
	assert R.send_to_design("Office cabin 20x10") == []
	assert R.send_to_design("20 ft x 10 office") == []
	assert keys(R.send_to_design("office cabin")) == ["size"]
	assert keys(R.send_to_design("", 20, 10)) == ["requirement"]


def test_design_status():
	assert keys(R.design_status("Drawing Sent", 0, 0)) == ["drawing"]
	assert R.design_status("Drawing Sent", 1, 0) == []
	assert keys(R.design_status("BOM & Quote Sent", 1, 0)) == ["quote_value"]
	assert R.design_status("Sent to Design", 0, 0) == []


def test_purchase_steps():
	assert keys(R.purchase_order("Registered Regular", None, False, 2)) == ["gstin", "address", "schedule_date"]
	assert R.purchase_order("Unregistered", None, True, 0) == []
	assert keys(R.purchase_invoice("", None, 1)) == ["bill_no", "bill_date", "receipt"]
	assert keys(R.purchase_receipt(None, 0)) == ["challan", "photo"]


def test_store_dispatch_project():
	assert keys(R.stock_issue("Material Issue", None, None)) == ["cabin"]
	assert R.stock_issue("Material Receipt", None, None) == [] and R.stock_issue("Material Issue", "WO-1", None) == []
	assert keys(R.delivery_note(None, None, False)) == ["qc", "vehicle_no", "transport"]
	assert keys(R.project_close("Completed", 0)) == ["handover"] and R.project_close("Open", 0) == []


def test_accounts_hr():
	assert keys(R.payment("Receive", "Customer", 0)) == ["references"]
	assert R.payment("Internal Transfer", None, 0) == [] and R.payment("Pay", "Employee", 0) == []
	assert keys(R.expense_claim(None, 0, 0)) == ["employee", "bill"] and R.expense_claim("E1", 0, 1) == []
	assert keys(R.employee_login({"cell_number": "x"})) == ["date_of_joining", "department", "designation"]


def test_notice_says_what_who_why():
	n = R.notice("Purchase Order PO-1", [("gstin", "Supplier GSTIN")], "Purchase", "Rushi")
	assert "Missing:" in n and "• Supplier GSTIN" in n and "Who fills it: Rushi (Purchase)" in n and "ERPNext" in n
