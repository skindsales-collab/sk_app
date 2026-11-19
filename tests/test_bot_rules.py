"""The WhatsApp hiring bot as a state machine (Rev 1, 17-Nov-2026): a whole conversation per dummy candidate, no frappe."""

from sk_app.bot_rules import say, step

QS = [{"code": "C1", "en": "Tell us about yourself", "mr": "स्वतःबद्दल सांगा", "hi": "अपने बारे में"}, {"code": "C5", "en": "teach back", "mr": "x", "hi": "y"},
	{"code": "F1", "en": "Which jobs", "mr": "कोणती कामे", "hi": "कौन से काम"}, {"code": "FT", "en": "Practical: tape", "mr": "p", "hi": "p", "is_test": 1}]
CTX = {"name": None, "jobs": ["Electrician", "Sales Executive"], "job_names": {"Electrician": "JO-1"}, "questions": QS,
	"teach_back": {"mr": "लाल टाइल दाबा", "hi": "लाल टाइल", "en": "tap the red tile"}, "slots": [{"date": "2026-11-18", "time": "10:00"}, {"date": "2026-11-18", "time": "10:30"}, {"date": "2026-11-19", "time": "11:00"}], "address": "MIDC Bhosari"}


def run(msgs, state=None, data=None):
	out = []
	for m in msgs:
		inc = m if isinstance(m, dict) else {"text": m}
		replies, state, data, effects = step(state, data or {}, inc, CTX)
		out.append((replies, state, effects))
	return out, state, data


def test_bot_says_it_is_a_bot_asks_language_and_consent():
	out, state, data = run(["Hi", "1", "होय"])
	assert "बॉट" in out[0][0][0] and out[0][1] == "lang"
	assert data["language"] == "Marathi" and out[1][1] == "consent"
	assert out[2][1] == "resume" and {"kind": "consent"} in out[2][2]


def test_resume_photo_then_basic_questions_then_done_no_interview_on_whatsapp():
	# R12 (SK 17-Nov): the bot collects basic data only; the interview is on the tablet
	out, state, data = run(["hi", "3", "yes", "a photo of me", {"media": {"kind": "image", "url": "/private/files/r.jpg"}}, "Ramesh Patil", "1", "3 years", "Pune", "ABC Fab"])
	assert "does not look like a resume" in out[3][0][0] and out[3][1] == "resume"
	assert any(e["kind"] == "resume" for e in out[4][2]) and out[4][1] == "f_name"
	assert any(e["kind"] == "applicant" for e in out[9][2]) and state == "done" and "contact you on WhatsApp" in out[9][0][0]
	assert not any(e["kind"] == "start_interview" for o in out for e in o[2])
	assert all("sk-apply" not in r and "http" not in r for o in out for r in o[0])  # no link to the candidate


def test_no_resume_five_questions_then_done():
	out, state, data = run(["hi", "2", "हाँ", "नहीं", "Ramesh Patil", "1", "3 saal", "Pune", "ABC Fab"])
	assert out[3][1] == "f_name" and data["name"] == "Ramesh Patil" and data["job"] == "Electrician" and data["experience"] == 3.0
	assert any(e["kind"] == "applicant" for e in out[8][2]) and state == "done" and "स्वचालित" in out[8][0][0]


def test_hr_salary_and_after_done():
	out, state, data = run(["hi", "1", "होय", "नाही", "Sita", "2", "1", "Nashik", "XYZ", "पगार किती?", "HR"])
	assert state == "hr" and any(e["kind"] == "hand_to_hr" for e in out[10][2])
	assert "पगाराबद्दल HR" in out[9][0][0]


def test_hr_and_delete_words():
	out, state, data = run(["hi", "1", "होय", "मदत"])
	assert state == "hr" and any(e["kind"] == "hand_to_hr" for e in out[3][2])
	out, state, data = run(["hi", "3", "yes", "DELETE"])
	assert state == "done" and any(e["kind"] == "delete" for e in out[3][2]) and "deleted" in out[3][0][0]


def test_bot_never_says_salary_or_score():
	for key in ("hello", "consent", "resume", "resume_again", "basic_done", "done", "slots", "booked"):
		for lang in ("Marathi", "Hindi", "English"):
			txt = say(key, lang, n=1, name="x", slots="s", date="d", time="t", address="a", jobs="j", i=1, q="q", text="x")
			assert "salary" not in txt.lower() and "पगार" not in txt and "score" not in txt.lower()
