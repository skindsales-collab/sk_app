# SK 20-Nov "CNA - no deal": which notes may send a lead for its quote (deal)
from sk_app.writers.lead_rules import note_moves_to_quote


def test_no_answer_notes_never_make_a_deal():
	for t in ("CNA", "cna", "C.N.A.", "CNA - customer did not answer", "busy, call back tomorrow", "switched off",
			"not reachable", "Did not pick", "no answer 2 times", "CNA security cabin 8x8"):
		assert not note_moves_to_quote(t), t


def test_requirement_notes_do():
	for t in ("Security cabin 8x8x8.6 3 qty", "Needs office cabin 20 x 10 at Chakan site", "asked rate for toilet block",
			"machine shifting from Bhosari to Talegaon"):
		assert note_moves_to_quote(t), t


def test_photo_or_real_talk_does():
	assert note_moves_to_quote("", photo=True)
	assert note_moves_to_quote("Call · Talked · wants quotation next week", talked=True)


def test_plain_chat_does_not():
	assert not note_moves_to_quote("ok")
	assert not note_moves_to_quote("will call again")
