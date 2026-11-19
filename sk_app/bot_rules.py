"""Pure rules of the WhatsApp hiring bot (Rev 1 + R12 / R13, SK 17-Nov-2026): a basic chat only, as a small state machine:
language, consent, the resume (PDF or a photo of it, never the candidate's own photo, never a link), then name, job,
experience, city and last company. No interview on WhatsApp: Round 1 happens on the office tablet.

step(state, data, incoming) -> (replies, new_state, new_data, effects). No frappe here: the same engine runs on the
WhatsApp Cloud API, on the Mac test console and in the 10-candidate test. Rules: the bot always says it is an automated
assistant; "HR" / "मदत" hands over to Aarti at any point; "DELETE" removes the data; salary talk gets "HR will discuss
this in person"; the candidate picks Marathi / Hindi / English; the bot never mentions a score."""

import re

LANGS = {"1": "Marathi", "2": "Hindi", "3": "English"}
HR_WORDS = ("hr", "मदत", "help", "madat")
SALARY_WORDS = ("salary", "पगार", "वेतन", "ctc", "pay ")
T = {  # key: (Marathi, Hindi, English)
	"hello": ("नमस्कार! मी SK Ind Tech Solutions चा स्वयंचलित HR सहाय्यक (बॉट) आहे. भाषा निवडा: 1 मराठी · 2 हिंदी · 3 English",
		"नमस्ते! मैं SK Ind Tech Solutions का स्वचालित HR सहायक (बॉट) हूँ. भाषा चुनिए: 1 मराठी · 2 हिंदी · 3 English",
		"Namaskar! I am the automated HR assistant (bot) of SK Ind Tech Solutions. Choose a language: 1 Marathi · 2 Hindi · 3 English"),
	"consent": ("तुमची माहिती फक्त भरतीसाठी वापरली जाईल. निवड न झाल्यास ६ महिने ठेवली जाईल. केव्हाही 'HR' लिहून माणसाशी बोलू शकता. पुढे जाण्यासाठी 'होय' लिहा.",
		"आपकी जानकारी सिर्फ भर्ती के लिए इस्तेमाल होगी. चयन न होने पर 6 महीने रखी जाएगी. कभी भी 'HR' लिखकर इंसान से बात कर सकते हैं. आगे बढ़ने के लिए 'हाँ' लिखिए.",
		"Your details are used only for hiring and kept 6 months if not selected. Type 'HR' at any time to talk to a person. Type 'yes' to continue."),
	"resume": ("कृपया तुमचा बायोडाटा पाठवा: PDF किंवा बायोडाट्याचा फोटो. (तुमचा स्वतःचा फोटो नको.) नसेल तर 'नाही' लिहा, मी ५ छोटे प्रश्न विचारेन.",
		"कृपया अपना बायोडाटा भेजिए: PDF या बायोडाटा की फोटो. (अपनी खुद की फोटो नहीं.) नहीं है तो 'नहीं' लिखिए, मैं 5 छोटे सवाल पूछूँगा.",
		"Please send your resume: a PDF or a photo of the resume. (Not a photo of yourself.) If you have none, type 'no' and I will ask 5 short questions."),
	"resume_again": ("ते बायोडाटा वाटत नाही. कृपया बायोडाट्याचा PDF किंवा फोटो पाठवा, किंवा 'नाही' लिहा.", "यह बायोडाटा नहीं लगता. कृपया बायोडाटा का PDF या फोटो भेजिए, या 'नहीं' लिखिए.",
		"That does not look like a resume. Please send the resume as a PDF or a photo of it, or type 'no'."),
	"basic_done": ("धन्यवाद {name}! तुमची माहिती मिळाली. SK Ind Tech ची टीम WhatsApp वर संपर्क करेल. (हा स्वयंचलित सहाय्यक आहे.)",
		"धन्यवाद {name}! आपकी जानकारी मिल गई. SK Ind Tech की टीम WhatsApp पर संपर्क करेगी. (यह स्वचालित सहायक है.)",
		"Thank you {name}! We have your details. The SK Ind Tech team will contact you on WhatsApp. (This is an automated assistant.)"),
	"q_name": ("तुमचे पूर्ण नाव?", "आपका पूरा नाम?", "Your full name?"),
	"q_job": ("कोणत्या पदासाठी अर्ज करत आहात? {jobs}", "किस पद के लिए आवेदन कर रहे हैं? {jobs}", "Which job are you applying for? {jobs}"),
	"q_exp": ("किती वर्षांचा अनुभव? (उदा. 3)", "कितने साल का अनुभव? (जैसे 3)", "How many years of experience? (e.g. 3)"),
	"q_city": ("तुमचे शहर / गाव?", "आपका शहर / गाँव?", "Your city / town?"),
	"q_last": ("शेवटची कंपनी?", "पिछली कंपनी?", "Your last company?"),
	"got_resume": ("धन्यवाद {name}. तुमचा अर्ज मिळाला. HR टीम २ कामाच्या दिवसांत उत्तर देईल.", "धन्यवाद {name}. आपका आवेदन मिला. HR टीम 2 कार्य दिवसों में जवाब देगी.",
		"Thank you {name}. We received your application. HR will reply within 2 working days."),
	"choice": ("पहिली मुलाखत: 1 आता WhatsApp वर द्या (सुमारे २० मिनिटे, आवाज किंवा मजकूर) · 2 ऑफिसमध्ये येऊन टॅबलेटवर द्या",
		"पहला इंटरव्यू: 1 अभी WhatsApp पर दीजिए (लगभग 20 मिनट, आवाज़ या टेक्स्ट) · 2 ऑफिस आकर टैबलेट पर दीजिए",
		"First interview: 1 answer now on WhatsApp (about 20 minutes, voice or text) · 2 come to the office (tablet)"),
	"start": ("ठीक आहे. {n} प्रश्न आहेत. प्रत्येकाला आवाज (व्हॉइस नोट) किंवा मजकुराने उत्तर द्या. थांबायचे असल्यास 'थांबा' लिहा; ४८ तासांत पुढे सुरू करता येईल.",
		"ठीक है. {n} सवाल हैं. हर एक का जवाब आवाज़ (वॉइस नोट) या टेक्स्ट से दीजिए. रुकना हो तो 'रुको' लिखिए; 48 घंटे में आगे जारी रख सकते हैं.",
		"OK. There are {n} questions. Answer each by voice note or text. Type 'stop' to pause; you can continue within 48 hours."),
	"q": ("प्रश्न {i}/{n}: {q}", "सवाल {i}/{n}: {q}", "Question {i}/{n}: {q}"),
	"teach": ("आता एक छोटे काम समजावतो, नीट ऐका: {text} ... आता हे तुम्ही तुमच्या शब्दांत मला परत सांगा.",
		"अब एक छोटा काम समझाता हूँ, ध्यान से सुनिए: {text} ... अब इसे अपने शब्दों में मुझे वापस बताइए.",
		"Now I explain one small task, listen carefully: {text} ... Now explain it back to me in your own words."),
	"too_short": ("थोडे अधिक सांगाल का? एक-दोन वाक्यांत.", "थोड़ा और बताइए? एक-दो वाक्य में.", "Could you say a little more? One or two sentences."),
	"voice_nt": ("आवाज समजला नाही. कृपया मजकुरात लिहा.", "आवाज़ समझ नहीं आई. कृपया टेक्स्ट में लिखिए.", "I could not understand the voice note. Please type it."),
	"done": ("संपले, धन्यवाद {name}! HR टीम तपासून २ कामाच्या दिवसांत कळवेल.", "पूरा हुआ, धन्यवाद {name}! HR टीम जाँच कर 2 कार्य दिवसों में बताएगी.",
		"Finished, thank you {name}! HR will check and reply within 2 working days."),
	"paused": ("थांबलो. ४८ तासांत 'पुढे' लिहून सुरू करा.", "रुक गए. 48 घंटे में 'आगे' लिखकर शुरू कीजिए.", "Paused. Type 'continue' within 48 hours to go on."),
	"slots": ("मुलाखतीची वेळ निवडा: {slots}. 1, 2 किंवा 3 लिहा.", "इंटरव्यू का समय चुनिए: {slots}. 1, 2 या 3 लिखिए.", "Pick an interview time: {slots}. Reply 1, 2 or 3."),
	"booked": ("नक्की: {date} रोजी {time} वाजता. पत्ता: {address}. आदल्या दिवशी आठवण करू.", "पक्का: {date} को {time} बजे. पता: {address}. एक दिन पहले याद दिलाएँगे.",
		"Confirmed: {date} at {time}. Address: {address}. We will remind you the day before."),
	"hr": ("ठीक आहे, HR (आरती) तुमच्याशी बोलतील. कृपया थोडी वाट पहा.", "ठीक है, HR (आरती) आपसे बात करेंगी. कृपया थोड़ा इंतज़ार कीजिए.", "OK, HR (Aarti) will talk to you. Please wait a little."),
	"salary": ("पगाराबद्दल HR प्रत्यक्ष भेटीत बोलतील.", "वेतन के बारे में HR व्यक्तिगत मुलाकात में बात करेंगे.", "HR will discuss salary in person."),
	"deleted": ("तुमच्या विनंतीनुसार तुमची माहिती हटवली आहे.", "आपके अनुरोध पर आपकी जानकारी हटा दी गई है.", "Your details have been deleted, as you asked."),
	"unknown": ("समजले नाही. 1, 2 किंवा 3 लिहा, किंवा 'HR' लिहा.", "समझ नहीं आया. 1, 2 या 3 लिखिए, या 'HR' लिखिए.", "I did not understand. Reply 1, 2 or 3, or type 'HR'."),
	"later": ("सध्या जागा निघाल्यास आम्ही संपर्क करू. धन्यवाद.", "जगह निकलने पर हम संपर्क करेंगे. धन्यवाद.", "We will contact you when a matching opening comes. Thank you."),
}
YES = ("yes", "y", "ho", "हो", "होय", "हाँ", "haan", "ha", "ok", "ओके", "1")
NO = ("no", "n", "nahi", "नाही", "नहीं", "nako", "2")
CONTINUE = ("continue", "पुढे", "आगे", "aage", "pudhe", "start", "सुरू")
STOP = ("stop", "थांबा", "रुको", "ruko", "thamba", "pause")


