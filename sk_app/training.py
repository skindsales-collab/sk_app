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
		"<ol><li>Home → <b>New Lead</b>.</li><li>Fastest: tap <b>📷 Photo</b> of the visiting card or enquiry note; the form fills itself.</li>"
		"<li>Or type, or tap 🎤 and speak.</li><li>Pick <b>Source</b> and <b>Segment</b> (Cabin, Machine Shifting, Job Work...).</li><li>Tap <b>Save</b>. The lead is now in ERPNext CRM under your name.</li></ol>",
		"<ol><li>होम → <b>नवीन लीड</b>.</li><li>सर्वात जलद: व्हिजिटिंग कार्ड किंवा चौकशीचा <b>📷 फोटो</b> काढा; फॉर्म आपोआप भरतो.</li>"
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
		"<li><b>Report Problem</b>: machine, material, quality, safety, customer, IT, pay/leave.</li></ol>",
		"<ol><li><b>माझा दिवस</b>: तुमची सर्व उघडी कामे, उशिराची आधी.</li><li><b>कामाची वही</b>: केलेले जादा काम लिहा (टाईप, आवाज, फोटो).</li>"
		"<li><b>DSI</b>: रोज संध्याकाळी 5:30 पूर्वी एक छोटी सुधारणा: काय सुधारले, आधी आणि नंतर, फोटो.</li>"
		"<li><b>समस्या कळवा</b>: मशीन, मटेरियल, गुणवत्ता, सुरक्षा, ग्राहक, IT, पगार/रजा.</li></ol>"),
	("My Score: KRA and KPI", "माझा स्कोअर: KRA आणि KPI", "All", 7,
		"<ol><li><b>My Score</b> shows your monthly targets and how much is done, counted from ERPNext.</li>"
		"<li>Green = target met, yellow = 80-99%, red = below 80%.</li><li>Score = done ÷ target × weight, up to 120% for each KPI.</li></ol>",
		"<ol><li><b>माझा स्कोअर</b> मध्ये तुमचे महिन्याचे लक्ष्य आणि किती पूर्ण झाले ते ERPNext मधून मोजून दिसते.</li>"
		"<li>हिरवा = लक्ष्य पूर्ण, पिवळा = 80-99%, लाल = 80% पेक्षा कमी.</li><li>स्कोअर = पूर्ण ÷ लक्ष्य × वजन, प्रत्येक KPI साठी 120% पर्यंत.</li></ol>"),
]


def seed_lessons():
	for title, title_mr, function, seq, content, content_mr in APP_LESSONS:
		if frappe.db.exists("SK Training Lesson", {"title": title}):
			continue
		frappe.get_doc({"doctype": "SK Training Lesson", "title": title, "title_marathi": title_mr, "function": function,
			"topic": "Using the app", "sequence": seq, "minutes": 2, "published": 1,
			"content": content, "content_marathi": content_mr}).insert(ignore_permissions=True)


def lessons(user: str, function: str) -> list[dict]:
	rows = frappe.get_all("SK Training Lesson", filters={"published": 1, "function": ["in", ["All", function]]},
		fields=["name", "title", "title_marathi", "topic", "minutes", "video_url", "content", "content_marathi"],
		order_by="sequence asc, creation asc")
	done = set(frappe.get_all("SK Training Done", filters={"user": user}, pluck="lesson"))
	for r in rows:
		r["done"] = r.name in done
	return rows


def mark_done(user: str, lesson: str) -> bool:
	if not frappe.db.exists("SK Training Lesson", {"name": lesson, "published": 1}):
		frappe.throw(frappe._("Lesson not found"))
	if not frappe.db.exists("SK Training Done", {"user": user, "lesson": lesson}):
		frappe.get_doc({"doctype": "SK Training Done", "user": user, "lesson": lesson,
			"completed_on": now_datetime()}).insert(ignore_permissions=True)
	return True
