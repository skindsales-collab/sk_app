from sk_app.writers.payment_rules import direction, problems


def test_direction():
	assert direction("Sales Invoice") == "Receive" and direction("Purchase Invoice") == "Pay" and direction("Item") is None


def test_problems():
	assert problems("Sales Invoice", "SI-1", 100, 100, "Bank", "IMPS1") == []
	assert problems("Sales Invoice", "SI-1", 100, None, "Cash", None) == []
	keys = lambda *a: [k for k, _w in problems(*a)]
	assert keys("Item", None, 0, None, None, None) == ["payment_not_linked", "payment_no_amount"]
	assert keys("Sales Invoice", "SI-1", 500, 100, "Bank", " ") == ["payment_above_due", "payment_no_utr"]
