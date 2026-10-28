"""Training tile: short lessons per function, ticked Done by each person. HR / managers add more lessons in ERPNext."""

import frappe
from frappe.utils import now_datetime

# Starter lessons on using the app. Seeded once (by title); edits made in ERPNext are never overwritten.
APP_LESSONS = [
	("Start: open the app and add it to your phone", "सुरुवात: ॲप उघडा आणि फोनवर जोडा", "All", 1,
		"<ol><li>Open Chrome and go to <b>/sk</b> on the ERPNext site.</li><li>Log in with your own ERPNext ID and password.</li>"
		"<li>Tap ⋮ then <b>Add to Home screen</b>. Now SK App opens like any app.</li><li>Tap <b>मराठी / English</b> at the top to change language.</li></ol>",
		"<ol><li>Chrome उघडा आणि ERPNext साईटवर <b>/sk</b> वर जा.</li><li>तुमच्या ERPNext ID आणि पासवर्डने लॉगिन करा.</li>"
		"<li>⋮ दाबा आणि <b>Add to Home screen</b> निवडा. आता SK App इतर ॲपसारखे उघडेल.</li><li>वर <b>मराठी / English</b> दाबून भाषा बदला.</li></ol>"),
	("What to do now card", "आता काय करायचे कार्ड", "All", 2,
		"<ol><li>Every hour the red card tells you the one most important job now.</li><li>Tap <b>Start</b> when you begin and <b>Done</b> when finished: you get the next job at once.</li>"
		"<li><b>Need more time</b> keeps the same job. <b>Problem</b> opens Report Problem.</li><li>🔊 reads the card aloud.</li></ol>",
		"<ol><li>दर तासाला लाल कार्ड आत्ताचे सर्वात महत्त्वाचे एक काम सांगते.</li><li>काम सुरू करताना <b>सुरू</b> आणि संपल्यावर <b>झाले</b> दाबा: लगेच पुढचे काम मिळेल.</li>"
		"<li><b>अजून वेळ हवा</b> तेच काम ठेवते. <b>अडचण</b> समस्या कळवा उघडते.</li><li>🔊 कार्ड वाचून दाखवते.</li></ol>"),
	("Enter a new lead in 1 minute", "1 मिनिटात नवीन लीड टाका", "Sales", 3,
		"<ol><li>Home → <b>New Lead</b>.</li><li>Fastest: tap <b>📷 Photo</b> of a visiting card, enquiry letter or email, drawing, spec sheet, invoice or WhatsApp screenshot. The phone reads it free and fills name, company, mobile, email, source, segment and the requirement (sizes, material, quantity, place). Check and correct.</li>"
		"<li>Or type, or tap 🎤 and speak.</li><li>Pick <b>Source</b> and <b>Segment</b> (Cabin, Machine Shifting, Job Work...).</li><li>Tap <b>Save</b>. The lead is now in ERPNext CRM under your name.</li></ol>",
		"<ol><li>होम → <b>नवीन लीड</b>.</li><li>सर्वात जलद: व्हिजिटिंग कार्ड, चौकशीचे पत्र किंवा ईमेल, ड्रॉइंग, स्पेसिफिकेशन, बिल किंवा WhatsApp स्क्रीनशॉटचा <b>📷 फोटो</b> काढा. फोन तो मोफत वाचतो आणि नाव, कंपनी, मोबाईल, ईमेल, सोर्स, सेगमेंट आणि गरज (साईज, मटेरियल, संख्या, ठिकाण) भरतो. तपासा आणि दुरुस्त करा.</li>"
		"<li>किंवा टाईप करा, किंवा 🎤 दाबून बोला.</li><li><b>Source</b> आणि <b>Segment</b> निवडा (Cabin, Machine Shifting, Job Work...).</li><li><b>जतन करा</b> दाबा. लीड तुमच्या नावाने ERPNext CRM मध्ये जाते.</li></ol>"),
	("Follow-up: call, WhatsApp, email", "फॉलो-अप: कॉल, WhatsApp, ईमेल", "Sales", 4,
		"<ol><li>Home → <b>Follow-up</b> shows all your open leads and deals. Red = overdue, do these first.</li>"
		"<li>New lead: call within <b>5 minutes</b>.</li><li>Tap 📞, 💬 or ✉️. After the call, come back to the app and pick what happened (Talked, No answer...). Add a note by typing, voice or photo.</li>"
		"<li>This is saved in CRM, so your manager sees it and your score counts it.</li></ol>",
		"<ol><li>होम → <b>फॉलो-अप</b> मध्ये तुमचे सर्व उघडे लीड आणि डील दिसतात. लाल = उशीर, हे आधी करा.</li>"
		"<li>नवीन लीड: <b>5 मिनिटांत</b> कॉल करा.</li><li>📞, 💬 किंवा ✉️ दाबा. कॉलनंतर ॲपमध्ये परत या आणि काय झाले ते निवडा (बोलणे झाले, उत्तर नाही...). टाईप, आवाज किंवा फोटोने नोंद जोडा.</li>"
		"<li>हे CRM मध्ये जतन होते, त्यामुळे मॅनेजरला दिसते आणि तुमच्या स्कोअरमध्ये मोजले जाते.</li></ol>"),
	("Lead page: status, drawings, quotation PDF", "लीड पान: स्थिती, ड्रॉइंग, कोटेशन PDF", "Sales", 5,
		"<ol><li>Tap a lead or deal to open it.</li><li>Change <b>Status</b> with one tap.</li>"
		"<li><b>Files</b> shows drawings and photos from design and ERPNext; tap to open. 📎 attaches a photo or file from your phone.</li>"
		"<li><b>Quotations</b> and <b>Sales Orders</b> open as PDF, ready to forward to the customer.</li></ol>",
		"<ol><li>लीड किंवा डील उघडण्यासाठी त्यावर दाबा.</li><li>एका टॅपने <b>स्थिती</b> बदला.</li>"
		"<li><b>फाईल्स</b> मध्ये डिझाईन आणि ERPNext मधील ड्रॉइंग व फोटो दिसतात; उघडण्यासाठी दाबा. 📎 ने फोनमधील फोटो किंवा फाईल जोडा.</li>"
		"<li><b>कोटेशन</b> आणि <b>सेल्स ऑर्डर</b> PDF म्हणून उघडतात, ग्राहकाला पाठवायला तयार.</li></ol>"),
	("My Day, Work Book and DSI", "माझा दिवस, कामाची वही आणि DSI", "All", 6,
		"<ol><li><b>My Day</b>: all your open work, overdue first.</li><li><b>Work Book</b>: write any extra work you did (type, voice, photo).</li>"
		"<li><b>DSI</b>: one Daily Small Improvement every day before 5:30 pm: what you made better, before and after, photo.</li>"
		"<li><b>Report Problem</b>: machine, material, quality, safety, customer, IT, leave.</li></ol>",
		"<ol><li><b>माझा दिवस</b>: तुमची सर्व उघडी कामे, उशिराची आधी.</li><li><b>कामाची वही</b>: केलेले जादा काम लिहा (टाईप, आवाज, फोटो).</li>"
		"<li><b>DSI</b>: रोज संध्याकाळी 5:30 पूर्वी एक छोटी सुधारणा: काय सुधारले, आधी आणि नंतर, फोटो.</li>"
		"<li><b>समस्या कळवा</b>: मशीन, मटेरियल, गुणवत्ता, सुरक्षा, ग्राहक, IT, रजा.</li></ol>"),
	("My Score: KRA and KPI", "माझा स्कोअर: KRA आणि KPI", "All", 7,
		"<ol><li><b>My Score</b> shows your monthly targets and how much is done, counted from ERPNext.</li>"
		"<li>Green = target met, yellow = 80-99%, red = below 80%.</li><li>Score = done ÷ target × weight, up to 120% for each KPI.</li></ol>",
		"<ol><li><b>माझा स्कोअर</b> मध्ये तुमचे महिन्याचे लक्ष्य आणि किती पूर्ण झाले ते ERPNext मधून मोजून दिसते.</li>"
		"<li>हिरवा = लक्ष्य पूर्ण, पिवळा = 80-99%, लाल = 80% पेक्षा कमी.</li><li>स्कोअर = पूर्ण ÷ लक्ष्य × वजन, प्रत्येक KPI साठी 120% पर्यंत.</li></ol>"),
	("Reminders with date and time", "तारीख आणि वेळेसह आठवण", "All", 8,
		"<ol><li>Home → <b>⏰ + Reminder</b>, or ⏰ on a lead page.</li><li>Write or speak what to do, pick date and time, and repeat (daily, weekly, monthly) if needed.</li>"
		"<li>At the time, the open app rings and shows the reminder on Home: tap <b>Done</b> or <b>In 10 min</b>.</li><li>Managers can give a reminder to a team member.</li></ol>",
		"<ol><li>होम → <b>⏰ + आठवण</b>, किंवा लीड पानावर ⏰.</li><li>काय करायचे ते लिहा किंवा बोला, तारीख व वेळ निवडा, गरज असल्यास पुनरावृत्ती (रोज, आठवड्याला, महिन्याला).</li>"
		"<li>वेळ झाल्यावर उघडे ॲप वाजते आणि होमवर आठवण दाखवते: <b>झाले</b> किंवा <b>10 मिनिटांनी</b> दाबा.</li><li>मॅनेजर टीममधील व्यक्तीला आठवण देऊ शकतात.</li></ol>"),
	("Calls: talk time and missed calls", "कॉल: बोलण्याचा वेळ आणि मिस कॉल", "Sales", 9,
		"<ol><li>Call from the app (📞 on Follow-up or a lead). When you come back, pick what happened; the talk time is filled for you, correct it if needed.</li>"
		"<li>Customer called you, or you called from the phone's dialer? Home → <b>Calls</b> → <b>Add a call</b>. A missed call: pick <b>Missed</b>.</li>"
		"<li><b>Calls</b> shows today's and this week's calls, talk time and missed calls. Managers and the CEO see the whole team.</li></ol>",
		"<ol><li>ॲपमधून कॉल करा (फॉलो-अप किंवा लीडवर 📞). परत आल्यावर काय झाले ते निवडा; बोलण्याचा वेळ आपोआप भरतो, गरज असल्यास दुरुस्त करा.</li>"
		"<li>ग्राहकाने कॉल केला, किंवा फोनच्या डायलरवरून कॉल केला? होम → <b>कॉल</b> → <b>कॉल नोंदवा</b>. मिस कॉल: <b>Missed</b> निवडा.</li>"
		"<li><b>कॉल</b> मध्ये आजचे व या आठवड्याचे कॉल, बोलण्याचा वेळ आणि मिस कॉल दिसतात. मॅनेजर आणि CEO यांना पूर्ण टीम दिसते.</li></ol>"),
	("WhatsApp and email from the app", "ॲपमधून WhatsApp आणि ईमेल", "Sales", 10,
		"<ol><li><b>WhatsApp</b>: pick a lead or type any number, choose a ready message, tap <b>Open chat</b>. WhatsApp opens with the text; attach the drawing or PDF there.</li>"
		"<li><b>Mail</b>: on a lead page tap ✉️, write, attach the quotation or drawing, send. The mail is saved on the lead.</li>"
		"<li>Items with 🔒 are paid services, not active now.</li></ol>",
		"<ol><li><b>WhatsApp</b>: लीड निवडा किंवा कोणताही नंबर टाका, तयार मेसेज निवडा, <b>चॅट उघडा</b> दाबा. मजकुरासह WhatsApp उघडते; तिथे ड्रॉइंग किंवा PDF जोडा.</li>"
		"<li><b>मेल</b>: लीड पानावर ✉️ दाबा, लिहा, कोटेशन किंवा ड्रॉइंग जोडा, पाठवा. मेल लीडवर जतन होतो.</li>"
		"<li>🔒 असलेल्या सेवा पेड आहेत, सध्या चालू नाहीत.</li></ol>"),
	("Company & Products: send to customer", "कंपनी व उत्पादने: ग्राहकाला पाठवा", "All", 11,
		"<ol><li>Home → <b>Company & Products</b>: website, presentation, product details, videos, customer FAQ, ready messages and Sales Manual pages.</li>"
		"<li><b>Open</b> to read, <b>Send</b> to share on WhatsApp, <b>Copy</b> to paste anywhere.</li><li>Sales Manual pages open only the pages you need, so the phone stays fast.</li></ol>",
		"<ol><li>होम → <b>कंपनी व उत्पादने</b>: वेबसाईट, प्रेझेंटेशन, उत्पादन माहिती, व्हिडिओ, ग्राहकांचे प्रश्न, तयार मेसेज आणि सेल्स मॅन्युअलची पाने.</li>"
		"<li>वाचण्यासाठी <b>उघडा</b>, WhatsApp वर देण्यासाठी <b>पाठवा</b>, कुठेही चिकटवण्यासाठी <b>कॉपी</b>.</li><li>सेल्स मॅन्युअलची फक्त हवी ती पाने उघडतात, त्यामुळे फोन जलद राहतो.</li></ol>"),
	("Voice typing: tap the mic", "आवाजाने लिहा: माईक दाबा", "All", 12,
		"<ol><li>Tap 🎤 next to a box. It turns red and says <b>Listening… speak now</b>.</li><li>Speak; the words appear as you talk. Tap the red mic to stop.</li>"
		"<li>EN / मर under the mic picks English or Marathi. If it says no permission, allow the microphone for Chrome.</li></ol>",
		"<ol><li>बॉक्सजवळील 🎤 दाबा. तो लाल होतो आणि <b>ऐकत आहे… आता बोला</b> दाखवतो.</li><li>बोला; शब्द लगेच दिसतात. थांबवण्यासाठी लाल माईक दाबा.</li>"
		"<li>माईकखालील EN / मर ने इंग्रजी किंवा मराठी निवडा. परवानगी नाही असे आले तर Chrome ला माईकची परवानगी द्या.</li></ol>"),
	# SK 27-Oct: "need to add this in app training"
	("Marketing list: greetings and promotions", "मार्केटिंग यादी: शुभेच्छा आणि प्रमोशन", "Marketing", 13,
		"<ol><li>The Marketing list is for <b>potential customers who are not leads</b>. We send them festival greetings and promotions to keep in touch.</li>"
		"<li>Open <b>More</b>, then <b>📇 Marketing list</b>.</li>"
		"<li><b>Add one person:</b> tap <b>➕ Add person</b>, then <b>📷 Camera</b> and photograph the visiting card. Name, company, mobile and email fill in by themselves. "
		"Or tap 🎤 and speak. Check the boxes, add the City, then tap <b>Save</b> twice (first tap shows what to check, second tap saves).</li>"
		"<li><b>Add an old list:</b> tap <b>📄 Upload Excel list</b> and pick the Excel or CSV file. It needs a <b>Name</b> and a <b>Mobile</b> column; Company, Email and City are used if present. "
		"A phone or Google Contacts export also works. The same mobile is never added twice.</li>"
		"<li><b>Send a greeting:</b> pick the festival (Diwali, New Year, Ganesh Chaturthi...) and tap <b>💬 Send on WhatsApp</b> next to each person. WhatsApp opens with the message ready; tap send. "
		"People not greeted yet are at the top. Every send is counted for you.</li>"
		"<li><b>Promotion:</b> pick <b>Promotion</b>, type the offer, then send on WhatsApp one by one. To mail everyone at once tap <b>📧 Promotion mail to all</b> (ERPNext Newsletter, group \"Marketing list\").</li>"
		"<li><b>Interested?</b> Tap <b>🔥 Interested: make lead</b>. New Lead opens with the details filled in; pick the Segment and Save.</li>"
		"<li>In ERPNext the list is in <b>Contact</b>, filter <b>Marketing list = Yes</b>.</li></ol>",
		"<ol><li>मार्केटिंग यादी <b>लीड नसलेल्या संभाव्य ग्राहकांसाठी</b> आहे. संपर्क टिकवण्यासाठी त्यांना सणाच्या शुभेच्छा आणि प्रमोशन पाठवतो.</li>"
		"<li><b>More</b> उघडा, मग <b>📇 मार्केटिंग यादी</b>.</li>"
		"<li><b>एक व्यक्ती जोडा:</b> <b>➕ व्यक्ती जोडा</b> दाबा, मग <b>📷 कॅमेरा</b> दाबून व्हिजिटिंग कार्डचा फोटो काढा. नाव, कंपनी, मोबाईल आणि ईमेल आपोआप भरतात. "
		"किंवा 🎤 दाबून बोला. बॉक्स तपासा, शहर टाका, मग <b>जतन करा</b> दोनदा दाबा (पहिल्यांदा काय तपासायचे ते दिसते, दुसऱ्यांदा जतन होते).</li>"
		"<li><b>जुनी यादी जोडा:</b> <b>📄 एक्सेल यादी अपलोड करा</b> दाबा आणि एक्सेल किंवा CSV फाईल निवडा. त्यात <b>Name</b> आणि <b>Mobile</b> कॉलम हवा; Company, Email, City असल्यास तेही घेतले जातात. "
		"फोन किंवा Google Contacts ची फाईलही चालते. एकच मोबाईल दोनदा जोडला जात नाही.</li>"
		"<li><b>शुभेच्छा पाठवा:</b> सण निवडा (दिवाळी, नवीन वर्ष, गणेश चतुर्थी...) आणि प्रत्येक व्यक्तीजवळ <b>💬 WhatsApp वर पाठवा</b> दाबा. मेसेजसह WhatsApp उघडते; पाठवा दाबा. "
		"अजून शुभेच्छा न दिलेले वर दिसतात. प्रत्येक पाठवलेला मेसेज तुमच्या नावाने मोजला जातो.</li>"
		"<li><b>प्रमोशन:</b> <b>प्रमोशन</b> निवडा, ऑफर लिहा, मग एक एक करून WhatsApp वर पाठवा. सर्वांना एकदम मेल करण्यासाठी <b>📧 सर्वांना प्रमोशन मेल</b> दाबा (ERPNext न्यूजलेटर, ग्रुप \"Marketing list\").</li>"
		"<li><b>रस आहे?</b> <b>🔥 रस आहे: लीड बनवा</b> दाबा. माहिती भरलेले नवीन लीड उघडते; सेगमेंट निवडा आणि जतन करा.</li>"
		"<li>ERPNext मध्ये ही यादी <b>Contact</b> मध्ये आहे, फिल्टर <b>Marketing list = Yes</b>.</li></ol>"),
	("Cold Calling list", "कोल्ड कॉलिंग यादी", "Marketing", 14,
		"<ol><li>Call-list data (old or bought lists, leads never called) is kept in <b>🧊 Cold Calling</b>, not in My Leads, so My Leads shows only real enquiries.</li>"
		"<li>Open <b>My Leads</b>, then <b>🧊 Cold Calling</b> at the top. Not-called people are first; search by name or mobile.</li>"
		"<li>Tap 📞 to call. When the customer is interested tap <b>🔥 Interested → My Leads</b>; the lead joins your normal follow-up.</li>"
		"<li>A lead that is only data can be moved back with <b>🧊 Move to Cold Calling</b> on the lead page.</li>"
		"<li>Uploading an Excel with source <b>Cold calling</b> puts the whole list here.</li></ol>",
		"<ol><li>कॉल-लिस्ट डेटा (जुनी किंवा विकत घेतलेली यादी, कधीही कॉल न केलेले लीड) <b>🧊 कोल्ड कॉलिंग</b> मध्ये ठेवला जातो, माझे लीड मध्ये नाही, त्यामुळे माझे लीड मध्ये फक्त खरी चौकशी दिसते.</li>"
		"<li><b>माझे लीड</b> उघडा, मग वर <b>🧊 कोल्ड कॉलिंग</b>. कॉल न केलेले आधी दिसतात; नाव किंवा मोबाईलने शोधा.</li>"
		"<li>📞 दाबून कॉल करा. ग्राहकाला रस असल्यास <b>🔥 रस आहे → माझे लीड</b> दाबा; लीड तुमच्या नेहमीच्या फॉलो-अप मध्ये जातो.</li>"
		"<li>फक्त डेटा असलेला लीड लीड पानावरील <b>🧊 कोल्ड कॉलिंगमध्ये हलवा</b> ने परत हलवता येतो.</li>"
		"<li>सोर्स <b>Cold calling</b> निवडून एक्सेल अपलोड केल्यास पूर्ण यादी इथे येते.</li></ol>"),
]


