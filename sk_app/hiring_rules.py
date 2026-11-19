"""Pure rules of SK App hiring (SK 17-Nov-2026, spec SKIT/HR/HIRE/001). No frappe here: tested without a site.

Round 1 on a tablet: 6 common questions, then the role family's 5 questions and 1 practical test. Claude scores 5
traits 1-5 with the candidate's own words as proof; Reliability is a flag, never a score. Bands: 4.0+ Call for Round 2,
3.0-3.9 SK to decide, below 3.0 Hold. Claude never rejects anyone: Aarti or SK decides. No salary anywhere."""

import re

FAMILIES = {"C": "Common (all roles)", "S": "Sales", "M": "Marketing", "D": "Design", "F": "Factory & Site", "T": "Store",
	"P": "Machine Shifting & Maintenance", "A": "Accounts", "H": "HR & Admin", "E": "ERP & IT"}
FAMILIES_MR = {"S": "विक्री", "M": "मार्केटिंग", "D": "डिझाइन", "F": "फॅक्टरी व साईट", "T": "स्टोअर", "P": "मशीन शिफ्टिंग व मेंटेनन्स",
	"A": "अकाउंट्स", "H": "एचआर व प्रशासन", "E": "ERP व IT"}
TRAITS = [("Attitude", 0.25), ("Role Skill", 0.25), ("Learning Ability", 0.20), ("Flexibility", 0.20), ("Communication", 0.10)]
SKILLS = [t for t, _w in TRAITS]
BANDS = (("Call for Round 2", 4.0), ("SK to decide", 3.0), ("Hold", 0.0))
STATUS_NEW, STATUS_REPLIED, STATUS_SHORTLISTED, STATUS_HOLD, STATUS_SELECTED, STATUS_NOT = "Open", "Replied", "Shortlisted", "Hold", "Accepted", "Rejected"
EMAIL_DOMAIN = "applicant.skind.local"
FORBIDDEN = {"religion": ("religion", "धर्म", "caste", "जात", "जाति"), "marriage": ("married", "marriage", "लग्न", "शादी", "विवाह"),
	"pregnancy / family plans": ("pregnan", "गर्भ", "family plan", "मुले होणार", "बच्चे"), "age": ("how old", "your age", "तुमचे वय", "आपकी उम्र"),
	"salary": ("salary", "पगार", "वेतन", "ctc")}
KEEP_MONTHS = 6  # a not-selected candidate's voice files and resume are deleted after 6 months (DPDP)


def family_of(designation: str | None, mapping: dict) -> str | None:
	"""Role family from the designation (the spec's table); None when the designation is not in it."""
	if not designation:
		return None
	if designation in mapping:
		return mapping[designation]
	low = designation.lower()
	for name, fam in mapping.items():
		if name.lower() in low or low in name.lower():
			return fam
	return None


def questions_for(family: str | None, bank: list[dict]) -> list[dict]:
	"""The tablet's question list: common first, then the family's questions, the practical test last."""
	common = sorted((q for q in bank if q.get("family") == "C" and q.get("active", 1)), key=lambda q: (q.get("seq") or 0, q["code"]))
	own = sorted((q for q in bank if q.get("family") == family and q.get("active", 1)), key=lambda q: (bool(q.get("is_test")), q.get("seq") or 0, q["code"]))
	return common + own


def applicant_email(email: str | None, mobile: str | None) -> str | None:
	"""Job Applicant needs an e-mail; many workers have none: <mobile>@applicant.skind.local, like the staff logins."""
	email = (email or "").strip().lower()
	if "@" in email:
		return email
	digits = re.sub(r"\D", "", mobile or "")[-10:]
	return f"{digits}@{EMAIL_DOMAIN}" if len(digits) == 10 else None


def forbidden_words(text: str) -> list[str]:
	low = (text or "").lower()
	return [topic for topic, words in FORBIDDEN.items() if any(w in low for w in words)]


def teach_back_score(steps_right: int) -> int:
	return {4: 5, 3: 4, 2: 3, 1: 2}.get(int(steps_right or 0), 1)


def overall(traits: list[dict]) -> float | None:
	"""Weighted average of the scored traits (a trait without a quote is left out). None when nothing is scored."""
	weights = dict(TRAITS)
	num, den = 0.0, 0.0
	for t in traits or []:
		score = t.get("score")
		if score in (None, "", 0) or not (t.get("evidence") or "").strip():
			continue
		w = weights.get(t.get("skill"), 0)
		num += w * float(score)
		den += w
	return round(num / den, 1) if den else None


