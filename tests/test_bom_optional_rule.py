def test_design_status_allows_quote_without_bom():
	from sk_app.quote_step_rules import quote_problem

	for ok in ("Drawing Approved", "Quote Ready", "BOM & Quote Sent"):
		assert quote_problem("Cabin", ok, True) is None
	assert quote_problem("Cabin", "Drawing Sent", True)  # the drawing is sent, not approved yet
