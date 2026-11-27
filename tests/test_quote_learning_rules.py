import pytest

from sk_app import quote_learning_rules as R

LINES = [{"kind": "cabin", "qty": 2, "rate": 100000, "amount": 200000}, {"kind": "option", "qty": 2, "rate": 5000, "amount": 10000},
	{"kind": "transport", "qty": 2, "rate": 6000, "amount": 12000}]


def test_similar_cabins_share_a_key():
	slabs = [[80, 1200], [160, 1100], [320, 1000]]
	assert R.band(60, slabs) == R.band(80, slabs) == "upto 80 sq ft"
	assert R.band(100, slabs) == "upto 160 sq ft" and R.band(500, slabs) == "large"
	assert R.band(0, None, "10x8") == "size 10x8"
	assert R.spec_key("design", "", "  LGSF   Office ") == "design | lgsf office"


def test_corrected_amount_goes_into_the_cabin_rate():
	rate = R.correction_rate(LINES, 202000, 2)  # options + transport (22,000) stay
	assert rate == 90000
	with pytest.raises(ValueError):
		R.correction_rate(LINES, 20000, 2)


def test_back_calculation():
	c = R.implied(100000, 90000, 200)
	assert c["factor"] == 0.9 and c["pct"] == -10 and c["per_sqft"] == 450 and c["teaches"]
	assert not R.implied(100000, 10000, 200)["teaches"]  # a typing slip never teaches


def test_lower_is_checked_like_a_discount():
	assert R.below_pct(222000, 202000) == 9.01
	assert R.below_pct(222000, 250000) == 0


def test_learned_amount_is_the_median_and_ignores_slips():
	out = R.learned(100000, [0.9, 0.95, 1.1, 5.0], qty=2, round_to=500)
	assert out["n"] == 3 and out["factor"] == 0.95 and out["rate"] == 95000 and out["cabins"] == 190000
	assert R.learned(100000, [], 1) is None and R.learned(100000, [9], 1) is None