def seed_lessons():
	from sk_app.manual_lessons import MANUAL_LESSONS, TOPIC
	from sk_app.manuals import FUNCTION_LESSONS

	frappe.db.sql("""update `tabSK Training Lesson` set lesson_type='App usage' where ifnull(lesson_type, '')=''""")
	rows = [(*r, [], "Using the app", "App usage") for r in APP_LESSONS + FUNCTION_LESSONS]
	rows += [(*r, TOPIC, "My function") for r in MANUAL_LESSONS]
	for title, title_mr, function, seq, content, content_mr, questions, topic, kind in rows:
		qs = [{"question": q, "choice_1": c[0], "choice_2": c[1], "choice_3": c[2], "correct": str(ok)} for q, c, ok in questions]
		name = frappe.db.get_value("SK Training Lesson", {"title": title})
		if name:  # app lessons follow the app: keep their text up to date; check questions only while HR has none
			frappe.db.set_value("SK Training Lesson", name, {"content": content, "content_marathi": content_mr}, update_modified=False)
			doc = frappe.get_doc("SK Training Lesson", name)
			if qs and not doc.questions:
				for q in qs:
					doc.append("questions", q)
				doc.save(ignore_permissions=True)
			continue
		frappe.get_doc({"doctype": "SK Training Lesson", "title": title, "title_marathi": title_mr, "function": function,
			"topic": topic, "lesson_type": kind, "sequence": seq, "minutes": 2 if not qs else 4, "published": 1,
			"content": content, "content_marathi": content_mr, "questions": qs}).insert(ignore_permissions=True)


