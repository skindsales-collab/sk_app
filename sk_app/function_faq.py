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
