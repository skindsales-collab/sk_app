"""Training → FAQ for HR, Production and Accounts (SK 27-Oct-2026: "FAQ not updated in HR, Production, Finance; Sales
already done"). Short questions staff really ask, answered from the manuals and the app. No salary items (salary is
confidential). Seeded once by title; answers edited in ERPNext (SK Library Item) are never overwritten.
"""

import frappe

# (function, sequence, question, question in Marathi, answer, answer in Marathi)
FUNCTION_FAQ = [
	# ---------- HR ----------
	("HR", 1, "Attendance is missing for a person today. What do I do?", "आज एखाद्याची हजेरी दिसत नाही. काय करू?",
		"Check that today's Optick file (men) and thumb machine file (office ladies) are uploaded in Attendance → Upload file. "
		"If the person is still missing, pick the employee once against the mobile number; the app remembers it next time.",
		"हजेरी → फाईल अपलोड मध्ये आजची ऑप्टिक फाईल (पुरुष) आणि थंब मशीन फाईल (ऑफिस महिला) टाकली आहे का ते पाहा. "
		"तरीही व्यक्ती दिसत नसेल तर मोबाईल नंबरसमोर एकदा कर्मचारी निवडा; ॲप पुढच्या वेळी लक्षात ठेवते."),
	("HR", 2, "Someone forgot to punch. How is it corrected?", "कोणी पंच करायला विसरले. दुरुस्ती कशी?",
		"The person asks from My Day → Attendance fix with the reason. HR opens Fix requests and picks Present, Half Day or Absent. "
		"Every fix is kept in ERPNext with who approved it.",
		"ती व्यक्ती माझा दिवस → हजेरी दुरुस्ती मधून कारणासह विनंती करते. HR दुरुस्ती विनंत्या उघडून हजर, अर्धा दिवस किंवा गैरहजर निवडते. "
		"प्रत्येक दुरुस्ती कोणी मंजूर केली त्यासह ERPNext मध्ये राहते."),
	("HR", 3, "By what time must attendance be in ERPNext?", "हजेरी ERPNext मध्ये किती वाजेपर्यंत हवी?",
		"Every day by 10 am. Then the late list goes to each head and the CEO screen shows the right numbers.",
		"रोज सकाळी 10 वाजेपर्यंत. मग उशिराची यादी प्रत्येक प्रमुखाला जाते आणि CEO स्क्रीनवर बरोबर आकडे दिसतात."),
	("HR", 4, "How does a person apply for leave?", "रजेसाठी अर्ज कसा करायचा?",
		"Leave & Expense → Leave → pick the dates and type, speak or type the reason, Send. The manager approves on the same screen "
		"(To approve tab). HR sees all leave in ERPNext.",
		"रजा व खर्च → रजा → तारखा आणि प्रकार निवडा, कारण बोला किंवा लिहा, पाठवा. मॅनेजर त्याच स्क्रीनवर (मंजुरीसाठी टॅब) मंजूर करतो. "
		"HR ला सर्व रजा ERPNext मध्ये दिसतात."),
	("HR", 5, "A new person joins. What documents do I take?", "नवीन व्यक्ती रुजू होते. कोणती कागदपत्रे घ्यायची?",
		"Photo of Aadhaar, PAN, bank passbook and a passport photo, taken in the app and attached to the Employee in ERPNext. "
		"Then create the person's SK App login with their mobile number, and give the first training lessons.",
		"आधार, पॅन, बँक पासबुक आणि पासपोर्ट फोटो यांचा ॲपमधून फोटो काढून ERPNext मधील कर्मचाऱ्याला जोडा. "
		"मग त्या व्यक्तीचा मोबाईल नंबर वापरून SK App लॉगिन करा आणि पहिले ट्रेनिंग धडे द्या."),
	("HR", 6, "How do I see who has finished training?", "ट्रेनिंग कोणी पूर्ण केले ते कसे पाहू?",
		"Training → Progress shows each person's lessons done and test marks, function by function. Remind the people who are behind.",
		"ट्रेनिंग → प्रगती मध्ये प्रत्येक व्यक्तीचे पूर्ण धडे आणि टेस्टचे गुण विभागानुसार दिसतात. मागे असलेल्यांना आठवण द्या."),
	("HR", 7, "What is on the HR graph on my main screen?", "माझ्या मुख्य स्क्रीनवरील HR ग्राफ काय दाखवतो?",
		"Days to recruit: from the day the opening is posted to the day the person joins, month by month. Lower is better. "
		"Tap 🎯 to see and add actions that bring it down.",
		"भरतीचे दिवस: जागा जाहीर केल्यापासून व्यक्ती रुजू होईपर्यंत, महिन्यानुसार. कमी असणे चांगले. "
		"ते कमी करणारी कामे पाहण्यासाठी व जोडण्यासाठी 🎯 दाबा."),
	("HR", 8, "A staff member asks HR about pay. What do I do?", "कर्मचारी HR ला पगाराबद्दल विचारतो. काय करू?",
		"Pay is not in the app; it is confidential. Ask the person to speak to SK directly.",
		"पगार ॲपमध्ये नाही; तो गोपनीय आहे. त्या व्यक्तीला थेट SK शी बोलायला सांगा."),

	# ---------- Production ----------
	("Production", 1, "Where do I see what to make today?", "आज काय बनवायचे ते कुठे दिसते?",
		"Home shows your work flow (Fabrication → Electrical → Carpentry → Painting → Final inspection). Tap a box for the jobs "
		"waiting there; red ones are late. Job Cards shows each job with the customer name and the product.",
		"होमवर तुमचा वर्क फ्लो दिसतो (फॅब्रिकेशन → इलेक्ट्रिकल → कारपेंटरी → पेंटिंग → अंतिम तपासणी). थांबलेली कामे पाहण्यासाठी बॉक्स दाबा; "
		"लाल = उशीर. जॉब कार्डमध्ये प्रत्येक काम ग्राहकाचे नाव आणि उत्पादनासह दिसते."),
	("Production", 2, "How do I start and finish a job card?", "जॉब कार्ड सुरू आणि पूर्ण कसे करायचे?",
		"Open the job card, tap Start. When finished take two photos (full job and close-up) and tap Done. Done sends the job to Quality "
		"and the next station sees it.",
		"जॉब कार्ड उघडा, सुरू दाबा. काम झाल्यावर दोन फोटो काढा (पूर्ण काम आणि जवळून) आणि झाले दाबा. झाले दाबल्यावर काम क्वालिटीकडे जाते "
		"आणि पुढच्या स्टेशनला दिसते."),
	("Production", 3, "Material is short. Whom do I tell?", "मटेरियल कमी आहे. कोणाला सांगू?",
		"Tap Need Material, speak or pick the items, the quantity and the date you need it, then Send to Store. The store person gets it "
		"at once; if stock is not there it goes to Purchase.",
		"मटेरियल हवे दाबा, वस्तू, संख्या आणि कधी हवे ती तारीख बोला किंवा निवडा, मग स्टोअरला पाठवा. स्टोअरला लगेच मिळते; "
		"स्टॉक नसेल तर ते परचेसकडे जाते."),
	("Production", 4, "Quality rejected my job. What next?", "क्वालिटीने माझे काम नाकारले. पुढे काय?",
		"The job comes back to you with the problem and photo. Fix it, take a new photo and tap Done again. Repeated problems go into "
		"Non-conformance so the cause is fixed for every cabin.",
		"काम अडचण आणि फोटोसह तुमच्याकडे परत येते. दुरुस्त करा, नवीन फोटो काढा आणि पुन्हा झाले दाबा. पुन्हा पुन्हा येणाऱ्या अडचणी "
		"नॉन-कन्फॉर्मन्समध्ये जातात म्हणजे प्रत्येक केबिनसाठी कारण दूर होते."),
	("Production", 5, "How do I know the delivery date of a cabin?", "केबिनची डिलिव्हरी तारीख कशी कळते?",
		"Order Board shows every cabin stage by stage with the customer, product and delivery date. Late ones are red at the top.",
		"ऑर्डर बोर्डवर प्रत्येक केबिन टप्प्यानुसार ग्राहक, उत्पादन आणि डिलिव्हरी तारखेसह दिसते. उशिराचे लाल रंगात वर दिसतात."),
	("Production", 6, "What is the Production graph on my main screen?", "माझ्या मुख्य स्क्रीनवरील उत्पादन ग्राफ काय आहे?",
		"Days to build 100 sq ft: for each cabin invoiced in the month, days from PO to invoice ÷ (its sq ft ÷ 100); the month "
		"shows the average of these (e.g. 10x20 in 8 days = 4, 10x10 in 5 days = 5). Lower is better. Tap 🎯 for the actions "
		"that bring it down; the ⏱️ tile shows each cabin.",
		"100 चौ.फूट बनवण्याचे दिवस: महिन्यात इनव्हॉइस झालेल्या प्रत्येक केबिनचे PO ते इनव्हॉइस दिवस ÷ (त्याचे चौ.फूट ÷ 100); "
		"महिन्याचा आकडा म्हणजे यांची सरासरी (उदा. 10x20 ला 8 दिवस = 4, 10x10 ला 5 दिवस = 5). कमी असणे चांगले. ते कमी करणाऱ्या "
		"कामांसाठी 🎯 दाबा; ⏱️ टाइलवर प्रत्येक केबिन दिसते."),
	("Production", 7, "A machine broke down or there is a safety problem.", "मशीन बंद पडले किंवा सुरक्षेची अडचण आहे.",
		"Tap Report Problem, pick Machine or Safety, take a photo and speak what happened. The owner is told at once and it stays open "
		"until it is fixed.",
		"समस्या कळवा दाबा, मशीन किंवा सुरक्षा निवडा, फोटो काढा आणि काय झाले ते बोला. जबाबदार व्यक्तीला लगेच कळते आणि दुरुस्त होईपर्यंत "
		"ते उघडे राहते."),
	("Production", 8, "The cabin is ready. How does it go for dispatch?", "केबिन तयार आहे. डिस्पॅचसाठी कसे जाते?",
		"After final inspection passes, it shows in Ready to Dispatch. Accounts makes the invoice from there and Stores issues the "
		"delivery note.",
		"अंतिम तपासणी पास झाल्यावर ते डिस्पॅचसाठी तयार मध्ये दिसते. तिथून अकाउंट्स इनव्हॉइस करते आणि स्टोअर डिलिव्हरी नोट देते."),

	# ---------- Accounts (Finance) ----------
	("Accounts", 1, "Where do I see today's money?", "आजचे पैसे कुठे दिसतात?",
		"Cash Today shows the bank and cash balance and the money in and out today, from ERPNext.",
		"आजची रोकड मध्ये बँक व रोख शिल्लक आणि आज आलेले व गेलेले पैसे ERPNext मधून दिसतात."),
	("Accounts", 2, "Which customers must I call for payment?", "पैशासाठी कोणत्या ग्राहकांना कॉल करायचा?",
		"To Collect lists customers who owe us, oldest first (0-30, 31-60, over 60 days). Make 10 calls a day; tap 📞 or 💬 and write "
		"what they promised. Over 30 days overdue also goes to the salesperson.",
		"वसुली मध्ये आपल्याला देणे असलेले ग्राहक जुने आधी दिसतात (0-30, 31-60, 60 पेक्षा जास्त दिवस). रोज 10 कॉल करा; 📞 किंवा 💬 दाबा "
		"आणि त्यांनी दिलेले वचन लिहा. 30 दिवसांपेक्षा जास्त थकलेले सेल्सच्या व्यक्तीकडेही जाते."),
	("Accounts", 3, "When are suppliers paid? Who approves?", "सप्लायरला पैसे कधी देतात? मंजुरी कोण देतो?",
		"Suppliers are paid on the 15th and 30th only. A payment above Rs 5,000 goes to SK for approval in the app first.",
		"सप्लायरला फक्त 15 आणि 30 तारखेला पैसे दिले जातात. Rs 5,000 पेक्षा जास्त पेमेंट आधी ॲपमध्ये SK कडे मंजुरीसाठी जाते."),
	("Accounts", 4, "Can production start without advance?", "ॲडव्हान्सशिवाय उत्पादन सुरू करता येते का?",
		"No. 50% advance comes before production starts. Only SK can approve otherwise.",
		"नाही. उत्पादन सुरू होण्यापूर्वी 50% ॲडव्हान्स लागतो. वेगळे करायचे असेल तर फक्त SK मंजूर करू शकतात."),
	("Accounts", 5, "Purchase sent a supplier bill. What do I do?", "परचेसने सप्लायरचे बिल पाठवले. काय करू?",
		"Open Bills to Post, check the bill photo against the PO and the goods received, then post it in ERPNext against the right "
		"project, so the project's material cost is correct.",
		"पोस्ट करायची बिले उघडा, बिलाचा फोटो PO आणि मिळालेल्या मालाशी तपासा, मग योग्य प्रोजेक्टवर ERPNext मध्ये पोस्ट करा, "
		"म्हणजे प्रोजेक्टचा मटेरियल खर्च बरोबर राहील."),
	("Accounts", 6, "What is the Accounts graph on my main screen?", "माझ्या मुख्य स्क्रीनवरील अकाउंट्स ग्राफ काय आहे?",
		"Projects with correct P&L: of the projects finished and invoiced in the month, how many have their material correctly posted "
		"to the project (for example 12 of 20 = 60%). Target 100%. Tap 🎯 for the actions to fix the rest.",
		"बरोबर P&L असलेले प्रोजेक्ट: महिन्यात पूर्ण होऊन इनव्हॉइस झालेल्या प्रोजेक्टपैकी किती प्रोजेक्टचे मटेरियल प्रोजेक्टवर बरोबर पोस्ट झाले "
		"(उदा. 20 पैकी 12 = 60%). लक्ष्य 100%. उरलेले दुरुस्त करण्याच्या कामांसाठी 🎯 दाबा."),
	("Accounts", 7, "When is the month closed?", "महिना कधी बंद करायचा?",
		"All bills, expenses and invoices of the month are posted and the P&L by segment (Cabin, Non-Cabin) is ready by the 7th of "
		"next month. The cash statement goes every Friday.",
		"महिन्याची सर्व बिले, खर्च आणि इनव्हॉइस पोस्ट करून सेगमेंटनुसार (केबिन, नॉन-केबिन) P&L पुढच्या महिन्याच्या 7 तारखेपर्यंत तयार. "
		"कॅश स्टेटमेंट दर शुक्रवारी."),
	("Accounts", 8, "Someone gave an expense bill. How is it entered?", "कोणी खर्चाचे बिल दिले. ते कसे नोंदवायचे?",
		"The person claims it from Leave & Expense → Expense with a photo of the bill; the manager approves. Accounts checks it in "
		"Expenses and pays it.",
		"ती व्यक्ती रजा व खर्च → खर्च मधून बिलाच्या फोटोसह क्लेम करते; मॅनेजर मंजूर करतो. अकाउंट्स खर्च मध्ये तपासून पैसे देते."),
]


