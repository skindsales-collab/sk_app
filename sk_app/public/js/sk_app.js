/* SK App phone screens. Talks only to sk_app.api.* with the user's own ERPNext session. */
(function () {
	const root = document.getElementById("sk-app");
	const CSRF = root.dataset.csrf;
	let state = { lang: "English", home: null, card: null, view: "home" };

	const T = {
		English: {
			my_day: "My Day", my_leads: "My Leads", my_deals: "My Deals", my_kpi: "My Score",
			work_book: "Work Book", dsi: "DSI", problem: "Report Problem", job_cards: "Job Cards",
			inspections: "Inspections", stock_alerts: "Stock Alerts", material_requests: "Material Requests",
			invoice_photo: "Invoice Photo", collections: "Collections", team_scorecards: "Team Scores",
			site_checklist: "Site Checklist", ceo_view: "CEO View",
			now: "What to do now", start: "Start", done: "Done", more_time: "Need more time",
			trouble: "Problem", refresh: "New card", back: "Back", save: "Save", speak: "Speak",
			photo: "Photo", saved: "Saved", soon: "Coming in a later phase. Use ERPNext for now:",
			open_erp: "Open in ERPNext", nothing: "Nothing open. Well done!",
			dsi_q: "What small improvement did you make today?", before: "Before", after: "After",
			work_q: "What did you do?", extra: "Extra work", problem_q: "What is the problem?",
			score: "Score this month", target: "Target", actual: "Actual", not_live: "not live yet",
			lang: "मराठी", leads: "Leads", deals: "Deals", due: "due", min: "min",
			follow_up: "Follow-up", new_lead: "New Lead", training: "Training", day_report: "Day Report",
			team_reports: "Team Reports", overdue: "Overdue", new_badge: "New", next: "Next", last: "Last",
			call: "Call", whatsapp: "WhatsApp", email: "Email", status: "Status", notes: "Notes", add_note: "Add note",
			note_q: "Note (type, speak or photo)", files: "Files & drawings", attach: "Attach photo / file",
			tasks: "CRM tasks", calls: "Calls", quotations: "Quotations", sales_orders: "Sales Orders",
			pdf: "PDF", send_customer: "Send on WhatsApp", share_pdf: "Share PDF", send_to: "Send to WhatsApp number",
			send: "Send", what_happened: "What happened?", skip: "Skip", open_crm: "Open in CRM",
			card_photo: "Photo: card, enquiry, drawing, spec or screenshot", reading: "Reading photo…", read_ok: "Filled from photo. Please check.",
			read_none: "Could not read. Please type.", cust_name: "Customer name", company: "Company", mobile: "Mobile",
			source: "Source", segment: "Segment", requirement: "Requirement", lesson_done: "I have done this lesson",
			done_tick: "Done", new_files: "New files on your leads", report_q: "What work did you do today?",
			problems_q: "Problems / help needed", plan_q: "Plan for tomorrow", captured: "Captured by the app today",
			cards_done: "Cards done", calls_made: "Calls", talk_minutes: "Talk min", missed_calls: "Missed", notes_added: "Notes", leads_created: "New leads",
			work_entries: "Work Book", dsi_done: "DSI", kpi_score: "Month score", send_report: "Send Day Report",
			report_sent: "Day Report sent", report_due: "Send today's Day Report", history: "Last 14 days",
			sent_of: "sent", not_sent: "Not sent", on_time: "on time", late: "late", rating: "Rating",
			comment: "Comment", save_review: "Save review", none: "None", new_drawing: "New drawing to send",
			correction: "Drawing correction", correction_q: "What should change? (type or speak)",
			correction_photo: "Photo / screenshot with marks (optional)", send_correction: "Send correction to design",
			correction_sent: "Sent to design. You will get the new drawing here.", design_status: "Design",
			self: "Self", customer: "Customer", no_number: "No number saved. Please type it.",
			calendar: "My Calendar", cal_today: "Today", cal_week: "My Week", cal_month: "My Month", done_today: "Done today",
			plan: "Plan", now_word: "NOW", later: "Does not fit today", tomorrow: "Work day is over: for tomorrow", week: "Week", orders: "Orders", order: "Order",
			open_items: "items", company_dates: "Company dates", done_word: "Done", due_overdue: "Due / overdue",
			tap_day: "Tap a day to see it.", d_Mon: "Mon", d_Tue: "Tue", d_Wed: "Wed", d_Thu: "Thu", d_Fri: "Fri", d_Sat: "Sat", d_Sun: "Sun",
			listening: "Listening… speak now. Tap the red mic to stop.", mic_blocked: "Microphone is blocked. Tap the 🔒 lock next to the address, then Permissions → Microphone → Allow.",
			mic_network: "Voice needs internet. Check mobile data and try again.", mic_nospeech: "Did not hear anything. Tap 🎤, wait for red, then speak.",
			mic_nomic: "No microphone found on this phone.", mic_unsupported: "Voice does not work in this browser. Use Chrome, or the mic on the keyboard.",
			mail: "Mail", reminders: "Reminders", library: "Company & Products",
			reminder: "Reminder", what_remind: "What to do (type or speak)", date: "Date", time: "Time", repeat: "Repeat",
			no_repeat: "Once", daily: "Every day", weekly: "Every week", monthly: "Every month", for_whom: "For",
			me: "Me", set_reminder: "Set reminder", snooze: "In 10 min", upcoming: "Next 7 days",
			talk_time: "Talk time", talk_min: "Talk time (minutes)", today: "Today", this_week: "This week", calls_n: "calls",
			talked: "talked", missed: "missed / no answer", add_call: "Add a call", incoming: "Customer called", outgoing: "I called", pick_customer: "Customer",
			team_talk: "Team talk time", locked: "Phase 2 (paid) - not active", rec_locked: "Automatic call recording",
			wa_locked: "WhatsApp messages inside the app (Business API)", any_number: "Send to any number", message: "Message",
			search: "Search", templates: "Ready messages", open_chat: "Open chat",
			mail_not_ready: "Company email is not connected to ERPNext yet. Ask the admin to add the Email Account (free). Until then ✉️ opens your phone's mail app.",
			to: "To", subject: "Subject", attach_files: "Attach", send_mail: "Send email", mail_sent: "Email sent", emails: "Emails",
			cat_Company: "Company", cat_Product: "Products", "cat_Customer FAQ": "FAQ", "cat_Message Template": "Messages", "cat_Sales Manual": "Sales Manual",
			open: "Open", copy: "Copy", copied: "Copied", all: "All",
			my_function: "My function", app_usage: "App usage", faq: "FAQ", team: "Team", read_pages: "Read the manual pages",
			check: "Lesson check", check_answers: "Check my answers", passed: "Passed", try_again: "Not yet. Read again and try.",
			lessons_done: "lessons done", photo_reading: "Reading the card on the phone… (first time takes a minute)",
		},
		Marathi: {
			my_day: "माझा दिवस", my_leads: "माझे लीड", my_deals: "माझे डील", my_kpi: "माझा स्कोअर",
			work_book: "कामाची वही", dsi: "DSI", problem: "समस्या कळवा", job_cards: "जॉब कार्ड",
			inspections: "तपासणी", stock_alerts: "स्टॉक सूचना", material_requests: "मटेरियल मागणी",
			invoice_photo: "बिलाचा फोटो", collections: "वसुली", team_scorecards: "टीम स्कोअर",
			site_checklist: "साईट चेकलिस्ट", ceo_view: "CEO दृश्य",
			now: "आता काय करायचे", start: "सुरू", done: "झाले", more_time: "अजून वेळ हवा",
			trouble: "अडचण", refresh: "नवीन कार्ड", back: "मागे", save: "जतन करा", speak: "बोला",
			photo: "फोटो", saved: "जतन झाले", soon: "हे पुढच्या टप्प्यात येईल. सध्या ERPNext वापरा:",
			open_erp: "ERPNext मध्ये उघडा", nothing: "काही काम उघडे नाही. छान!",
			dsi_q: "आज तुम्ही कोणती छोटी सुधारणा केली?", before: "आधी", after: "नंतर",
			work_q: "तुम्ही काय काम केले?", extra: "जादा काम", problem_q: "समस्या काय आहे?",
			score: "या महिन्याचा स्कोअर", target: "लक्ष्य", actual: "प्रत्यक्ष", not_live: "अजून सुरू नाही",
			lang: "English", leads: "लीड", deals: "डील", due: "मुदत", min: "मिनिटे",
			follow_up: "फॉलो-अप", new_lead: "नवीन लीड", training: "प्रशिक्षण", day_report: "दिवसाचा अहवाल",
			team_reports: "टीम अहवाल", overdue: "उशीर", new_badge: "नवीन", next: "पुढे", last: "शेवटचे",
			call: "कॉल", whatsapp: "WhatsApp", email: "ईमेल", status: "स्थिती", notes: "नोंदी", add_note: "नोंद जोडा",
			note_q: "नोंद (टाईप, बोला किंवा फोटो)", files: "फाईल्स आणि ड्रॉइंग", attach: "फोटो / फाईल जोडा",
			tasks: "CRM कामे", calls: "कॉल", quotations: "कोटेशन", sales_orders: "सेल्स ऑर्डर",
			pdf: "PDF", send_customer: "WhatsApp वर पाठवा", share_pdf: "PDF शेअर करा", send_to: "WhatsApp नंबरवर पाठवा",
			send: "पाठवा", what_happened: "काय झाले?", skip: "वगळा", open_crm: "CRM मध्ये उघडा",
			card_photo: "फोटो: कार्ड, चौकशी, ड्रॉइंग, स्पेसिफिकेशन किंवा स्क्रीनशॉट", reading: "फोटो वाचत आहे…", read_ok: "फोटोवरून भरले. कृपया तपासा.",
			read_none: "वाचता आले नाही. कृपया टाईप करा.", cust_name: "ग्राहकाचे नाव", company: "कंपनी", mobile: "मोबाईल",
			source: "स्रोत", segment: "विभाग", requirement: "गरज", lesson_done: "मी हा धडा पूर्ण केला",
			done_tick: "पूर्ण", new_files: "तुमच्या लीडवर नवीन फाईल्स", report_q: "आज तुम्ही कोणते काम केले?",
			problems_q: "अडचणी / मदत हवी", plan_q: "उद्याचे नियोजन", captured: "आज ॲपने नोंदवलेले",
			cards_done: "कार्ड पूर्ण", calls_made: "कॉल", talk_minutes: "बोलणे मिनिटे", missed_calls: "मिस कॉल", notes_added: "नोंदी", leads_created: "नवीन लीड",
			work_entries: "कामाची वही", dsi_done: "DSI", kpi_score: "महिन्याचा स्कोअर", send_report: "अहवाल पाठवा",
			report_sent: "दिवसाचा अहवाल पाठवला", report_due: "आजचा दिवसाचा अहवाल पाठवा", history: "मागील 14 दिवस",
			sent_of: "पाठवले", not_sent: "पाठवला नाही", on_time: "वेळेवर", late: "उशिरा", rating: "रेटिंग",
			comment: "टिप्पणी", save_review: "रिव्ह्यू जतन करा", none: "काही नाही", new_drawing: "पाठवायचे नवीन ड्रॉइंग",
			correction: "ड्रॉइंग दुरुस्ती", correction_q: "काय बदलायचे? (टाईप करा किंवा बोला)",
			correction_photo: "खुणा केलेला फोटो / स्क्रीनशॉट (ऐच्छिक)", send_correction: "दुरुस्ती डिझाईनला पाठवा",
			correction_sent: "डिझाईनला पाठवले. नवीन ड्रॉइंग इथेच मिळेल.", design_status: "डिझाईन",
			self: "स्वतः", customer: "ग्राहक", no_number: "नंबर नाही. कृपया टाईप करा.",
			calendar: "माझे कॅलेंडर", cal_today: "आज", cal_week: "माझा आठवडा", cal_month: "माझा महिना", done_today: "आज झालेले",
			plan: "नियोजन", now_word: "आता", later: "आज बसत नाही", tomorrow: "आजचा दिवस संपला: उद्यासाठी", week: "आठवडा", orders: "ऑर्डर", order: "ऑर्डर",
			open_items: "कामे", company_dates: "कंपनी तारखा", done_word: "झाले", due_overdue: "मुदत / उशीर",
			tap_day: "दिवस पाहण्यासाठी दाबा.", d_Mon: "सोम", d_Tue: "मंगळ", d_Wed: "बुध", d_Thu: "गुरु", d_Fri: "शुक्र", d_Sat: "शनि", d_Sun: "रवि",
			listening: "ऐकत आहे… आता बोला. थांबवण्यासाठी लाल माईक दाबा.", mic_blocked: "माईक बंद आहे. पत्त्याशेजारील 🔒 दाबा, मग Permissions → Microphone → Allow.",
			mic_network: "आवाजासाठी इंटरनेट हवे. मोबाईल डेटा तपासा आणि पुन्हा करा.", mic_nospeech: "काही ऐकू आले नाही. 🎤 दाबा, लाल झाल्यावर बोला.",
			mic_nomic: "या फोनवर माईक सापडला नाही.", mic_unsupported: "या ब्राउजरमध्ये आवाज चालत नाही. Chrome वापरा, किंवा कीबोर्डवरील माईक.",
			mail: "मेल", reminders: "आठवणी", library: "कंपनी व उत्पादने",
			reminder: "आठवण", what_remind: "काय करायचे (टाईप करा किंवा बोला)", date: "तारीख", time: "वेळ", repeat: "पुन्हा",
			no_repeat: "एकदाच", daily: "रोज", weekly: "दर आठवड्याला", monthly: "दर महिन्याला", for_whom: "कोणासाठी",
			me: "मी", set_reminder: "आठवण लावा", snooze: "10 मिनिटांनी", upcoming: "पुढील 7 दिवस",
			talk_time: "बोलण्याचा वेळ", talk_min: "बोलण्याचा वेळ (मिनिटे)", today: "आज", this_week: "हा आठवडा", calls_n: "कॉल",
			talked: "बोलणे झाले", missed: "मिस / उत्तर नाही", add_call: "कॉल नोंदवा", incoming: "ग्राहकाने कॉल केला", outgoing: "मी कॉल केला", pick_customer: "ग्राहक",
			team_talk: "टीमचा बोलण्याचा वेळ", locked: "टप्पा 2 (सशुल्क) - सुरू नाही", rec_locked: "आपोआप कॉल रेकॉर्डिंग",
			wa_locked: "ॲपमध्ये WhatsApp मेसेज (Business API)", any_number: "कोणत्याही नंबरवर पाठवा", message: "मेसेज",
			search: "शोधा", templates: "तयार मेसेज", open_chat: "चॅट उघडा",
			mail_not_ready: "कंपनी ईमेल अजून ERPNext ला जोडलेला नाही. ॲडमिनला Email Account जोडायला सांगा (मोफत). तोपर्यंत ✉️ फोनचे मेल ॲप उघडते.",
			to: "कोणाला", subject: "विषय", attach_files: "जोडा", send_mail: "ईमेल पाठवा", mail_sent: "ईमेल पाठवला", emails: "ईमेल",
			cat_Company: "कंपनी", cat_Product: "उत्पादने", "cat_Customer FAQ": "प्रश्नोत्तरे", "cat_Message Template": "मेसेज", "cat_Sales Manual": "सेल्स मॅन्युअल",
			open: "उघडा", copy: "कॉपी", copied: "कॉपी झाले", all: "सर्व",
			my_function: "माझे काम", app_usage: "ॲप वापर", faq: "प्रश्नोत्तरे", team: "टीम", read_pages: "मॅन्युअलची पाने वाचा",
			check: "धडा तपासणी", check_answers: "उत्तरे तपासा", passed: "पास", try_again: "अजून नाही. पुन्हा वाचा आणि प्रयत्न करा.",
			lessons_done: "धडे पूर्ण", photo_reading: "फोनवर कार्ड वाचत आहे… (पहिल्यांदा एक मिनिट लागेल)",
		},
	};
	// mobile-number logins and Home for people in several functions (SK, 26-Oct-2026)
	Object.assign(T.English, {
		logins: "Logins", team_leads: "Team Leads", for_everyone: "For everyone", set_pin: "Set your own PIN", set_pin_why: "HR gave you a first PIN. Make your own PIN now (4 to 8 digits). Do not tell anyone.",
		old_pin: "PIN from HR", new_pin: "New PIN", new_pin2: "New PIN again", pin_mismatch: "The two new PINs are not the same",
		pin_saved: "PIN saved", no_login: "No login yet", has_login: "Have login", closed_login: "Login closed",
		make_login: "Make login", new_login: "New login", name: "Name", functions_pick: "Function(s)", reports_to: "Reports to",
		language: "Language", workstation: "Workstation", login_ready: "Login ready", first_pin: "First PIN",
		pin_note: "Give the PIN by hand or WhatsApp. The person makes their own PIN at the first login.",
		reset_pin: "Reset PIN", close_login: "Close login", close_q: "Close this login? All past work stays in ERPNext.",
		edit_login: "Change functions", login_link: "Your SK App login", people_n: "people", without_login: "without login",
		pin_set_pending: "PIN not set yet",
	});
	Object.assign(T.Marathi, {
		logins: "लॉगिन", team_leads: "टीमचे लीड", for_everyone: "सर्वांसाठी", set_pin: "तुमचा स्वतःचा पिन ठेवा", set_pin_why: "HR ने पहिला पिन दिला आहे. आता तुमचा स्वतःचा पिन ठेवा (4 ते 8 अंक). कोणालाही सांगू नका.",
		old_pin: "HR ने दिलेला पिन", new_pin: "नवीन पिन", new_pin2: "नवीन पिन पुन्हा", pin_mismatch: "दोन्ही नवीन पिन सारखे नाहीत",
		pin_saved: "पिन सेव्ह झाला", no_login: "अजून लॉगिन नाही", has_login: "लॉगिन आहे", closed_login: "लॉगिन बंद",
		make_login: "लॉगिन बनवा", new_login: "नवीन लॉगिन", name: "नाव", functions_pick: "काम (फंक्शन)", reports_to: "कोणाला रिपोर्ट",
		language: "भाषा", workstation: "वर्कस्टेशन", login_ready: "लॉगिन तयार", first_pin: "पहिला पिन",
		pin_note: "पिन हाताने किंवा WhatsApp ने द्या. पहिल्या लॉगिनला ती व्यक्ती स्वतःचा पिन ठेवेल.",
		reset_pin: "पिन रीसेट", close_login: "लॉगिन बंद करा", close_q: "हे लॉगिन बंद करायचे? आधीचे सर्व काम ERPNext मध्ये राहील.",
		edit_login: "काम बदला", login_link: "तुमचे SK App लॉगिन", people_n: "लोक", without_login: "लॉगिनशिवाय",
		pin_set_pending: "पिन अजून ठेवला नाही",
	});
	// Store and Purchase screens (26-Oct-2026)
	Object.assign(T.English, {
		stock_check: "Stock Check",
		receive: "Receive",
		issue: "Issue",
		store_requests: "Requests",
		dispatch: "Dispatch",
		low_stock: "Low Stock",
		stock_count: "Stock Count",
		new_item: "New Item",
		buy_requests: "Requests",
		get_rates: "Get Rates",
		compare: "Compare",
		po_follow_up: "Follow-up",
		suppliers: "Suppliers",
		bills: "Bills",
		last_rates: "Last Rates",
		po_approvals: "PO Approvals",
		search_item: "Item (type or speak)",
		low: "Low",
		received: "Last received",
		issued: "Last issued",
		used_in_jobs: "Used in jobs",
		receive_help: "Material at the gate: tap its Purchase Order.",
		without_po: "Without Purchase Order",
		challan_photo: "Photo of supplier challan",
		ordered: "Ordered",
		pending: "Pending",
		goods_photo: "Photo of material at gate",
		save_receipt: "Save · send for checking",
		supplier: "Supplier",
		item: "Item",
		qty: "Quantity",
		why_no_po: "Why no PO? (speak)",
		issue_help: "Tap the job, then type or speak what is given.",
		job_card: "Job Card",
		needed: "Needed",
		given: "Given",
		other_item: "Other item",
		taken_by: "Taken by",
		taker_photo: "Photo of person taking material",
		needed_by: "needed",
		short: "Short",
		to_purchase: "Purchase",
		loaded_photo: "Photo of loaded cabin",
		plate_photo: "Photo of vehicle number plate",
		vehicle_no: "Vehicle number",
		driver_mobile: "Driver mobile",
		dispatch_tell: "Dispatch · tell Accounts & Sales",
		have: "Have",
		reorder_at: "re-order at",
		order: "Order",
		no_low: "Nothing below re-order level (or no levels set yet).",
		send_all_purchase: "Send all to Purchase",
		store_name: "Store",
		count_help: "Count each item and type or speak the number. Leave blank what you did not count.",
		rack_photo: "Photo of rack",
		send_differences: "Send differences for OK",
		item_photo: "Photo of item / label",
		item_name: "Item name",
		group: "Group",
		unit: "Unit",
		send_approval: "Send for approval",
		similar: "Similar items already in ERPNext. Same item?",
		urgent: "Urgent",
		get_rates_selected: "Get rates for selected",
		items: "Items",
		add_item_first: "Pick an item first",
		add_item: "Add item",
		no_suggestion: "No past supplier for this item. Add suppliers below.",
		add_supplier: "Add supplier",
		need_by: "Need by",
		send_rate_request: "Make rate request",
		add_quote: "Add quote (photo / screenshot)",
		quotes: "quotes",
		best: "Best",
		days: "days",
		make_po: "Make PO",
		last_purchase: "Last purchase",
		saving_vs_last: "Saving vs last rate",
		approval_rule: "SK must approve a PO above",
		quote_photo: "Photo / screenshot of supplier's reply",
		rate: "Rate (Rs, before GST)",
		delivery_days: "Delivery days",
		days_late: "days late",
		due_today: "due today",
		note: "Note",
		new_supplier: "New Supplier",
		gst_photo: "Photo of GST certificate / visiting card",
		supplier_name: "Supplier name",
		cheque_photo: "Photo of cancelled cheque (bank details)",
		bill_photo: "Photo of supplier bill",
		bill_no: "Bill number",
		amount: "Amount (Rs, with GST)",
		bill_for: "For which job / order",
		send_accounts: "Send to Accounts",
		approve: "Approve",
		reject: "Reject",
		receipt_saved: "Receipt saved",
		issued_ok: "Issued",
		kept_draft: "Saved as draft, owner to check",
		sent_purchase: "Sent to Purchase",
		dispatched: "Dispatch saved",
		differences_sent: "differences sent",
		no_differences: "No differences. Well done!",
		sent_approval: "Sent for approval",
		tick_items: "Tick the items first",
		sent_sk: "sent to SK for approval",
		po_placed: "PO placed",
		supplier_said: "What did the supplier say?",
		promised_date: "New promised date",
		approved: "Approved",
		rejected: "Rejected",
		reject_why: "Why reject?",
	});
	Object.assign(T.Marathi, {
		stock_check: "स्टॉक तपासा",
		receive: "माल आला",
		issue: "माल द्या",
		store_requests: "मागण्या",
		dispatch: "डिस्पॅच",
		low_stock: "कमी स्टॉक",
		stock_count: "स्टॉक मोजणी",
		new_item: "नवीन आयटम",
		buy_requests: "खरेदी मागण्या",
		get_rates: "दर मागवा",
		compare: "दर तुलना",
		po_follow_up: "पाठपुरावा",
		suppliers: "सप्लायर",
		bills: "बिले",
		last_rates: "मागील दर",
		po_approvals: "PO मंजुरी",
		search_item: "आयटम (टाइप करा किंवा बोला)",
		low: "कमी",
		received: "शेवटचा आलेला",
		issued: "शेवटचा दिलेला",
		used_in_jobs: "कोणत्या कामात वापरला",
		receive_help: "गेटवर माल आला: त्याची PO टॅप करा.",
		without_po: "PO शिवाय",
		challan_photo: "सप्लायर चलनाचा फोटो",
		ordered: "ऑर्डर",
		pending: "बाकी",
		goods_photo: "गेटवरील मालाचा फोटो",
		save_receipt: "सेव्ह · तपासणीला पाठवा",
		supplier: "सप्लायर",
		item: "आयटम",
		qty: "संख्या",
		why_no_po: "PO का नाही? (बोला)",
		issue_help: "काम टॅप करा, मग काय दिले ते टाइप करा किंवा बोला.",
		job_card: "जॉब कार्ड",
		needed: "लागणारे",
		given: "दिलेले",
		other_item: "इतर आयटम",
		taken_by: "कोणी घेतले",
		taker_photo: "माल घेणाऱ्याचा फोटो",
		needed_by: "पर्यंत हवे",
		short: "कमी",
		to_purchase: "खरेदी",
		loaded_photo: "लोड केलेल्या केबिनचा फोटो",
		plate_photo: "गाडीच्या नंबर प्लेटचा फोटो",
		vehicle_no: "गाडी नंबर",
		driver_mobile: "ड्रायव्हर मोबाईल",
		dispatch_tell: "डिस्पॅच · अकाउंट्स व सेल्सला कळवा",
		have: "आहे",
		reorder_at: "पुन्हा ऑर्डर पातळी",
		order: "ऑर्डर",
		no_low: "काहीही कमी नाही (किंवा पातळी अजून ठरवली नाही).",
		send_all_purchase: "सर्व खरेदीला पाठवा",
		store_name: "स्टोअर",
		count_help: "प्रत्येक आयटम मोजा आणि संख्या टाइप करा किंवा बोला. न मोजलेले रिकामे ठेवा.",
		rack_photo: "रॅकचा फोटो",
		send_differences: "फरक मंजुरीला पाठवा",
		item_photo: "आयटम / लेबलचा फोटो",
		item_name: "आयटमचे नाव",
		group: "गट",
		unit: "युनिट",
		send_approval: "मंजुरीला पाठवा",
		similar: "असेच आयटम ERPNext मध्ये आहेत. हाच आहे का?",
		urgent: "तातडीचे",
		get_rates_selected: "निवडलेल्यांचे दर मागवा",
		items: "आयटम",
		add_item_first: "आधी आयटम निवडा",
		add_item: "आयटम जोडा",
		no_suggestion: "या आयटमचा जुना सप्लायर नाही. खाली सप्लायर जोडा.",
		add_supplier: "सप्लायर जोडा",
		need_by: "कधीपर्यंत हवे",
		send_rate_request: "दर मागणी करा",
		add_quote: "दर जोडा (फोटो / स्क्रीनशॉट)",
		quotes: "दर",
		best: "सर्वात चांगला",
		days: "दिवस",
		make_po: "PO बनवा",
		last_purchase: "मागील खरेदी",
		saving_vs_last: "मागील दरापेक्षा बचत",
		approval_rule: "यापेक्षा मोठ्या PO ला SK ची मंजुरी लागते:",
		quote_photo: "सप्लायरच्या उत्तराचा फोटो / स्क्रीनशॉट",
		rate: "दर (रु, GST आधी)",
		delivery_days: "डिलिव्हरी दिवस",
		days_late: "दिवस उशीर",
		due_today: "आज यायचे",
		note: "नोंद",
		new_supplier: "नवीन सप्लायर",
		gst_photo: "GST सर्टिफिकेट / व्हिजिटिंग कार्डचा फोटो",
		supplier_name: "सप्लायरचे नाव",
		cheque_photo: "रद्द चेकचा फोटो (बँक तपशील)",
		bill_photo: "सप्लायर बिलाचा फोटो",
		bill_no: "बिल नंबर",
		amount: "रक्कम (रु, GST सह)",
		bill_for: "कोणत्या काम / ऑर्डरसाठी",
		send_accounts: "अकाउंट्सला पाठवा",
		approve: "मंजूर",
		reject: "नामंजूर",
		receipt_saved: "पावती सेव्ह झाली",
		issued_ok: "माल दिला",
		kept_draft: "ड्राफ्ट म्हणून सेव्ह, मालक तपासतील",
		sent_purchase: "खरेदीला पाठवले",
		dispatched: "डिस्पॅच सेव्ह झाले",
		differences_sent: "फरक पाठवले",
		no_differences: "काहीही फरक नाही. छान!",
		sent_approval: "मंजुरीला पाठवले",
		tick_items: "आधी आयटम निवडा",
		sent_sk: "SK कडे मंजुरीला पाठवले",
		po_placed: "PO दिली",
		supplier_said: "सप्लायर काय म्हणाला?",
		promised_date: "नवीन दिलेली तारीख",
		approved: "मंजूर केले",
		rejected: "नामंजूर केले",
		reject_why: "का नामंजूर?",
	});
	// Production, subcontractor and Quality screens (26-Oct-2026)
	Object.assign(T.English, {
		order_board: "Order Board",
		job_cards: "Job Cards",
		my_jobs: "My Jobs",
		need_material: "Need Material",
		progress_photos: "Progress Photos",
		ready_dispatch: "Ready to Dispatch",
		non_conformance: "Non-Conformance",
		my_fixes: "To Fix",
		inspect: "Inspect",
		final_check: "Final Check",
		board_help: "Every cabin in production, stage by stage. Green done · orange working · grey waiting.",
		delivery: "Delivery",
		not_set: "not set",
		no_order_link: "No Sales Order / delivery date on this job",
		no_job_cards: "No job cards",
		started: "started",
		see_drawing: "See drawing",
		jobs_today: "jobs for you today",
		photo_full: "Photo 1: full job",
		photo_detail: "Photo 2: close-up (joints, finish)",
		workers_used: "Workers used",
		anything_tell: "Anything to tell? (speak)",
		job_done_qc: "Job done · send to Quality",
		job_done_ok: "Job done. Quality is told.",
		job_done_draft: "Job done and saved. Office will close it in ERPNext.",
		say_material: "What do you need? (speak)",
		send_store: "Send to Store",
		sent_store: "Sent to Store",
		cabin: "Cabin",
		qc_pending: "QC pending",
		new_nc: "New problem (Non-Conformance)",
		fixed: "Fixed",
		incoming: "Incoming (from Store)",
		stage: "Stage (from Job Cards)",
		final: "Final (before dispatch)",
		check_now: "Check",
		checklist: "Checklist",
		accepted_qty: "Accepted qty",
		rejected_qty: "Rejected qty",
		sample: "Sample checked",
		save_check: "Save check",
		not_ok: "Not OK",
		what_wrong: "What is wrong? (speak)",
		pick_checklist: "Pick the checklist above.",
		rework_sent: "Rework sent",
		defect_photo: "Photo of defect",
		by_when: "Fix by",
		send_fixer: "Send to the person who fixes",
		what_done: "What did you do? (speak)",
		after_photo: "Photo after fixing",
		qty_matches: "Quantity matches bill", no_damage_rust: "No damage / rust", size_as_ordered: "Size and grade as ordered",
		size_as_drawing: "Size as per drawing", weld_finish: "Weld and finish OK", clean_safe: "Clean, no sharp edges",
	});
	Object.assign(T.Marathi, {
		order_board: "ऑर्डर बोर्ड",
		job_cards: "जॉब कार्ड",
		my_jobs: "माझी कामे",
		need_material: "माल हवा",
		progress_photos: "प्रगती फोटो",
		ready_dispatch: "डिस्पॅचला तयार",
		non_conformance: "दोष (NC)",
		my_fixes: "दुरुस्ती",
		inspect: "तपासणी",
		final_check: "अंतिम तपासणी",
		board_help: "उत्पादनातील प्रत्येक केबिन, टप्प्याने. हिरवा झाले · नारिंगी चालू · राखाडी बाकी.",
		delivery: "डिलिव्हरी",
		not_set: "ठरली नाही",
		no_order_link: "या कामाला सेल्स ऑर्डर / डिलिव्हरी तारीख नाही",
		no_job_cards: "जॉब कार्ड नाही",
		started: "सुरू",
		see_drawing: "ड्रॉइंग पहा",
		jobs_today: "आज तुमची कामे",
		photo_full: "फोटो 1: पूर्ण काम",
		photo_detail: "फोटो 2: जवळून (जोड, फिनिश)",
		workers_used: "किती कामगार",
		anything_tell: "काही सांगायचे आहे? (बोला)",
		job_done_qc: "काम झाले · क्वालिटीला पाठवा",
		job_done_ok: "काम झाले. क्वालिटीला कळवले.",
		job_done_draft: "काम झाले व सेव्ह झाले. ऑफिस ERPNext मध्ये बंद करेल.",
		say_material: "काय हवे? (बोला)",
		send_store: "स्टोअरला पाठवा",
		sent_store: "स्टोअरला पाठवले",
		cabin: "केबिन",
		qc_pending: "QC बाकी",
		new_nc: "नवीन दोष (NC)",
		fixed: "दुरुस्त",
		incoming: "येणारा माल (स्टोअर)",
		stage: "टप्पा (जॉब कार्ड)",
		final: "अंतिम (डिस्पॅच आधी)",
		check_now: "तपासा",
		checklist: "चेकलिस्ट",
		accepted_qty: "स्वीकारलेले",
		rejected_qty: "नाकारलेले",
		sample: "किती तपासले",
		save_check: "तपासणी सेव्ह करा",
		not_ok: "बरोबर नाही",
		what_wrong: "काय चुकले? (बोला)",
		pick_checklist: "वर चेकलिस्ट निवडा.",
		rework_sent: "पुन्हा कामासाठी पाठवले",
		defect_photo: "दोषाचा फोटो",
		by_when: "कधीपर्यंत दुरुस्त",
		send_fixer: "दुरुस्त करणाऱ्याला पाठवा",
		what_done: "काय केले? (बोला)",
		after_photo: "दुरुस्तीनंतरचा फोटो",
		qty_matches: "बिलाप्रमाणे नग", no_damage_rust: "तुटफूट / गंज नाही", size_as_ordered: "ऑर्डरप्रमाणे साईज व ग्रेड",
		size_as_drawing: "ड्रॉइंगप्रमाणे साईज", weld_finish: "वेल्डिंग व फिनिश ठीक", clean_safe: "स्वच्छ, धारदार कडा नाहीत",
	});
	const ICON = {
		my_day: "☀️", my_leads: "📞", my_deals: "🤝", my_kpi: "⭐", work_book: "📒", dsi: "💡", problem: "🚩",
		job_cards: "🛠️", inspections: "✅", stock_alerts: "📦", material_requests: "🧾", invoice_photo: "📷",
		collections: "💰", team_scorecards: "👥", site_checklist: "📋", ceo_view: "📊",
		calendar: "📅", follow_up: "🔔", new_lead: "➕", training: "🎓", day_report: "📝", team_reports: "🗂️",
		calls: "📞", whatsapp: "💬", mail: "✉️", reminders: "⏰", library: "🏢", logins: "🔑", team_leads: "👥",
		stock_check: "📦", receive: "🚚", issue: "📤", store_requests: "📋", dispatch: "🚛", low_stock: "⚠️", stock_count: "🔢", new_item: "🆕",
		buy_requests: "📋", get_rates: "💬", compare: "⚖️", po_follow_up: "📞", suppliers: "🏭", bills: "📷", last_rates: "💹", po_approvals: "✅",
		order_board: "🏗️", job_cards: "🛠️", my_jobs: "🛠️", need_material: "📦", progress_photos: "📸", ready_dispatch: "🚛", non_conformance: "❗",
		my_fixes: "🔧", inspect: "🔍", final_check: "🏁",
	};
	const t = (k) => (T[state.lang] || T.English)[k] || k;
	const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

	async function call(method, args, post) {
		const opts = { headers: { Accept: "application/json", "X-Frappe-CSRF-Token": CSRF }, credentials: "same-origin" };
		let url = "/api/method/sk_app.api." + method;
		if (post) {
			opts.method = "POST";
			opts.headers["Content-Type"] = "application/json";
			opts.body = JSON.stringify(args || {});
		} else if (args) {
			url += "?" + new URLSearchParams(args);
		}
		const res = await fetch(url, opts);
		const data = await res.json().catch(() => ({}));
		if (!res.ok) {
			let msg = "Error";
			try { msg = JSON.parse(JSON.parse(data._server_messages)[0]).message; } catch (e) { msg = data.exception || msg; }
			throw new Error(msg);
		}
		return data.message;
	}

	async function upload(file) {
		const fd = new FormData();
		fd.append("file", file, file.name);
		fd.append("is_private", "1");
		const res = await fetch("/api/method/upload_file", { method: "POST", body: fd, headers: { "X-Frappe-CSRF-Token": CSRF }, credentials: "same-origin" });
		const data = await res.json();
		if (!res.ok) throw new Error("Upload failed");
		return data.message.file_url;
	}

	function toast(msg, bad) {
		const el = document.createElement("div");
		el.className = "sk-toast" + (bad ? " bad" : "");
		el.textContent = msg;
		document.body.appendChild(el);
		setTimeout(() => el.remove(), 2600);
	}

	const micLang = {}; // per text box: "en" or "mr"; default follows the app language
	let listening = null; // the one running recognition: { rec, input, button, base, got }
	function micError(code) {
		return { "not-allowed": t("mic_blocked"), "service-not-allowed": t("mic_blocked"), network: t("mic_network"),
			"no-speech": t("mic_nospeech"), "audio-capture": t("mic_nomic") }[code] || t("mic_nospeech");
	}
	function stopListening() {
		if (!listening) return;
		try { listening.rec.stop(); } catch (e) { /* already stopped */ }
	}
	// Tap 🎤: it turns red "Listening… speak now", words appear in the box while you speak, and it keeps listening
	// until you stop talking (tap the red mic to stop early). Each failure says why (permission, internet, silence).
	function speakInto(input, button) {
		const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
		if (!SR) { toast(t("mic_unsupported"), true); return; }
		if (listening) { const same = listening.input === input; stopListening(); if (same) return; }
		const rec = new SR();
		const ml = micLang[input.id] || (state.lang === "Marathi" ? "mr" : "en");
		rec.lang = ml === "mr" ? "mr-IN" : "en-IN";
		rec.interimResults = true;
		rec.continuous = true;
		rec.maxAlternatives = 1;
		const L = { rec, input, button, base: input.value ? input.value.replace(/\s+$/, "") + " " : "", got: "", error: null };
		listening = L;
		rec.onstart = () => {
			if (button) { button.classList.add("on"); button.textContent = "●"; }
			const hint = document.createElement("div");
			hint.className = "sk-listening";
			hint.textContent = "🔴 " + t("listening");
			(input.closest(".sk-field") || input.parentElement).appendChild(hint);
			L.hint = hint;
			if (navigator.vibrate) navigator.vibrate(60);
		};
		rec.onresult = (e) => {
			let final = "", interim = "";
			for (let i = 0; i < e.results.length; i++) {
				const txt = e.results[i][0].transcript;
				if (e.results[i].isFinal) final += txt + " "; else interim += txt;
			}
			// Android repeats earlier final parts in continuous mode: keep the longest final text seen
			if (final.trim().length >= L.got.length) L.got = final.trim();
			input.value = L.base + (L.got + " " + interim).trim();
		};
		rec.onerror = (e) => { L.error = e.error; };
		rec.onend = () => {
			if (button) { button.classList.remove("on"); button.textContent = "🎤"; }
			if (L.hint) L.hint.remove();
			input.value = (L.base + L.got).trim() || input.value.trim();
			if (listening === L) listening = null;
			if (L.error && L.error !== "aborted") toast(micError(L.error), true);
			else if (!L.got && !L.error) toast(t("mic_nospeech"), true);
		};
		try { rec.start(); } catch (e) { listening = null; toast(micError(""), true); }
	}

	function readAloud(text) {
		if (!window.speechSynthesis) return;
		const u = new SpeechSynthesisUtterance(text);
		u.lang = state.lang === "Marathi" ? "mr-IN" : "en-IN";
		speechSynthesis.cancel();
		speechSynthesis.speak(u);
	}

	function whoAmI() {
		const h = state.home || {};
		const fn = h.home && h.home.label ? (h.home.label[state.lang] || h.home.label.English) : "";
		return [h.full_name || h.user, fn].filter(Boolean).join(" · ");
	}

	// fixed at the top on every screen: back / logo, screen title, the person's name and function, language
	function header(title) {
		return `<header class="sk-head">
			${state.view !== "home" ? `<button class="sk-back" data-go="home">‹</button>` : `<img src="/assets/sk_app/icons/icon-192.png" class="sk-logo" alt="SK">`}
			<div class="sk-title">${esc(title)}<small>${esc(whoAmI())}</small></div>
			<button class="sk-lang" data-act="lang">${t("lang")}</button>
		</header>`;
	}

	function fitHead() {
		const h = root.querySelector(".sk-head");
		if (h) document.body.style.paddingTop = h.offsetHeight + "px";
	}
	new MutationObserver(fitHead).observe(root, { childList: true });
	window.addEventListener("resize", fitHead);

	function cardHtml(card) {
		if (!card) return `<section class="sk-card"><div class="sk-card-label">${t("now")}</div><button class="sk-btn" data-act="newcard">${t("refresh")}</button></section>`;
		const answered = card.response ? `<div class="sk-answered">✓ ${esc(card.response)}</div>` : "";
		return `<section class="sk-card">
			<div class="sk-card-label">${t("now")} <button class="sk-icon" data-act="read" title="Read aloud">🔊</button></div>
			<div class="sk-card-text">${esc(card.card_text)}</div>
			<div class="sk-card-meta">${esc(card.minutes || "")} ${t("min")} · ${esc(card.source || "")}</div>
			${answered}
			<div class="sk-card-actions">
				<button class="sk-btn go" data-resp="Started">▶ ${t("start")}</button>
				<button class="sk-btn ok" data-resp="Done">✓ ${t("done")}</button>
				<button class="sk-btn" data-resp="Need more time">⏱ ${t("more_time")}</button>
				<button class="sk-btn bad" data-resp="Problem">⚠ ${t("trouble")}</button>
			</div>
			<button class="sk-link" data-act="newcard">↻ ${t("refresh")}</button>
		</section>`;
	}

	// Home is only small icons (SK). Alerts become a red count on their icon: new drawings on Follow-up, reminders
	// due now on Reminders, the evening Day Report on its icon. The "What to do now" card lives in My Day.
	function fileBanners() {
		return ((state.home && state.home.new_files) || []).map((f) => `<button class="sk-banner new" data-open="${esc(f.doctype)}" data-name="${esc(f.attached_to_name)}">📐 ${t("new_drawing")}: ${esc(f.title)}<br><small>${esc(f.file_name)}</small></button>`).join("");
	}
	function renderHome() {
		const h = state.home;
		const fn = h.home;
		const badge = {
			...(h.badges || {}),
			follow_up: (h.new_files || []).length,
			reminders: dueNow().length,
			day_report: !h.day_report_sent && new Date().getHours() >= 17 ? "!" : 0,
		};
		if (h.must_set_pin) return renderSetPin();
		const tile = (k) => `<button class="sk-tile" data-go="${k}"><span class="sk-tile-icon">${ICON[k] || "•"}</span><span>${t(k)}</span>${badge[k] ? `<b class="sk-dot">${esc(badge[k])}</b>` : ""}</button>`;
		const tiles = (keys) => `<div class="sk-tiles small">${keys.map(tile).join("")}</div>`;
		if (!h.sections) { root.innerHTML = header("SK App") + `<main>${tiles(fn.tiles)}</main>`; return; }
		// a person in several functions: one labelled row per function, then the tiles everyone has (SK, 26-Oct)
		const label = (l) => (l && (l[state.lang] || l.English)) || "";
		const rows = h.sections.sections.filter((x) => x.tiles.length).map((x) => `<h3 class="sk-h sk-fn-row">${esc(label(x.label))}</h3>${tiles(x.tiles)}`).join("");
		root.innerHTML = header("SK App") + `<main>${rows}<h3 class="sk-h sk-fn-row">${t("for_everyone")}</h3>${tiles(h.sections.shared)}</main>`;
	}

	function renderSetPin() {
		state.view = "home";
		root.innerHTML = header(t("set_pin")) + `<main class="sk-form">
			<p class="sk-note">🔑 ${t("set_pin_why")}</p>
			<label class="sk-field"><span>${t("old_pin")}</span><input id="p-old" type="password" inputmode="numeric" autocomplete="current-password"></label>
			<label class="sk-field"><span>${t("new_pin")}</span><input id="p-new" type="password" inputmode="numeric" autocomplete="new-password" maxlength="8"></label>
			<label class="sk-field"><span>${t("new_pin2")}</span><input id="p-new2" type="password" inputmode="numeric" autocomplete="new-password" maxlength="8"></label>
			<button class="sk-btn ok wide" data-act="pin-save">${t("save")}</button></main>`;
	}

	// HR: every login is made from the person's mobile number; the app gives a first PIN (SK, 26-Oct)
	let loginOpts = null;
	async function renderLogins() {
		const people = await call("hr_people");
		root._people = people;
		const none = people.filter((p) => p.state === "none");
		const fnLabel = (f) => { const o = loginOpts && loginOpts.functions.find((x) => x.name === f); return o ? (o.label[state.lang] || o.label.English || f) : f; };
		const row = (p, i) => {
			const sub = [p.designation, p.mobile, p.functions.map(fnLabel).join(" + ")].filter(Boolean).join(" · ");
			const warn = p.state === "active" && p.must_set_pin ? ` <span class="sk-due">${t("pin_set_pending")}</span>` : "";
			const btn = p.state === "none" ? `<button class="sk-chip on" data-act="login-new" data-i="${i}">+ ${t("make_login")}</button>`
				: p.state === "closed" ? `<button class="sk-chip" data-act="login-new" data-i="${i}">↺ ${t("make_login")}</button>`
				: `<button class="sk-chip" data-act="login-new" data-i="${i}">✏️ ${t("edit_login")}</button>
					<button class="sk-chip" data-act="login-reset" data-i="${i}">🔑 ${t("reset_pin")}</button>
					<button class="sk-chip bad" data-act="login-close" data-i="${i}">✕ ${t("close_login")}</button>`;
			return `<li class="sk-item sk-person"><div><b>${esc(p.name)}</b>${warn}<div class="sk-item-meta">${esc(sub)}</div></div><div class="sk-row sk-wrap">${btn}</div></li>`;
		};
		const group = (title, st) => {
			const rows = people.map((p, i) => (p.state === st ? row(p, i) : "")).join("");
			return rows ? `<h3 class="sk-h">${title}</h3><ul class="sk-list">${rows}</ul>` : "";
		};
		root.innerHTML = header(t("logins")) + `<main>
			<p class="sk-note">${people.length} ${t("people_n")} · ${none.length} ${t("without_login")}</p>
			<button class="sk-btn go wide" data-act="login-new">➕ ${t("new_login")}</button>
			${group(t("no_login"), "none")}${group(t("has_login"), "active")}${group(t("closed_login"), "closed")}</main>`;
		if (!loginOpts) loginOpts = await call("hr_login_options").catch(() => null);
	}

	async function loginSheet(p) {
		if (!loginOpts) loginOpts = await call("hr_login_options");
		p = p || { functions: [] };
		const have = new Set(p.functions.length ? p.functions : (p.home ? [p.home] : []));
		const fns = loginOpts.functions.map((f) => `<button class="sk-chip ${have.has(f.name) ? "on" : ""}" data-fnpick="${esc(f.name)}">${esc(f.label[state.lang] || f.label.English || f.name)}</button>`).join("");
		const mgr = `<option value="">-</option>` + loginOpts.managers.map((m) => `<option value="${esc(m.user)}" ${m.user === p.manager ? "selected" : ""}>${esc(m.full_name || m.user)}</option>`).join("");
		const ws = `<option value="">-</option>` + loginOpts.workstations.map((w) => `<option ${w === p.workstation ? "selected" : ""}>${esc(w)}</option>`).join("");
		sheet(`<h3 class="sk-h">🔑 ${p.name ? esc(p.name) : t("new_login")}</h3>
			<label class="sk-field"><span>${t("name")}</span><input id="g-name" value="${esc(p.name || "")}" ${p.employee ? "readonly" : ""}></label>
			<label class="sk-field"><span>${t("mobile")}</span><input id="g-mobile" type="tel" inputmode="numeric" value="${esc(p.mobile || "")}" placeholder="98XXXXXXXX"></label>
			<div class="sk-field"><span>${t("functions_pick")}</span><div class="sk-row sk-wrap" id="g-fns">${fns}</div></div>
			<label class="sk-field" id="g-ws-row"><span>${t("workstation")}</span><select id="g-ws" class="sk-select">${ws}</select></label>
			<label class="sk-field"><span>${t("reports_to")}</span><select id="g-mgr" class="sk-select">${mgr}</select></label>
			<label class="sk-field"><span>${t("language")}</span><select id="g-lang" class="sk-select"><option>English</option><option value="Marathi" ${state.lang === "Marathi" ? "selected" : ""}>मराठी</option></select></label>
			<button class="sk-btn ok wide" data-act="login-make" data-emp="${esc(p.employee || "")}">${t("make_login")}</button>
			<button class="sk-btn wide" data-act="close-sheet">${t("back")}</button>`);
		showWorkstation();
	}
	function showWorkstation() {
		const on = !!root.querySelector('[data-fnpick="Subcontractor"].on');
		const r = document.getElementById("g-ws-row");
		if (r) r.style.display = on ? "" : "none";
	}

	function pinSheet(r) {
		const msg = `${t("login_link")}: ${location.origin}/sk\n${t("mobile")}: ${r.mobile}\n${t("first_pin")}: ${r.pin}`;
		root._pinMsg = { mobile: r.mobile, text: msg };
		sheet(`<h3 class="sk-h">✅ ${t("login_ready")}</h3>
			<p class="sk-big">${t("mobile")}: <b>${esc(r.mobile || "")}</b><br>${t("first_pin")}: <b>${esc(r.pin)}</b></p>
			<p class="sk-note">${t("pin_note")}</p>
			<button class="sk-btn ok wide" data-act="login-wa">💬 ${t("send")} WhatsApp</button>
			<button class="sk-btn wide" data-act="close-sheet">${t("done")}</button>`);
	}

	function itemRow(i) {
		const due = i.due ? `<span class="sk-due">${t("due")} ${esc(i.due.slice(5, 16))}</span>` : "";
		const link = i.doctype && i.name ? (i.doctype.startsWith("CRM ") ? `/crm/${i.doctype === "CRM Lead" ? "leads" : "deals"}/${encodeURIComponent(i.name)}` : `/app/${i.doctype.toLowerCase().replace(/ /g, "-")}/${encodeURIComponent(i.name)}`) : "";
		let open = link ? `<a class="sk-open" href="${link}">›</a>` : "";
		if (i.doctype && i.doctype.startsWith("CRM ") && i.name) open = `<button class="sk-open" data-open="${esc(i.doctype)}" data-name="${esc(i.name)}">›</button>`;
		if (i.kind === "day_report") open = `<button class="sk-open" data-go="day_report">›</button>`;
		if (i.kind === "send_file") open = `<button class="sk-open" data-open="${esc(i.ref_doctype)}" data-name="${esc(i.ref_name)}">›</button>`;
		return `<li class="sk-item k-${esc(i.kind)}"><div><div class="sk-item-title">${esc(i.title)}</div><div class="sk-item-meta">${esc(i.kind.replace("_", " "))} · ${esc(i.minutes)} ${t("min")} ${due}</div></div>${open}</li>`;
	}

	async function renderMyDay() {
		const d = await call("my_day");
		if (!state.card || Date.now() - new Date(String(state.card.slot_start).replace(" ", "T")).getTime() > 10 * 60 * 1000) {
			state.card = await call("next_card", {}, true).catch(() => state.card);
		}
		root.innerHTML = header(t("my_day")) + `<main>${cardHtml(state.card || d.card)}<ul class="sk-list">${d.items.map(itemRow).join("") || `<li class="sk-empty">${t("nothing")}</li>`}</ul></main>`;
	}

	async function renderLeads(which) {
		const d = await call("my_leads");
		const rows = which === "my_deals" ? d.deals : d.leads;
		root.innerHTML = header(t(which)) + `<main><ul class="sk-list">${rows.map(itemRow).join("") || `<li class="sk-empty">${t("nothing")}</li>`}</ul></main>`;
	}

	async function renderKpi() {
		const d = await call("my_kpi");
		const rows = d.kpis.map((k) => {
			const pct = k.monthly_target ? Math.min(100, Math.round((k.actual / k.monthly_target) * 100)) : 0;
			const fmt = (v) => (k.unit === "Rs" ? "₹" + (v / 100000).toFixed(1) + " L" : k.unit === "%" ? v + "%" : v);
			return `<li class="sk-kpi c-${k.colour}"><div class="sk-kpi-top"><span>${esc(k.kpi_label)}</span><span>${k.weight}%</span></div>
				<div class="sk-bar"><div style="width:${pct}%"></div></div>
				<div class="sk-kpi-num">${k.live ? `${t("actual")} ${fmt(k.actual)} / ${t("target")} ${fmt(k.monthly_target)}` : t("not_live")}</div></li>`;
		}).join("");
		const stars = "★".repeat(Math.min(5, Math.round(d.total_score / 20))) + "☆".repeat(5 - Math.min(5, Math.round(d.total_score / 20)));
		root.innerHTML = header(t("my_kpi")) + `<main><div class="sk-score"><div>${t("score")} · ${esc(d.month)}</div><div class="sk-score-num">${d.total_score}%</div><div class="sk-stars">${stars}</div></div><ul class="sk-list">${rows}</ul></main>`;
	}

	function formField(id, label, big) {
		return `<label class="sk-field"><span>${esc(label)}</span><div class="sk-input-row">
			${big ? `<textarea id="${id}" rows="3"></textarea>` : `<input id="${id}">`}
			<div class="sk-micbox"><button class="sk-mic" data-mic="${id}" title="${t("speak")}">🎤</button>
			<button class="sk-miclang" data-miclang="${id}">${(micLang[id] || (state.lang === "Marathi" ? "mr" : "en")) === "en" ? "EN" : "मर"}</button></div></div></label>`;
	}

	function photoField(id, label, anyFile) {
		return `<label class="sk-field"><span>${esc(label || t("photo"))}</span><input id="${id || "f-photo"}" type="file" ${anyFile ? 'accept="image/*,application/pdf,.dwg,.dxf,.xlsx,.docx"' : 'accept="image/*" capture="environment"'}></label>`;
	}

	async function photoUrl(id) {
		const f = document.getElementById(id || "f-photo");
		return f && f.files[0] ? upload(f.files[0]) : null;
	}

	function renderDsi() {
		root.innerHTML = header(t("dsi")) + `<main class="sk-form">${formField("f-what", t("dsi_q"), true)}${formField("f-before", t("before"))}${formField("f-after", t("after"))}${photoField()}
			<button class="sk-btn ok wide" data-act="save-dsi">${t("save")}</button></main>`;
	}

	async function renderWork(kind) {
		const problem = kind === "problem";
		const types = ["Machine breakdown", "Material shortage", "Quality issue", "Safety", "Customer complaint", "IT / app", "Pay / leave", "Other"];
		const pick = problem ? `<div class="sk-chips">${types.map((p) => `<button class="sk-chip" data-ptype="${p}">${p}</button>`).join("")}</div>` : "";
		let log = "";
		if (!problem) {
			const rows = await call("my_work_log", { days: 7 });
			log = `<ul class="sk-list">${rows.map((r) => `<li class="sk-item"><div><div class="sk-item-title">${esc(r.description)}</div><div class="sk-item-meta">${esc(r.date)} · ${esc(r.entry_type)} · ${esc(r.status)}</div></div></li>`).join("")}</ul>`;
		}
		root.innerHTML = header(t(kind)) + `<main class="sk-form">${pick}${formField("f-desc", problem ? t("problem_q") : t("work_q"), true)}${photoField()}
			<button class="sk-btn ${problem ? "bad" : "ok"} wide" data-act="save-work" data-kind="${problem ? "Problem" : "Extra Work"}">${t("save")}</button>${log}</main>`;
	}

	function renderSoon(k) {
		const desk = (state.home.home && state.home.home.desk) || "/app";
		root.innerHTML = header(t(k)) + `<main><p class="sk-soon">${t("soon")}</p><a class="sk-btn wide" href="${desk}">${t("open_erp")}</a></main>`;
	}

	// ---------- CRM on the phone ----------
	let crmOpts = null;
	let pending = null; // contact the person just started (call / WhatsApp / email), to log on return
	let current = null; // lead or deal open on the detail screen

	async function options() {
		if (!crmOpts) crmOpts = await call("crm_options");
		return crmOpts;
	}

	function waNumber(m) {
		let d = String(m || "").replace(/\D/g, "");
		if (d.length === 11 && d[0] === "0") d = d.slice(1);
		return d.length === 10 ? "91" + d : d;
	}

	function contactButtons(r) {
		const b = (ch, icon, ok) => `<button class="sk-cbtn" ${ok ? "" : "disabled"} data-contact="${ch}" data-doctype="${esc(r.doctype)}" data-name="${esc(r.name)}" data-mobile="${esc(r.mobile || "")}" data-email="${esc(r.email || "")}">${icon}</button>`;
		return `<div class="sk-contact">${b("Call", "📞", r.mobile)}${b("WhatsApp", "💬", r.mobile)}${b("Email", "✉️", r.email)}</div>`;
	}

	function when(s) { return s ? esc(String(s).slice(5, 16)) : ""; }

	async function renderFollowUp() {
		const rows = await call("follow_up");
		const li = rows.map((r) => `<li class="sk-fu ${r.overdue ? "late" : r.new ? "new" : ""}">
			<button class="sk-fu-main" data-open="${esc(r.doctype)}" data-name="${esc(r.name)}">
				<div class="sk-item-title">${esc(r.title)} ${r.new ? `<span class="sk-badge">${t("new_badge")}</span>` : ""}${r.overdue ? `<span class="sk-badge bad">${t("overdue")}</span>` : ""}</div>
				<div class="sk-item-meta">${esc(r.person || "")} · ${esc(r.status || "")} · ${r.doctype === "CRM Deal" ? t("deals") : t("leads")}</div>
				${r.next || r.due ? `<div class="sk-item-meta">${t("next")}: ${esc(r.next || "")} ${r.due ? "· " + when(r.due) : ""}</div>` : ""}
				${r.last ? `<div class="sk-item-meta">${t("last")}: ${esc(r.last.text)} · ${when(r.last.on)}</div>` : ""}
			</button>${contactButtons(r)}</li>`).join("");
		root.innerHTML = header(t("follow_up")) + `<main>${fileBanners()}<button class="sk-btn go wide" data-go="new_lead">➕ ${t("new_lead")}</button><ul class="sk-list sk-gap">${li || `<li class="sk-empty">${t("nothing")}</li>`}</ul></main>`;
	}

	function erpDocRow(doctype, d, mobile) {
		const amt = d.grand_total ? "₹" + Number(d.grand_total).toLocaleString("en-IN") : "";
		return `<li class="sk-item"><div><div class="sk-item-title">${esc(d.name)}</div><div class="sk-item-meta">${esc(d.status || "")} · ${esc(d.transaction_date || "")} · ${amt}</div>
			<div class="sk-row">
				<a class="sk-chip" href="${esc(d.pdf)}" target="_blank">📄 ${t("pdf")}</a>
				<button class="sk-chip" data-act="wa-send" data-doctype="${doctype}" data-name="${esc(d.name)}" data-mobile="${esc(mobile || "")}">💬 ${t("send_customer")}</button>
				<button class="sk-chip" data-act="share-pdf" data-pdf="${esc(d.pdf)}" data-file="${esc(d.name)}.pdf">↗ ${t("share_pdf")}</button>
			</div></div></li>`;
	}

	async function renderDetail(doctype, name) {
		const [d, o, mails] = await Promise.all([call("crm_detail", { doctype, name }), options(), call("mail_thread", { doctype, name }).catch(() => [])]);
		const doc = d.doc;
		current = { doctype, name, mobile: doc.mobile_no || doc.phone, email: doc.email };
		const statuses = (doctype === "CRM Lead" ? o.lead_statuses : o.deal_statuses) || [];
		const chips = statuses.map((s) => `<button class="sk-chip ${s.name === doc.status ? "on" : ""}" data-act="status" data-status="${esc(s.name)}">${esc(s.name)}</button>`).join("");
		const files = d.files.map((f) => `<li class="sk-item"><div><a class="sk-item-title" href="${esc(f.file_url)}" target="_blank">📎 ${esc(f.file_name)}</a><div class="sk-item-meta">${esc(f.owner)} · ${when(f.creation)}</div></div>
			<button class="sk-open ${f.for_customer ? "sk-send" : ""}" data-act="share-pdf" data-pdf="${esc(f.file_url)}" data-file="${esc(f.file_name)}" ${f.for_customer ? `data-fileid="${esc(f.name)}"` : ""}>${f.for_customer ? "💬 " + t("send") : "↗"}</button>
			${f.for_customer ? `<button class="sk-open sk-fix" data-act="correction" data-fileid="${esc(f.name)}" data-file="${esc(f.file_name)}">✏️</button>` : ""}</li>`).join("");
		const tasks = d.tasks.map((x) => `<li class="sk-item"><div><div class="sk-item-title">${esc(x.title)}</div><div class="sk-item-meta">${esc(x.status)} · ${when(x.due_date)}</div></div></li>`).join("");
		const calls = d.calls.map((x) => `<li class="sk-item"><div><div class="sk-item-title">📞 ${esc(x.type)} · ${esc(x.status)}</div><div class="sk-item-meta">${when(x.creation)}${x.duration ? " · " + t("talk_time") + " " + dur(x.duration) : ""}</div></div></li>`).join("");
		const notes = d.notes.map((n) => `<li class="sk-item"><div><div class="sk-item-title">${esc(n.title)}</div>${n.content && n.content !== n.title ? `<div>${esc(n.content)}</div>` : ""}<div class="sk-item-meta">${esc(n.owner)} · ${when(n.creation)}</div></div></li>`).join("");
		const sec = (title, body) => body ? `<h3 class="sk-h">${title}</h3><ul class="sk-list">${body}</ul>` : "";
		const mobile = current.mobile;
		root.innerHTML = header(doc.organization || doc.lead_name || name) + `<main>
			<div class="sk-info"><div class="sk-item-title">${esc(doc.lead_name || "")}</div>
				<div class="sk-item-meta">${esc(mobile || "")} ${doc.email ? "· " + esc(doc.email) : ""}</div>
				<div class="sk-item-meta">${[doc.status, doc.source, doc.sk_segment, doc.deal_value ? "₹" + Number(doc.deal_value).toLocaleString("en-IN") : ""].filter(Boolean).map(esc).join(" · ")}</div>
				${doc.next_step ? `<div class="sk-item-meta">${t("next")}: ${esc(doc.next_step)}</div>` : ""}
				${doc.design_status ? `<div class="sk-item-meta">📐 ${t("design_status")}: <b>${esc(doc.design_status)}</b></div>` : ""}
				${contactButtons({ doctype, name, mobile, email: doc.email })}</div>
			<h3 class="sk-h">${t("status")}</h3><div class="sk-chips">${chips}</div>
			<div class="sk-form">${formField("f-note", t("note_q"), true)}${photoField("f-photo", t("attach"), true)}
				<button class="sk-btn ok wide" data-act="save-note">${t("add_note")}</button>
				<button class="sk-btn wide sk-gap" data-act="reminder-new" data-doctype="${esc(doctype)}" data-name="${esc(name)}">⏰ + ${t("reminder")}</button></div>
			${sec(t("quotations"), d.quotations.map((q) => erpDocRow("Quotation", q, mobile)).join(""))}
			${sec(t("sales_orders"), d.sales_orders.map((q) => erpDocRow("Sales Order", q, mobile)).join(""))}
			${sec(t("files"), files)}${sec(t("tasks"), tasks)}${sec(t("emails"), mails.map((m) => `<li class="sk-item"><div><div class="sk-item-title">${m.sent_or_received === "Received" ? "📥" : "📤"} ${esc(m.subject || "")}</div>
				<div class="sk-libtext">${esc((m.text || "").slice(0, 400))}</div><div class="sk-item-meta">${esc(m.sender || "")} · ${when(m.communication_date)}</div></div></li>`).join(""))}
			${sec(t("notes"), notes)}${sec(t("calls"), calls)}
			<a class="sk-btn wide" href="${esc(d.crm_url)}">${t("open_crm")}</a></main>`;
	}

	function sheet(html) {
		closeSheet();
		const el = document.createElement("div");
		el.className = "sk-sheet-wrap";
		el.innerHTML = `<div class="sk-sheet sk-form">${html}</div>`;
		root.appendChild(el);
		return el;
	}
	function closeSheet() { const s = root.querySelector(".sk-sheet-wrap"); if (s) s.remove(); }

	function outcomeSheet(p) {
		const outs = p.channel === "Call" ? ((crmOpts && crmOpts.call_outcomes) || ["Talked", "No answer", "Busy", "Missed", "Call back later", "Wrong number"]) : [];
		// time away on the call, rounded to half minutes; the person corrects it if the phone rang long
		const away = Math.max(0, Math.round(((p.back || Date.now()) - p.at) / 30000) / 2);
		sheet(`<h3 class="sk-h">${t("what_happened")} (${t(p.channel.toLowerCase())})</h3>
			<div class="sk-chips">${outs.map((x) => `<button class="sk-chip" data-ptype="${esc(x)}">${esc(x)}</button>`).join("")}</div>
			${p.channel === "Call" ? `<label class="sk-field"><span>${t("talk_min")}</span><input id="f-outmin" type="number" inputmode="decimal" min="0" step="0.5" value="${away}"></label>` : ""}
			${formField("f-out", t("note_q"), true)}${photoField("f-outphoto")}
			<button class="sk-btn ok wide" data-act="save-contact">${t("save")}</button>
			<button class="sk-btn wide" data-act="close-sheet">${t("skip")}</button>`);
	}

	function waSheet(doctype, name, mobile) {
		const self = (state.home && state.home.mobile) || "";
		sheet(`<h3 class="sk-h">${t("send_to")}</h3>
			<div class="sk-contact sk-two">
				<button class="sk-chip" data-wa-pick="${esc(self)}">👤 1) ${t("self")}</button>
				<button class="sk-chip on" data-wa-pick="${esc(mobile || "")}">🧑‍💼 2) ${t("customer")}</button>
			</div>
			<label class="sk-field"><span>${t("mobile")}</span><div class="sk-input-row"><input id="f-wa" type="tel" value="${esc(mobile || "")}"></div></label>
			<button class="sk-btn ok wide" data-act="wa-go" data-doctype="${esc(doctype)}" data-name="${esc(name)}">💬 ${t("send")}</button>
			<button class="sk-btn wide" data-act="close-sheet">${t("back")}</button>`);
	}

	async function sharePdf(url, fileName) {
		const res = await fetch(url, { credentials: "same-origin" });
		if (!res.ok) throw new Error("Could not get the file");
		const blob = await res.blob();
		const file = new File([blob], fileName, { type: blob.type || "application/pdf" });
		if (navigator.canShare && navigator.canShare({ files: [file] })) return navigator.share({ files: [file], title: fileName });
		const a = document.createElement("a");
		a.href = URL.createObjectURL(blob);
		a.download = fileName;
		a.click();
	}

	async function renderNewLead() {
		const o = await options();
		const sel = (id, label, items) => `<label class="sk-field"><span>${esc(label)}</span><select id="${id}" class="sk-select"><option value=""></option>${(items || []).map((x) => `<option>${esc(x)}</option>`).join("")}</select></label>`;
		root.innerHTML = header(t("new_lead")) + `<main class="sk-form">
			${photoField("f-card", "📷 " + t("card_photo"))}
			${formField("f-first", t("cust_name"))}${formField("f-org", t("company"))}
			<label class="sk-field"><span>${t("mobile")}</span><div class="sk-input-row"><input id="f-mobile" type="tel"></div></label>
			<label class="sk-field"><span>${t("email")}</span><div class="sk-input-row"><input id="f-email" type="email"></div></label>
			${sel("f-source", t("source"), o.sources)}${sel("f-segment", t("segment"), o.segments)}
			${formField("f-req", t("requirement"), true)}
			<button class="sk-btn ok wide" data-act="save-lead">${t("save")}</button></main>`;
		document.getElementById("f-card").addEventListener("change", readCard);
	}

	let cardUrl = null;
	// Free reading on the phone itself (tesseract, bundled in the app; loaded only now, then cached by the phone).
	// Claude is used instead only if the company adds its key later.
	let ocrWorker = null;
	function loadScript(src) {
		return new Promise((ok, bad) => { const el = document.createElement("script"); el.src = src; el.onload = ok; el.onerror = bad; document.head.appendChild(el); });
	}
	async function shrink(file, max) {
		const img = await createImageBitmap(file);
		const k = Math.min(1, max / Math.max(img.width, img.height));
		const c = document.createElement("canvas");
		c.width = Math.round(img.width * k);
		c.height = Math.round(img.height * k);
		c.getContext("2d").drawImage(img, 0, 0, c.width, c.height);
		return c;
	}
	async function readOnPhone(file, progress) {
		const base = "/assets/sk_app/ocr/";
		if (!window.Tesseract) await loadScript(base + "tesseract.min.js");
		if (!ocrWorker) {
			ocrWorker = await Tesseract.createWorker("eng", 1, { workerPath: base + "worker.min.js", corePath: base, langPath: base.slice(0, -1),
				gzip: true, logger: (m) => { if (m.status && m.progress != null) progress(m.status, m.progress); } });
			// read line by line across the page: keeps invoice / spec table rows together (default mode splits columns)
			await ocrWorker.setParameters({ tessedit_pageseg_mode: "4", preserve_interword_spaces: "1" });
		}
		const { data } = await ocrWorker.recognize(await shrink(file, 2000));
		return window.skParseCard(data.text);
	}
	async function readCard(ev) {
		const f = ev.target.files[0];
		if (!f) return;
		const fill = (d) => {
			const set = (id, v) => { const el = document.getElementById(id); if (el && v && !el.value) el.value = v; };
			set("f-first", d.first_name); set("f-org", d.organization); set("f-mobile", d.mobile_no); set("f-email", d.email); set("f-req", d.requirement);
			// source / segment: pick the list entry whose name contains the word found (IndiaMART, Cabin, Machine Shifting...)
			const pick = (id, word) => {
				const el = document.getElementById(id);
				if (!el || !word || el.value) return;
				const o = [...el.options].find((x) => x.value && x.value.toLowerCase().replace(/\s+/g, "").includes(word.replace(/\s+/g, "")));
				if (o) el.value = o.value;
			};
			pick("f-source", d.source); pick("f-segment", d.segment);
			return !!(d.first_name || d.organization || d.mobile_no || d.email || d.requirement);
		};
		const note = document.createElement("div");
		note.className = "sk-listening";
		note.textContent = "⏳ " + t("photo_reading");
		ev.target.after(note);
		try {
			const up = upload(f).then((u) => { cardUrl = u; return u; });
			let d = {};
			try { d = (await call("read_photo", { file_url: await up }, true)) || {}; } catch (e) { d = {}; }
			if (!fill(d)) {
				d = await readOnPhone(f, (st, pr) => { note.textContent = `⏳ ${t("photo_reading")} ${Math.round(pr * 100)}%`; });
				await up;
				if (!fill(d)) { toast(t("read_none"), true); return; }
			}
			toast(t("read_ok"));
		} catch (e) { toast(t("read_none"), true); } finally { note.remove(); }
	}

	// Training: 1) My function (e.g. Sales Manual lessons) 2) App usage 3) customer FAQ; managers also see their team
	let lessons = [], trainTab = "My function";
	async function renderTraining() {
		const mr = state.lang === "Marathi";
		const tabs = [["My function", t("my_function")], ["App usage", t("app_usage")], ["FAQ", t("faq")]];
		if (hasTeam()) tabs.push(["Team", t("team")]);
		const bar = `<div class="cal-tabs">${tabs.map(([k, l]) => `<button class="${trainTab === k ? "on" : ""}" data-train="${k}">${l}</button>`).join("")}</div>`;
		let body = "";
		if (trainTab === "FAQ") {
			body = libraryList(await call("library", { category: "Customer FAQ" }));
		} else if (trainTab === "Team") {
			const d = await call("team_training");
			body = `<ul class="sk-list">${d.people.map((p) => `<li class="sk-item"><div class="sk-grow"><div class="sk-item-title">${esc(p.full_name)}</div>
				<div class="sk-bar"><div style="width:${p.total ? Math.round((100 * p.done) / p.total) : 0}%"></div></div>
				<div class="sk-item-meta">${p.done} / ${p.total} ${t("lessons_done")}</div></div></li>`).join("") || `<li class="sk-empty">${t("none")}</li>`}</ul>`;
		} else {
			lessons = await call("training_lessons");
			const rows = lessons.filter((l) => l.lesson_type === trainTab);
			const done = rows.filter((l) => l.done).length;
			body = `<div class="sk-item-meta">${done} / ${rows.length} ${t("lessons_done")}</div><ul class="sk-list">${rows.map((l) => `<li class="sk-item"><button class="sk-fu-main" data-lesson="${esc(l.name)}">
				<div class="sk-item-title">${l.done ? "✅" : "🎓"} ${esc((mr && l.title_marathi) || l.title)}</div>
				<div class="sk-item-meta">${esc(l.topic || "")} · ${esc(l.minutes || 2)} ${t("min")}${l.score ? " · " + esc(l.score) : ""}</div></button></li>`).join("") || `<li class="sk-empty">${t("nothing")}</li>`}</ul>`;
		}
		root.innerHTML = header(t("training")) + `<main>${bar}${body}</main>`;
	}

	async function renderLesson(name) {
		const l = await call("training_lesson", { name });
		const mr = state.lang === "Marathi";
		state.view = "lesson";
		const video = l.video_url ? `<a class="sk-btn wide" href="${esc(l.video_url)}" target="_blank">▶ Video</a>` : "";
		const pages = l.pages_url ? `<a class="sk-btn wide" href="${esc(l.pages_url)}" target="_blank">📖 ${t("read_pages")}</a>` : "";
		const qs = (l.questions || []).map((q, i) => `<div class="sk-q"><div class="sk-item-title">${i + 1}. ${esc(q.question)}</div>
			<div class="sk-chips">${q.choices.map((c, j) => `<button class="sk-chip" data-q="${i}" data-choice="${j + 1}">${esc(c)}</button>`).join("")}</div></div>`).join("");
		const finish = l.questions && l.questions.length
			? `<h3 class="sk-h">✍️ ${t("check")}</h3>${qs}<button class="sk-btn ok wide" data-act="lesson-done" data-lesson="${esc(l.name)}" data-n="${l.questions.length}">✓ ${t("check_answers")}</button>`
			: `<button class="sk-btn ok wide" data-act="lesson-done" data-lesson="${esc(l.name)}">✓ ${t("lesson_done")}</button>`;
		// lesson HTML is written by HR / managers in ERPNext (SK Training Lesson)
		root.innerHTML = header((mr && l.title_marathi) || l.title) + `<main><div class="sk-lesson">${(mr && l.content_marathi) || l.content || ""}</div>${pages}${video}
			${l.done ? `<div class="sk-answered">✅ ${t("done_tick")}</div>` : ""}${finish}
			<button class="sk-btn wide" data-go="training">‹ ${t("training")}</button></main>`;
	}

	// ---------- Day Report ----------
	function factChips(c) {
		const keys = ["cards_done", "calls_made", "talk_minutes", "missed_calls", "notes_added", "leads_created", "work_entries"];
		return `<div class="sk-facts">${keys.map((k) => `<div><b>${esc(c[k] || 0)}</b><span>${t(k)}</span></div>`).join("")}
			<div><b>${c.dsi_done ? "✓" : "✗"}</b><span>${t("dsi_done")}</span></div><div><b>${esc(c.kpi_score || 0)}%</b><span>${t("kpi_score")}</span></div></div>`;
	}

	async function renderDayReport() {
		const [d, hist] = await Promise.all([call("my_day_report"), call("my_day_reports", { days: 14 })]);
		const r = d.report || {};
		const c = d.captured;
		root.innerHTML = header(t("day_report")) + `<main class="sk-form">
			${r.submitted_on ? `<div class="sk-answered">✓ ${t("report_sent")} · ${when(r.submitted_on)}</div>` : ""}
			<h3 class="sk-h">${t("captured")}</h3>${factChips(c)}
			${c.auto_summary ? `<pre class="sk-pre">${esc(c.auto_summary)}</pre>` : ""}
			${formField("f-done", t("report_q"), true)}${formField("f-prob", t("problems_q"), true)}${formField("f-plan", t("plan_q"), true)}${photoField()}
			<button class="sk-btn ok wide" data-act="save-report">${t("send_report")}</button>
			<h3 class="sk-h">${t("history")}</h3><ul class="sk-list">${hist.map((h) => `<li class="sk-item"><div><div class="sk-item-title">${esc(h.date)} ${h.on_time ? "· " + t("on_time") : "· " + t("late")}</div>
				<div>${esc(h.work_done)}</div>${h.manager_rating || h.manager_comment ? `<div class="sk-item-meta">⭐ ${esc(h.manager_rating || "")} ${esc(h.manager_comment || "")}</div>` : ""}</div></li>`).join("")}</ul></main>`;
		document.getElementById("f-done").value = r.work_done || "";
		document.getElementById("f-prob").value = r.problems || "";
		document.getElementById("f-plan").value = r.plan_tomorrow || "";
	}

	let teamDay = null;
	async function renderTeamReports() {
		const d = await call("team_day_reports", teamDay ? { day: teamDay } : {});
		const ratings = ["Good", "OK", "Needs improvement"];
		const people = d.people.map((p) => {
			const r = p.report;
			if (!r) return `<li class="sk-item k-lead_new"><div><div class="sk-item-title">${esc(p.full_name)}</div><div class="sk-item-meta">${esc(p.function || "")} · ❌ ${t("not_sent")}</div></div></li>`;
			return `<li class="sk-item"><div class="sk-grow"><div class="sk-item-title">${esc(p.full_name)} · ${r.on_time ? "✅ " + t("on_time") : "⏰ " + t("late")}</div>
				<div class="sk-item-meta">${esc(p.function || "")} · ${when(r.submitted_on)}</div>
				${factChips(r)}<div>${esc(r.work_done)}</div>
				${r.problems ? `<div class="sk-prob">⚠ ${esc(r.problems)}</div>` : ""}
				${r.plan_tomorrow ? `<div class="sk-item-meta">${t("plan_q")}: ${esc(r.plan_tomorrow)}</div>` : ""}
				${r.photo ? `<a href="${esc(r.photo)}" target="_blank">📷 ${t("photo")}</a>` : ""}
				<div class="sk-chips sk-gap">${ratings.map((x) => `<button class="sk-chip ${r.manager_rating === x ? "on" : ""}" data-rate="${esc(r.name)}" data-rating="${x}">${x}</button>`).join("")}</div>
				<div class="sk-input-row"><input id="c-${esc(r.name)}" placeholder="${t("comment")}" value="${esc(r.manager_comment || "")}"><button class="sk-mic" data-mic="c-${esc(r.name)}">🎤</button></div>
				<button class="sk-btn wide" data-act="save-review" data-report="${esc(r.name)}">${t("save_review")}</button></div></li>`;
		}).join("");
		root.innerHTML = header(t("team_reports")) + `<main><div class="sk-score"><input type="date" id="f-day" class="sk-date" value="${esc(d.date)}"><div class="sk-score-num">${d.sent} / ${d.total}</div><div>${t("sent_of")}</div></div>
			<ul class="sk-list">${people || `<li class="sk-empty">${t("none")}</li>`}</ul></main>`;
		document.getElementById("f-day").addEventListener("change", (e) => { teamDay = e.target.value; go("team_reports"); });
	}

	// ---------- Calendars: Today / My Week / My Month ----------
	let calTab = "today", calDay = null, calMonth = null;
	const hm = (s) => (s ? String(s).slice(11, 16) : "");
	const lakh = (v) => "₹" + (Number(v || 0) / 100000).toFixed(1) + " L";
	const KIND_CLS = { lead_new: "red", send_file: "red", day_report: "red", dsi: "green", lunch: "grey", event: "yel" };

	function calTabs() {
		return `<div class="cal-tabs">${["today", "week", "month"].map((k) => `<button class="${calTab === k ? "on" : ""}" data-cal="${k}">${t("cal_" + k)}</button>`).join("")}</div>`;
	}

	function evRow(x) {
		const it = x.item || x;
		let open = "";
		if (it.kind === "send_file") open = `data-open="${esc(it.ref_doctype)}" data-name="${esc(it.ref_name)}"`;
		else if (it.doctype && it.doctype.startsWith("CRM ") && it.name) open = `data-open="${esc(it.doctype)}" data-name="${esc(it.name)}"`;
		else if (it.kind === "day_report") open = `data-go="day_report"`;
		else if (it.kind === "dsi") open = `data-go="dsi"`;
		return `<button class="ev ${KIND_CLS[x.kind || it.kind] || ""}" ${open}>${esc(x.title || it.title)}<small>${esc((it.kind || x.kind || "").replace("_", " "))}${it.minutes ? " · " + esc(it.minutes) + " " + t("min") : ""}</small></button>`;
	}

	async function renderCalToday() {
		const d = await call("cal_today");
		const now = hm(d.now);
		let html = d.all_day.map((x) => `<span class="chip2 navy">${esc(x)}</span>`).join("");
		if (d.done.length) html += `<h3 class="sk-h">✓ ${t("done_today")}</h3>` + d.done.map((x) => `<div class="slot"><div class="t">${hm(x.time)}</div><div class="ev green">${esc(x.title)}</div></div>`).join("");
		html += `<h3 class="sk-h">${t("plan")}</h3><div class="now">${t("now_word")} ${now}</div>`;
		html += d.slots.map((x) => `<div class="slot"><div class="t">${hm(x.start)}</div>${evRow(x)}</div>`).join("") || `<div class="sk-empty">${t("nothing")}</div>`;
		if (d.later.length) html += `<h3 class="sk-h">${d.now.slice(11, 16) >= String(d.work_end).slice(0, 5) ? t("tomorrow") : t("later")}</h3>` + d.later.map((x) => `<div class="slot"><div class="t"></div>${evRow(x)}</div>`).join("");
		return html;
	}

	async function renderCalWeek() {
		const d = await call("cal_week", calDay ? { day: calDay } : {});
		let html = `<div class="sk-score sk-cal-head"><button class="sk-nav" data-week="${esc(d.start)}" data-step="-7">‹</button>
			<div><div>${t("week")} ${d.week_no} · ${esc(d.start.slice(8))}/${esc(d.start.slice(5, 7))} – ${esc(d.end.slice(8))}/${esc(d.end.slice(5, 7))}</div>
			<small>${d.orders_target ? `${t("orders")} ${lakh(d.orders)} / ${lakh(d.orders_target)} · ` : ""}${d.open_items} ${t("open_items")}</small></div>
			<button class="sk-nav" data-week="${esc(d.start)}" data-step="7">›</button></div>`;
		html += d.days.map((x) => {
			const chips = x.company.map((c) => `<span class="chip2 navy">${esc(c)}</span>`).join("") +
				x.events.map((e) => `<span class="chip2 yel">${e.time ? esc(e.time) + " " : ""}${esc(e.title)}</span>`).join("") +
				(x.orders ? `<span class="chip2 green">${t("order")} ${lakh(x.orders)}</span>` : "") + (x.dsi ? `<span class="chip2 green">DSI ✓</span>` : "") +
				x.due.map((i) => `<button class="chip2 ${i.overdue ? "red" : ""}" ${i.doctype && i.doctype.startsWith("CRM ") ? `data-open="${esc(i.doctype)}" data-name="${esc(i.name)}"` : ""}>${i.overdue ? "⚠ " : ""}${esc(i.title)}</button>`).join("");
			return `<div class="day ${x.today ? "today" : ""} ${x.working ? "" : "off"}"><h4><span>${t("d_" + x.day)} ${esc(x.date.slice(8))}</span><span class="sk-item-meta">${x.due.length} ${t("open_items")}</span></h4>${chips || `<span class="sk-item-meta">—</span>`}</div>`;
		}).join("");
		return html;
	}

	async function renderCalMonth() {
		const d = await call("cal_month", calMonth || {});
		let html = `<div class="sk-score sk-cal-head"><button class="sk-nav" data-month="${d.year}-${d.month}" data-step="-1">‹</button>
			<div><div>${esc(d.label)}</div><small>${t("score")} ${d.score}%${d.orders_target ? ` · ${t("orders")} ${lakh(d.orders)} / ${lakh(d.orders_target)}` : ""} · ${d.dsi} DSI</small></div>
			<button class="sk-nav" data-month="${d.year}-${d.month}" data-step="1">›</button></div><div class="grid">`;
		html += ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((w) => `<div class="h">${t("d_" + w)}</div>`).join("");
		html += '<div class="cell off"></div>'.repeat(d.days[0].weekday);
		html += d.days.map((x) => `<button class="cell ${x.today ? "today" : ""}" data-calday="${esc(x.date)}"><b>${x.day}</b>
			${x.company.map((c) => `<span class="dot m">${esc(c)}</span>`).join("")}${x.events.map((e) => `<span class="dot y">${esc(e)}</span>`).join("")}
			${x.orders ? `<span class="dot g">${lakh(x.orders)}</span>` : ""}${x.due ? `<span class="dot ${x.overdue ? "r" : "m"}">${x.due} ${t("due")}</span>` : ""}${x.dsi ? `<span class="dot g">DSI</span>` : ""}</button>`).join("");
		html += `</div><div class="legend"><span class="chip2 navy">${t("company_dates")}</span><span class="chip2 green">${t("done_word")}</span><span class="chip2 red">${t("due_overdue")}</span> · ${t("tap_day")}</div>`;
		return html;
	}

	async function renderCalendar() {
		const body = calTab === "week" ? await renderCalWeek() : calTab === "month" ? await renderCalMonth() : await renderCalToday();
		root.innerHTML = header(t("calendar")) + `<main>${calTabs()}${body}</main>`;
	}

	// ---------- shared ----------
	const hasTeam = () => !!(state.home && state.home.home && state.home.home.tiles.includes("team_reports"));
	const pad2 = (n) => String(n).padStart(2, "0");
	const dur = (sec) => `${Math.floor((sec || 0) / 60)}:${pad2((sec || 0) % 60)}`;
	const store = { get(k) { try { return JSON.parse(localStorage.getItem(k) || "null"); } catch (e) { return null; } },
		set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* private mode: fine */ } } };
	let contacts = null; // the person's open leads / deals, for pickers (loaded once per visit)
	async function myContacts() {
		if (!contacts) contacts = await call("follow_up");
		return contacts;
	}
	function contactSelect(id, selected) {
		return `<label class="sk-field"><span>${t("pick_customer")}</span><select id="${id}" class="sk-select"><option value=""></option>${(contacts || []).map((c) =>
			`<option value="${esc(c.doctype)}|${esc(c.name)}" data-mobile="${esc(c.mobile || "")}" data-email="${esc(c.email || "")}" ${selected === c.name ? "selected" : ""}>${esc(c.title)}${c.person ? " · " + esc(c.person) : ""}</option>`).join("")}</select></label>`;
	}
	const lockedRow = (what) => `<div class="sk-locked">🔒 <b>${esc(what)}</b><br><small>${t("locked")}</small></div>`;

	// ---------- Reminders ----------
	function dueNow() {
		const seen = store.get("sk_rem_seen") || {};
		return ((state.home && state.home.due_reminders) || []).filter((r) => !(seen[r.name + r.at] > Date.now()));
	}
	function reminderBanners() {
		return dueNow().map((r) => `<div class="sk-banner rem">⏰ ${esc(r.title)} <small>${esc(hm(r.at))}</small>
			<div class="sk-row"><button class="sk-chip" data-act="rem-done" data-doctype="${esc(r.doctype)}" data-name="${esc(r.name)}">✓ ${t("done")}</button>
			<button class="sk-chip" data-act="rem-snooze" data-key="${esc(r.name + r.at)}">⏱ ${t("snooze")}</button>
			${r.ref_doctype ? `<button class="sk-chip" data-open="${esc(r.ref_doctype)}" data-name="${esc(r.ref_name)}">›</button>` : ""}</div></div>`).join("");
	}
	async function reminderSheet(doctype, name) {
		const now = new Date(Date.now() + 60 * 60 * 1000);
		const day = `${now.getFullYear()}-${pad2(now.getMonth() + 1)}-${pad2(now.getDate())}`;
		const team = hasTeam() ? await call("my_team").catch(() => []) : [];
		sheet(`<h3 class="sk-h">⏰ ${t("reminder")}</h3>${formField("f-rem", t("what_remind"), true)}
			<div class="sk-two-col"><label class="sk-field"><span>${t("date")}</span><input id="f-remdate" type="date" value="${day}"></label>
			<label class="sk-field"><span>${t("time")}</span><input id="f-remtime" type="time" value="${pad2(now.getHours())}:00"></label></div>
			<label class="sk-field"><span>${t("repeat")}</span><select id="f-remrep" class="sk-select"><option value="">${t("no_repeat")}</option>
				<option value="Daily">${t("daily")}</option><option value="Weekly">${t("weekly")}</option><option value="Monthly">${t("monthly")}</option></select></label>
			${team.length ? `<label class="sk-field"><span>${t("for_whom")}</span><select id="f-remfor" class="sk-select"><option value="">${t("me")}</option>${team.map((p) => `<option value="${esc(p.user)}">${esc(p.full_name)}</option>`).join("")}</select></label>` : ""}
			<button class="sk-btn ok wide" data-act="rem-save" data-doctype="${esc(doctype || "")}" data-name="${esc(name || "")}">⏰ ${t("set_reminder")}</button>
			<button class="sk-btn wide" data-act="close-sheet">${t("back")}</button>`);
	}
	async function renderReminders() {
		const rows = await call("my_reminders", { days: 7 });
		root.innerHTML = header(t("reminders")) + `<main>${reminderBanners()}<button class="sk-btn go wide" data-act="reminder-new">⏰ + ${t("reminder")}</button>
			<h3 class="sk-h">${t("upcoming")}</h3><ul class="sk-list">${rows.map((r) => `<li class="sk-item"><div class="sk-grow"><div class="sk-item-title">${esc(r.title)}</div>
			<div class="sk-item-meta">${esc(r.at.slice(8, 10))}/${esc(r.at.slice(5, 7))} ${esc(hm(r.at))}${r.repeat ? " · ↻ " + esc(r.repeat) : ""}</div></div>
			${r.ref_doctype ? `<button class="sk-open" data-open="${esc(r.ref_doctype)}" data-name="${esc(r.ref_name)}">›</button>` : ""}
			<button class="sk-open" data-act="rem-done" data-doctype="${esc(r.doctype)}" data-name="${esc(r.name)}">✓</button></li>`).join("") || `<li class="sk-empty">${t("nothing")}</li>`}</ul></main>`;
	}

	// ---------- Calls: free (phone dialer + log with talk time); recording is Phase 2 ----------
	function talkBox(label, x) {
		return `<div><b>${x.calls}</b><span>${label}: ${t("calls_n")}</span></div><div><b>${x.talked}</b><span>${t("talked")}</span></div><div><b>${dur(x.talk_seconds)}</b><span>${t("talk_time")}</span></div><div><b>${x.missed || 0}</b><span>${t("missed")}</span></div>`;
	}
	async function renderCalls() {
		const [d] = await Promise.all([call("my_calls"), myContacts()]);
		let team = "";
		if (hasTeam()) {
			const tc = await call("team_calls");
			team = `<h3 class="sk-h">👥 ${t("team_talk")}</h3><ul class="sk-list">${tc.people.map((p) => `<li class="sk-item"><div class="sk-grow"><div class="sk-item-title">${esc(p.full_name)}</div>
				<div class="sk-item-meta">${t("today")}: ${p.day.calls} ${t("calls_n")} · ${dur(p.day.talk_seconds)} · ${p.day.missed || 0} ${t("missed")} · ${t("this_week")}: ${p.week.calls} · ${dur(p.week.talk_seconds)} · ${p.week.missed || 0} ${t("missed")}</div></div></li>`).join("") || `<li class="sk-empty">${t("none")}</li>`}</ul>`;
		}
		const rows = d.calls.map((c) => `<li class="sk-item"><button class="sk-fu-main" ${c.reference_doctype ? `data-open="${esc(c.reference_doctype)}" data-name="${esc(c.reference_docname)}"` : ""}>
			<div class="sk-item-title">${c.type === "Incoming" ? "📥" : "📤"} ${esc(c.title)} · ${esc(c.status)}</div>
			<div class="sk-item-meta">${when(c.creation)} · ${t("talk_time")} ${dur(c.duration)}${c.note_text ? " · " + esc(c.note_text) : ""}</div></button></li>`).join("");
		root.innerHTML = header(t("calls")) + `<main>
			<div class="sk-facts">${talkBox(t("today"), d.today)}</div><div class="sk-facts">${talkBox(t("this_week"), d.week)}</div>
			<button class="sk-btn go wide" data-go="follow_up">📞 ${t("follow_up")}</button>
			<button class="sk-btn wide sk-gap" data-act="call-add">➕ ${t("add_call")}</button>
			${team}<h3 class="sk-h">${t("history")}</h3><ul class="sk-list">${rows || `<li class="sk-empty">${t("nothing")}</li>`}</ul>
			${lockedRow(t("rec_locked"))}</main>`;
	}
	function addCallSheet() {
		const outs = (crmOpts && crmOpts.call_outcomes) || ["Talked", "No answer", "Busy", "Missed", "Call back later", "Wrong number"];
		sheet(`<h3 class="sk-h">➕ ${t("add_call")}</h3>${contactSelect("f-callwho")}
			<div class="sk-contact sk-two"><button class="sk-chip on" data-dir="Outgoing">📤 ${t("outgoing")}</button><button class="sk-chip" data-dir="Incoming">📥 ${t("incoming")}</button></div>
			<div class="sk-chips">${outs.map((x, i) => `<button class="sk-chip ${i === 0 ? "on" : ""}" data-ptype="${esc(x)}">${esc(x)}</button>`).join("")}</div>
			<label class="sk-field"><span>${t("talk_min")}</span><input id="f-callmin" type="number" inputmode="decimal" min="0" step="0.5" value="1"></label>
			${formField("f-callnote", t("note_q"), true)}
			<button class="sk-btn ok wide" data-act="call-save">${t("save")}</button><button class="sk-btn wide" data-act="close-sheet">${t("back")}</button>`);
	}

	// ---------- WhatsApp: free (opens WhatsApp); inbox inside the app is Phase 2 ----------
	let waFilter = "";
	async function renderWhatsApp() {
		const [rows, tpl] = await Promise.all([myContacts(), call("library", { category: "Message Template" })]);
		const q = waFilter.toLowerCase();
		const list = rows.filter((r) => r.mobile && (!q || (r.title + " " + (r.person || "")).toLowerCase().includes(q))).slice(0, 60);
		root.innerHTML = header(t("whatsapp")) + `<main>
			<label class="sk-field"><span>🔍 ${t("search")}</span><input id="f-wasearch" value="${esc(waFilter)}"></label>
			<ul class="sk-list">${list.map((r) => `<li class="sk-item"><button class="sk-fu-main" data-open="${esc(r.doctype)}" data-name="${esc(r.name)}">
				<div class="sk-item-title">${esc(r.title)}</div><div class="sk-item-meta">${esc(r.person || "")} · ${esc(r.mobile)}</div></button>
				<button class="sk-cbtn" data-contact="WhatsApp" data-doctype="${esc(r.doctype)}" data-name="${esc(r.name)}" data-mobile="${esc(r.mobile)}">💬</button></li>`).join("") || `<li class="sk-empty">${t("nothing")}</li>`}</ul>
			<h3 class="sk-h">${t("any_number")}</h3>
			<label class="sk-field"><span>${t("mobile")}</span><div class="sk-input-row"><input id="f-wanum" type="tel"></div></label>
			${formField("f-wamsg", t("message"), true)}
			${tpl.length ? `<div class="sk-chips">${tpl.map((x) => `<button class="sk-chip" data-tpl="${esc(x.name)}">${esc(x.title)}</button>`).join("")}</div>` : ""}
			<button class="sk-btn ok wide" data-act="wa-free">💬 ${t("open_chat")}</button>
			${lockedRow(t("wa_locked"))}</main>`;
		root._tpl = tpl;
		const box = document.getElementById("f-wasearch");
		box.addEventListener("input", () => { waFilter = box.value; clearTimeout(box._t); box._t = setTimeout(() => go("whatsapp").then(() => { const b = document.getElementById("f-wasearch"); b.focus(); b.setSelectionRange(b.value.length, b.value.length); }), 400); });
	}

	// ---------- Mail: free once the company Email Account is connected in ERPNext ----------
	async function renderMail() {
		const d = await call("my_mail");
		root.innerHTML = header(t("mail")) + `<main>${d.ready ? "" : `<div class="sk-locked">✉️ ${t("mail_not_ready")}</div>`}
			<ul class="sk-list">${d.mails.map((m) => `<li class="sk-item"><button class="sk-fu-main" data-open="${esc(m.reference_doctype)}" data-name="${esc(m.reference_name)}">
				<div class="sk-item-title">${m.sent_or_received === "Received" ? "📥" : "📤"} ${esc(m.subject || "")}</div>
				<div class="sk-item-meta">${esc(m.title)} · ${when(m.communication_date)}${m.has_attachment ? " · 📎" : ""}</div>
				<div class="sk-item-meta">${esc(m.preview || "")}</div></button></li>`).join("") || `<li class="sk-empty">${t("nothing")}</li>`}</ul></main>`;
	}
	async function mailSheet(doctype, name, email) {
		const ready = (await call("my_mail")).ready;
		if (!ready) { window.location.href = "mailto:" + (email || ""); return; }
		const d = await call("crm_detail", { doctype, name });
		const files = [...d.quotations.map((q) => ({ id: "Quotation:" + q.name, label: "📄 " + q.name })),
			...d.sales_orders.map((q) => ({ id: "Sales Order:" + q.name, label: "📄 " + q.name })),
			...d.files.filter((f) => f.for_customer).map((f) => ({ id: f.name, label: "📎 " + f.file_name }))];
		sheet(`<h3 class="sk-h">✉️ ${t("email")}</h3>
			<label class="sk-field"><span>${t("to")}</span><div class="sk-input-row"><input id="f-mto" type="email" value="${esc(email || "")}"></div></label>
			${formField("f-msub", t("subject"))}${formField("f-mbody", t("message"), true)}
			${files.length ? `<h3 class="sk-h">${t("attach_files")}</h3><div class="sk-chips">${files.map((f) => `<button class="sk-chip" data-mfile="${esc(f.id)}">${esc(f.label)}</button>`).join("")}</div>` : ""}
			<button class="sk-btn ok wide" data-act="mail-send" data-doctype="${esc(doctype)}" data-name="${esc(name)}">✉️ ${t("send_mail")}</button>
			<button class="sk-btn wide" data-act="close-sheet">${t("back")}</button>`);
	}

	// ---------- Company & Products library, FAQ, messages, Sales Manual ----------
	let libCat = "Company", libItems = [];
	const absUrl = (u) => (u && u.startsWith("/") ? location.origin + u : u || "");
	function libraryList(rows) {
		libItems = libItems.concat(rows.filter((r) => !libItems.some((x) => x.name === r.name)));
		const mr = state.lang === "Marathi";
		return `<ul class="sk-list">${rows.map((r) => {
			const text = (mr && r.text_marathi) || r.text || "";
			const open = r.open_url ? `<a class="sk-chip" href="${esc(r.open_url)}" target="_blank">${r.kind === "link" ? "🔗" : "📄"} ${t("open")}</a>` : "";
			const send = r.sendable ? `<button class="sk-chip" data-act="lib-wa" data-item="${esc(r.name)}">💬 ${t("send")}</button>` : "";
			const share = r.sendable && r.kind === "file" ? `<button class="sk-chip" data-act="share-pdf" data-pdf="${esc(r.open_url)}" data-file="${esc(r.title)}">↗ ${t("share_pdf")}</button>` : "";
			const copy = text ? `<button class="sk-chip" data-act="lib-copy" data-item="${esc(r.name)}">⧉ ${t("copy")}</button>` : "";
			return `<li class="sk-item"><div class="sk-grow"><div class="sk-item-title">${esc((mr && r.title_marathi) || r.title)}</div>
				${r.product && r.product !== "All" ? `<div class="sk-item-meta">${esc(r.product)}</div>` : ""}
				${text ? `<div class="sk-libtext">${esc(text)}</div>` : ""}<div class="sk-row">${open}${send}${share}${copy}</div></div></li>`;
		}).join("") || `<li class="sk-empty">${t("nothing")}</li>`}</ul>`;
	}
	async function renderLibrary() {
		const cats = ["Company", "Product", "Customer FAQ", "Message Template", "Sales Manual"];
		const rows = await call("library", { category: libCat });
		root.innerHTML = header(t("library")) + `<main><div class="cal-tabs sk-wrap">${cats.map((c) => `<button class="${libCat === c ? "on" : ""}" data-libcat="${esc(c)}">${t("cat_" + c)}</button>`).join("")}</div>
			${libraryList(rows)}</main>`;
	}
	function libMessage(item) {
		const mr = state.lang === "Marathi";
		return [(mr && item.title_marathi) || item.title, (mr && item.text_marathi) || item.text, absUrl(item.open_url)].filter(Boolean).join("\n");
	}
	// send any text on WhatsApp: 1) Self 2) Customer (current lead) or pick one of my leads, or type a number
	async function waTextSheet(text) {
		await myContacts();
		const self = (state.home && state.home.mobile) || "";
		const mobile = (current && current.mobile) || "";
		sheet(`<h3 class="sk-h">${t("send_to")}</h3>
			<div class="sk-contact sk-two"><button class="sk-chip" data-wa-pick="${esc(self)}">👤 1) ${t("self")}</button>
				<button class="sk-chip ${mobile ? "on" : ""}" data-wa-pick="${esc(mobile)}">🧑‍💼 2) ${t("customer")}</button></div>
			${contactSelect("f-wawho")}
			<label class="sk-field"><span>${t("mobile")}</span><div class="sk-input-row"><input id="f-wa" type="tel" value="${esc(mobile)}"></div></label>
			<label class="sk-field"><span>${t("message")}</span><textarea id="f-watext" rows="4">${esc(text)}</textarea></label>
			<button class="sk-btn ok wide" data-act="wa-text">💬 ${t("send")}</button><button class="sk-btn wide" data-act="close-sheet">${t("back")}</button>`);
		const sel = document.getElementById("f-wawho");
		sel.addEventListener("change", () => { const o = sel.selectedOptions[0]; if (o && o.dataset.mobile) document.getElementById("f-wa").value = o.dataset.mobile; });
	}

	// ---------- Store and Purchase (SK drafts F01 / F02, 26-Oct-2026) ----------
	// Store and Purchase people mostly tap and take photos; numbers can be spoken with the 🎤. Every save makes the
	// ERPNext document under their own login (drafts where Accounts / the owner must check first).
	const S = {}; // screen state: lists from the server, the picked PO / job / order, the items picked for rates
	const num = (x) => Number(x || 0).toLocaleString("en-IN", { maximumFractionDigits: 2 });
	const money = (x) => "Rs " + Number(x || 0).toLocaleString("en-IN", { maximumFractionDigits: 0 });
	const qtyBox = (id, value, label) => `<input id="${id}" class="sk-qty" type="number" inputmode="decimal" step="any" value="${value == null ? "" : esc(value)}" aria-label="${esc(label || "")}">`;
	const empty = () => `<li class="sk-empty">${t("nothing")}</li>`;
	const li = (title, meta, right, extra) => `<li class="sk-item ${extra || ""}"><div><div class="sk-item-title">${title}</div><div class="sk-item-meta">${meta || ""}</div></div>${right || ""}</li>`;
	function pick(id, label, list, attr) {
		return `<label class="sk-field"><span>${esc(label)}</span><select id="${id}" class="sk-select" ${attr || ""}><option value=""></option>${(list || []).map((x) => typeof x === "string" ? `<option>${esc(x)}</option>` : `<option value="${esc(x.value)}">${esc(x.label)}</option>`).join("")}</select></label>`;
	}
	// type or speak a few letters, then pick from the list (suppliers / items from ERPNext)
	function finder(id, label, kind) {
		return `<label class="sk-field"><span>${esc(label)}</span><div class="sk-input-row"><input id="${id}" list="${id}-dl" data-find="${kind}" autocomplete="off">
			<div class="sk-micbox"><button class="sk-mic" data-mic="${id}">🎤</button></div></div><datalist id="${id}-dl"></datalist></label>`;
	}
	let findTimer = null;
	root.addEventListener("input", (ev) => {
		const el = ev.target;
		if (!el.dataset || !el.dataset.find) return;
		clearTimeout(findTimer);
		findTimer = setTimeout(async () => {
			const rows = el.dataset.find === "supplier" ? await call("buy_suppliers", { q: el.value }) : await call("store_search", { q: el.value });
			const dl = document.getElementById(el.id + "-dl");
			if (dl) dl.innerHTML = rows.map((r) => el.dataset.find === "supplier" ? `<option value="${esc(r.name)}">${esc(r.supplier_name)}</option>`
				: `<option value="${esc(r.item_code)}">${esc(r.item_name)} · ${num(r.qty)} ${esc(r.uom || "")}</option>`).join("");
		}, 300);
	});

	async function renderStockCheck() {
		root.innerHTML = header(t("stock_check")) + `<main class="sk-form">${formField("s-q", t("search_item"))}
			<button class="sk-btn go wide" data-act="st-search">🔎 ${t("search")}</button><ul class="sk-list sk-gap" id="s-res"></ul></main>`;
		return stockResults("");
	}
	async function stockResults(q) {
		S.items = await call("store_search", { q });
		document.getElementById("s-res").innerHTML = S.items.map((r, i) => li(`${esc(r.item_name)} ${r.low ? `<span class="sk-due">${t("low")}</span>` : ""}`,
			`${esc(r.item_code)} · ${esc(r.group || "")}<br>${r.warehouses.map((w) => `${esc(w.warehouse)}: ${num(w.qty)}`).join(" · ")}`,
			`<button class="sk-open" data-act="st-item" data-i="${i}"><b>${num(r.qty)}</b> ${esc(r.uom || "")}<br><small>${money(r.value)}</small></button>`)).join("") || empty();
	}
	async function itemSheet(code) {
		const d = await call("store_item", { item_code: code });
		const mv = (rows) => rows.map((r) => `<li>${esc(r.posting_date)} · ${num(r.actual_qty)} · ${esc(r.voucher_type)} ${esc(r.voucher_no)}</li>`).join("") || `<li>${t("none")}</li>`;
		sheet(`<h3 class="sk-h">📦 ${esc(d.item_name)}</h3><p class="sk-note">${esc(d.item_code)} · ${esc(d.item_group || "")}</p>
			<b>${t("received")}</b><ul class="sk-mini">${mv(d.received)}</ul><b>${t("issued")}</b><ul class="sk-mini">${mv(d.issued)}</ul>
			<b>${t("used_in_jobs")}</b><ul class="sk-mini">${d.jobs.map((j) => `<li>${esc(j.work_order)} · ${num(j.qty)}</li>`).join("") || `<li>${t("none")}</li>`}</ul>
			<button class="sk-btn wide" data-act="close-sheet">${t("back")}</button>`);
	}

	async function renderReceive() {
		S.pos = await call("store_open_pos");
		root.innerHTML = header(t("receive")) + `<main><p class="sk-note">${t("receive_help")}</p><ul class="sk-list">${S.pos.map((p, i) => li(esc(p.supplier_name),
			`${esc(p.name)} · ${t("due")} ${esc(p.schedule_date || "")} · ${p.items.length} ${t("open_items")}`,
			`<button class="sk-chip on" data-act="st-po" data-i="${i}">${t("receive")}</button>`, p.late ? "k-lead_new" : "")).join("") || empty()}</ul>
			<button class="sk-btn wide sk-gap" data-act="st-nopo">${t("without_po")}</button></main>`;
	}
	function receiveForm(i) {
		const p = S.pos[i];
		S.po = p;
		root.innerHTML = header(t("receive")) + `<main class="sk-form"><h3 class="sk-h">${esc(p.supplier_name)} · ${esc(p.name)}</h3>
			${photoField("r-challan", "📷 " + t("challan_photo"))}
			<ul class="sk-list">${p.items.map((r, k) => li(esc(r.item_name), `${t("ordered")} ${num(r.qty)} · ${t("pending")} ${num(r.pending)} ${esc(r.uom || "")}`,
				qtyBox("r-q" + k, r.pending, r.item_name))).join("")}</ul>
			${photoField("r-goods", "📷 " + t("goods_photo"))}${formField("r-note", t("note_q"))}
			<button class="sk-btn go wide" data-act="st-receive">${t("save_receipt")}</button></main>`;
	}
	function receiveNoPo() {
		S.po = null;
		root.innerHTML = header(t("without_po")) + `<main class="sk-form">${finder("r-sup", t("supplier"), "supplier")}${finder("r-item", t("item"), "item")}
			<label class="sk-field"><span>${t("qty")}</span>${qtyBox("r-qty")}</label>${formField("r-reason", t("why_no_po"), true)}
			${photoField("r-challan", "📷 " + t("challan_photo"))}<button class="sk-btn go wide" data-act="st-receive">${t("save_receipt")}</button></main>`;
	}

	async function renderIssue() {
		S.wos = await call("store_work_orders");
		root.innerHTML = header(t("issue")) + `<main><p class="sk-note">${t("issue_help")}</p><ul class="sk-list">${S.wos.map((w, i) => li(esc(w.item_name || w.production_item),
			`${esc(w.name)} · ${num(w.qty)} · ${(w.job_cards || []).map((j) => esc(j.operation || "")).filter(Boolean).join(", ")}`,
			`<button class="sk-chip on" data-act="st-wo" data-i="${i}">${t("issue")}</button>`)).join("") || empty()}</ul></main>`;
	}
	function issueForm(i) {
		const w = S.wos[i];
		S.wo = w;
		root.innerHTML = header(t("issue")) + `<main class="sk-form"><h3 class="sk-h">${esc(w.item_name || w.production_item)} · ${esc(w.name)}</h3>
			${pick("i-jc", t("job_card"), (w.job_cards || []).map((j) => ({ value: j.name, label: `${j.name} · ${j.operation || ""} · ${j.workstation || ""}` })))}
			<ul class="sk-list">${w.items.map((r, k) => li(esc(r.item_name || r.item_code), `${t("needed")} ${num(r.required_qty)} · ${t("given")} ${num(r.transferred_qty)} · ${esc(r.source_warehouse || "")}`,
				qtyBox("i-q" + k, "", r.item_name))).join("")}</ul>
			${finder("i-extra", t("other_item"), "item")}<label class="sk-field"><span>${t("qty")}</span>${qtyBox("i-extra-q")}</label>
			${formField("i-who", t("taken_by"))}${photoField("i-photo", "📷 " + t("taker_photo"))}
			<button class="sk-btn ok wide" data-act="st-issue">✓ ${t("issue")}</button></main>`;
	}

	async function renderStoreRequests() {
		S.reqs = await call("store_requests", { kind: "store" });
		root.innerHTML = header(t("store_requests")) + `<main><ul class="sk-list">${S.reqs.map((r, i) => li(`${esc(r.item_name)} · ${num(r.qty)} ${esc(r.uom || "")}`,
			`${esc(r.by)} · ${esc(r.request)}${r.work_order ? " · " + esc(r.work_order) : ""} · ${t("needed_by")} ${esc(r.needed_by)}${r.age_hours > 2 ? ` <span class="sk-due">${num(r.age_hours)} h</span>` : ""}`,
			`<div class="sk-col">${r.short ? `<span class="sk-due">${t("short")} ${num(r.short)}</span><button class="sk-chip" data-act="st-req-buy" data-i="${i}">→ ${t("to_purchase")}</button>`
				: `<button class="sk-chip on" data-act="st-req-issue" data-i="${i}">${t("issue")}</button>`}</div>`, r.short ? "k-lead_new" : "")).join("") || empty()}</ul></main>`;
	}

	async function renderDispatch() {
		S.sos = await call("store_dispatch_orders");
		root.innerHTML = header(t("dispatch")) + `<main><ul class="sk-list">${S.sos.map((o, i) => li(esc(o.customer_name), `${esc(o.name)} · ${money(o.grand_total)} · ${t("due")} ${esc(o.delivery_date || "")}`,
			`<button class="sk-chip on" data-act="st-so" data-i="${i}">${t("dispatch")}</button>`)).join("") || empty()}</ul></main>`;
	}
	function dispatchForm(i) {
		const o = S.sos[i];
		S.so = o;
		root.innerHTML = header(t("dispatch")) + `<main class="sk-form"><h3 class="sk-h">${esc(o.customer_name)} · ${esc(o.name)}</h3>
			${photoField("d-cabin", "📷 " + t("loaded_photo"))}${photoField("d-plate", "📷 " + t("plate_photo"))}
			${formField("d-vehicle", t("vehicle_no"))}<label class="sk-field"><span>${t("driver_mobile")}</span><div class="sk-input-row"><input id="d-driver" type="tel"></div></label>
			${formField("d-note", t("note_q"))}<button class="sk-btn ok wide" data-act="st-dispatch">✓ ${t("dispatch_tell")}</button></main>`;
	}

	async function renderLowStock() {
		S.low = await call("store_low_stock");
		root.innerHTML = header(t("low_stock")) + `<main><ul class="sk-list">${S.low.map((r) => li(esc(r.item_name), `${esc(r.warehouse)} · ${t("have")} ${num(r.qty)} · ${t("reorder_at")} ${num(r.level)}`,
			`<span class="sk-chip">${t("order")} ${num(r.order)}</span>`, "k-lead_new")).join("") || `<li class="sk-empty">${t("no_low")}</li>`}</ul>
			${S.low.length ? `<button class="sk-btn go wide" data-act="st-order-low">${t("send_all_purchase")} (${S.low.length})</button>` : ""}</main>`;
	}

	async function renderStockCount() {
		const whs = await call("store_warehouses");
		root.innerHTML = header(t("stock_count")) + `<main class="sk-form">${pick("c-wh", t("store_name"), whs, 'data-act-change="st-count-wh"')}<div id="c-list"></div></main>`;
		document.getElementById("c-wh").addEventListener("change", countList);
	}
	async function countList() {
		const wh = val("c-wh");
		S.count = wh ? await call("store_count_list", { warehouse: wh }) : [];
		document.getElementById("c-list").innerHTML = `<p class="sk-note">${t("count_help")}</p><ul class="sk-list">${S.count.map((r, k) => li(esc(r.item_name),
			`${esc(r.item_code)} · ERPNext ${num(r.qty)}`, `<div class="sk-input-row sk-countbox">${qtyBox("c-q" + k, "", r.item_name)}<div class="sk-micbox"><button class="sk-mic" data-mic="c-q${k}">🎤</button></div></div>`)).join("") || empty()}</ul>
			${photoField("c-photo", "📷 " + t("rack_photo"))}<button class="sk-btn go wide" data-act="st-count">${t("send_differences")}</button>`;
	}

	async function renderNewItem() {
		const o = await call("store_item_options");
		root.innerHTML = header(t("new_item")) + `<main class="sk-form">${photoField("n-photo", "📷 " + t("item_photo"))}${formField("n-name", t("item_name"))}
			<div id="n-similar"></div>${pick("n-group", t("group"), o.groups)}${pick("n-uom", t("unit"), o.uoms)}${pick("n-wh", t("store_name"), o.warehouses)}
			<button class="sk-btn go wide" data-act="st-new-item">${t("send_approval")}</button></main>`;
		document.getElementById("n-name").addEventListener("change", async () => {
			const rows = await call("store_similar", { name: val("n-name") });
			document.getElementById("n-similar").innerHTML = rows.length ? `<p class="sk-note">⚠ ${t("similar")}: ${rows.map((r) => `${esc(r.item_name)} (${esc(r.item_code)})`).join(", ")}</p>` : "";
		});
	}

	// ---------- Purchase ----------
	async function renderBuyRequests() {
		S.breqs = await call("buy_requests");
		root.innerHTML = header(t("buy_requests")) + `<main><ul class="sk-list">${S.breqs.map((r, i) => li(`<label class="sk-check"><input type="checkbox" data-breq="${i}"> ${esc(r.item_name)} · ${num(r.qty)} ${esc(r.uom || "")}</label>`,
			`${esc(r.by)} · ${esc(r.request)} · ${t("needed_by")} ${esc(r.needed_by)}${r.last_rate ? ` · ${t("last")} ${money(r.last_rate)} (${esc(r.last_supplier)})` : ""}`,
			r.urgent ? `<span class="sk-due">${t("urgent")}</span>` : "", r.urgent ? "k-lead_new" : "")).join("") || empty()}</ul>
			${S.breqs.length ? `<button class="sk-btn go wide" data-act="pu-rates-selected">💬 ${t("get_rates_selected")}</button>` : ""}</main>`;
	}

	async function renderGetRates() {
		S.rateItems = S.rateItems || [];
		const first = S.rateItems[0];
		const sugg = first ? await call("buy_suggest", { item_code: first.item_code }) : [];
		S.sugg = sugg;
		const d = new Date(); d.setDate(d.getDate() + 3);
		root.innerHTML = header(t("get_rates")) + `<main class="sk-form">
			<h3 class="sk-h">${t("items")}</h3><ul class="sk-list">${S.rateItems.map((r, k) => li(esc(r.item_name || r.item_code), "", qtyBox("g-q" + k, r.qty))).join("") || `<li class="sk-empty">${t("add_item_first")}</li>`}</ul>
			${finder("g-item", t("add_item"), "item")}<label class="sk-field"><span>${t("qty")}</span>${qtyBox("g-qty")}</label>
			<button class="sk-btn wide" data-act="pu-add-item">+ ${t("add_item")}</button>
			<h3 class="sk-h">${t("suppliers")}</h3><ul class="sk-list">${sugg.map((s, k) => li(`<label class="sk-check"><input type="checkbox" data-sup="${esc(s.name)}" ${k < 3 ? "checked" : ""}> ${esc(s.supplier_name)}</label>`,
				[s.gstin, s.supplier_group, s.last_bill && t("last") + " " + s.last_bill].filter(Boolean).map(esc).join(" · "))).join("") || `<li class="sk-empty">${t("no_suggestion")}</li>`}</ul>
			${finder("g-sup", t("add_supplier"), "supplier")}
			<label class="sk-field"><span>${t("need_by")}</span><input id="g-date" type="date" class="sk-select" value="${d.toISOString().slice(0, 10)}"></label>
			<button class="sk-btn go wide" data-act="pu-rfq">💬 ${t("send_rate_request")}</button></main>`;
	}
	function rfqSent(r) {
		S.rfq = r;
		sheet(`<h3 class="sk-h">✅ ${esc(r.name)}</h3><p class="sk-note">${esc(r.text)}</p>
			${r.suppliers.map((s, k) => `<div class="sk-row sk-wrap sk-gap"><b>${esc(s.supplier_name)}</b>
				<button class="sk-chip on" data-act="pu-wa" data-k="${k}">💬 WhatsApp</button>
				${s.email_id ? `<a class="sk-chip" href="mailto:${esc(s.email_id)}?subject=${encodeURIComponent("Rate request " + r.name)}&body=${encodeURIComponent(r.text)}">✉️ ${t("email")}</a>` : ""}</div>`).join("")}
			<button class="sk-btn wide" data-act="close-sheet">${t("done")}</button>`);
	}

	async function renderCompare() {
		S.quoted = await call("buy_quoted_items");
		root.innerHTML = header(t("compare")) + `<main><button class="sk-btn go wide" data-act="pu-quote-new">📷 + ${t("add_quote")}</button>
			<ul class="sk-list sk-gap">${S.quoted.map((r, i) => li(esc(r.item_name), `${r.quotes} ${t("quotes")}`, `<button class="sk-open" data-act="pu-cmp" data-i="${i}">›</button>`)).join("") || empty()}</ul></main>`;
	}
	async function compareItem(code) {
		const c = await call("buy_compare", { item_code: code });
		S.cmp = c;
		root.innerHTML = header(t("compare")) + `<main><h3 class="sk-h">${esc(c.item_name)}</h3><ul class="sk-list">${c.quotes.map((q, k) => li(`${esc(q.supplier)} ${k === 0 ? `<span class="sk-chip on">${t("best")}</span>` : ""}`,
			`${money(q.rate)} × ${num(q.qty)} · ${q.lead_time_days || "-"} ${t("days")} · ${esc(q.name)}`,
			`<button class="sk-chip" data-act="pu-po" data-sq="${esc(q.name)}" data-total="${q.rate * q.qty}">${t("make_po")}</button>`)).join("") || empty()}
			${c.last ? li(t("last_purchase"), `${esc(c.last.supplier)} · ${esc(c.last.date)}`, `<b>${money(c.last.rate)}</b>`) : ""}</ul>
			${c.saving != null ? `<p class="sk-note">${t("saving_vs_last")}: <b>${money(c.saving)}</b></p>` : ""}
			<p class="sk-note">${t("approval_rule")} ${money(c.limit)}</p></main>`;
	}
	function quoteSheet() {
		sheet(`<h3 class="sk-h">📷 ${t("add_quote")}</h3>${photoField("q-photo", "📷 " + t("quote_photo"))}${finder("q-sup", t("supplier"), "supplier")}${finder("q-item", t("item"), "item")}
			<label class="sk-field"><span>${t("qty")}</span>${qtyBox("q-qty", S.rateItems && S.rateItems[0] ? S.rateItems[0].qty : "")}</label>
			<label class="sk-field"><span>${t("rate")}</span><div class="sk-input-row">${qtyBox("q-rate")}<div class="sk-micbox"><button class="sk-mic" data-mic="q-rate">🎤</button></div></div></label>
			<label class="sk-field"><span>${t("delivery_days")}</span>${qtyBox("q-days")}</label>
			<button class="sk-btn ok wide" data-act="pu-quote-save">${t("save")}</button><button class="sk-btn wide" data-act="close-sheet">${t("back")}</button>`);
	}

	async function renderFollowUpPo() {
		S.late = await call("buy_follow_up");
		root.innerHTML = header(t("po_follow_up")) + `<main><ul class="sk-list">${S.late.map((p, i) => li(esc(p.supplier_name),
			`${esc(p.name)} · ${esc(p.items)} · ${p.days_late > 0 ? `<span class="sk-due">${p.days_late} ${t("days_late")}</span>` : t("due_today")}`,
			`<div class="sk-col">${p.mobile ? `<a class="sk-chip" href="tel:${esc(p.mobile)}">📞</a><a class="sk-chip" target="_blank" href="https://wa.me/${waNumber(p.mobile)}">💬</a>` : ""}
			<button class="sk-chip" data-act="pu-note" data-i="${i}">🎤 ${t("note")}</button></div>`, p.days_late > 0 ? "k-lead_new" : "")).join("") || empty()}</ul></main>`;
	}

	async function renderSuppliers() {
		root.innerHTML = header(t("suppliers")) + `<main class="sk-form"><button class="sk-btn go wide" data-act="pu-sup-new">+ ${t("new_supplier")}</button>
			${formField("p-q", t("search"))}<button class="sk-btn wide" data-act="pu-sup-search">🔎 ${t("search")}</button><ul class="sk-list sk-gap" id="p-res"></ul></main>`;
		return supplierResults("");
	}
	async function supplierResults(q) {
		const rows = await call("buy_suppliers", { q });
		document.getElementById("p-res").innerHTML = rows.map((s) => li(esc(s.supplier_name), [s.gstin, s.supplier_group].filter(Boolean).map(esc).join(" · "),
			s.mobile_no ? `<a class="sk-chip" href="tel:${esc(s.mobile_no)}">📞</a>` : "")).join("") || empty();
	}
	async function newSupplierForm() {
		const groups = await call("buy_supplier_groups");
		root.innerHTML = header(t("new_supplier")) + `<main class="sk-form">${photoField("ns-photo", "📷 " + t("gst_photo"))}${formField("ns-name", t("supplier_name"))}
			${formField("ns-gstin", "GSTIN")}<label class="sk-field"><span>${t("mobile")}</span><div class="sk-input-row"><input id="ns-mobile" type="tel"></div></label>
			${pick("ns-group", t("group"), groups)}${photoField("ns-cheque", "📷 " + t("cheque_photo"))}
			<button class="sk-btn go wide" data-act="pu-sup-save">${t("save")}</button></main>`;
	}

	function renderBills() {
		root.innerHTML = header(t("bills")) + `<main class="sk-form">${photoField("b-photo", "📷 " + t("bill_photo"))}${finder("b-sup", t("supplier"), "supplier")}
			${formField("b-no", t("bill_no"))}<label class="sk-field"><span>${t("amount")}</span>${qtyBox("b-amt")}</label>${formField("b-for", t("bill_for"))}
			<button class="sk-btn go wide" data-act="pu-bill">${t("send_accounts")}</button></main>`;
	}

	async function renderLastRates() {
		root.innerHTML = header(t("last_rates")) + `<main class="sk-form">${formField("lr-q", t("search_item"))}<button class="sk-btn go wide" data-act="pu-lr">🔎 ${t("search")}</button><ul class="sk-list sk-gap" id="lr-res"></ul></main>`;
	}

	async function renderApprovals() {
		S.appr = await call("buy_approvals");
		root.innerHTML = header(t("po_approvals")) + `<main><ul class="sk-list">${S.appr.map((p, i) => li(esc(p.supplier_name), `${esc(p.name)} · ${t("due")} ${esc(p.schedule_date || "")}`,
			`<div class="sk-col"><b>${money(p.grand_total)}</b><a class="sk-chip" href="/app/purchase-order/${encodeURIComponent(p.name)}">PDF</a>
			<button class="sk-chip on" data-act="pu-approve" data-i="${i}">✓ ${t("approve")}</button><button class="sk-chip bad" data-act="pu-reject" data-i="${i}">✗ ${t("reject")}</button></div>`)).join("") || empty()}</ul></main>`;
	}

	// taps on the Store / Purchase screens; returns true when handled
	async function storeAct(act, el) {
		const i = Number(el.dataset.i);
		const saved = (msg) => toast(msg || t("saved"));
		switch (act) {
			case "st-search": return stockResults(val("s-q"));
			case "st-item": return itemSheet(S.items[i].item_code);
			case "st-po": return receiveForm(i);
			case "st-nopo": return receiveNoPo();
			case "st-receive": {
				el.disabled = true;
				const args = { challan_photo: await photoUrl("r-challan"), goods_photo: await photoUrl("r-goods"), note: val("r-note") };
				if (S.po) {
					args.purchase_order = S.po.name;
					args.items = JSON.stringify(S.po.items.map((r, k) => ({ po_detail: r.name, qty: val("r-q" + k) })));
				} else {
					Object.assign(args, { supplier: val("r-sup"), reason: val("r-reason"), items: JSON.stringify([{ item_code: val("r-item"), qty: val("r-qty") }]) });
				}
				const r = await call("store_receive", args, true);
				saved(`${t("receipt_saved")}: ${r.name}`);
				return go("receive");
			}
			case "st-wo": return issueForm(i);
			case "st-issue": {
				el.disabled = true;
				const items = S.wo.items.map((r, k) => ({ item_code: r.item_code, qty: val("i-q" + k) })).filter((x) => Number(x.qty) > 0);
				if (val("i-extra") && Number(val("i-extra-q")) > 0) items.push({ item_code: val("i-extra"), qty: val("i-extra-q") });
				const r = await call("store_issue", { work_order: S.wo.name, items: JSON.stringify(items), taken_by: val("i-who"), job_card: val("i-jc") || null, photo: await photoUrl("i-photo") }, true);
				saved(r.posted ? `${t("issued_ok")}: ${r.name}` : `${t("kept_draft")}: ${r.name}`);
				return go("issue");
			}
			case "st-req-issue": { const r = await call("store_request_issue", { request: S.reqs[i].request }, true); saved(r.posted ? `${t("issued_ok")}: ${r.name}` : `${t("kept_draft")}: ${r.name}`); return go("store_requests"); }
			case "st-req-buy": { const r = await call("store_request_to_purchase", { request: S.reqs[i].request }, true); saved(`${t("sent_purchase")}: ${r.name}`); return go("store_requests"); }
			case "st-so": return dispatchForm(i);
			case "st-dispatch": {
				el.disabled = true;
				const r = await call("store_dispatch", { sales_order: S.so.name, vehicle_no: val("d-vehicle"), driver_mobile: val("d-driver"), note: val("d-note"),
					cabin_photo: await photoUrl("d-cabin"), plate_photo: await photoUrl("d-plate") }, true);
				saved(`${t("dispatched")}: ${r.name}`);
				return go("dispatch");
			}
			case "st-order-low": { el.disabled = true; const r = await call("store_order_low", {}, true); saved(`${t("sent_purchase")}: ${r.name}`); return go("low_stock"); }
			case "st-count": {
				el.disabled = true;
				const counts = S.count.map((r, k) => ({ item_code: r.item_code, qty: val("c-q" + k) })).filter((x) => x.qty !== "");
				const r = await call("store_count", { warehouse: val("c-wh"), counts: JSON.stringify(counts), photo: await photoUrl("c-photo") }, true);
				saved(r.name ? `${r.differences} ${t("differences_sent")}: ${r.name}` : t("no_differences"));
				el.disabled = false;
				return;
			}
			case "st-new-item": {
				el.disabled = true;
				const r = await call("store_new_item", { item_name: val("n-name"), item_group: val("n-group"), uom: val("n-uom"), warehouse: val("n-wh") || null, photo: await photoUrl("n-photo") }, true);
				saved(`${t("sent_approval")}: ${r.name}`);
				return go("home");
			}
			case "pu-rates-selected": {
				S.rateItems = [...root.querySelectorAll("[data-breq]:checked")].map((c) => S.breqs[Number(c.dataset.breq)])
					.map((r) => ({ item_code: r.item_code, item_name: r.item_name, qty: r.qty, uom: r.uom, request: r.request, row: r.row }));
				if (!S.rateItems.length) return toast(t("tick_items"), true);
				return go("get_rates");
			}
			case "pu-add-item": {
				if (!val("g-item")) return toast(t("add_item_first"), true);
				S.rateItems = S.rateItems || [];
				S.rateItems.forEach((r, k) => { r.qty = val("g-q" + k) || r.qty; });
				S.rateItems.push({ item_code: val("g-item"), qty: val("g-qty") || 1 });
				return go("get_rates");
			}
			case "pu-rfq": {
				el.disabled = true;
				const items = (S.rateItems || []).map((r, k) => ({ ...r, qty: val("g-q" + k) || r.qty }));
				const sups = [...root.querySelectorAll("[data-sup]:checked")].map((c) => c.dataset.sup);
				if (val("g-sup")) sups.push(val("g-sup"));
				const r = await call("buy_rfq", { items: JSON.stringify(items), suppliers: JSON.stringify(sups), need_by: val("g-date") }, true);
				el.disabled = false;
				return rfqSent(r);
			}
			case "pu-wa": { const s = S.rfq.suppliers[Number(el.dataset.k)]; return window.open("https://wa.me/" + (s.mobile_no ? waNumber(s.mobile_no) : "") + "?text=" + encodeURIComponent(S.rfq.text), "_blank"); }
			case "pu-cmp": return compareItem(S.quoted[i].item_code);
			case "pu-quote-new": return quoteSheet();
			case "pu-quote-save": {
				el.disabled = true;
				await call("buy_quote", { supplier: val("q-sup"), item_code: val("q-item"), qty: val("q-qty"), rate: val("q-rate"), days: val("q-days"),
					photo: await photoUrl("q-photo"), rfq: S.rfq ? S.rfq.name : null }, true);
				closeSheet();
				saved();
				return compareItem(val("q-item") || (S.cmp && S.cmp.item_code));
			}
			case "pu-po": {
				el.disabled = true;
				const r = await call("buy_make_po", { supplier_quotation: el.dataset.sq }, true);
				saved(r.needs_approval ? `${r.name}: ${t("sent_sk")}` : r.posted ? `${t("po_placed")}: ${r.name}` : `${t("kept_draft")}: ${r.name}`);
				return;
			}
			case "pu-note": {
				const p = S.late[i];
				S.notePo = p.name;
				return sheet(`<h3 class="sk-h">${esc(p.supplier_name)} · ${esc(p.name)}</h3>${formField("fn-text", t("supplier_said"), true)}
					<label class="sk-field"><span>${t("promised_date")}</span><input id="fn-date" type="date" class="sk-select"></label>
					<button class="sk-btn ok wide" data-act="pu-note-save">${t("save")}</button><button class="sk-btn wide" data-act="close-sheet">${t("back")}</button>`);
			}
			case "pu-note-save": { await call("buy_follow_up_note", { purchase_order: S.notePo, text: val("fn-text"), promised: val("fn-date") || null }, true); closeSheet(); return saved(); }
			case "pu-sup-search": return supplierResults(val("p-q"));
			case "pu-sup-new": return newSupplierForm();
			case "pu-sup-save": {
				el.disabled = true;
				const r = await call("buy_new_supplier", { supplier_name: val("ns-name"), gstin: val("ns-gstin"), mobile: val("ns-mobile"), group: val("ns-group") || null,
					photo: await photoUrl("ns-photo"), cheque_photo: await photoUrl("ns-cheque") }, true);
				saved(`${t("saved")}: ${r.name}`);
				return go("suppliers");
			}
			case "pu-bill": {
				el.disabled = true;
				const r = await call("buy_send_bill", { supplier: val("b-sup"), photo: await photoUrl("b-photo"), amount: val("b-amt"), bill_no: val("b-no"), against: val("b-for") }, true);
				saved(`${t("sent_accounts")} (${r.sent_to})`);
				return go("bills");
			}
			case "pu-lr": {
				const rows = await call("buy_last_rates", { q: val("lr-q") });
				document.getElementById("lr-res").innerHTML = rows.map((r) => li(esc(r.item_name), `${esc(r.supplier)} · ${esc(r.date)}`, `<b>${money(r.rate)}</b> / ${esc(r.uom || "")}`)).join("") || empty();
				return;
			}
			case "pu-approve": { await call("buy_decide", { purchase_order: S.appr[i].name, approve: 1 }, true); saved(t("approved")); return go("po_approvals"); }
			case "pu-reject": {
				const why = window.prompt(t("reject_why"));
				if (why === null) return;
				await call("buy_decide", { purchase_order: S.appr[i].name, approve: 0, reason: why }, true);
				saved(t("rejected"));
				return go("po_approvals");
			}
		}
		return false;
	}

	// ---------- Production, subcontractors and Quality (SK drafts F03 / F04, 26-Oct-2026) ----------
	const stageChip = (s) => `<span class="sk-stage ${s.state}">${esc(s.operation || "")}</span>`;
	async function renderOrderBoard() {
		S.board = await call("prod_board");
		root.innerHTML = header(t("order_board")) + `<main><p class="sk-note">${t("board_help")}</p><ul class="sk-list">${S.board.map((w) => `<li class="sk-item sk-person ${w.late ? "k-lead_new" : ""}">
			<div><div class="sk-item-title">${esc(w.item_name || w.production_item)}</div>
			<div class="sk-item-meta">${esc(w.name)}${w.customer ? " · " + esc(w.customer) : ""} · ${t("delivery")}: ${esc(w.expected_delivery_date || t("not_set"))}${w.late ? ` <span class="sk-due">${t("late")}</span>` : ""}</div>
			${w.no_order ? `<div class="sk-item-meta sk-due">⚠ ${t("no_order_link")}</div>` : ""}</div>
			<div class="sk-stages">${w.stages.map(stageChip).join("") || t("no_job_cards")}</div></li>`).join("") || empty()}</ul></main>`;
	}

	// one big card per job: Start / Photo / Done / Need material / Problem (subcontractor and manager)
	async function renderJobs(view) {
		S.jobs = await call("prod_job_cards");
		const sub = view === "my_jobs";
		const card = (j, i) => `<section class="sk-card ${j.status === "Work In Progress" ? "sk-working" : ""}">
			<div class="sk-card-label">${esc(j.operation || "")} · ${esc(j.workstation || "")} <button class="sk-icon" data-act="pr-read" data-i="${i}">🔊</button></div>
			<div class="sk-card-text">${esc(j.item_name || j.production_item)}</div>
			<div class="sk-card-meta">${esc(j.name)} · ${esc(j.work_order || "")}${j.started ? ` · ${t("started")} ${esc(j.started.slice(11, 16))}` : ""} · 📷 ${j.photos}</div>
			<div class="sk-card-actions">
				${j.started ? "" : `<button class="sk-btn go" data-act="pr-start" data-i="${i}">▶ ${t("start")}</button>`}
				<button class="sk-btn" data-act="pr-photo" data-i="${i}">📸 ${t("photo")}</button>
				<button class="sk-btn ok" data-act="pr-done" data-i="${i}">✅ ${t("done")}</button>
				<button class="sk-btn" data-act="pr-need" data-i="${i}">📦 ${t("need_material")}</button>
				<button class="sk-btn bad" data-go="problem">⚠ ${t("trouble")}</button>
			</div>${j.drawing ? `<a class="sk-link" href="${esc(j.drawing.file_url)}" target="_blank">📄 ${t("see_drawing")}</a>` : ""}</section>`;
		root.innerHTML = header(t(view)) + `<main>${sub ? `<p class="sk-note">🔊 ${S.jobs.length} ${t("jobs_today")}</p>` : ""}${S.jobs.map(card).join("") || `<p class="sk-empty">${t("nothing")}</p>`}</main>`;
		if (sub && S.jobs.length) readAloud(`${S.jobs.length} ${t("jobs_today")}`);
	}
	function doneSheet(i) {
		const j = S.jobs[i];
		S.job = j;
		sheet(`<h3 class="sk-h">✅ ${esc(j.operation || "")} · ${esc(j.item_name || "")}</h3>
			${photoField("pd-1", "📷 " + t("photo_full"))}${photoField("pd-2", "📷 " + t("photo_detail"))}
			<label class="sk-field"><span>${t("workers_used")}</span>${qtyBox("pd-workers")}</label>${formField("pd-remark", t("anything_tell"), true)}
			<button class="sk-btn ok wide" data-act="pr-done-save">✅ ${t("job_done_qc")}</button><button class="sk-btn wide" data-act="close-sheet">${t("back")}</button>`);
	}
	function needSheet(j) {
		S.job = j || null;
		sheet(`<h3 class="sk-h">📦 ${t("need_material")}${j ? " · " + esc(j.operation || "") : ""}</h3>
			${j ? "" : pick("pn-job", t("job_card"), (S.jobs || []).map((x) => ({ value: x.name, label: `${x.name} · ${x.operation || ""} · ${x.item_name || ""}` })))}
			${formField("pn-spoken", t("say_material"), true)}${finder("pn-item", t("item"), "item")}<label class="sk-field"><span>${t("qty")}</span>${qtyBox("pn-qty")}</label>
			<label class="sk-field"><span>${t("needed_by")}</span><input id="pn-date" type="date" class="sk-select" value="${new Date().toISOString().slice(0, 10)}"></label>
			<button class="sk-btn go wide" data-act="pr-need-save">${t("send_store")}</button><button class="sk-btn wide" data-act="close-sheet">${t("back")}</button>`);
	}
	async function renderNeedMaterial() {
		S.jobs = await call("prod_job_cards");
		root.innerHTML = header(t("need_material")) + `<main></main>`;
		needSheet(null);
	}
	async function renderProgressPhotos() {
		S.board = S.board || await call("prod_board");
		root.innerHTML = header(t("progress_photos")) + `<main class="sk-form">${pick("pp-wo", t("cabin"), S.board.map((w) => ({ value: w.name, label: `${w.item_name || w.production_item} · ${w.name}` })))}
			${photoField("pp-photo", "📷 " + t("photo"))}${formField("pp-note", t("note_q"))}<button class="sk-btn go wide" data-act="pr-progress">${t("save")}</button></main>`;
	}
	async function renderReadyDispatch() {
		const rows = await call("prod_ready");
		root.innerHTML = header(t("ready_dispatch")) + `<main><ul class="sk-list">${rows.map((w) => li(esc(w.item_name || w.production_item),
			`${esc(w.name)}${w.customer ? " · " + esc(w.customer) : ""}${w.sales_order ? " · " + esc(w.sales_order) : ` · <span class="sk-due">${t("no_order_link")}</span>`}`,
			w.qc === "Accepted" ? `<span class="sk-chip on">QC ✓</span>` : `<span class="sk-chip">${w.qc === "Rejected" ? "QC ✗" : t("qc_pending")}</span>`)).join("") || empty()}</ul></main>`;
	}

	async function renderNcs(view) {
		S.ncs = await call("qc_open_ncs");
		const canNew = view === "non_conformance" && (state.home.functions || []).includes("Quality");
		root.innerHTML = header(t(view)) + `<main>${canNew ? `<button class="sk-btn bad wide" data-act="qc-nc-new">📷 + ${t("new_nc")}</button>` : ""}
			<ul class="sk-list sk-gap">${S.ncs.map((n, i) => li(esc(n.subject), esc(n.details || "").replace(/\n/g, "<br>"),
				`<button class="sk-chip on" data-act="qc-nc-fix" data-i="${i}">✓ ${t("fixed")}</button>`, "k-lead_new")).join("") || empty()}</ul></main>`;
	}

	async function renderInspect(view) {
		const p = await call("qc_pending");
		const groups = view === "final_check" ? [["final", t("final")]] : [["incoming", t("incoming")], ["stage", t("stage")], ["final", t("final")]];
		S.checks = [];
		const rows = (key) => p[key].map((c) => { S.checks.push(c); const i = S.checks.length - 1;
			return li(`${esc(c.item_name || c.item_code)}${c.operation ? " · " + esc(c.operation) : ""}`, `${esc(c.reference_name)} · ${esc(c.from || "")} · ${num(c.qty)} · ${when(c.since)}`,
				`<button class="sk-chip on" data-act="qc-open" data-i="${i}">${t("check_now")}</button>`); }).join("");
		root.innerHTML = header(t(view)) + `<main>${groups.map(([k, label]) => `<h3 class="sk-h">${label} (${p[k].length})</h3><ul class="sk-list">${rows(k) || empty()}</ul>`).join("")}</main>`;
	}
	async function inspectForm(i) {
		const c = S.checks[i];
		S.check = c;
		const o = await call("qc_templates", { reference_type: c.reference_type, operation: c.operation || "", item_code: c.item_code });
		root.innerHTML = header(t("inspect")) + `<main class="sk-form"><h3 class="sk-h">${esc(c.item_name || c.item_code)}${c.operation ? " · " + esc(c.operation) : ""}</h3>
			<p class="sk-note">${esc(c.reference_type)} ${esc(c.reference_name)} · ${esc(c.from || "")}</p>
			${pick("q-tpl", t("checklist"), o.templates)}<div id="q-points"></div>
			${c.reference_type === "Purchase Receipt" ? `<label class="sk-field"><span>${t("accepted_qty")}</span>${qtyBox("q-acc", c.qty)}</label><label class="sk-field"><span>${t("rejected_qty")}</span>${qtyBox("q-rej", 0)}</label>` : ""}
			<label class="sk-field"><span>${t("sample")}</span>${qtyBox("q-sample", 1)}</label>
			${photoField("q-p1", "📷 " + t("photo"))}${photoField("q-p2", "📷 " + t("photo"))}${formField("q-remark", t("note_q"))}
			<div class="sk-row"><button class="sk-btn ok wide" data-act="qc-save">${t("save_check")}</button></div></main>`;
		const sel = document.getElementById("q-tpl");
		sel.addEventListener("change", () => loadPoints(sel.value));
		if (o.guess) sel.value = o.guess;
		loadPoints(o.guess || "");
	}
	// no template in ERPNext yet: a short standard list so a check is never blocked
	const DEFAULT_POINTS = { "Purchase Receipt": ["qty_matches", "no_damage_rust", "size_as_ordered"], "Job Card": ["size_as_drawing", "weld_finish", "clean_safe"] };
	async function loadPoints(tpl) {
		S.points = tpl ? await call("qc_checklist", { template: tpl })
			: (DEFAULT_POINTS[S.check.reference_type] || DEFAULT_POINTS["Job Card"]).map((k) => ({ specification: t(k) }));
		document.getElementById("q-points").innerHTML = S.points.map((p, k) => `<div class="sk-point"><div class="sk-item-title">${esc(p.specification)}${p.value ? ` <small>(${esc(p.value)})</small>` : ""}</div>
			<div class="sk-row"><button class="sk-chip on" data-qok="${k}" data-v="1">✓ OK</button><button class="sk-chip" data-qok="${k}" data-v="0">✗ ${t("not_ok")}</button></div>
			<div class="sk-qnote" id="q-note-wrap-${k}" hidden>${formField("q-note-" + k, t("what_wrong"))}</div></div>`).join("") || `<p class="sk-note">${t("pick_checklist")}</p>`;
	}

	async function prodAct(act, el) {
		const i = Number(el.dataset.i);
		switch (act) {
			case "pr-read": { const j = S.jobs[i]; return readAloud(`${j.operation || ""}. ${j.item_name || ""}`); }
			case "pr-start": { await call("prod_start", { job_card: S.jobs[i].name }, true); toast(t("saved")); return go(state.view); }
			case "pr-photo": {
				const inp = document.createElement("input");
				inp.type = "file"; inp.accept = "image/*"; inp.capture = "environment";
				inp.onchange = async () => { if (!inp.files[0]) return; const url = await upload(inp.files[0]); await call("prod_photo", { job_card: S.jobs[i].name, photo: url }, true); toast(t("saved")); go(state.view); };
				return inp.click();
			}
			case "pr-done": return doneSheet(i);
			case "pr-done-save": {
				el.disabled = true;
				const photos = [await photoUrl("pd-1"), await photoUrl("pd-2")].filter(Boolean);
				const r = await call("prod_done", { job_card: S.job.name, photos: JSON.stringify(photos), workers: val("pd-workers"), remark: val("pd-remark") }, true);
				closeSheet();
				toast(r.posted ? t("job_done_ok") : t("job_done_draft"));
				return go(state.view);
			}
			case "pr-need": return needSheet(S.jobs[i]);
			case "pr-need-save": {
				el.disabled = true;
				const items = val("pn-item") && Number(val("pn-qty")) > 0 ? [{ item_code: val("pn-item"), qty: val("pn-qty") }] : [];
				const jc = S.job ? S.job.name : val("pn-job");
				const r = await call("prod_need_material", { items: JSON.stringify(items), job_card: jc || null, needed_by: val("pn-date"), spoken: val("pn-spoken") }, true);
				closeSheet();
				toast(r.request ? `${t("sent_store")}: ${r.request}` : t("sent_store"));
				return state.view === "need_material" ? go("home") : undefined;
			}
			case "pr-progress": {
				el.disabled = true;
				await call("prod_progress_photo", { work_order: val("pp-wo"), photo: await photoUrl("pp-photo"), note: val("pp-note") }, true);
				toast(t("saved"));
				return go("progress_photos");
			}
			case "qc-open": return inspectForm(i);
			case "qc-save": {
				const points = S.points.map((p, k) => {
					const on = root.querySelector(`[data-qok="${k}"].on`);
					return { specification: p.specification, value: p.value, ok: on ? Number(on.dataset.v) : 1, note: val("q-note-" + k) };
				});
				el.disabled = true;
				const photos = [await photoUrl("q-p1"), await photoUrl("q-p2")].filter(Boolean);
				const c = S.check;
				const r = await call("qc_save", { reference_type: c.reference_type, reference_name: c.reference_name, item_code: c.item_code, points: JSON.stringify(points),
					template: val("q-tpl") || null, sample_size: val("q-sample") || 1, accepted_qty: val("q-acc") || null, rejected_qty: val("q-rej") || null,
					photos: JSON.stringify(photos), remark: val("q-remark"), inspection_type: c.inspection_type }, true);
				toast(r.status === "Accepted" ? `✓ ${t("passed")}: ${r.name}` : `✗ ${t("rework_sent")}${r.non_conformance ? ": " + r.non_conformance : ""}`, r.status !== "Accepted");
				return go(c.inspection_type === "Outgoing" ? "final_check" : "inspect");
			}
			case "qc-nc-new": {
				S.jobs = S.jobs || await call("prod_job_cards").catch(() => []);
				return sheet(`<h3 class="sk-h">❗ ${t("new_nc")}</h3>${photoField("nc-photo", "📷 " + t("defect_photo"))}${formField("nc-subject", t("what_wrong"), true)}
					${pick("nc-job", t("job_card"), (S.jobs || []).map((x) => ({ value: x.name, label: `${x.name} · ${x.operation || ""} · ${x.workstation || ""}` })))}
					<label class="sk-field"><span>${t("by_when")}</span><input id="nc-date" type="date" class="sk-select"></label>
					<button class="sk-btn bad wide" data-act="qc-nc-save">${t("send_fixer")}</button><button class="sk-btn wide" data-act="close-sheet">${t("back")}</button>`);
			}
			case "qc-nc-save": {
				el.disabled = true;
				const photos = [await photoUrl("nc-photo")].filter(Boolean);
				await call("qc_raise_nc", { subject: val("nc-subject"), details: val("nc-subject"), job_card: val("nc-job") || null, by_when: val("nc-date") || null, photos: JSON.stringify(photos) }, true);
				closeSheet();
				toast(t("saved"));
				return go("non_conformance");
			}
			case "qc-nc-fix": {
				S.nc = S.ncs[i];
				return sheet(`<h3 class="sk-h">✓ ${esc(S.nc.subject)}</h3>${formField("nf-action", t("what_done"), true)}${photoField("nf-photo", "📷 " + t("after_photo"))}
					<button class="sk-btn ok wide" data-act="qc-nc-close">${t("save")}</button><button class="sk-btn wide" data-act="close-sheet">${t("back")}</button>`);
			}
			case "qc-nc-close": {
				el.disabled = true;
				await call("qc_close_nc", { name: S.nc.name, action: val("nf-action"), photo: await photoUrl("nf-photo") }, true);
				closeSheet();
				toast(t("saved"));
				return go(state.view);
			}
		}
		return false;
	}

	// Sales manager: the whole team's leads and deals with his own (SK, 26-Oct-2026)
	let teamPerson = "";
	async function renderTeamLeads() {
		const d = await call("team_follow_up", teamPerson ? { person: teamPerson } : {});
		const chip = (u, label) => `<button class="sk-chip ${teamPerson === u ? "on" : ""}" data-teamp="${esc(u)}">${esc(label)}</button>`;
		const people = d.people.map((p) => `<li class="sk-item"><button class="sk-fu-main" data-teamp="${esc(p.user)}"><div class="sk-item-title">${esc(p.full_name)}</div>
			<div class="sk-item-meta">${p.open} ${t("open_items")} · ${p.new} ${t("new_badge")} · <span class="${p.overdue ? "sk-due" : ""}">${p.overdue} ${t("overdue")}</span>${p.deal_value ? ` · ₹${Number(p.deal_value).toLocaleString("en-IN")}` : ""}</div></button>
			${p.score != null ? `<b>${Math.round(p.score)}%</b>` : ""}</li>`).join("");
		const rows = d.rows.map((r) => `<li class="sk-fu ${r.overdue ? "late" : r.new ? "new" : ""}"><button class="sk-fu-main" data-open="${esc(r.doctype)}" data-name="${esc(r.name)}">
			<div class="sk-item-title">${esc(r.title)} ${r.new ? `<span class="sk-badge">${t("new_badge")}</span>` : ""}${r.overdue ? `<span class="sk-badge bad">${t("overdue")}</span>` : ""}</div>
			<div class="sk-item-meta">👤 ${esc(r.owner_name)} · ${esc(r.status || "")} · ${r.doctype === "CRM Deal" ? t("deals") : t("leads")}</div>
			${r.next || r.due ? `<div class="sk-item-meta">${t("next")}: ${esc(r.next || "")} ${r.due ? "· " + when(r.due) : ""}</div>` : ""}
			${r.last ? `<div class="sk-item-meta">${t("last")}: ${esc(r.last.text)} · ${when(r.last.on)}</div>` : ""}</button>${contactButtons(r)}</li>`).join("");
		root.innerHTML = header(t("team_leads")) + `<main><ul class="sk-list">${people}</ul>
			<div class="sk-row sk-wrap sk-gap">${chip("", t("all"))}${d.people.map((p) => chip(p.user, p.full_name)).join("")}</div>
			<ul class="sk-list sk-gap">${rows || `<li class="sk-empty">${t("nothing")}</li>`}</ul></main>`;
	}

	const LIVE_VIEWS = { my_day: renderMyDay, my_leads: () => renderLeads("my_leads"), my_deals: () => renderLeads("my_deals"),
		my_kpi: renderKpi, dsi: renderDsi, work_book: () => renderWork("work_book"), problem: () => renderWork("problem"),
		follow_up: renderFollowUp, new_lead: renderNewLead, training: renderTraining, day_report: renderDayReport,
		team_reports: renderTeamReports, calendar: renderCalendar, detail: () => renderDetail(current.doctype, current.name),
		reminders: renderReminders, calls: renderCalls, whatsapp: renderWhatsApp, mail: renderMail, library: renderLibrary,
		logins: renderLogins, team_leads: renderTeamLeads, stock_check: renderStockCheck, receive: renderReceive, issue: renderIssue, store_requests: renderStoreRequests,
		dispatch: renderDispatch, low_stock: renderLowStock, stock_count: renderStockCount, new_item: renderNewItem,
		buy_requests: renderBuyRequests, get_rates: renderGetRates, compare: renderCompare, po_follow_up: renderFollowUpPo,
		suppliers: renderSuppliers, bills: renderBills, last_rates: renderLastRates, po_approvals: renderApprovals,
		order_board: renderOrderBoard, job_cards: () => renderJobs("job_cards"), my_jobs: () => renderJobs("my_jobs"), need_material: renderNeedMaterial,
		progress_photos: renderProgressPhotos, ready_dispatch: renderReadyDispatch, non_conformance: () => renderNcs("non_conformance"),
		my_fixes: () => renderNcs("my_fixes"), inspect: () => renderInspect("inspect"), final_check: () => renderInspect("final_check") };

	async function go(view) {
		state.view = view;
		if (view === "home") contacts = null;
		try {
			if (view === "home") {
				renderHome();
				// red counts change as jobs are done and checks are saved: refresh them quietly
				return call("home").then((h) => { state.home = h; if (state.view === "home" && !document.querySelector(".sk-sheet")) renderHome(); }).catch(() => {});
			}
			const fn = LIVE_VIEWS[view];
			return fn ? await fn() : renderSoon(view);
		} catch (e) { toast(e.message, true); }
	}

	root.addEventListener("click", async (ev) => {
		const el = ev.target.closest("button, [data-go]");
		if (!el) return;
		try {
			if (el.dataset.go) return go(el.dataset.go);
			if (el.dataset.open) { current = { doctype: el.dataset.open, name: el.dataset.name }; return go("detail"); }
			if (el.dataset.lesson && !el.dataset.act) return renderLesson(el.dataset.lesson);
			if (el.dataset.train) { trainTab = el.dataset.train; return go("training"); }
			if (el.dataset.q !== undefined) {
				el.parentElement.querySelectorAll(".sk-chip").forEach((c) => c.classList.remove("on"));
				el.classList.add("on");
				return;
			}
			if (el.dataset.contact) {
				const ch = el.dataset.contact;
				pending = { channel: ch, doctype: el.dataset.doctype, name: el.dataset.name, at: Date.now() };
				options().catch(() => null);
				if (ch === "Call") window.location.href = "tel:" + el.dataset.mobile;
				else if (ch === "WhatsApp") window.open("https://wa.me/" + waNumber(el.dataset.mobile), "_blank");
				else { pending = null; return mailSheet(el.dataset.doctype, el.dataset.name, el.dataset.email); }
				return;
			}
			if (el.dataset.waPick !== undefined) {
				el.parentElement.querySelectorAll(".sk-chip").forEach((c) => c.classList.remove("on"));
				el.classList.add("on");
				document.getElementById("f-wa").value = el.dataset.waPick;
				if (!el.dataset.waPick) toast(t("no_number"), true);
				return;
			}
			if (el.dataset.libcat) { libCat = el.dataset.libcat; return go("library"); }
			if (el.dataset.dir || el.dataset.mfile) {
				if (el.dataset.dir) el.parentElement.querySelectorAll(".sk-chip").forEach((c) => c.classList.remove("on"));
				el.classList.toggle("on", el.dataset.dir ? true : !el.classList.contains("on"));
				return;
			}
			if (el.dataset.tpl) {
				const x = (root._tpl || []).find((r) => r.name === el.dataset.tpl);
				if (x) document.getElementById("f-wamsg").value = (state.lang === "Marathi" && x.text_marathi) || x.text || x.title;
				return;
			}
			if (el.dataset.cal) { calTab = el.dataset.cal; if (calTab === "today") calDay = null; return go("calendar"); }
			if (el.dataset.week) { const d = new Date(el.dataset.week); d.setDate(d.getDate() + Number(el.dataset.step)); calDay = d.toISOString().slice(0, 10); return go("calendar"); }
			if (el.dataset.month) {
				let [y, m] = el.dataset.month.split("-").map(Number);
				m += Number(el.dataset.step);
				if (m < 1) { m = 12; y -= 1; } else if (m > 12) { m = 1; y += 1; }
				calMonth = { year: y, month: m };
				return go("calendar");
			}
			if (el.dataset.calday) { calDay = el.dataset.calday; calTab = "week"; return go("calendar"); }
			if (el.dataset.miclang) {
				const cur = micLang[el.dataset.miclang] || (state.lang === "Marathi" ? "mr" : "en");
				micLang[el.dataset.miclang] = cur === "en" ? "mr" : "en";
				el.textContent = micLang[el.dataset.miclang] === "en" ? "EN" : "मर";
				return;
			}
			if (el.dataset.rate) {
				root.querySelectorAll(`[data-rate="${el.dataset.rate}"]`).forEach((c) => c.classList.remove("on"));
				el.classList.add("on");
				return;
			}
			if (el.dataset.mic) return speakInto(document.getElementById(el.dataset.mic), el);
			if (el.dataset.ptype) {
				(el.parentElement || root).querySelectorAll(".sk-chip").forEach((c) => c.classList.remove("on"));
				el.classList.add("on");
				return;
			}
			if (el.dataset.resp && state.card) {
				state.card = await call("respond_card", { card: state.card.name, response: el.dataset.resp }, true);
				toast(t("saved"));
				return el.dataset.resp === "Problem" ? go("problem") : go(state.view);
			}
			if (el.dataset.teamp !== undefined) { teamPerson = el.dataset.teamp; return go("team_leads"); }
			if (el.dataset.fnpick) { el.classList.toggle("on"); return showWorkstation(); }
			const act = el.dataset.act;
			if (act && (act.startsWith("st-") || act.startsWith("pu-"))) return await storeAct(act, el);
			if (act && (act.startsWith("pr-") || act.startsWith("qc-"))) return await prodAct(act, el);
			if (el.dataset.qok !== undefined) {
				const k = el.dataset.qok;
				root.querySelectorAll(`[data-qok="${k}"]`).forEach((c) => c.classList.remove("on"));
				el.classList.add("on");
				document.getElementById("q-note-wrap-" + k).hidden = el.dataset.v === "1";
				return;
			}
			if (act === "pin-save") {
				if (val("p-new") !== val("p-new2")) return toast(t("pin_mismatch"), true);
				el.disabled = true;
				await call("set_pin", { old_pin: val("p-old"), new_pin: val("p-new") }, true);
				state.home.must_set_pin = false;
				toast(t("pin_saved"));
				return go("home");
			}
			if (act === "login-new") return loginSheet(el.dataset.i !== undefined ? root._people[Number(el.dataset.i)] : null);
			if (act === "login-make") {
				el.disabled = true;
				const functions = [...root.querySelectorAll("[data-fnpick].on")].map((c) => c.dataset.fnpick);
				const r = await call("hr_make_login", { mobile: val("g-mobile"), functions: JSON.stringify(functions), employee: el.dataset.emp || null,
					full_name: val("g-name"), manager: val("g-mgr") || null, language: val("g-lang"), workstation: functions.includes("Subcontractor") ? val("g-ws") || null : null }, true);
				await renderLogins();
				return pinSheet(r);
			}
			if (act === "login-reset") {
				const r = await call("hr_reset_pin", { user: root._people[Number(el.dataset.i)].user }, true);
				return pinSheet(r);
			}
			if (act === "login-close") {
				const p = root._people[Number(el.dataset.i)];
				if (!window.confirm(`${p.name}: ${t("close_q")}`)) return;
				await call("hr_close_login", { user: p.user }, true);
				toast(t("saved"));
				return renderLogins();
			}
			if (act === "login-wa" && root._pinMsg) {
				return window.open("https://wa.me/" + waNumber(root._pinMsg.mobile) + "?text=" + encodeURIComponent(root._pinMsg.text), "_blank");
			}
			if (act === "newcard") { state.card = await call("next_card", { force: 1 }, true); return go(state.view); }
			if (act === "read" && state.card) return readAloud(state.card.card_text);
			if (act === "lang") {
				state.lang = state.lang === "English" ? "Marathi" : "English";
				await call("set_language", { language: state.lang }, true);
				state.card = await call("next_card", { force: 1 }, true);
				return go(state.view);
			}
			if (act === "save-dsi") {
				el.disabled = true;
				await call("add_dsi", { what_changed: val("f-what"), before_text: val("f-before"), after_text: val("f-after"), photo: await photoUrl() }, true);
				toast(t("saved"));
				return go("home");
			}
			if (act === "save-work") {
				el.disabled = true;
				const chip = root.querySelector(".sk-chip.on");
				await call("add_work", { description: val("f-desc"), entry_type: el.dataset.kind, problem_type: chip ? chip.dataset.ptype : null, photo: await photoUrl() }, true);
				toast(t("saved"));
				return go(el.dataset.kind === "Problem" ? "home" : "work_book");
			}
			if (act === "close-sheet") { pending = null; return closeSheet(); }
			if (act === "status") {
				await call("set_crm_status", { doctype: current.doctype, name: current.name, status: el.dataset.status }, true);
				toast(t("saved"));
				return go("detail");
			}
			if (act === "save-note") {
				el.disabled = true;
				await call("add_crm_note", { doctype: current.doctype, name: current.name, text: val("f-note"), photo: await photoUrl("f-photo") }, true);
				toast(t("saved"));
				return go("detail");
			}
			if (act === "save-contact" && pending) {
				el.disabled = true;
				const chip = root.querySelector(".sk-sheet .sk-chip.on");
				await call("log_contact", { doctype: pending.doctype, name: pending.name, channel: pending.channel,
					outcome: chip ? chip.dataset.ptype : null, text: val("f-out"), photo: await photoUrl("f-outphoto"),
					duration: Math.round(Number(val("f-outmin") || 0) * 60) }, true);
				pending = null;
				closeSheet();
				toast(t("saved"));
				return go(state.view);
			}
			if (act === "correction") {
				sheet(`<h3 class="sk-h">✏️ ${t("correction")}</h3><div class="sk-item-meta">${esc(el.dataset.file)}</div>
					${formField("f-fix", t("correction_q"), true)}${photoField("f-fixphoto", t("correction_photo"))}
					<button class="sk-btn bad wide" data-act="send-correction" data-fileid="${esc(el.dataset.fileid)}">${t("send_correction")}</button>
					<button class="sk-btn wide" data-act="close-sheet">${t("back")}</button>`);
				return;
			}
			if (act === "send-correction") {
				el.disabled = true;
				const r = await call("request_correction", { doctype: current.doctype, name: current.name, text: val("f-fix"),
					file: el.dataset.fileid, photo: await photoUrl("f-fixphoto") }, true);
				closeSheet();
				toast(r.status_set ? t("correction_sent") : t("saved"));
				return go("detail");
			}
			if (act === "reminder-new") return reminderSheet(el.dataset.doctype, el.dataset.name);
			if (act === "rem-save") {
				const d = val("f-remdate"), tm = val("f-remtime");
				if (!d || !tm) throw new Error(t("date") + " / " + t("time"));
				el.disabled = true;
				await call("add_reminder", { title: val("f-rem"), when: `${d} ${tm}:00`, repeat: val("f-remrep"),
					doctype: el.dataset.doctype || null, name: el.dataset.name || null, for_user: val("f-remfor") || null }, true);
				closeSheet();
				toast(t("saved"));
				return go(state.view);
			}
			if (act === "rem-done") {
				await call("done_reminder", { doctype: el.dataset.doctype, name: el.dataset.name }, true);
				if (state.home) state.home.due_reminders = (state.home.due_reminders || []).filter((r) => r.name !== el.dataset.name);
				toast(t("saved"));
				return go(state.view);
			}
			if (act === "rem-snooze") {
				const seen = store.get("sk_rem_seen") || {};
				seen[el.dataset.key] = Date.now() + 10 * 60 * 1000;
				store.set("sk_rem_seen", seen);
				return go(state.view);
			}
			if (act === "call-add") { await options(); return addCallSheet(); }
			if (act === "call-save") {
				const who = val("f-callwho");
				if (!who) throw new Error(t("pick_customer"));
				const [doctype, name] = who.split("|");
				const dir = root.querySelector(".sk-sheet [data-dir].on");
				const out = root.querySelector(".sk-sheet [data-ptype].on");
				el.disabled = true;
				await call("add_call", { doctype, name, direction: dir ? dir.dataset.dir : "Outgoing", outcome: out ? out.dataset.ptype : null,
					minutes: val("f-callmin") || 0, text: val("f-callnote") }, true);
				closeSheet();
				toast(t("saved"));
				return go(state.view);
			}
			if (act === "wa-free") {
				const num = waNumber(val("f-wanum"));
				if (num.length < 10) throw new Error(t("no_number"));
				window.open("https://wa.me/" + num + (val("f-wamsg") ? "?text=" + encodeURIComponent(val("f-wamsg")) : ""), "_blank");
				return;
			}
			if (act === "wa-text") {
				const num = waNumber(val("f-wa"));
				if (num.length < 10) throw new Error(t("no_number"));
				window.open("https://wa.me/" + num + "?text=" + encodeURIComponent(val("f-watext")), "_blank");
				return closeSheet();
			}
			if (act === "lib-wa") {
				const x = libItems.find((r) => r.name === el.dataset.item);
				return waTextSheet(x ? libMessage(x) : "");
			}
			if (act === "lib-copy") {
				const x = libItems.find((r) => r.name === el.dataset.item);
				await navigator.clipboard.writeText(x ? libMessage(x) : "");
				return toast(t("copied"));
			}
			if (act === "mail-send") {
				el.disabled = true;
				const files = [...root.querySelectorAll(".sk-sheet [data-mfile].on")].map((c) => c.dataset.mfile);
				await call("send_mail", { doctype: el.dataset.doctype, name: el.dataset.name, to: val("f-mto"), subject: val("f-msub"),
					message: val("f-mbody"), files: JSON.stringify(files) }, true);
				closeSheet();
				toast(t("mail_sent"));
				return state.view === "detail" ? go("detail") : null;
			}
			if (act === "wa-send") return waSheet(el.dataset.doctype, el.dataset.name, el.dataset.mobile);
			if (act === "wa-go") {
				const num = waNumber(val("f-wa"));
				if (num.length < 10) throw new Error(t("no_number"));
				const w = window.open("about:blank", "_blank"); // open now, while the tap still counts, so the phone allows it
				const d = await call("share_link", { doctype: el.dataset.doctype, name: el.dataset.name }, true);
				const url = "https://wa.me/" + num + "?text=" + encodeURIComponent(d.message);
				if (w) w.location.href = url; else window.location.href = url;
				return closeSheet();
			}
			if (act === "share-pdf") {
				await sharePdf(el.dataset.pdf, el.dataset.file);
				if (el.dataset.fileid) {
					await call("mark_file_sent", { file: el.dataset.fileid }, true);
					if (state.home) state.home.new_files = (state.home.new_files || []).filter((f) => f.name !== el.dataset.fileid);
					toast(t("saved"));
				}
				return;
			}
			if (act === "save-lead") {
				el.disabled = true;
				const name = await call("new_lead", { first_name: val("f-first"), organization: val("f-org"), mobile_no: val("f-mobile"),
					email: val("f-email"), source: val("f-source"), segment: val("f-segment"), requirement: val("f-req"), photo: cardUrl }, true);
				cardUrl = null;
				toast(t("saved"));
				current = { doctype: "CRM Lead", name };
				return go("detail");
			}
			if (act === "lesson-done") {
				const n = Number(el.dataset.n || 0);
				const answers = [];
				for (let i = 0; i < n; i++) { const c = root.querySelector(`[data-q="${i}"].on`); answers.push(c ? c.dataset.choice : ""); }
				const r = await call("training_done", { lesson: el.dataset.lesson, answers: JSON.stringify(answers) }, true);
				if (!r.passed) { toast(`${r.score} / ${r.questions} · ${t("try_again")}`, true); return; }
				toast(`✅ ${t("passed")}${r.questions ? ` ${r.score} / ${r.questions}` : ""}`);
				return go("training");
			}
			if (act === "save-report") {
				el.disabled = true;
				await call("send_day_report", { work_done: val("f-done"), problems: val("f-prob"), plan_tomorrow: val("f-plan"), photo: await photoUrl() }, true);
				if (state.home) state.home.day_report_sent = true;
				toast(t("report_sent"));
				return go("day_report");
			}
			if (act === "save-review") {
				const rep = el.dataset.report;
				const chip = root.querySelector(`[data-rate="${rep}"].on`);
				await call("review_day_report", { report: rep, rating: chip ? chip.dataset.rating : null, comment: val("c-" + rep) }, true);
				toast(t("saved"));
				return;
			}
		} catch (e) {
			el.disabled = false;
			toast(e.message, true);
		}
	});

	function val(id) { const el = document.getElementById(id); return el ? el.value.trim() : ""; }

	async function start() {
		try {
			state.home = await call("home");
			state.lang = state.home.language || "English";
			state.card = state.home.card;
			renderHome();
			if (!state.card || Date.now() - new Date(state.card.slot_start.replace(" ", "T")).getTime() > 60 * 60 * 1000) {
				state.card = await call("next_card", {}, true);
				if (state.view === "home") renderHome();
			}
		} catch (e) {
			root.innerHTML = `<div class="sk-loading">${esc(e.message)}</div>`;
		}
	}

	// back from the phone's call / WhatsApp / email app: ask what happened and log it in CRM
	document.addEventListener("visibilitychange", () => {
		if (!document.hidden && pending && !root.querySelector(".sk-sheet-wrap") && Date.now() - pending.at > 1500) { pending.back = Date.now(); outcomeSheet(pending); }
	});

	function beep() {
		try {
			const ctx = new (window.AudioContext || window.webkitAudioContext)();
			const o = ctx.createOscillator();
			o.frequency.value = 880;
			o.connect(ctx.destination);
			o.start();
			o.stop(ctx.currentTime + 0.4);
		} catch (e) { /* no sound on this phone */ }
	}

	// check every minute while the app is open (and at once when it comes back to the screen):
	// a new drawing from the AI / design alerts straight away, not at the next hourly card
	async function poll() {
		if (document.hidden || !state.home) return;
		try {
			const h = await call("home");
			const known = new Set((state.home.new_files || []).map((f) => f.name));
			const fresh = (h.new_files || []).filter((f) => !known.has(f.name));
			const newCard = h.card && (!state.card || h.card.name !== state.card.name);
			state.home = h;
			if (newCard) state.card = h.card;
			if (fresh.length) {
				if (navigator.vibrate) navigator.vibrate([300, 150, 300]);
				beep();
				toast(`📐 ${t("new_drawing")}: ${fresh[0].title}`);
			} else if (newCard && navigator.vibrate) navigator.vibrate(200);
			// reminders whose time has come: buzz and beep once each, and show them on Home
			const alerted = store.get("sk_rem_alerted") || {};
			const ring = dueNow().filter((r) => !alerted[r.name + r.at]);
			ring.forEach((r) => { alerted[r.name + r.at] = 1; });
			if (ring.length) {
				store.set("sk_rem_alerted", alerted);
				if (navigator.vibrate) navigator.vibrate([400, 200, 400, 200, 400]);
				beep();
				toast(`⏰ ${ring[0].title}`);
			}
			if ((fresh.length || newCard || ring.length) && state.view === "home") renderHome();
		} catch (e) { /* offline: try again later */ }
	}
	setInterval(poll, 60 * 1000);
	document.addEventListener("visibilitychange", () => { if (!document.hidden && !pending) poll(); });

	start().then(() => setTimeout(poll, 3000));
})();
