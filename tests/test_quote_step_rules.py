from sk_app.quote_step_rules import DRAWING_FIRST, QUALIFY_FIRST_QUOTE, may_qualify, quote_problem


def test_steps_in_order_sk_21_nov():
	assert not may_qualify(0) and may_qualify(1)
	assert quote_problem("Cabin", None, False) == QUALIFY_FIRST_QUOTE
	for status in ("Not Required", "Sent to Design", "In Design", "Drawing Sent", "Revision Requested", "On Hold", None):
		assert quote_problem("Cabin", status, True) == DRAWING_FIRST, status
	assert quote_problem("Cabin", "Drawing Approved", True) is None
	assert quote_problem("Cabin", "BOM & Quote Sent", True) is None
	assert quote_problem("Non-Cabin", None, True) is None  # machine shifting: no drawing step