def seed_faq():
	for function, seq, title, title_mr, text, text_mr in FUNCTION_FAQ:
		if frappe.db.exists("SK Library Item", {"title": title, "category": "FAQ"}):
			continue
		frappe.get_doc({"doctype": "SK Library Item", "title": title, "title_marathi": title_mr, "category": "FAQ",
			"audience": "Internal", "function": function, "sequence": seq, "enabled": 1, "product": "All",
			"text": text, "text_marathi": text_mr}).insert(ignore_permissions=True)


# ---------- Subcontractor on site jobs (SK 9-Nov: Santosh's FAQ was empty) ----------
FUNCTION_FAQ += [
	("Subcontractor", 1, "My job does not show in Site jobs. Why?", "माझे काम साईट जॉब मध्ये दिसत नाही. का?",
		"A job shows only after SK places the service order (PO) on your company. Ask SK / Purchase whether the PO is placed; a draft PO does not show.",
		"SK ने तुमच्या कंपनीवर सर्व्हिस ऑर्डर (PO) दिल्यावरच काम दिसते. PO दिला का ते SK / खरेदीला विचारा; ड्राफ्ट PO दिसत नाही."),
	("Subcontractor", 2, "The app refuses my bill. What is missing?", "ॲप माझे बिल घेत नाही. काय कमी आहे?",
		"The customer's signed job report must be in the app first (Site jobs → job → Signed report, photo). Then Bill with bill number, date and a photo of the bill.",
		"आधी ग्राहकाची सही असलेला जॉब रिपोर्ट ॲपमध्ये हवा (साईट जॉब → काम → सही केलेला रिपोर्ट, फोटो). मग बिल नंबर, तारीख आणि बिलाच्या फोटोसह बिल."),
	("Subcontractor", 3, "Who approves my work and when do I get paid?", "माझे काम कोण मंजूर करते आणि पैसे कधी मिळतात?",
		"SK's Non-Cabin owner approves the work in the app (your job shows 'approved'). Accounts then pays as per the PO term: 50% advance + 50% after bill, or 100% after bill with no credit days.",
		"SK चे नॉन-केबिन मालक ॲपमध्ये काम मंजूर करतात (काम 'मंजूर' दाखवते). मग अकाउंट्स PO च्या अटीप्रमाणे पैसे देते: 50% आगाऊ + 50% बिलानंतर, किंवा बिलानंतर 100%."),
	("Subcontractor", 4, "I did extra work on site. Can I add it to the bill?", "साईटवर जादा काम केले. बिलात टाकू का?",
		"Not without a PO for it. Tell SK (Problem / Suggestion or a call) before doing extra work; SK adds it to the PO or makes a new one. Only PO items are paid.",
		"त्याचा PO असल्याशिवाय नाही. जादा काम करण्याआधी SK ला सांगा (अडचण / सूचना किंवा फोन); SK PO मध्ये जोडते किंवा नवीन PO करते. फक्त PO मधील कामाचे पैसे मिळतात."),
	("Subcontractor", 5, "The daily photo did not upload. What now?", "रोजचा फोटो अपलोड झाला नाही. आता काय?",
		"Check the mobile network and try again from Site jobs → job → Daily photo. If it still fails, send the photo on WhatsApp to SK the same day and say the job name; it is attached for you.",
		"मोबाईल नेटवर्क तपासा आणि साईट जॉब → काम → रोजचा फोटो मधून पुन्हा करा. तरीही नाही झाले तर त्याच दिवशी SK ला WhatsApp वर फोटो पाठवा आणि कामाचे नाव सांगा; तो जोडला जातो."),
	("Subcontractor", 6, "I forgot my PIN or the app is locked.", "पिन विसरलो किंवा ॲप लॉक झाले.",
		"Login screen → Forgot PIN: the CEO gets your request and sends a new PIN. The app locks after 30 minutes without use; enter your PIN (or fingerprint / face) to open it again.",
		"लॉगिन स्क्रीन → पिन विसरलात: CEO ला विनंती जाते आणि ते नवीन पिन पाठवतात. 30 मिनिटे वापर नसेल तर ॲप लॉक होते; पिन (किंवा फिंगरप्रिंट / फेस) टाकून पुन्हा उघडा."),
]