def _functions(user: str, function: str | None = None) -> list[str]:
	"""All the person's functions (point 7: someone in two functions sees the lessons of both)."""
	from sk_app.logins import profile_functions

	out = profile_functions(user) or ([function] if function else [])
	if "Sales" in out and "Marketing" not in out:
		out.append("Marketing")  # every salesperson has the Marketing features (SK 26-Oct)
	return out


def lessons(user: str, function: str) -> list[dict]:
	"""Lessons for the person's functions, without content (opened one at a time), with done / score."""
	rows = frappe.get_all("SK Training Lesson", filters={"published": 1, "function": ["in", ["All", *_functions(user, function)]]},
		fields=["name", "title", "title_marathi", "topic", "lesson_type", "minutes"],
		order_by="sequence asc, creation asc")
	done = {d.lesson: d for d in frappe.get_all("SK Training Done", filters={"user": user}, fields=["lesson", "score", "questions"])}
	for r in rows:
		d = done.get(r.name)
		r["done"] = bool(d)
		r["score"] = f"{d.score}/{d.questions}" if d and d.questions else None
		r["lesson_type"] = r.lesson_type or "App usage"
	return rows


def lesson(user: str, name: str) -> dict:
	"""One lesson with its content and check questions (the correct answers stay on the server)."""
	doc = frappe.get_doc("SK Training Lesson", name)
	if not doc.published:
		frappe.throw(frappe._("Lesson not found"))
	out = {k: doc.get(k) for k in ("name", "title", "title_marathi", "topic", "lesson_type", "minutes", "video_url",
		"content", "content_marathi")}
	out["questions"] = [{"question": q.question, "choices": [c for c in (q.choice_1, q.choice_2, q.choice_3) if c]}
		for q in doc.questions]
	out["pages_url"] = f"/api/method/sk_app.api.library_pdf?item={doc.library_item}" if doc.library_item else None
	out["done"] = bool(frappe.db.exists("SK Training Done", {"user": user, "lesson": name}))
	return out


