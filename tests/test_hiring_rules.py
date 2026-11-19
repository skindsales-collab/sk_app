"""SK HR hiring (17-Nov-2026): question set per role family, scores and bands, e-mail fallback, messages, no forbidden topics."""

from sk_app.hiring_rules import (applicant_email, band, clean_scores, family_of, feedback_result, forbidden_words, message, overall,
	questions_for, rank, stars, summary_text, teach_back_score)

BANK = [{"code": "C1", "family": "C", "seq": 1, "en": "Tell us about yourself"}, {"code": "C2", "family": "C", "seq": 2, "en": "Flexibility"},
	{"code": "F1", "family": "F", "seq": 1, "en": "Which jobs"}, {"code": "FT", "family": "F", "seq": 6, "is_test": 1, "en": "Tape measure"},
	{"code": "F2", "family": "F", "seq": 2, "en": "Plan a day"}, {"code": "S1", "family": "S", "seq": 1, "en": "Enquiry"}]


def test_question_set_common_then_family_then_test():
	assert [q["code"] for q in questions_for("F", BANK)] == ["C1", "C2", "F1", "F2", "FT"]
	assert [q["code"] for q in questions_for(None, BANK)] == ["C1", "C2"]


def test_family_from_designation():
	m = {"Electrician": "F", "Sales Executive - Frontline": "S"}
	assert family_of("Electrician", m) == "F" and family_of("Sales Executive - Frontline", m) == "S"
	assert family_of("Senior Electrician", m) == "F" and family_of("Chef", m) is None


def test_email_fallback_like_staff_logins():
	assert applicant_email("Ram@Example.com", "98220") == "ram@example.com"
	assert applicant_email("", "+91 98220 12345") == "9822012345@applicant.skind.local"
	assert applicant_email(None, "123") is None


def test_scores_need_a_quote_and_never_reject():
	data = {"traits": [{"skill": "Attitude", "score": 4, "evidence": "I redid the weld"}, {"skill": "Role Skill", "score": 3, "evidence": "x"},
		{"skill": "Learning Ability", "score": 5, "evidence": "4 of 4 steps"}, {"skill": "Flexibility", "score": 4, "evidence": "y"},
		{"skill": "Communication", "score": 9, "evidence": ""}], "reliability": "Reject: 3 jobs in a year", "strengths": ["a", "b", "c", "d"],
		"concerns": ["c1", "c2", "c3"], "round2_questions": ["q1", "q2", "q3", "q4"], "one_line": "Good welder"}
	s = clean_scores(data)
	comm = next(t for t in s["traits"] if t["skill"] == "Communication")
	assert comm["score"] is None and comm["note"] == "not enough answer"
	assert s["overall"] == 3.9 and s["band"] == "SK to decide"  # weights re-scale when a trait has no quote (checker 17-Nov)
	assert "reject" not in s["reliability"].lower() and len(s["strengths"]) == 3 and len(s["concerns"]) == 2 and len(s["round2_questions"]) == 3
	assert feedback_result("Call for Round 2") == "Cleared" and feedback_result("SK to decide") == "Cleared" and feedback_result("Hold") is None


def test_bands_and_teach_back():
	assert band(4.0) == "Call for Round 2" and band(3.9) == "SK to decide" and band(2.9) == "Hold" and band(None) == "Not enough answer"
	assert overall([]) is None and teach_back_score(4) == 5 and teach_back_score(0) == 1
	assert stars(4) == "★★★★☆" and stars(None) == "—"


def test_rank_best_first_unscored_last():
	rows = rank([{"name": "a", "overall": 3.2}, {"name": "b", "overall": None}, {"name": "c", "overall": 4.4}])
	assert [r["name"] for r in rows] == ["c", "a", "b"] and rows[0]["rank"] == 1 and rows[0]["of"] == 3


def test_forbidden_topics_and_messages():
	assert forbidden_words("What is your salary expectation?") == ["salary"] and forbidden_words("तुमचे वय किती?") == ["age"]
	assert forbidden_words("Tell us about a mistake you made at work") == []
	txt = message("W3", name="Ram", date="18-Nov", time="10:30", address="MIDC Bhosari")
	assert "Ram" in txt and "मुलाखत" in txt and "salary" not in txt.lower()
	assert summary_text("Ram", "Electrician", clean_scores({"traits": [], "one_line": "x"})).startswith("Ram · Electrician")


from sk_app.hiring_rules import R2_STANDARD, claude_questions_from, combined, r2_average, r2_feedback_scores, r2_questions


def test_round2_questions_claude_first_then_five_standard():
	qs = r2_questions(["How do you check paint finish?", "One site fitting that went wrong?", "What would you learn first?", "extra"])
	assert len(qs) == 3 + 5 and qs[0]["kind"] == "claude" and qs[3]["q"] == R2_STANDARD[0][0] and qs[3]["mr"]
	assert claude_questions_from("Claude Round 1: 4.0 / 5 · Call for Round 2 · Ask: 1) How do you check paint finish? 2) One site fitting that went wrong? 3) What first?") == \
		["How do you check paint finish?", "One site fitting that went wrong?", "What first?"]
	assert claude_questions_from("no questions here") == []


def test_round2_taps_average_feedback_and_combined():
	rows = [{"q": "a", "quality": 4, "confidence": 5, "attitude": 4, "flexibility": 3}, {"q": "b", "quality": 2, "confidence": None, "attitude": 4, "flexibility": 4}]
	assert r2_average(rows) == round((4 + 5 + 4 + 3 + 2 + 4 + 4) / 7, 1)
	fb = {t["skill"]: t["score"] for t in r2_feedback_scores(rows, 5)}  # 5 = Learning Ability carried over from Round 1
	assert fb == {"Attitude": 4, "Role Skill": 3, "Learning Ability": 5, "Flexibility": 4, "Communication": 5}
	assert r2_feedback_scores([{"q": "x", "tags": ["Calm"]}], None)[2]["score"] is None  # tags and feel never score
	assert "selected" in message("W9", name="Ram", job="Electrician").lower() and "15" in message("W6b", name="Ram") and "meeting us" in message("W7", name="Ram")
	assert combined(4.0, 3.5) == 3.7 and combined(None, 3.5) == 3.5 and combined(4.2, None) == 4.2 and combined(None, None) is None


from datetime import datetime, timedelta

from sk_app.hiring_rules import FREE_REPLIES_PER_MONTH, may_reply_free


def test_bot_replies_only_free_inside_24h_and_under_the_cap():
	now = datetime(2026, 11, 17, 12, 0)
	assert may_reply_free(now - timedelta(hours=2), now, 10) == (True, "")
	assert may_reply_free(now - timedelta(hours=25), now, 10)[0] is False
	assert may_reply_free(None, now, 0)[0] is False
	ok, why = may_reply_free(now - timedelta(minutes=5), now, FREE_REPLIES_PER_MONTH)
	assert not ok and "Business app" in why
	assert "WorkIndia" in message("W0", name="Ram", job="Electrician")
