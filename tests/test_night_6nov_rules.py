"""Rules added for the 7-Nov 7 AM PR: GST fill, payment → bill(s), people without login, switch gate."""
from sk_app.core.gate_rules import compare
from sk_app.writers.app_user_rules import missing_logins
from sk_app.writers.payment_allocate_rules import allocate, by_narration
from sk_app.writers.taxes_rules import needs_fill, pick_template, same_state

T = [{"name": "Output GST In-state - SITSPL", "company": "SK", "disabled": 0, "is_default": 0},
	{"name": "Output GST Out-state - SITSPL", "company": "SK", "disabled": 0, "is_default": 0},
	{"name": "Output GST RCM In-state - SITSPL", "company": "SK", "disabled": 0, "is_default": 0},
	{"name": "Output GST In-state - SKE", "company": "SKE", "disabled": 0, "is_default": 0}]


def test_gst_template():
	assert pick_template(T, "SK", True) == "Output GST In-state - SITSPL"
	assert pick_template(T, "SK", False) == "Output GST Out-state - SITSPL"
	assert pick_template(T, "SKE", False) is None
	assert pick_template(T + [{"name": "Std", "company": "SK", "disabled": 0, "is_default": 1}], "SK", False) == "Std"
	assert same_state("27AAAA", "27BBBB", None, None) and not same_state("27AAAA", "24BBBB", None, None)
	assert same_state(None, None, "Maharashtra", "Maharashtra") and not same_state(None, None, "Gujarat", "Maharashtra")
	assert same_state(None, None, None, None)
	assert needs_fill("Sales Order", 0, None, 1000) and not needs_fill("Quotation", 0, None, 1000)
	assert not needs_fill("Sales Invoice", 2, None, 1000) and not needs_fill("Sales Invoice", 0, "T", 1000) and not needs_fill("Sales Order", 0, None, 0)


INV = [{"name": "SI-1", "outstanding": 10000, "date": "2026-10-01"}, {"name": "SI-2", "outstanding": 20000, "date": "2026-10-10"},
	{"name": "SI-3", "outstanding": 30000, "date": "2026-10-20"}, {"name": "SI-4", "outstanding": 25000, "date": "2026-10-25"}]


def test_allocate():
	assert allocate(20000, INV) == ([{"name": "SI-2", "amount": 20000.0}], "same amount")
	assert allocate(30000, INV)[1] == "same amount"  # an exact invoice beats the oldest-first sum (10000 + 20000)
	rows, why = allocate(60000, INV)  # 10000 + 20000 + 30000
	assert why == "oldest invoices add up" and [r["name"] for r in rows] == ["SI-1", "SI-2", "SI-3"]
	rows, why = allocate(45000, INV)  # 20000 + 25000 is the only set
	assert why == "invoices add up" and sorted(r["name"] for r in rows) == ["SI-2", "SI-4"]
	assert allocate(55000, INV) == ([], "more than one set of invoices adds up")  # 30000+25000 or 10000+20000+25000
	assert allocate(7000, INV) == ([], "no invoice or set of invoices matches")
	assert allocate(5000, INV[:1]) == ([{"name": "SI-1", "amount": 5000.0}], "part payment of the only open invoice")
	assert allocate(0, INV)[0] == [] and allocate(100, [])[1] == "no open invoice"
	named = [{**i, "name": "ACC-SINV-2026-0000" + i["name"][-1]} for i in INV]  # real names are long; a short key is not matched
	rows, why = allocate(45000, named, "paid against ACC-SINV-2026-00003 and ACC-SINV-2026-00002 by NEFT")
	assert why == "bill number in narration" and [r["name"] for r in rows] == ["ACC-SINV-2026-00002", "ACC-SINV-2026-00003"]
	assert sum(r["amount"] for r in rows) == 45000
	rows, why = allocate(50000, named, "ref ACC-SINV-2026-00003")  # narration wins, allocation up to the invoice
	assert rows == [{"name": "ACC-SINV-2026-00003", "amount": 30000.0}]
	same = [{"name": "A", "outstanding": 500, "date": "2026-10-01"}, {"name": "B", "outstanding": 500, "date": "2026-10-02"}]
	assert allocate(500, same) == ([], "several invoices of this amount")
	assert by_narration("PUR/NC/066/25-26 paid", [{"name": "PINV-1", "bill_no": "PUR/NC/066/25-26"}]) == [{"name": "PINV-1", "bill_no": "PUR/NC/066/25-26"}]


def test_missing_logins():
	emp = [{"name": "E1", "employee_name": "A", "user_id": "a@x", "cell_number": "9999999999", "status": "Active"},
		{"name": "E2", "employee_name": "B", "user_id": None, "cell_number": "+91 98888 88888", "status": "Active"},
		{"name": "E3", "employee_name": "C", "user_id": None, "cell_number": None, "status": "Active"},
		{"name": "E4", "employee_name": "D", "user_id": None, "cell_number": "9", "status": "Left"}]
	sup = [{"name": "S1", "supplier_name": "Tech", "mobile": "09922847858"}, {"name": "S2", "supplier_name": "Done", "mobile": None}]
	out = missing_logins(emp, sup, {"a@x"}, {"S2"})
	assert [(o["kind"], o["name"], o["mobile"], o["can_make"]) for o in out] == [
		("Employee", "E2", "9888888888", True), ("Employee", "E3", "", False), ("Supplier", "S1", "9922847858", True)]


def test_gate_compare():
	before = {"Sales Order": {"total": 105, "by_owner": {"a": 60, "b": 45}}, "CRM Lead": {"total": 3391, "by_owner": {"a": 3391}}}
	now = {"Sales Order": {"total": 108, "by_owner": {"a": 63, "b": 45}}, "CRM Lead": {"total": 3391, "by_owner": {"a": 3391}}}
	new = {"Sales Order": {"total": 3, "by_owner": {"a": 3}}, "CRM Lead": {"total": 0, "by_owner": {}}}
	r = compare(before, now, new)
	assert r["ok"] and r["rows"][0] == {"doctype": "Sales Order", "before": 105, "now": 108, "new": 3, "missing": 0}
	now["Sales Order"] = {"total": 106, "by_owner": {"a": 63, "b": 43}}
	r = compare(before, now, new)
	assert not r["ok"] and r["missing"] == {"Sales Order": {"total": 2, "by_owner": {"b": 2}}}
	assert compare({}, {}, {})["ok"]