def pass_mark(total: int) -> int:
	"""2 of 3, or two thirds of the questions rounded up."""
	return -(-2 * total // 3)


def mark_done(user: str, lesson: str, answers: list | None = None) -> dict:
	"""Finish a lesson. With check questions, `answers` (choice numbers 1-3, in order) must reach the pass mark."""
	if not frappe.db.exists("SK Training Lesson", {"name": lesson, "published": 1}):
		frappe.throw(frappe._("Lesson not found"))
	questions = frappe.get_doc("SK Training Lesson", lesson).questions
	answers = [str(a) for a in (answers or [])]
	score = sum(1 for i, q in enumerate(questions) if i < len(answers) and answers[i] == str(q.correct))
	total = len(questions)
	if total and score < pass_mark(total):
		return {"passed": False, "score": score, "questions": total}
	name = frappe.db.get_value("SK Training Done", {"user": user, "lesson": lesson})
	if name:
		frappe.db.set_value("SK Training Done", name, {"score": score, "questions": total})
	else:
		frappe.get_doc({"doctype": "SK Training Done", "user": user, "lesson": lesson, "score": score, "questions": total,
			"completed_on": now_datetime()}).insert(ignore_permissions=True)
	return {"passed": True, "score": score, "questions": total}


def team_progress(manager: str) -> dict:
	"""For managers: how many lessons each team member finished, of those for their function."""
	from sk_app.day_report import _team

	out = []
	for p in _team(manager):
		total = frappe.db.count("SK Training Lesson", {"published": 1, "function": ["in", ["All", *_functions(p.user, p.home)]]})
		done = frappe.db.count("SK Training Done", {"user": p.user})
		out.append({"user": p.user, "full_name": p.full_name, "function": p.home, "done": done, "total": total})
	return {"people": out}


# ---------- FAQ per function, with "Ask a question" (point 7) ----------

FAQ_TAG = "[FAQ question]"


def faq(user: str, q: str | None = None) -> dict:
	"""FAQ of each of the person's functions (Sales: the customer FAQ too), plus questions waiting for my answer."""
	functions = _functions(user)
	cats = ["FAQ", "Customer FAQ"] if {"Sales", "Marketing", "Machine Shifting"} & set(functions) else ["FAQ"]
	filters = {"enabled": 1, "category": ["in", cats], "function": ["in", ["All", *functions]]}
	or_filters = None
	if (q or "").strip():
		like = f"%{q.strip()}%"
		or_filters = [["title", "like", like], ["text", "like", like], ["title_marathi", "like", like], ["text_marathi", "like", like]]
	from sk_app.library import LIST_FIELDS

	rows = frappe.get_all("SK Library Item", filters=filters, or_filters=or_filters, fields=LIST_FIELDS,
		order_by="function asc, sequence asc, title asc", limit=0)
	for r in rows:
		r["kind"] = "file" if r.file else "link" if r.link else "text"
		r["open_url"] = r.file or r.link
		r["sendable"] = r.audience == "Customer"
	asked = frappe.get_all("ToDo", filters={"allocated_to": user, "status": "Open", "description": ["like", f"{FAQ_TAG}%"]},
		fields=["name", "description", "assigned_by", "date"], order_by="creation asc")
	for a in asked:
		a["question"] = frappe.utils.strip_html(a.description)[len(FAQ_TAG):].strip()
		a["by"] = frappe.utils.get_fullname(a.assigned_by) if a.assigned_by else ""
	return {"rows": rows, "to_answer": asked, "functions": functions}


def _owner_of(user: str, function: str) -> str | None:
	"""Who answers a function's questions: the person's own manager, else the first person of the function with a team,
	else Management."""
	from sk_app.store import _users_with_function

	manager = frappe.db.get_value("SK App User", {"user": user}, "manager")
	if manager:
		return manager
	people = _users_with_function(function)
	heads = [p for p in people if p != user and frappe.db.exists("SK App User", {"manager": p, "enabled": 1})]
	return (heads or [p for p in _users_with_function("Management") if p != user] or [None])[0]


def _ceos() -> list[str]:
	from sk_app.requisition import _ceos

	return _ceos()


SCREEN_TAG = " ⟦screen: "


def split_screen(question: str) -> tuple[str, str]:
	"""The question text and the screen it was asked from (kept at the end of the ToDo text)."""
	q = question or ""
	if SCREEN_TAG in q and q.endswith("⟧"):
		q, _sep, screen = q.rpartition(SCREEN_TAG)
		return q.strip(), screen[:-1].strip()
	return q.strip(), ""


def ask(user: str, question: str, function: str | None = None, photo: str | None = None, screen: str | None = None) -> dict:
	"""SK 28-Oct (Rev 1 point 6): "My question" with a screenshot or photo goes to the CEO's Questions screen.
	SK 28-Oct (help on every screen): asked from the ❓ button of any SK App or ERPNext screen, with the screen's name;
	Claude drafts the answer and the action in the background for the CEO to check."""
	if not (question or "").strip():
		frappe.throw(frappe._("Please speak or type the question"))
	function = function or (_functions(user) or ["All"])[0]
	if (screen or "").strip():
		question = f"{question.strip()[:440]}{SCREEN_TAG}{str(screen).strip()[:50]}⟧"
	ceos = [c for c in _ceos() if c != user]
	owner = ceos[0] if ceos else _owner_of(user, function)
	if not owner:
		frappe.throw(frappe._("Nobody to answer yet. Please ask your manager."))
	todo = frappe.get_doc({"doctype": "ToDo", "allocated_to": owner, "assigned_by": user, "status": "Open", "priority": "Medium",
		"description": f"{FAQ_TAG} {function}: {question.strip()[:500]}", "date": frappe.utils.add_days(frappe.utils.nowdate(), 2)}
		).insert(ignore_permissions=True)
	from sk_app.store import attach

	attach(photo, "ToDo", todo.name, user)
	frappe.enqueue("sk_app.training.ai_draft", queue="short", todo=todo.name, enqueue_after_commit=True)
	return {"owner": frappe.utils.get_fullname(owner), "todo": todo.name}


# ---------- Claude's draft answer for the CEO (SK 28-Oct) ----------
AI_TAG = "[AI draft]"
ACTIONS = ("how_to", "app_fix", "erp_setting", "data_fix", "need_info")


def _faq_context(function: str, limit: int = 60) -> str:
	rows = frappe.get_all("SK Library Item", filters={"enabled": 1, "category": ["in", ["FAQ", "Customer FAQ"]],
		"function": ["in", ["All", function]]}, fields=["title", "text"], order_by="sequence asc", limit=limit)
	lessons = frappe.get_all("SK Training Lesson", filters={"published": 1, "function": ["in", ["All", function]]},
		fields=["title", "content"], order_by="sequence asc", limit=40)
	parts = [f"Q: {r.title}\nA: {frappe.utils.strip_html(r.text or '')[:400]}" for r in rows]
	parts += [f"Lesson: {r.title}\n{frappe.utils.strip_html(r.content or '')[:500]}" for r in lessons]
	return "\n\n".join(parts)[:24000]


def ai_draft(todo: str):
	"""Background job: Claude reads the question, the screenshot and the function's FAQ / lessons, and writes a draft
	answer plus what to do (how-to answer, app fix, ERPNext setting, data correction). Kept as a comment on the
	question; nothing is sent to the person until the CEO sends it."""
	from sk_app import claude

	if not claude.available():
		return
	t = frappe.get_doc("ToDo", todo)
	function, question = _question_of(t)
	question, screen = split_screen(question)
	images = []
	for url in _photos("ToDo", t.name)[:2]:
		try:
			f = frappe.get_doc("File", {"file_url": url})
			ext = url.rsplit(".", 1)[-1].lower()
			media = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}.get(ext)
			content = f.get_content()
			if media and len(content) < 4.5 * 1024 * 1024:
				images.append((content, media))
		except Exception:
			continue
	asker = frappe.utils.get_fullname(t.assigned_by) if t.assigned_by else ""
	draft = claude.help_draft(question, function, screen, asker, _faq_context(function), images)
	if draft:
		t.add_comment("Comment", AI_TAG + " " + frappe.as_json(draft, indent=None))