# ---------- Purchase, Stores, Quality, Marketing, Management, Machine Shifting (SK 10-Nov "all ok") ----------
# Answers use only what the function manuals (manual_lessons) and the app screens already say.
FUNCTION_FAQ += [
	# Purchase
	("Purchase", 1, "Where do I see what to buy today?", "आज काय खरेदी करायचे ते कुठे दिसते?",
		"Main screen → Requests: every store request waiting for a PO. Turn each one into a PO the same day.",
		"मुख्य स्क्रीन → खरेदी मागण्या: PO ची वाट पाहणारी प्रत्येक स्टोअर मागणी. प्रत्येकीचा त्याच दिवशी PO करा."),
	("Purchase", 2, "Which POs need SK's approval?", "कोणत्या PO ला SK ची मंजुरी लागते?",
		"Every PO of ₹5,000 and above goes to the CEO's PO Approvals for one-tap approval. A PO made in ERPNext outside the app is flagged the same way.",
		"₹5,000 व त्यावरील प्रत्येक PO एका टॅपच्या मंजुरीसाठी CEO च्या PO मंजुरीत जातो. ॲपबाहेर ERPNext मध्ये केलेला PO सुद्धा तसाच दाखवला जातो."),
	("Purchase", 3, "How many rates must I take?", "किती दर घ्यायचे?",
		"3 rates for the main items (GI sheet, PUF panel, ISMC, wire) every week, from Get Rates. The app shows the last rate so you can see the saving.",
		"मुख्य आयटमचे (GI शीट, PUF पॅनेल, ISMC, वायर) दर आठवड्याला 3 दर, दर मागवा मधून. ॲप मागील दर दाखवते म्हणजे बचत दिसते."),
	("Purchase", 4, "A supplier is late. What do I do?", "सप्लायर उशिरा आहे. काय करू?",
		"Open Follow-up: call or WhatsApp the supplier from there and note the new date. Late suppliers go on the weekly delay list and lower the supplier score.",
		"पाठपुरावा उघडा: तिथूनच सप्लायरला कॉल किंवा WhatsApp करा आणि नवीन तारीख नोंदवा. उशिरा येणारे सप्लायर आठवड्याच्या उशीर यादीत जातात आणि त्यांचा स्कोअर कमी होतो."),
	("Purchase", 5, "When are suppliers paid?", "सप्लायरला पैसे कधी मिळतात?",
		"On the 15th and the 30th, after the CEO approves in Payment OK. Plan big payments with Accounts before these dates.",
		"15 व 30 तारखेला, CEO ने पेमेंट मंजुरीत मंजूर केल्यावर. मोठी पेमेंट या तारखांआधी अकाउंट्ससोबत प्लॅन करा."),
	("Purchase", 6, "Material is needed urgently and there is no PO.", "माल तातडीने हवा आणि PO नाही.",
		"Raise the requisition marked urgent; it goes to the CEO first, then the PO. Buying without a PO counts against the Stores and Purchase KPI.",
		"तातडीची खरेदी मागणी करा; ती आधी CEO कडे जाते, मग PO. PO शिवाय खरेदी स्टोअर व पर्चेसच्या KPI मध्ये कमी धरली जाते."),
	# Stores
	("Stores", 1, "Material came. How do I receive it?", "माल आला. तो कसा घ्यायचा?",
		"Main screen → Receive: pick the PO, check quantity, take a photo of the bill and of the material. Enter it within 2 hours of arrival.",
		"मुख्य स्क्रीन → माल आला: PO निवडा, नग तपासा, बिलाचा व मालाचा फोटो काढा. माल आल्यावर 2 तासांत एंट्री करा."),
	("Stores", 2, "Material came without a PO.", "PO शिवाय माल आला.",
		"Do not issue it. Keep it on hold with a photo and tell Purchase; it is received only after the PO is placed.",
		"तो देऊ नका. फोटोसह होल्डवर ठेवा आणि पर्चेसला कळवा; PO झाल्यावरच माल घेतला जातो."),
	("Stores", 3, "How do I give material to the factory?", "फॅक्टरीला माल कसा द्यायचा?",
		"Main screen → Issue: pick the job card and the items. Issue the same day the request comes (KPI ≥ 95%).",
		"मुख्य स्क्रीन → माल द्या: जॉब कार्ड आणि आयटम निवडा. मागणी आलेल्या दिवशीच माल द्या (KPI ≥ 95%)."),
	("Stores", 4, "Stock is running low. Whom do I tell?", "स्टॉक कमी होत आहे. कोणाला सांगू?",
		"Raise a Purchase requisition from the main screen before it runs out; every week send the low-stock list to Purchase.",
		"संपण्याआधी मुख्य स्क्रीनवरून खरेदी मागणी करा; दर आठवड्याला कमी स्टॉक यादी पर्चेसला पाठवा."),
	("Stores", 5, "When is the stock count?", "स्टॉक मोजणी कधी?",
		"Count the top items before the 5th of every month, so Accounts can make the P&L by the 7th. The difference must stay within 1%.",
		"दर महिन्याच्या 5 तारखेपूर्वी मुख्य आयटम मोजा, म्हणजे अकाउंट्स 7 तारखेपर्यंत P&L करू शकतात. फरक 1% च्या आत हवा."),
	("Stores", 6, "A cabin is going out. What must Stores do?", "केबिन बाहेर जात आहे. स्टोअरने काय करायचे?",
		"Make the dispatch note and take a loading photo for every cabin. Quality's final check must be passed first.",
		"प्रत्येक केबिनसाठी डिस्पॅच नोट करा आणि लोडिंग फोटो काढा. आधी क्वालिटीची अंतिम तपासणी पास हवी."),
	# Quality
	("Quality", 1, "Which stages do I check?", "कोणते टप्पे तपासायचे?",
		"Main screen → Inspect: chassis weld, wall panels, roof water test, wiring + earthing + MCB, paint. A photo for each stage.",
		"मुख्य स्क्रीन → तपासणी: चेसिस वेल्ड, भिंत पॅनेल, छप्पर पाणी चाचणी, वायरिंग + अर्थिंग + MCB, पेंट. प्रत्येक टप्प्याचा फोटो."),
	("Quality", 2, "I found a defect. What do I do?", "दोष सापडला. काय करू?",
		"Open Non-Conformance, add a photo and the cause. Production gets it; the job waits until your re-check photo passes.",
		"दोष (NC) उघडा, फोटो आणि कारण टाका. उत्पादनाला ते जाते; तुमचा पुन्हा तपासणी फोटो पास होईपर्यंत काम थांबते."),
	("Quality", 3, "Can a cabin go out with an open NC?", "उघडा NC असताना केबिन जाऊ शकते का?",
		"No. Final Check before every dispatch; a job with an open NC is not dispatched.",
		"नाही. प्रत्येक डिस्पॅचपूर्वी अंतिम तपासणी; उघडा NC असलेले काम डिस्पॅच होत नाही."),
	("Quality", 4, "A customer complained after delivery.", "डिलिव्हरीनंतर ग्राहकाची तक्रार आली.",
		"Log it in the app, visit within 48 hours, take photos and write the root cause. Close it only after the customer's OK.",
		"ॲपमध्ये नोंदवा, 48 तासांत भेट द्या, फोटो काढा आणि मूळ कारण लिहा. ग्राहकाचा OK आल्यावरच बंद करा."),
	("Quality", 5, "What is the Quality graph on my main screen?", "माझ्या मुख्य स्क्रीनवरील क्वालिटी ग्राफ काय आहे?",
		"First-time pass by month (target ≥ 95%). Also watched: repeat NC = 0 and complaints ≤ 1 per 20 cabins.",
		"महिन्यानुसार पहिल्याच वेळी पास (टार्गेट ≥ 95%). तसेच: पुन्हा NC = 0 आणि 20 केबिनमागे ≤ 1 तक्रार."),
	("Quality", 6, "What goes in the weekly report?", "आठवड्याच्या अहवालात काय?",
		"The top 3 defects of the week with their root cause and the action taken. Send it from Day Report or Problem / Suggestion.",
		"आठवड्यातील टॉप 3 दोष, त्यांचे मूळ कारण आणि केलेली कृती. दिवसाचा अहवाल किंवा समस्या / सूचना मधून पाठवा."),
	# Marketing
	("Marketing", 1, "A new enquiry came on IndiaMART. How fast must I answer?", "IndiaMART वर नवीन चौकशी आली. किती लवकर उत्तर?",
		"Within 5 minutes. Check IndiaMART every hour; JustDial alerts get a call within 1 minute.",
		"5 मिनिटांत. IndiaMART दर तासाला तपासा; JustDial नोटिफिकेशनवर 1 मिनिटात कॉल."),
	("Marketing", 2, "How do I put an enquiry in the app?", "चौकशी ॲपमध्ये कशी टाकायची?",
		"Main screen → New Lead with name, mobile and the source (IndiaMART, JustDial, GeM, Google ...). A lead without a mobile or name cannot move on.",
		"मुख्य स्क्रीन → नवीन लीड: नाव, मोबाईल आणि सोर्स (IndiaMART, JustDial, GeM, Google ...). नाव किंवा मोबाईल नसलेली लीड पुढे जात नाही."),
	("Marketing", 3, "The same customer enquired again.", "तोच ग्राहक पुन्हा चौकशी करतो.",
		"The app refuses the same mobile twice on the same day. Open the old lead from My Leads and add a note instead.",
		"एकाच दिवशी तोच मोबाईल दोनदा ॲप घेत नाही. माझे लीड मधून जुनी लीड उघडा आणि नोट टाका."),
	("Marketing", 4, "When do I check GeM tenders?", "GeM टेंडर कधी तपासायचे?",
		"Every day at 10 am. File at least 3 cabin tenders a month.",
		"रोज सकाळी 10 वाजता. महिन्याला किमान 3 केबिन टेंडर भरा."),
	("Marketing", 5, "What do I do on Google Business?", "Google Business वर काय करायचे?",
		"Every Saturday: upload 3 new site photos and send review links to old customers.",
		"दर शनिवारी: 3 नवीन साईट फोटो टाका आणि जुन्या ग्राहकांना रिव्ह्यू लिंक पाठवा."),
	("Marketing", 6, "Which leads must I follow up today?", "आज कोणत्या लीडचा फॉलो-अप?",
		"Main screen → Follow-up lists today's calls. Call or WhatsApp from there; the call note is saved on the lead.",
		"मुख्य स्क्रीन → फॉलो-अप मध्ये आजचे कॉल दिसतात. तिथूनच कॉल किंवा WhatsApp करा; कॉलची नोट लीडवर राहते."),
	# Management
	("Management", 1, "What do I look at every day?", "रोज काय पाहायचे?",
		"CEO Overview for 10 minutes: orders, quotations, dispatch, cash. Then PO Approvals and Payment OK the same day.",
		"CEO आढावा 10 मिनिटे: ऑर्डर, कोटेशन, डिस्पॅच, कॅश. मग त्याच दिवशी PO मंजुरी आणि पेमेंट मंजुरी."),
	("Management", 2, "Which POs come to me?", "माझ्याकडे कोणते PO येतात?",
		"Every PO of ₹5,000 and above, urgent requisitions, and any PO above the limit made in ERPNext outside the app.",
		"₹5,000 व त्यावरील प्रत्येक PO, तातडीच्या खरेदी मागण्या, आणि ॲपबाहेर ERPNext मध्ये केलेला मर्यादेवरील कोणताही PO."),
	("Management", 3, "How do I see what a team member sees?", "टीम सदस्याला काय दिसते ते कसे पाहू?",
		"View Member App: pick the person; you see their screens read-only, nothing is saved in their name.",
		"सदस्याचे ॲप पहा: व्यक्ती निवडा; त्यांचे स्क्रीन फक्त पाहता येतात, त्यांच्या नावाने काही सेव्ह होत नाही."),
	("Management", 4, "What is the weekly review rhythm?", "आठवड्याचा आढावा कसा?",
		"Monday: sales funnel per person. Wednesday: factory and dispatch. Friday: cash.",
		"सोमवार: दर व्यक्ती सेल्स फनेल. बुधवार: फॅक्टरी व डिस्पॅच. शुक्रवार: कॅश."),
	("Management", 5, "Someone forgot their PIN.", "कोणी पिन विसरले.",
		"Their Forgot PIN request comes to you; set a new PIN for them. The first PIN of every new person is also given by the CEO.",
		"त्यांची पिन विसरल्याची विनंती तुमच्याकडे येते; त्यांना नवीन पिन द्या. प्रत्येक नवीन व्यक्तीचा पहिला पिनही CEO देतात."),
	("Management", 6, "Where do problems from staff go?", "कर्मचाऱ्यांच्या समस्या कुठे जातात?",
		"Problem / Suggestion from anyone: the AI checks and answers it; only corrections or changes in the app come to you or Samir for approval.",
		"कोणाचीही समस्या / सूचना: AI तपासून उत्तर देते; फक्त ॲपमधील दुरुस्ती किंवा बदल तुमच्याकडे किंवा Samir कडे मंजुरीसाठी येतात."),
	# Machine Shifting (Non-Cabin owner)
	("Machine Shifting", 1, "Where do I see my machine shifting enquiries?", "माझ्या मशीन शिफ्टिंग चौकशी कुठे दिसतात?",
		"Main screen → My Deals: every Non-Cabin lead and deal (Machine Shifting, Job Work, Maintenance) that you own, by stage.",
		"मुख्य स्क्रीन → माझे डील: तुमच्या मालकीच्या सर्व नॉन-केबिन लीड व डील (मशीन शिफ्टिंग, जॉब वर्क, मेंटेनन्स), टप्प्यानुसार."),
	("Machine Shifting", 2, "Where do I keep what I saw at the site survey?", "साईट सर्व्हेमध्ये पाहिलेले कुठे ठेवायचे?",
		"Open the deal from My Deals and add a note with photos (machine, path, crane access). It stays on the deal for the quote and for the subcontractor.",
		"माझे डील मधून डील उघडा आणि फोटोसह नोट टाका (मशीन, रस्ता, क्रेन जाण्याची जागा). ती कोटेशनसाठी व सबकॉन्ट्रॅक्टरसाठी डीलवर राहते."),
	("Machine Shifting", 3, "The order is won. How does the job start?", "ऑर्डर मिळाली. काम कसे सुरू होते?",
		"Mark the deal won (it becomes a Sales Order). Then place the service PO on the subcontractor from Site jobs; the job shows on his phone at once.",
		"डील जिंकलेले करा (त्याची सेल्स ऑर्डर होते). मग साईट कामे मधून सबकॉन्ट्रॅक्टरवर सर्व्हिस PO द्या; काम लगेच त्याच्या फोनवर दिसते."),
	("Machine Shifting", 4, "Which payment term goes on the service PO?", "सर्व्हिस PO वर कोणती पेमेंट अट?",
		"One of two: 50% advance with the PO and 50% after the bill, or 100% after the bill with no credit days.",
		"दोनपैकी एक: PO सोबत 50% आगाऊ आणि बिलानंतर 50%, किंवा बिलानंतर 100%, उधारी नाही."),
	("Machine Shifting", 5, "The subcontractor sent his bill. What do I do?", "सबकॉन्ट्रॅक्टरने बिल पाठवले. काय करू?",
		"Open Site jobs: check the signed job report and the bill, then Approve. Accounts pays as per the PO term only after your approval.",
		"साईट कामे उघडा: सही केलेला जॉब रिपोर्ट आणि बिल तपासा, मग मंजूर करा. तुमच्या मंजुरीनंतरच अकाउंट्स PO अटीप्रमाणे पैसे देते."),
	("Machine Shifting", 6, "The customer wants extra work on site.", "ग्राहकाला साईटवर जादा काम हवे.",
		"Quote it to the customer first, then change the service PO or place a new one before the work. Work not on a PO is not paid.",
		"आधी ग्राहकाला कोटेशन द्या, मग काम सुरू होण्याआधी सर्व्हिस PO बदला किंवा नवीन PO द्या. PO मध्ये नसलेल्या कामाचे पैसे मिळत नाहीत."),
]