def say(key: str, lang: str | None, **kw) -> str:
	idx = {"Marathi": 0, "Hindi": 1, "English": 2}.get(lang or "", 0)
	return T[key][idx].format(**{k: (v if v not in (None, "") else "—") for k, v in kw.items()})


def _low(text) -> str:
	return (text or "").strip().lower()


def is_hr_request(text) -> bool:
	return _low(text) in HR_WORDS or _low(text).startswith("hr ")


def is_salary(text) -> bool:
	return any(w in _low(text) for w in SALARY_WORDS)


def step(state: str | None, data: dict, incoming: dict, ctx: dict) -> tuple[list[str], str, dict, list[dict]]:
	"""incoming: {text, media: {kind: 'image|document|audio', url}, transcript}. ctx: {jobs: [titles], questions: [{code, en, mr, hi, is_test}],
	teach_back: {mr, hi, en}, slots: [{date, time}], address, name}. Returns (replies, state, data, effects)."""
	data = dict(data or {})
	text = incoming.get("text") or ""
	low = _low(text)
	lang = data.get("language")
	effects: list[dict] = []
	if low == "delete":
		return [say("deleted", lang)], "done", data, [{"kind": "delete"}]
	if is_hr_request(text):
		return [say("hr", lang)], "hr", data, [{"kind": "hand_to_hr", "why": "candidate asked for HR"}]
	if is_salary(text):
		return [say("salary", lang)], state or "lang", data, effects
	if state in (None, "", "lang"):
		if low in LANGS:
			data["language"] = LANGS[low]
			return [say("consent", data["language"])], "consent", data, effects
		return [say("hello", None)], "lang", data, effects
	if state == "consent":
		if low in YES:
			data["consent"] = True
			return [say("resume", lang)], "resume", data, [{"kind": "consent"}]
		return [say("consent", lang)], "consent", data, effects
	if state == "resume":
		# R12 (SK 17-Nov): the bot asks only for the resume (PDF or a photo of it), never the candidate's own photo and never a link;
		# anything else gets a polite ask-again; then the basic questions (name, job, experience, city, last company)
		media = incoming.get("media") or {}
		if media.get("kind") in ("image", "document"):
			data["resume_url"] = media.get("url")
			effects.append({"kind": "resume", "url": media.get("url")})
			return [say("q_name", lang)], "f_name", data, effects
		if low in NO:
			return [say("q_name", lang)], "f_name", data, effects
		return [say("resume_again", lang) if (text or media) else say("resume", lang)], "resume", data, effects
	if state == "f_name":
		data["name"] = text.strip()[:140]
		return [say("q_job", lang, jobs=" · ".join(f"{i}. {j}" for i, j in enumerate(ctx.get("jobs") or [], 1)))], "f_job", data, effects
	if state == "f_job":
		jobs = ctx.get("jobs") or []
		pick = jobs[int(low) - 1] if low.isdigit() and 0 < int(low) <= len(jobs) else next((j for j in jobs if low and low in j.lower()), text.strip()[:140])
		data["job"] = pick
		return [say("q_exp", lang)], "f_exp", data, effects
	if state == "f_exp":
		m = re.search(r"\d+(?:\.\d+)?", text or "")
		data["experience"] = float(m.group(0)) if m else 0
		return [say("q_city", lang)], "f_city", data, effects
	if state == "f_city":
		data["city"] = text.strip()[:80]
		return [say("q_last", lang)], "f_last", data, effects
	if state == "f_last":
		data["last_employer"] = text.strip()[:140]
		effects.append({"kind": "applicant", "data": data})
		# R12: basic chat only. No interview on WhatsApp: the team books the Round 1 slot (a 'Slot:' comment) and the tablet asks the questions.
		return [say("basic_done", lang, name=data.get("name"))], "done", data, effects
	if state in ("done", "hr"):
		return [say("later", lang)] if state == "done" else [say("hr", lang)], state, data, effects
	return [say("unknown", lang)], state or "lang", data, effects