def _draft_of(todo: str) -> dict | None:
	c = frappe.get_all("Comment", filters={"reference_doctype": "ToDo", "reference_name": todo, "comment_type": "Comment",
		"content": ["like", f"{AI_TAG}%"]}, pluck="content", order_by="creation desc", limit=1)
	if not c:
		return None
	try:
		import json

		d = json.loads(frappe.utils.strip_html(c[0])[len(AI_TAG):].strip())
		return d if isinstance(d, dict) else None
	except ValueError:
		return None


def _may_answer(user: str, t) -> bool:
	"""The person it was sent to; any CEO answers the questions sent to the CEO."""
	ceos = _ceos()
	return t.allocated_to == user or (user in ceos and t.allocated_to in ceos)


def answer(user: str, todo: str, text: str, add_to_faq=1) -> dict:
	"""The owner answers; the answer goes back to the person and, when useful, into the function's FAQ."""
	t = frappe.get_doc("ToDo", todo)
	if not _may_answer(user, t) or not (t.description or "").startswith(FAQ_TAG):
		frappe.throw(frappe._("This question is not for you"), frappe.PermissionError)
	if not (text or "").strip():
		frappe.throw(frappe._("Please speak or type the answer"))
	body = frappe.utils.strip_html(t.description)[len(FAQ_TAG):].strip()
	function, _sep, question = body.partition(": ")
	question, _screen = split_screen(question)
	item = None
	if str(add_to_faq) in ("1", "true", "True"):
		meta = frappe.get_meta("SK Library Item").get_field("function").options.split("\n")
		item = frappe.get_doc({"doctype": "SK Library Item", "title": question[:140], "category": "FAQ", "audience": "Internal",
			"function": function if function in meta else "All", "enabled": 1, "text": text.strip()}).insert(ignore_permissions=True).name
	t.db_set("status", "Closed")
	if t.assigned_by:
		frappe.get_doc({"doctype": "ToDo", "allocated_to": t.assigned_by, "assigned_by": user, "status": "Open", "priority": "Low",
			"description": f"Answer to your question \"{question[:120]}\": {text.strip()[:400]}", "date": frappe.utils.nowdate()}
			).insert(ignore_permissions=True)
	return {"faq": item}


