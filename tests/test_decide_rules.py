"""PR B Home: the "Decide now" strip, at most 4 items, the person's functions in order, only what is waiting."""

from sk_app.core.decide_rules import MAX, keys_for, pick


def test_ceo_sees_approvals_overdue_unbilled_low_stock():
	got = pick(["Management"], {"approvals": 3, "overdue_orders": 2, "unbilled": 21, "low_stock": 5})
	assert [(x["key"], x["n"], x["go"]) for x in got] == [("approvals", 3, "po_approvals"), ("overdue_orders", 2, "dispatch"),
		("unbilled", 21, "invoices"), ("low_stock", 5, "low_stock")]


def test_only_waiting_items_and_at_most_four():
	assert pick(["Sales"], {"leads_untouched": 0, "quotes_waiting": 4}) == [{"key": "quotes_waiting", "n": 4, "label": "quotations waiting",
		"go": "follow_up"}]
	many = pick(["Management", "Sales", "Stores"], {k: 1 for k in keys_for(["Management", "Sales", "Stores"])})
	assert len(many) == MAX and [x["key"] for x in many][:4] == ["approvals", "overdue_orders", "unbilled", "low_stock"]
	assert pick(["Stores", "Management"], {"low_stock": 2, "mr_waiting": 1})[1]["key"] == "low_stock"  # no repeat of low_stock
	assert len(pick(["Stores", "Management"], {"low_stock": 2, "mr_waiting": 1})) == 2


def test_a_sales_login_reads_only_sales_counts():
	assert keys_for(["Sales"]) == {"leads_untouched", "quotes_waiting"}
	assert keys_for(["HR"]) == set() and pick(["HR"], {"approvals": 9}) == []