def band(score: float | None) -> str:
	if score is None:
		return "Not enough answer"
	for name, floor in BANDS:
		if score >= floor:
			return name
	return "Hold"


def clean_scores(data: dict) -> dict:
	"""Claude's JSON made safe: whole-number scores 1-5, no score without a quote, overall and band recomputed, never
	'Reject' anywhere, at most 3 strengths / 2 concerns / 3 Round 2 questions."""
	out = {"traits": [], "reliability": str(data.get("reliability") or "OK")[:300], "strengths": [], "concerns": [], "resume_check": [],
		"round2_questions": [], "one_line": str(data.get("one_line") or "")[:300]}
	by = {t.get("skill"): t for t in (data.get("traits") or []) if isinstance(t, dict)}
	for skill in SKILLS:
		t = by.get(skill) or {}
		evidence = str(t.get("evidence") or "").strip()
		try:
			score = int(round(float(t.get("score")))) if evidence else None
		except (TypeError, ValueError):
			score = None
		score = min(5, max(1, score)) if score else None
		out["traits"].append({"skill": skill, "score": score, "evidence": evidence[:400] if score else "", "note": "" if score else "not enough answer"})
	out["overall"] = overall(out["traits"])
	out["band"] = band(out["overall"])
	out["strengths"] = [str(x)[:300] for x in (data.get("strengths") or [])[:3]]
	out["concerns"] = [str(x)[:300] for x in (data.get("concerns") or [])[:2]]
	out["round2_questions"] = [str(x)[:300] for x in (data.get("round2_questions") or [])[:3]]
	for rc in (data.get("resume_check") or [])[:6]:
		if isinstance(rc, dict):
			out["resume_check"].append({"claim": str(rc.get("claim") or "")[:150], "result": str(rc.get("result") or "not tested")[:30], "why": str(rc.get("why") or "")[:200]})
	text = " ".join([out["reliability"], out["one_line"], *out["strengths"], *out["concerns"]]).lower()
	if "reject" in text:
		out["one_line"] = out["one_line"].replace("Reject", "Hold").replace("reject", "hold")
		out["reliability"] = out["reliability"].replace("Reject", "Hold").replace("reject", "hold")
	return out


def feedback_result(band_name: str) -> str | None:
	"""Interview Feedback.result: Cleared for Call for Round 2 and SK to decide; Hold stays blank (Aarti decides); never Rejected."""
	return "Cleared" if band_name in ("Call for Round 2", "SK to decide") else None


def stars(score) -> str:
	n = int(round(float(score or 0)))
	return "★" * n + "☆" * (5 - n) if n else "—"


def rank(rows: list[dict]) -> list[dict]:
	"""Ranked list for a job: best overall first, unscored last; each row gets rank and total."""
	scored = sorted((r for r in rows if r.get("overall") is not None), key=lambda r: -float(r["overall"]))
	rest = [r for r in rows if r.get("overall") is None]
	out = scored + rest
	for i, r in enumerate(out, 1):
		r["rank"], r["of"] = i, len(out)
	return out


def summary_text(name: str, job: str, scores: dict, rank_no=None, of=None) -> str:
	"""The 1-page summary as plain text (the app renders it; the same goes into Interview Feedback)."""
	lines = [f"{name} · {job}" + (f" · Rank {rank_no} of {of}" if rank_no else ""),
		f"Overall {scores.get('overall') if scores.get('overall') is not None else '—'} / 5 · {scores.get('band')}"]
	lines += [f"{t['skill']}: {stars(t['score'])}" + (f" — {t['evidence']}" if t.get("evidence") else " — not enough answer") for t in scores.get("traits", [])]
	lines.append(f"Reliability: {scores.get('reliability') or 'OK'}")
	if scores.get("strengths"):
		lines.append("Strengths: " + " | ".join(scores["strengths"]))
	if scores.get("concerns"):
		lines.append("Concerns: " + " | ".join(scores["concerns"]))
	if scores.get("resume_check"):
		lines.append("Resume check: " + " | ".join(f"{r['claim']}: {r['result']}" + (f" ({r['why']})" if r.get("why") else "") for r in scores["resume_check"]))
	if scores.get("round2_questions"):
		lines.append("Ask in Round 2: " + " | ".join(f"{i}) {q}" for i, q in enumerate(scores["round2_questions"], 1)))
	if scores.get("one_line"):
		lines.append(scores["one_line"])
	return "\n".join(lines)