# ---------- CEO Questions screen (SK 28-Oct, Rev 1 point 6) ----------
# Questions from Training come to the CEO grouped by function and topic with a one-line summary (free word rules now;
# a Claude summary once the Claude key is added). The CEO answers (typed or spoken), the answer goes to the person and
# into the FAQ, or "Send for development" puts it in the AI & ERP improvement inbox; once built the CEO marks it
# deployed in the app or in ERPNext and the person is told.

DEV_TAG = "[Question]"
STOP = set("""a an the is are was were be to of in on for and or but with how what why when where which who can could should would
do does did i we you my our your it this that these those me us not no yes please sir madam app erp erpnext from by at as
have has had will shall get got give show see use used using make made there their them they he she his her its then than
so if into out up down about all any some one two need want करा कसे काय का आहे नाही मला आम्ही हे ते तो ती मध्ये आणि""".split())


def _question_of(t) -> tuple[str, str]:
	body = frappe.utils.strip_html(t.description or "")[len(FAQ_TAG):].strip()
	function, _sep, question = body.partition(": ")
	return function, question or body


def _keywords(text: str) -> list[str]:
	import re

	return [w for w in re.findall(r"[\w\u0900-\u097F]+", (text or "").lower()) if len(w) > 2 and w not in STOP and not w.isdigit()]


