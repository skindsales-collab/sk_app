# SK 20-Nov: cabin requirement words -> ticks; Annual Revenue amount -> customer budget (Irfan Ansari deal 00168)
from sk_app.writers.lead_rules import cabin_fill


def test_irfan_deal():
	d = {"custom_special_requirements": "2 Nos. cabin required 20ft x 10ft x 8.6ft.\\n1st cabin is required attached toilet and washroom\\n2nd cabin required plain",
		"annual_revenue": 435000, "custom_customer_budget": 0, "expected_deal_value": 0, "custom_toilet_required": 0}
	assert cabin_fill(d) == {"custom_toilet_required": 1, "custom_customer_budget": 435000, "expected_deal_value": 435000}


def test_ac_furniture_and_nothing_cleared():
	d = {"custom_special_requirements": "office with split AC, 2 workstation tables", "custom_ac_required": 0,
		"custom_furniture_required": 0, "custom_toilet_required": 1, "custom_customer_budget": 300000, "annual_revenue": 500000}
	assert cabin_fill(d) == {"custom_ac_required": 1, "custom_furniture_required": 1}


def test_plain_cabin_sets_nothing():
	assert cabin_fill({"custom_special_requirements": "plain cabin 10x8, back side window"}) == {}