# WhatsApp texts (EN + MR), Phase 1: HR taps Send and the text opens in WhatsApp; Phase 2: sent by the Cloud API
FREE_REPLY_HOURS = 24      # R11: the bot replies only inside Meta's free 24-hour service window the candidate opened
FREE_REPLIES_PER_MONTH = 950  # R11: stop before the 1,000 free service replies per number per month
MESSAGES = {
	"W0": ("Namaskar {name}, you applied for {job} at SK Ind Tech on WorkIndia. Reply 1 to start your application on WhatsApp.",
		"नमस्कार {name}, तुम्ही WorkIndia वर SK Ind Tech मध्ये {job} पदासाठी अर्ज केला. WhatsApp वर अर्ज सुरू करण्यासाठी 1 पाठवा."),
	"W2": ("Thank you {name}. We received your application for {job}. We will reply within 2 working days.",
		"धन्यवाद {name}. {job} पदासाठी तुमचा अर्ज मिळाला. २ कामाच्या दिवसांत आम्ही उत्तर देऊ."),
	"W3": ("{name}, please come for the first interview on {date} at {time}. Address: {address}. It takes about 30 minutes, on a tablet, in Marathi, Hindi or English. Reply 1 to confirm or 2 to change the time.",
		"{name}, पहिल्या मुलाखतीसाठी {date} रोजी {time} वाजता या. पत्ता: {address}. सुमारे ३० मिनिटे, टॅबलेटवर, मराठी, हिंदी किंवा इंग्रजीत. नक्की असल्यास 1, वेळ बदलायची असल्यास 2 पाठवा."),
	"W4": ("Reminder: your interview at SK Ind Tech is tomorrow at {time}.", "आठवण: SK Ind Tech मध्ये तुमची मुलाखत उद्या {time} वाजता आहे."),
	"W5": ("{name}, you are selected for the second interview with our CEO on {date} at {time}.", "{name}, आमच्या CEO सोबत दुसऱ्या मुलाखतीसाठी तुमची निवड झाली आहे: {date}, {time}."),
	"W6": ("Thank you {name}. There is no opening matching your profile now. We will keep your details for 6 months and contact you if one opens.",
		"धन्यवाद {name}. सध्या तुमच्या प्रोफाइलला योग्य जागा नाही. तुमची माहिती ६ महिने ठेवू आणि जागा निघाल्यास संपर्क करू."),
	"W7": ("Thank you {name} for meeting us. We are not moving ahead this time. We wish you all the best.",
		"{name}, भेटीसाठी धन्यवाद. या वेळी आम्ही पुढे जात नाही आहोत. तुम्हाला पुढील वाटचालीसाठी शुभेच्छा."),
	"W6b": ("Thank you {name}. Your profile is on hold after the second interview. We will contact you within 15 days.",
		"धन्यवाद {name}. तुमची प्रोफाइल सध्या होल्डवर आहे. १५ दिवसांत आम्ही संपर्क करू."),
	"W9": ("Congratulations {name}! You are selected for {job} at SK Ind Tech Solutions. HR will call you today with the joining date and documents list.",
		"अभिनंदन {name}! SK Ind Tech Solutions मध्ये {job} पदासाठी तुमची निवड झाली आहे. रुजू होण्याची तारीख आणि कागदपत्रांची यादी सांगण्यासाठी HR आज तुम्हाला फोन करेल."),
	"W8": ("Your details have been deleted, as you asked.", "तुमच्या विनंतीनुसार तुमची माहिती हटवली आहे."),
}


def may_reply_free(last_message_on, now, sent_this_month: int) -> tuple[bool, str]:
	"""(ok, why not): the bot may reply only when the candidate wrote first within 24 hours and the month's free replies are
	not used up (R11, SK 17-Nov 'free only'). Otherwise SK / Samir reply by hand from the Business app."""
	if not last_message_on:
		return False, "candidate has not written first"
	if (now - last_message_on).total_seconds() > FREE_REPLY_HOURS * 3600:
		return False, "more than 24 hours since the candidate's last message"
	if sent_this_month >= FREE_REPLIES_PER_MONTH:
		return False, f"{FREE_REPLIES_PER_MONTH} free replies used this month: reply by hand in the Business app"
	return True, ""