def _check_ceo(user: str):
	if user != "Administrator" and user not in _ceos():
		frappe.throw(frappe._("Only the CEO answers these questions"), frappe.PermissionError)


def _photos(doctype: str, name: str) -> list[str]:
	return frappe.get_all("File", filters={"attached_to_doctype": doctype, "attached_to_name": name}, pluck="file_url", order_by="creation asc")


def questions(user: str) -> dict:
	_check_ceo(user)
	ceos = _ceos() or [user]
	todos = frappe.get_all("ToDo", filters={"allocated_to": ["in", ceos], "status": "Open", "description": ["like", f"{FAQ_TAG}%"]},
		fields=["name", "description", "assigned_by", "date", "creation"], order_by="creation asc", limit=0)
	rows = []
	for t in todos:
		function, question = _question_of(t)
		question, screen = split_screen(question)
		rows.append({"todo": t.name, "function": function, "question": question, "screen": screen, "ai": _draft_of(t.name),
			"by": frappe.utils.get_fullname(t.assigned_by) if t.assigned_by else "",
			"date": str(t.creation)[:16], "photos": _photos("ToDo", t.name), "words": _keywords(question)})
	# topic of a question = its word asked most often across all open questions of the same function
	count = {}
	for r in rows:
		for w in set(r["words"]):
			count[(r["function"], w)] = count.get((r["function"], w), 0) + 1
	groups = {}
	for r in rows:
		ranked = sorted(set(r["words"]), key=lambda w: (-count[(r["function"], w)], w))
		topic = ranked[0] if ranked and count[(r["function"], ranked[0])] > 1 else "other"
		groups.setdefault((r["function"], topic), []).append(r)
	out = []
	for (function, topic), items in sorted(groups.items(), key=lambda g: (-len(g[1]), g[0])):
		people = sorted({i["by"] for i in items if i["by"]})
		label = f"about “{topic}”" if topic != "other" else "on other topics"
		out.append({"function": function, "topic": topic, "rows": [{k: v for k, v in i.items() if k != "words"} for i in items],
			"summary": f"{len(items)} question{'s' if len(items) > 1 else ''} {label} from {', '.join(people) or 'the team'}"})
	dev = frappe.get_all("SK Work Log", filters={"entry_type": "Problem", "description": ["like", f"{DEV_TAG}%"], "status": ["!=", "Done"]},
		fields=["name", "user", "date", "description", "status", "photo"], order_by="date asc", limit=0)
	for d in dev:
		d["by"] = frappe.utils.get_fullname(d.user)
		d["question"] = (d.description or "")[len(DEV_TAG):].strip()
		d["date"] = str(d.date)
	return {"groups": out, "open": len(rows), "dev": dev}


