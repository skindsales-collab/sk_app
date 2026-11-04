from sk_app.core.fact_rules import score, words


def test_short_query_needs_every_word():
	q = words("non cabin owner")
	assert score(q, "Owner of non-cabin data", "All non-cabin data belongs to Aditya") > 0
	assert score(words("cabin rate"), "Owner of non-cabin data", "Aditya") == 0


def test_long_question_matches_on_some_words():
	q = words("Who should I give the non cabin quotation of Rothe Erde to, which salesperson?")
	assert score(q, "Owner of non-cabin data", "All non-cabin data (customers, quotes, orders) belongs to Aditya; salesperson auto") > 0


def test_topic_words_count_more():
	q = words("cash payment")
	a = score(q, "Payments mode", "cash allowed with reason; net banking")
	b = score(q, "Opening cash", "cash in hand 1,72,052 payment")
	assert a > 0 and b > 0


def test_stop_words_dropped():
	assert words("What is the GST wording for the quote?") == ["gst", "wording", "quote"]