def message(key: str, **values) -> str:
	"""English + Marathi in one text, blanks left readable."""
	en, mr = MESSAGES[key]
	safe = {k: (v or "—") for k, v in values.items()}
	for k in ("name", "job", "date", "time", "address"):
		safe.setdefault(k, "—")
	text = en.format(**safe) + "\n\n" + mr.format(**safe)
	assert "salary" not in text.lower() and "पगार" not in text
	return text


# ---- SK's Round 2 on the tablet (R8, SK 17-Nov): Claude's 3 questions, then 5 standard ones, then SK's own ----
R2_STANDARD = [
	("Tell me about the hardest job you did. What was your part?", "तुम्ही केलेले सर्वात अवघड काम सांगा. त्यात तुमचा भाग काय होता?"),
	("Your senior is wrong in front of a customer. What do you do?", "ग्राहकासमोर तुमचे वरिष्ठ चुकीचे बोलत आहेत. तुम्ही काय कराल?"),
	("Where do you want to be in 3 years?", "३ वर्षांनी तुम्ही कुठे असावे असे वाटते?"),
	("What will you do in your first 30 days here?", "इथे पहिल्या ३० दिवसांत तुम्ही काय कराल?"),
	("Do you have any question for us?", "तुम्हाला आम्हाला काही विचारायचे आहे का?"),
]
R2_TAGS = ["Good eye contact", "Calm", "Confident", "Nervous", "Honest", "Avoids eye contact", "Evasive", "Over-confident"]
R2_TAGS_MR = {"Good eye contact": "चांगला नजरसंपर्क", "Calm": "शांत", "Confident": "आत्मविश्वासू", "Nervous": "घाबरलेला", "Honest": "प्रामाणिक",
	"Avoids eye contact": "नजर टाळतो", "Evasive": "टाळाटाळ", "Over-confident": "अतिआत्मविश्वास"}
R2_RATINGS = ("quality", "confidence", "attitude", "flexibility")


def r2_questions(claude_questions: list[str], evidence: dict | None = None) -> list[dict]:
	"""The Round 2 list: Claude's questions (with the Round 1 reason) first, then SK's 5 standard ones."""
	out = [{"q": q, "mr": "", "why": (evidence or {}).get(q) or "Round 1 weak point", "kind": "claude"} for q in (claude_questions or [])[:3] if q]
	out += [{"q": en, "mr": mr, "why": "", "kind": "standard"} for en, mr in R2_STANDARD]
	return out


def r2_average(entries: list[dict]) -> float | None:
	"""Average of SK's taps (quality, confidence, attitude, flexibility) over the answered questions, 1 decimal."""
	vals = [float(e[k]) for e in entries or [] for k in R2_RATINGS if e.get(k)]
	return round(sum(vals) / len(vals), 1) if vals else None


def r2_feedback_scores(entries: list[dict], r1_learning=None) -> list[dict]:
	"""SK's taps as the 5 skills for Interview Feedback (checker 17-Nov): only rated questions count; quality -> Role Skill,
	confidence -> Communication, attitude -> Attitude, flexibility -> Flexibility; Learning Ability carries over from
	Round 1. Tags and the overall feel are shown, never scored."""
	def avg(k):
		v = [float(e[k]) for e in entries or [] if e.get(k)]
		return round(sum(v) / len(v)) if v else None
	return [{"skill": "Attitude", "score": avg("attitude")}, {"skill": "Role Skill", "score": avg("quality")},
		{"skill": "Learning Ability", "score": int(r1_learning) if r1_learning else None}, {"skill": "Flexibility", "score": avg("flexibility")},
		{"skill": "Communication", "score": avg("confidence")}]


def combined(r1_overall, r2_avg) -> float | None:
	"""Final = Round 1 × 40% + SK's Round 2 ratings × 60% (R8); one side missing = the other alone."""
	if r1_overall is None and r2_avg is None:
		return None
	if r1_overall is None:
		return round(float(r2_avg), 1)
	if r2_avg is None:
		return round(float(r1_overall), 1)
	return round(0.4 * float(r1_overall) + 0.6 * float(r2_avg), 1)


def claude_questions_from(text: str | None) -> list[str]:
	"""The 3 Round 2 questions out of Claude's 'Claude Round 1: … Ask: 1) … 2) … 3) …' comment or feedback text."""
	import re as _re

	t = text or ""
	m = _re.search(r"Ask(?: in Round 2)?\s*:\s*(.+)", t, _re.S)
	if not m:
		return []
	body = m.group(1).split("\n")[0] if "1)" not in m.group(1).split("\n")[0] else m.group(1)
	parts = [x.strip(" |·") for x in _re.split(r"\s*\d\)\s*", body) if x.strip(" |·")]
	return [x.split("\n")[0].strip() for x in parts][:3]