def send_for_development(user: str, todo: str, note: str | None = None) -> dict:
	_check_ceo(user)
	t = frappe.get_doc("ToDo", todo)
	if not (t.description or "").startswith(FAQ_TAG):
		frappe.throw(frappe._("Not a Training question"))
	function, question = _question_of(t)
	photos = _photos("ToDo", t.name)
	clean, where = split_screen(question)
	text = f"{DEV_TAG} {function}: {clean}" + (f" | CEO: {note.strip()}" if (note or "").strip() else "") + (f" | Screen: {where}" if where else "")
	log = frappe.get_doc({"doctype": "SK Work Log", "user": t.assigned_by or user, "date": frappe.utils.nowdate(), "entry_type": "Problem",
		"problem_type": "IT / app", "description": text[:2000], "status": "Open", "photo": photos[0] if photos else None,
		"reference_doctype": "ToDo", "reference_name": t.name}).insert(ignore_permissions=True)
	t.db_set("status", "Closed")
	handoff = None
	if frappe.db.exists("DocType", "SK Hub Handoff"):
		q, screen = split_screen(question)
		handoff = frappe.get_doc({"doctype": "SK Hub Handoff", "from_user": user, "from_team": "Management", "from_project": "SK App ❓",
			"to_team": "IT / ERP", "status": "Open", "subject": f"{function}: {q}"[:140],
			"details": "\n".join(x for x in (f"Asked by {frappe.utils.get_fullname(t.assigned_by)}" if t.assigned_by else "",
				f"Screen: {screen}" if screen else "", f"CEO: {note.strip()}" if (note or "").strip() else "",
				f"Screenshot: {photos[0]}" if photos else "") if x),
			"reference_doctype": "SK Work Log", "reference_name": log.name}).insert(ignore_permissions=True).name
	if t.assigned_by:
		_tell(t.assigned_by, user, f"Your question \"{split_screen(question)[0][:120]}\" was sent for development (AI & ERP desk).")
	return {"work_log": log.name, "handoff": handoff}


def mark_deployed(user: str, work_log: str, where: str = "App") -> dict:
	_check_ceo(user)
	if where not in ("App", "ERPNext"):
		frappe.throw(frappe._("Pick App or ERPNext"))
	log = frappe.get_doc("SK Work Log", work_log)
	if not (log.description or "").startswith(DEV_TAG):
		frappe.throw(frappe._("Not a question sent for development"))
	log.db_set("status", "Done")
	log.add_comment("Comment", f"Deployed in {'the SK App' if where == 'App' else 'ERPNext'} (marked by {frappe.utils.get_fullname(user)})")
	for todo in frappe.get_all("ToDo", filters={"reference_type": "SK Work Log", "reference_name": work_log, "status": "Open"}, pluck="name"):
		frappe.db.set_value("ToDo", todo, "status", "Closed")  # the AI desk's item is finished too
	question = (log.description or "")[len(DEV_TAG):].strip().split(" | CEO:", 1)[0].split(" | Screen:", 1)[0]
	if log.user and log.user != user:
		_tell(log.user, user, f"Done: \"{question[:120]}\" is now in {'the SK App' if where == 'App' else 'ERPNext'}.")
	return {"work_log": work_log, "where": where}


def _tell(to: str, by: str, text: str):
	frappe.get_doc({"doctype": "ToDo", "allocated_to": to, "assigned_by": by, "status": "Open", "priority": "Low",
		"description": text[:500], "date": frappe.utils.nowdate()}).insert(ignore_permissions=True)


def question_count(user: str) -> int:
	if user not in _ceos():
		return 0
	return frappe.db.count("ToDo", {"allocated_to": ["in", _ceos()], "status": "Open", "description": ["like", f"{FAQ_TAG}%"]})