# ---- self-service Round 1 in the meeting room (R9 / R10, SK 17-Nov: no HR person) ----
VIDEO_KEEP_DAYS = 7
INTERVIEWER_NAME = "SK HR Sahayak"
DISCLOSURE = {"English": "This is an automated interviewer of SK Ind Tech Solutions, not a live person.",
	"Marathi": "हा SK Ind Tech Solutions चा स्वयंचलित मुलाखतकार आहे, खरी व्यक्ती नाही.", "Hindi": "यह SK Ind Tech Solutions का स्वचालित इंटरव्यूअर है, कोई वास्तविक व्यक्ति नहीं."}
CONSENT = {
	"English": "Your video and voice will be recorded only for this job. The CEO may view it. Your spoken answers are turned into text and analysed by AI (Claude) and outside speech services. The video is deleted automatically after 7 days, and backup copies are removed within the backup period (up to 30 days). The written answers and scores are kept for 6 months. You may refuse; then you will be interviewed in person with no penalty. To withdraw or ask for deletion at any time, message HR WhatsApp.",
	"Marathi": "तुमचा व्हिडिओ आणि आवाज फक्त या नोकरीसाठी रेकॉर्ड केला जाईल. CEO तो पाहू शकतात. तुमची बोललेली उत्तरे मजकुरात बदलून AI (Claude) आणि बाहेरील स्पीच सेवांकडून तपासली जातात. व्हिडिओ ७ दिवसांनी आपोआप हटवला जातो, आणि बॅकअप प्रती बॅकअप कालावधीत (जास्तीत जास्त ३० दिवस) काढल्या जातात. लिखित उत्तरे आणि गुण ६ महिने ठेवले जातात. तुम्ही नकार देऊ शकता; मग तुमची मुलाखत प्रत्यक्ष होईल, कोणताही तोटा नाही. केव्हाही माघार घेण्यासाठी किंवा हटवण्यासाठी HR WhatsApp वर संदेश पाठवा.",
	"Hindi": "आपका वीडियो और आवाज़ सिर्फ इस नौकरी के लिए रिकॉर्ड होगी. CEO इसे देख सकते हैं. आपके बोले गए जवाब टेक्स्ट में बदलकर AI (Claude) और बाहरी स्पीच सेवाओं से जाँचे जाते हैं. वीडियो 7 दिन बाद अपने आप हट जाता है, और बैकअप प्रतियाँ बैकअप अवधि (अधिकतम 30 दिन) में हटा दी जाती हैं. लिखित जवाब और अंक 6 महीने रखे जाते हैं. आप मना कर सकते हैं; तब आपका इंटरव्यू आमने-सामने होगा, कोई नुकसान नहीं. कभी भी वापस लेने या हटाने के लिए HR WhatsApp पर संदेश भेजिए.",
}
AGREE_WORDS = ("i agree", "agree", "मान्य", "सहमत", "ho", "हो", "हाँ", "yes")


def said_agree(text: str | None) -> bool:
	low = (text or "").strip().lower()
	return any(w in low for w in AGREE_WORDS)


def speech_measures(words: int, start_delay_s, duration_s, long_pauses) -> dict:
	"""Information only, never a score (R9.5): pace and pauses are not judged."""
	dur = float(duration_s or 0)
	return {"start_delay_s": round(float(start_delay_s or 0), 1), "duration_s": round(dur, 1), "wpm": int(round(words / (dur / 60))) if dur >= 5 and words else None,
		"long_pauses": int(long_pauses or 0)}


def speech_line(answers: list[dict]) -> str:
	"""'Speech: answered 11/12, average 55 sec, pace normal' for SK's card; pace is only named, never scored."""
	if not answers:
		return ""
	answered = [a for a in answers if (a.get("text") or "").strip()]
	durs = [float(a.get("duration_s") or 0) for a in answered if a.get("duration_s")]
	wpms = [a["wpm"] for a in answered if a.get("wpm")]
	avg = round(sum(durs) / len(durs)) if durs else None
	mean = sum(wpms) / len(wpms) if wpms else None
	pace = "n/a" if mean is None else "normal" if 80 <= mean <= 160 else "slow" if mean < 80 else "fast"
	return f"Speech: answered {len(answered)}/{len(answers)}" + (f", average {avg} sec" if avg else "") + f", pace {pace}"
