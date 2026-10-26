/* SK App phone screens. Talks only to sk_app.api.* with the user's own ERPNext session. */
(function () {
	const root = document.getElementById("sk-app");
	const CSRF = root.dataset.csrf;
	// SK 26-Oct: after a deploy an open app kept the old screens; Home now reloads itself once a new version is live
	const LOADED_V = ((document.currentScript && document.currentScript.src) || "").split("v=")[1] || "";
	function reloadIfNew(h) {
		if (h && h.v && LOADED_V && h.v !== LOADED_V && !state.viewAs && state.view === "home" && !document.querySelector(".sk-sheet")) {
			location.reload();
			return true;
		}
		return false;
	}
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
	Object.assign(T.English, {
		bulk_logins: "Add many logins (paste list)",
		bulk_help: "One person per line: Name | Mobile | Function | Employee ID | Workstation | Reports to (mobile) | Language. Only name, mobile and function are needed.",
		make_logins: "Make all logins",
		logins_made: "logins made",
		bulk_pin_note: "Write down or WhatsApp each PIN now: it is shown only once.",
		keeps_password: "Keeps own PIN / password (use Reset PIN for a new one)",
	});
	Object.assign(T.Marathi, {
		bulk_logins: "एकदम अनेक लॉगिन (यादी पेस्ट करा)",
		bulk_help: "प्रत्येक ओळीत एक व्यक्ती: नाव | मोबाईल | विभाग | Employee ID | वर्कस्टेशन | रिपोर्ट (मोबाईल) | भाषा. नाव, मोबाईल व विभाग पुरेसे.",
		make_logins: "सर्व लॉगिन बनवा",
		logins_made: "लॉगिन बनले",
		bulk_pin_note: "प्रत्येक पिन आत्ताच लिहून घ्या किंवा WhatsApp करा: तो एकदाच दिसतो.",
		keeps_password: "स्वतःचा पिन / पासवर्ड तसाच (नवीनसाठी Reset PIN)",
	});
	// Finance screens (26-Oct-2026)
	Object.assign(T.English, {
		cash_today: "Cash Today",
		to_collect: "To Collect",
		to_pay: "To Pay",
		pay_approvals: "Payment OK",
		bills_to_post: "Bills to Post",
		invoices: "Invoices",
		expenses: "Expenses",
		segment_pnl: "Segment P&L",
		month_close: "Month Close",
		pay_mode: "Mode",
		utr_no: "UTR / cheque no.",
		pay_date: "Payment date",
		pay_proof: "Payment screenshot / photo",
		bank_cash_now: "Bank + cash now",
		in_today: "in today",
		out_today: "out today",
		today_payments: "Payments today",
		no_bank_yet: "No bank or cash account in ERPNext yet: ask Samir to add the bank account.",
		over_60: "Over 60 days",
		d31_60: "31 to 60 days",
		d0_30: "1 to 30 days late",
		not_due: "Not yet due",
		days_late: "days late",
		promise: "Promise",
		received: "Received",
		total_due: "Total due",
		pay_rule: "Above the PO limit, SK's OK is needed before paying.",
		bill: "Bill",
		ask_sk: "Ask SK",
		paid: "Paid",
		bill_photos: "Bill photos from Purchase / Store",
		see_photo: "photo",
		make_bill: "Make bill",
		already_done: "Done",
		drafts_check: "Drafts to check and post",
		check: "Check",
		post: "Post",
		posted: "posted",
		dispatched_no_invoice: "Dispatched, no invoice yet",
		make_invoice: "Make invoice",
		petty_cash: "Petty cash voucher",
		claims_to_pay: "Approved expense claims to pay",
		this_month: "This month margin",
		income: "Income",
		cost: "Cost",
		pnl_note: "From ERPNext books by cost centre. Only as good as the entries made.",
		mc_stock_close: "Stock closing",
		mc_pnl: "P&L",
		mc_mar: "MAR (monthly review)",
		mc_gstr1: "GSTR-1",
		mc_gstr3b: "GSTR-3B",
		by_date: "By",
		wa_due_1: "Dear",
		wa_due_2: "Gentle reminder: invoice",
		wa_due_3: "has",
		wa_due_4: "Kindly arrange the payment. Thank you.",
		what_customer_said: "What did the customer say? (speak)",
		promised_on: "Promised date",
		save_payment: "Save payment",
		kept_draft: "saved as draft (see note in ERPNext)",
		asked_sk: "SK is asked",
		against_po: "Against PO",
		supplier_bill_no: "Supplier's bill no.",
		bill_date: "Bill date",
		no_po_bill: "No open PO for this supplier: make this bill in ERPNext.",
		pick_po: "Please pick the PO",
		draft_made: "draft made, check and post",
		voucher_photo: "Voucher / bill photo",
		spent_on: "Spent on what? (speak)",
		expense_head: "Expense head",
		paid_from: "Paid from",
		segment: "Segment",
	});
	Object.assign(T.Marathi, {
		cash_today: "आजची रोकड",
		to_collect: "येणे बाकी",
		to_pay: "देणे बाकी",
		pay_approvals: "पेमेंट मंजुरी",
		bills_to_post: "बिल पोस्ट करा",
		invoices: "इनव्हॉइस",
		expenses: "खर्च",
		segment_pnl: "विभागवार नफा",
		month_close: "महिना बंद",
		pay_mode: "प्रकार",
		utr_no: "UTR / चेक नं.",
		pay_date: "पेमेंट तारीख",
		pay_proof: "पेमेंट स्क्रीनशॉट / फोटो",
		bank_cash_now: "आता बँक + रोकड",
		in_today: "आज आले",
		out_today: "आज गेले",
		today_payments: "आजचे पेमेंट",
		no_bank_yet: "ERPNext मध्ये बँक / कॅश खाते नाही: समीरला बँक खाते टाकायला सांगा.",
		over_60: "60 दिवसांपेक्षा जास्त",
		d31_60: "31 ते 60 दिवस",
		d0_30: "1 ते 30 दिवस उशीर",
		not_due: "अजून मुदत आहे",
		days_late: "दिवस उशीर",
		promise: "वचन",
		received: "मिळाले",
		total_due: "एकूण येणे",
		pay_rule: "PO मर्यादेपेक्षा जास्त रकमेसाठी पेमेंटआधी SK ची मंजुरी लागते.",
		bill: "बिल",
		ask_sk: "SK ला विचारा",
		paid: "दिले",
		bill_photos: "खरेदी / स्टोअरकडून आलेले बिल फोटो",
		see_photo: "फोटो",
		make_bill: "बिल बनवा",
		already_done: "झाले",
		drafts_check: "तपासून पोस्ट करायचे ड्राफ्ट",
		check: "तपासा",
		post: "पोस्ट",
		posted: "पोस्ट झाले",
		dispatched_no_invoice: "डिस्पॅच झाले, इनव्हॉइस नाही",
		make_invoice: "इनव्हॉइस बनवा",
		petty_cash: "पेटी कॅश व्हाउचर",
		claims_to_pay: "मंजूर खर्च, पेमेंट बाकी",
		this_month: "या महिन्याचा नफा",
		income: "उत्पन्न",
		cost: "खर्च",
		pnl_note: "ERPNext च्या हिशोबातून, कॉस्ट सेंटरनुसार. नोंदी जितक्या बरोबर तितके बरोबर.",
		mc_stock_close: "स्टॉक क्लोजिंग",
		mc_pnl: "नफा-तोटा",
		mc_mar: "MAR (मासिक आढावा)",
		mc_gstr1: "GSTR-1",
		mc_gstr3b: "GSTR-3B",
		by_date: "तारीख",
		wa_due_1: "नमस्कार",
		wa_due_2: "आठवण: इनव्हॉइस",
		wa_due_3: "ची रक्कम",
		wa_due_4: "कृपया पेमेंट करावे. धन्यवाद.",
		what_customer_said: "ग्राहक काय म्हणाले? (बोला)",
		promised_on: "वचन दिलेली तारीख",
		save_payment: "पेमेंट सेव्ह करा",
		kept_draft: "ड्राफ्ट म्हणून सेव्ह (ERPNext मध्ये नोंद पहा)",
		asked_sk: "SK ला विचारले",
		against_po: "कोणत्या PO साठी",
		supplier_bill_no: "सप्लायरचा बिल नं.",
		bill_date: "बिल तारीख",
		no_po_bill: "या सप्लायरचा उघडा PO नाही: हे बिल ERPNext मध्ये बनवा.",
		pick_po: "PO निवडा",
		draft_made: "ड्राफ्ट बनला, तपासून पोस्ट करा",
		voucher_photo: "व्हाउचर / बिल फोटो",
		spent_on: "कशावर खर्च? (बोला)",
		expense_head: "खर्च खाते",
		paid_from: "कुठून दिले",
		segment: "विभाग",
	});
	// change list Rev 13, part A: AI & ERP desk, week plan, saved lead, mic / camera
	Object.assign(T.English, {
		improvement_inbox: "Improvement Inbox", dept_visits: "Department Visit", erp_gaps: "ERP Gaps", app_users: "App Users",
		change_list: "Change List", projects: "Projects", training_progress: "Training Progress", erpnext_desk: "ERPNext desk",
		inbox_new: "New, to sort", inbox_working: "Being fixed", sort_as: "Sort as", works_close: "Works: close + DSI",
		fix_note: "What was done? (speak)", visit_note: "What did you find? (speak)", not_today: "not in the app today",
		problems_open: "Open problems", visit_plan: "Visit plan", last_notes: "Last visit notes", logged_today: "Today",
		never: "Never logged in", earlier: "Not today", first_pin_left: "first PIN", of_word: "of", made_word: "made",
		people_n2: "people", lessons_n: "lessons", finished_n: "finished all", open_tasks: "open tasks", late_tasks: "late",
		did_extra: "＋ I did extra work", to_do: "To do", move_to: "Move to", moved: "moved", load: "Load",
		routine: "Weekly routine", new_today: "New today", to_call: "To call", lead_saved: "Lead saved in ERPNext CRM → Leads",
		lead_no: "Lead no", owner: "Owner", call_now: "Call now", open_lead: "Open lead", another_lead: "Another lead",
		camera: "Camera", gallery: "Gallery / screenshot", pdf_file: "PDF / file", retake: "Retake", remove: "Remove",
		uploading: "Sending…", uploaded: "Sent ✓", upload_retry: "Network weak, trying again…",
		open_chrome: "Mic / camera work best in Chrome. Tap here to open the SK App in Chrome.",
		cash_today: "Cash / Bank", to_collect: "Receivables", to_pay: "Payables", bills_to_post: "Purchase Invoice and Debit Note",
		invoices: "Sales Invoice and Credit Note", expenses: "Journal Voucher", dir_expenses: "Direct and Indirect Expenses",
		segment_pnl: "Segment Wise P&L", month_close: "Month Wise Report", ledger_wise: "Ledger-wise", work_tab: "To do",
		opening: "Opening", closing: "Closing", dr: "Dr", cr: "Cr", bills_n: "bills", returns_n: "debit / credit notes",
		drafts_n: "drafts", net: "Net", direct: "Direct", indirect: "Indirect", gross: "Gross", net_pl: "Net P&L",
		common_cost: "Common (not split yet)", closing_list: "Closing checklist", month_pl: "Month-wise P&L", inv_n: "invoices",
		team_box: "Team mailbox", my_customers: "My customers", st_New: "New", st_Taken: "Taken", st_Replied: "Replied",
		"st_Lead made": "Lead made", "st_Not a lead": "Not a lead", take: "I'll answer", give_to: "Give to", make_lead_btn: "Make lead",
		not_lead: "Not a lead", reply: "Reply", reply_q: "Your reply (speak or type)", by_word: "by", lead_sources: "Lead Sources",
		upload_list: "Upload IndiaMART / JustDial list (Excel)", leads_made: "new leads", added_old: "added to earlier leads",
		skipped_n: "rows without mobile / e-mail", last_check: "Last mail check", check_now: "Check mails now",
		pull_api: "IndiaMART Pull API: paid add-on, Phase 2", mailboxes: "Mailboxes", set_up: "set up", not_set_up: "not set up in ERPNext yet",
		on_word: "On", off_word: "Off", this_month2: "this month", source_word: "Source",
		erp_roles: "ERPNext roles", upload_failed: "File could not be sent.", draft_back: "Your unsaved form was filled back in.",
	});
	Object.assign(T.Marathi, {
		improvement_inbox: "सुधारणा इनबॉक्स", dept_visits: "विभाग भेट", erp_gaps: "ERP त्रुटी", app_users: "ॲप वापरकर्ते",
		change_list: "बदल यादी", projects: "प्रकल्प", training_progress: "प्रशिक्षण प्रगती", erpnext_desk: "ERPNext डेस्क",
		inbox_new: "नवीन, वर्गीकरण बाकी", inbox_working: "दुरुस्ती चालू", sort_as: "प्रकार", works_close: "चालते: बंद + DSI",
		fix_note: "काय केले? (बोला)", visit_note: "काय आढळले? (बोला)", not_today: "आज ॲपमध्ये नाही",
		problems_open: "उघड्या समस्या", visit_plan: "भेटीचे नियोजन", last_notes: "मागील भेटीच्या नोंदी", logged_today: "आज",
		never: "कधीच लॉगिन नाही", earlier: "आज नाही", first_pin_left: "पहिला PIN", of_word: "पैकी", made_word: "बनले",
		people_n2: "लोक", lessons_n: "धडे", finished_n: "सर्व पूर्ण", open_tasks: "उघडी कामे", late_tasks: "उशीर",
		did_extra: "＋ मी जादा काम केले", to_do: "करायचे", move_to: "या दिवशी हलवा", moved: "हलवले", load: "भार",
		routine: "आठवड्याचे ठरलेले काम", new_today: "आजचे नवीन", to_call: "कॉल करायचे", lead_saved: "लीड ERPNext CRM → Leads मध्ये सेव्ह झाली",
		lead_no: "लीड नं.", owner: "मालक", call_now: "आता कॉल करा", open_lead: "लीड उघडा", another_lead: "दुसरी लीड",
		camera: "कॅमेरा", gallery: "गॅलरी / स्क्रीनशॉट", pdf_file: "PDF / फाईल", retake: "पुन्हा घ्या", remove: "काढा",
		uploading: "पाठवत आहे…", uploaded: "पाठवले ✓", upload_retry: "नेटवर्क कमी, पुन्हा प्रयत्न…",
		open_chrome: "माईक / कॅमेरा Chrome मध्ये नीट चालतात. SK App Chrome मध्ये उघडण्यासाठी येथे दाबा.",
		cash_today: "कॅश / बँक", to_collect: "येणे (Receivables)", to_pay: "देणे (Payables)", bills_to_post: "खरेदी बिल आणि डेबिट नोट",
		invoices: "विक्री बिल आणि क्रेडिट नोट", expenses: "जर्नल व्हाउचर", dir_expenses: "प्रत्यक्ष आणि अप्रत्यक्ष खर्च",
		segment_pnl: "विभागवार नफा-तोटा", month_close: "महिनावार अहवाल", ledger_wise: "लेजरनुसार", work_tab: "करायचे",
		opening: "सुरुवातीची शिल्लक", closing: "शिल्लक", dr: "Dr", cr: "Cr", bills_n: "बिले", returns_n: "डेबिट / क्रेडिट नोट",
		drafts_n: "ड्राफ्ट", net: "निव्वळ", direct: "प्रत्यक्ष", indirect: "अप्रत्यक्ष", gross: "एकूण नफा", net_pl: "निव्वळ नफा-तोटा",
		common_cost: "सामायिक (विभागले नाही)", closing_list: "क्लोजिंग यादी", month_pl: "महिनावार नफा-तोटा", inv_n: "बिले",
		team_box: "टीम मेलबॉक्स", my_customers: "माझे ग्राहक", st_New: "नवीन", st_Taken: "घेतले", st_Replied: "उत्तर दिले",
		"st_Lead made": "लीड बनली", "st_Not a lead": "लीड नाही", take: "मी उत्तर देतो", give_to: "यांना द्या", make_lead_btn: "लीड बनवा",
		not_lead: "लीड नाही", reply: "उत्तर", reply_q: "तुमचे उत्तर (बोला किंवा लिहा)", by_word: "", lead_sources: "लीड स्रोत",
		upload_list: "IndiaMART / JustDial यादी (Excel) अपलोड करा", leads_made: "नवीन लीड", added_old: "जुन्या लीडमध्ये जोडले",
		skipped_n: "मोबाईल / ईमेल नसलेल्या ओळी", last_check: "शेवटची मेल तपासणी", check_now: "आता मेल तपासा",
		pull_api: "IndiaMART Pull API: पैशाची सेवा, टप्पा 2", mailboxes: "मेलबॉक्स", set_up: "तयार", not_set_up: "ERPNext मध्ये अजून नाही",
		on_word: "चालू", off_word: "बंद", this_month2: "या महिन्यात", source_word: "स्रोत",
		erp_roles: "ERPNext रोल", upload_failed: "फाईल पाठवता आली नाही.", draft_back: "सेव्ह न केलेला फॉर्म परत भरला.",
	});
	// change list point 2: Cabin / Non-Cabin customers
	Object.assign(T.English, {
		customers: "Customers", tag_tally: "Tag from Tally (Cabin / Non-Cabin sales)", seg_not_set: "Segment not set", seg_all: "All", seg_cabin: "Cabin", seg_noncabin: "Non-Cabin",
		pick_segment: "Please pick the segment (Cabin or Non-Cabin)", orders_word: "orders", tag_hint: "Tap the segment: the right team then sees this customer.",
		seen_by_mgmt: "Customers without a segment are seen by Management only until tagged.",
		"Cabin": "Cabin", "Non-Cabin": "Non-Cabin",
	});
	Object.assign(T.Marathi, {
		customers: "ग्राहक", tag_tally: "Tally प्रमाणे विभाग लावा", seg_not_set: "विभाग ठरवलेला नाही", seg_all: "सर्व", seg_cabin: "केबिन", seg_noncabin: "नॉन-केबिन",
		pick_segment: "कृपया विभाग निवडा (केबिन की नॉन-केबिन)", orders_word: "ऑर्डर", tag_hint: "विभागावर टॅप करा: योग्य टीमला हा ग्राहक दिसेल.",
		seen_by_mgmt: "विभाग नसलेले ग्राहक टॅग होईपर्यंत फक्त व्यवस्थापनाला दिसतात.",
		"Cabin": "केबिन", "Non-Cabin": "नॉन-केबिन",
	});
	// change list point 3: CEO "View Member App"
	Object.assign(T.English, {
		view_member: "View Member App", viewing: "Viewing", viewing_app: "app", exit_view: "Exit", view_only: "View only: nothing is saved, sent or called in the member's name",
		idea_q: "💡 Your idea for this page (speak or type)", idea_sent: "Idea sent to the AI & ERP desk", last_active: "last active",
		view_hint: "Tap a member: the app opens exactly as they see it, with their data. View only.",
	});
	Object.assign(T.Marathi, {
		view_member: "सदस्याचे ॲप पहा", viewing: "पाहत आहे:", viewing_app: "यांचे ॲप", exit_view: "बाहेर", view_only: "फक्त पाहणे: सदस्याच्या नावाने काहीही सेव्ह, पाठवले किंवा कॉल होत नाही",
		idea_q: "💡 या पानासाठी तुमची कल्पना (बोला किंवा लिहा)", idea_sent: "कल्पना AI & ERP डेस्ककडे पाठवली", last_active: "शेवटचे सक्रिय",
		view_hint: "सदस्यावर टॅप करा: ॲप त्यांना दिसते तसेच, त्यांच्या माहितीसह उघडते. फक्त पाहणे.",
	});
	// change list point 13: CEO live dashboards
	Object.assign(T.English, {
		dash_overview: "CEO Overview", dash_daily_review: "Daily Review", dash_sales: "Sales", dash_marketing: "Marketing", dash_machine_shifting: "Machine Shifting", dash_job_work: "Job Work", dash_cr100: "100 Cr", dash_finance: "Finance", dash_manufacturing: "Manufacturing", dash_purchase: "Purchase", dash_store: "Store", dash_quality: "Quality", dash_hr: "HR", dash_ai: "AI & ERP",
		live_dash: "📊 Live dashboards (ERPNext)", vs_last: "last month", dash_open: "Tap a number to see its list, then a row for the full record.",
		swipe_hint: "Swipe left / right for the next page", open_desk: "Open in ERPNext",
	});
	Object.assign(T.Marathi, {
		dash_overview: "CEO आढावा", dash_daily_review: "दैनिक आढावा", dash_sales: "विक्री", dash_marketing: "मार्केटिंग", dash_machine_shifting: "मशीन शिफ्टिंग", dash_job_work: "जॉब वर्क", dash_cr100: "100 कोटी", dash_finance: "वित्त", dash_manufacturing: "उत्पादन", dash_purchase: "खरेदी", dash_store: "स्टोअर", dash_quality: "गुणवत्ता", dash_hr: "एचआर", dash_ai: "AI आणि ERP",
		live_dash: "📊 लाईव्ह डॅशबोर्ड (ERPNext)", vs_last: "मागील महिना", dash_open: "यादीसाठी आकड्यावर टॅप करा, पूर्ण माहितीसाठी ओळीवर.",
		swipe_hint: "पुढील पानासाठी डावीकडे / उजवीकडे सरकवा", open_desk: "ERPNext मध्ये उघडा",
	});
	// change list point 5: customer complaints
	Object.assign(T.English, {
		complaints: "Complaints", new_complaint: "＋ New complaint", cp_mine: "My complaints", cp_to_fix: "To fix", cp_all: "All",
		cp_customer: "Customer (type a few letters)", cp_order: "Order / delivery", cp_type: "Complaint type", cp_what: "What is wrong (speak or write)",
		cp_files: "Photo / video / file", cp_sent: "Complaint sent to", cp_accept: "Accept", cp_fix_by: "Fix by", cp_fixed: "Fixed",
		cp_after: "After-fix photo", cp_done_what: "What was done", cp_ok: "Customer OK", cp_not_ok: "Customer NOT OK", cp_wa: "WhatsApp update to customer",
		cp_late: "late", st_Registered: "Registered", st_Accepted: "Accepted", st_Fixed: "Fixed", st_Closed: "Closed", "st_Not OK": "Not OK",
		cp_pick_customer: "Please pick the customer from the list", cp_note: "Customer says (speak or write)",
	});
	Object.assign(T.Marathi, {
		complaints: "तक्रारी", new_complaint: "＋ नवीन तक्रार", cp_mine: "माझ्या तक्रारी", cp_to_fix: "दुरुस्त करायच्या", cp_all: "सर्व",
		cp_customer: "ग्राहक (काही अक्षरे लिहा)", cp_order: "ऑर्डर / डिलिव्हरी", cp_type: "तक्रारीचा प्रकार", cp_what: "काय चुकले (बोला किंवा लिहा)",
		cp_files: "फोटो / व्हिडिओ / फाईल", cp_sent: "तक्रार पाठवली:", cp_accept: "स्वीकारा", cp_fix_by: "दुरुस्ती तारीख", cp_fixed: "दुरुस्त झाले",
		cp_after: "दुरुस्तीनंतरचा फोटो", cp_done_what: "काय केले", cp_ok: "ग्राहक समाधानी", cp_not_ok: "ग्राहक समाधानी नाही", cp_wa: "ग्राहकाला WhatsApp अपडेट",
		cp_late: "उशीर", st_Registered: "नोंदवली", st_Accepted: "स्वीकारली", st_Fixed: "दुरुस्त", st_Closed: "बंद", "st_Not OK": "समाधानी नाही",
		cp_pick_customer: "कृपया यादीतून ग्राहक निवडा", cp_note: "ग्राहक काय म्हणाला (बोला किंवा लिहा)",
	});
	// change list point 7: FAQ per function
	Object.assign(T.English, { faq_ask: "Ask a question", faq_q: "Your question (speak or type)", faq_sent: "Question sent to", faq_to_answer: "Questions for you to answer",
		faq_answer: "Your answer (speak or type)", faq_add: "Add to the FAQ for everyone" });
	Object.assign(T.Marathi, { faq_ask: "प्रश्न विचारा", faq_q: "तुमचा प्रश्न (बोला किंवा लिहा)", faq_sent: "प्रश्न पाठवला:", faq_to_answer: "तुम्ही उत्तर द्यायचे प्रश्न",
		faq_answer: "तुमचे उत्तर (बोला किंवा लिहा)", faq_add: "सर्वांसाठी FAQ मध्ये जोडा" });
	// change list point 8: product cards
	Object.assign(T.English, { product_asked: "Product asked (optional)", products_for: "Products for this customer", card_missing: "Card not made yet (photos, sizes, brochure needed)",
		brochure: "Brochure" });
	Object.assign(T.Marathi, { product_asked: "विचारलेले उत्पादन (ऐच्छिक)", products_for: "या ग्राहकासाठी उत्पादने", card_missing: "कार्ड अजून बनले नाही (फोटो, साईझ, ब्रोशर हवे)",
		brochure: "ब्रोशर" });
	// change list point 1: check before saving
	Object.assign(T.English, { check_before: "Check before saving (as in ERPNext)", check_red: "✗ Red lines are needed by ERPNext: please fill or correct them, then Save.",
		check_ok: "Looks right. Tap a suggestion to use it, then Save.", goes_to: "Goes to", photo_dark: "Photo is dark: retake in light?", photo_blur: "Photo looks blurred: retake?" });
	Object.assign(T.Marathi, { check_before: "सेव्ह करण्यापूर्वी तपासा (ERPNext प्रमाणे)", check_red: "✗ लाल ओळी ERPNext ला हव्या आहेत: भरा किंवा दुरुस्त करा, मग सेव्ह करा.",
		check_ok: "बरोबर दिसते. सूचना वापरायची असल्यास टॅप करा, मग सेव्ह करा.", goes_to: "कुठे जाईल", photo_dark: "फोटो अंधारात आहे: प्रकाशात पुन्हा घ्या?", photo_blur: "फोटो धूसर आहे: पुन्हा घ्या?" });
	// change list point 16 + HR draft Rev 2: attendance (Optick / thumb), leave, expenses
	Object.assign(T.English, { attendance: "Attendance", leave_expense: "Leave & Expense", att_in: "In", att_out: "Out", att_no_in: "No check-in yet",
		att_wait_file: "Check-in not here yet (HR uploads the Optick file)", att_leave: "On leave", att_off: "Day off", att_late: "late",
		att_my_month: "My attendance", att_present: "Present", att_absent: "Absent", att_half: "Half day", att_missed: "If Optick missed me",
		att_selfie: "🤳 Selfie check-in (backup)", att_ask_fix: "✋ Ask HR to fix", att_fix_what: "What to fix (e.g. I came at 9:05, Optick did not read)",
		att_today: "Today", att_month: "Month", att_upload: "Upload", att_late_after: "Late after", att_no_checkin: "No check-in",
		att_fix_req: "Fix requests", att_file: "Optick / thumb machine file (Excel or CSV)", att_device: "Machine", att_check_file: "Check file",
		att_save: "✅ Save check-ins", att_rows: "rows", att_matched: "matched", att_not_found: "not found: pick the employee once",
		att_missed_out: "missed out-punch (Optick 23:00 Auto Checkout)", att_already: "already in ERPNext", att_made: "check-ins saved",
		att_att_made: "attendance marked", att_reason: "Reason (speak or write)", att_fix: "Fix", att_status: "Status", att_skip: "skip",
		lv_leave: "Leave", lv_expense: "Expense", lv_to_approve: "To approve", lv_type: "Leave type", lv_from: "From", lv_to: "To",
		lv_half: "Half day", lv_reason: "Reason (speak or write)", lv_apply: "Apply for leave", lv_sent: "Sent for approval to", lv_left: "left",
		lv_mine: "My leave", ex_type: "Expense type", ex_amount: "Amount (Rs)", ex_date: "Date", ex_bill: "Bill photo", ex_note: "What for (speak or write)",
		ex_claim: "Claim expense", ex_mine: "My expense claims", lv_approve: "✓ Approve", lv_reject: "✗ Reject", ex_posted: "Approved: Accounts pays it",
		no_employee: "Your login is not linked to an ERPNext Employee yet. Please ask HR." });
	Object.assign(T.Marathi, { attendance: "हजेरी", leave_expense: "रजा व खर्च", att_in: "आत", att_out: "बाहेर", att_no_in: "अजून हजेरी नाही",
		att_wait_file: "हजेरी अजून आली नाही (HR ऑप्टिक फाईल अपलोड करते)", att_leave: "रजेवर", att_off: "सुट्टी", att_late: "उशीर",
		att_my_month: "माझी हजेरी", att_present: "हजर", att_absent: "गैरहजर", att_half: "अर्धा दिवस", att_missed: "ऑप्टिकने हजेरी घेतली नाही तर",
		att_selfie: "🤳 सेल्फी हजेरी (बॅकअप)", att_ask_fix: "✋ HR ला दुरुस्ती सांगा", att_fix_what: "काय दुरुस्त करायचे (उदा. मी 9:05 ला आलो, ऑप्टिकने घेतले नाही)",
		att_today: "आज", att_month: "महिना", att_upload: "अपलोड", att_late_after: "उशीर नंतर", att_no_checkin: "हजेरी नाही",
		att_fix_req: "दुरुस्ती विनंत्या", att_file: "ऑप्टिक / थंब मशीन फाईल (Excel किंवा CSV)", att_device: "मशीन", att_check_file: "फाईल तपासा",
		att_save: "✅ हजेरी सेव्ह करा", att_rows: "ओळी", att_matched: "जुळले", att_not_found: "सापडले नाही: एकदा कर्मचारी निवडा",
		att_missed_out: "बाहेर जाण्याची नोंद नाही (ऑप्टिक 23:00 Auto Checkout)", att_already: "आधीच ERPNext मध्ये", att_made: "हजेरी नोंदी सेव्ह",
		att_att_made: "हजेरी लावली", att_reason: "कारण (बोला किंवा लिहा)", att_fix: "दुरुस्त करा", att_status: "स्थिती", att_skip: "वगळा",
		lv_leave: "रजा", lv_expense: "खर्च", lv_to_approve: "मंजुरीसाठी", lv_type: "रजेचा प्रकार", lv_from: "पासून", lv_to: "पर्यंत",
		lv_half: "अर्धा दिवस", lv_reason: "कारण (बोला किंवा लिहा)", lv_apply: "रजेचा अर्ज करा", lv_sent: "मंजुरीसाठी पाठवले:", lv_left: "शिल्लक",
		lv_mine: "माझ्या रजा", ex_type: "खर्चाचा प्रकार", ex_amount: "रक्कम (रु)", ex_date: "तारीख", ex_bill: "बिलाचा फोटो", ex_note: "कशासाठी (बोला किंवा लिहा)",
		ex_claim: "खर्च मागा", ex_mine: "माझे खर्च", lv_approve: "✓ मंजूर", lv_reject: "✗ नामंजूर", ex_posted: "मंजूर: अकाउंट्स पैसे देईल",
		no_employee: "तुमचे लॉगिन अजून ERPNext कर्मचाऱ्याशी जोडलेले नाही. कृपया HR ला सांगा." });
	Object.assign(T.English, { send_design: "Send to design (AI drawing)", design_sent: "Sent to design as deal", design_not_sent: "Not sent to design:" });
	Object.assign(T.Marathi, { send_design: "डिझाईनला पाठवा (AI ड्रॉइंग)", design_sent: "डिझाईनला डील म्हणून पाठवले", design_not_sent: "डिझाईनला पाठवले नाही:" });
	T.English.mic_blocked = "Microphone / camera is blocked. Open Chrome → ⋮ → Settings → Site settings → Microphone (or Camera) → this site → Allow. Then come back and tap 🎤 again.";
	T.Marathi.mic_blocked = "माईक / कॅमेरा बंद आहे. Chrome → ⋮ → Settings → Site settings → Microphone (किंवा Camera) → ही साईट → Allow. मग परत येऊन 🎤 दाबा.";
	T.English.mic_network = "Voice needs internet. Check mobile data, or use the 🎤 on your phone keyboard (works offline for English).";
	T.Marathi.mic_network = "आवाजासाठी इंटरनेट हवे. मोबाईल डेटा तपासा, किंवा कीबोर्डवरील 🎤 वापरा.";
	Object.assign(T.English, { lk_locked: "Locked", lk_touch: "Touch finger or look at the phone", lk_open_face: "Open with face / finger",
		lk_ask_ceo: "Not working or new phone? Ask the CEO to reset it.", lk_pin: "Your PIN", lk_open: "Open",
		lk_cancelled: "Not checked. Tap the button and touch the finger sensor or look at the phone.",
		lk_setup: "Set up face / finger", lk_setup_why: "From now on the app opens only with your phone's fingerprint or face lock, no PIN. Your finger and face stay on the phone; nothing is sent.",
		lk_setup_now: "Set up now", lk_setup_done: "Face / finger set up. The PIN is not needed any more.",
		lk_reset: "Reset face / finger", lk_reset_q: "Reset face / finger? The person opens with the PIN once and sets it up again.", lk_reset_done: "Face / finger reset" });
	Object.assign(T.Marathi, { lk_locked: "लॉक आहे", lk_touch: "बोट लावा किंवा फोनकडे पहा", lk_open_face: "चेहरा / बोटाने उघडा",
		lk_ask_ceo: "चालत नाही किंवा नवीन फोन? CEO ला रीसेट करायला सांगा.", lk_pin: "तुमचा पिन", lk_open: "उघडा",
		lk_cancelled: "तपासले नाही. बटण दाबा आणि बोट लावा किंवा फोनकडे पहा.",
		lk_setup: "चेहरा / बोट लॉक सुरू करा", lk_setup_why: "आता पासून ॲप फक्त फोनच्या बोट / चेहरा लॉकने उघडेल, पिन नाही. बोट आणि चेहरा फोनवरच राहतात; काहीही पाठवले जात नाही.",
		lk_setup_now: "आत्ता सुरू करा", lk_setup_done: "चेहरा / बोट लॉक तयार. आता पिन लागणार नाही.",
		lk_reset: "चेहरा / बोट रीसेट", lk_reset_q: "चेहरा / बोट रीसेट करायचे? ती व्यक्ती एकदा पिनने उघडून परत सुरू करेल.", lk_reset_done: "चेहरा / बोट रीसेट झाले" });
	const ICON = {
		my_day: "☀️", my_leads: "🎯", my_deals: "🤝", my_kpi: "⭐", work_book: "📒", dsi: "💡", problem: "🚩",
		job_cards: "🛠️", inspections: "✅", stock_alerts: "📦", material_requests: "🧾", invoice_photo: "📷",
		collections: "💰", team_scorecards: "👥", site_checklist: "📋", ceo_view: "📊",
		calendar: "📅", follow_up: "🔔", new_lead: "➕", training: "🎓", day_report: "📝", team_reports: "🗂️",
		calls: "📞", whatsapp: "💬", mail: "✉️", reminders: "⏰", library: "🏢", logins: "🔑", team_leads: "👥",
		stock_check: "📦", receive: "🚚", issue: "📤", store_requests: "📋", dispatch: "🚛", low_stock: "⚠️", stock_count: "🔢", new_item: "🆕",
		buy_requests: "📋", get_rates: "💬", compare: "⚖️", po_follow_up: "📞", suppliers: "🏭", bills: "📷", last_rates: "💹", po_approvals: "✅",
		order_board: "🏗️", job_cards: "🛠️", my_jobs: "🛠️", need_material: "📦", progress_photos: "📸", ready_dispatch: "🚛", non_conformance: "❗",
		my_fixes: "🔧", inspect: "🔍", final_check: "🏁",
		improvement_inbox: "📥", dept_visits: "🏢", erp_gaps: "🧩", app_users: "👥", change_list: "📋", projects: "🗂️",
		training_progress: "📈", erpnext_desk: "🖥️", lead_sources: "🧲", dir_expenses: "🧾", customers: "🏠", view_member: "👀", complaints: "🛠️", attendance: "🕘", leave_expense: "🌴",
		dash_overview: "🏁", dash_daily_review: "🗓️", dash_sales: "💼", dash_marketing: "📣", dash_machine_shifting: "🏗️", dash_job_work: "⚙️", dash_cr100: "🎯", dash_finance: "💰", dash_manufacturing: "🏭", dash_purchase: "🛒", dash_store: "📦", dash_quality: "✅", dash_hr: "👥", dash_ai: "🤖",
		cash_today: "💰", to_collect: "📥", to_pay: "📤", pay_approvals: "✅", bills_to_post: "🧾", invoices: "🧮", expenses: "💸", segment_pnl: "📊", month_close: "🗓️",
	};
	const t = (k) => (T[state.lang] || T.English)[k] || k;
	const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

	// while the CEO views a member's app every reading screen runs as the member (their own permissions); saving is blocked
	const VIEW_OWN = new Set(["view_members", "view_suggest", "report_screen_error"]);
	async function call(method, args, post, background) {
		if (state.viewAs && !VIEW_OWN.has(method)) {
			if (post) throw new Error(t("view_only"));
			args = { member: state.viewAs.user, method, args: JSON.stringify(args || {}), view: state.view };
			method = "view_as";
		}
		const opts = { headers: { Accept: "application/json", "X-Frappe-CSRF-Token": CSRF }, credentials: "same-origin" };
		if (background) opts.headers["X-SK-Background"] = "1"; // the minute check does not keep the app unlocked
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
			if (String(msg).includes("SK_LOCKED")) { if (!post && !background) lockHit = true; showLock(); throw new Error(t("lk_locked")); }
			throw new Error(String(msg).replace(/<[^>]*>/g, "")); // ERPNext messages carry <strong> tags
		}
		return data.message;
	}

	async function upload(file) {
		const fd = new FormData();
		fd.append("file", file, file.name);
		fd.append("is_private", "1");
		const res = await fetch("/api/method/upload_file", { method: "POST", body: fd, headers: { "X-Frappe-CSRF-Token": CSRF }, credentials: "same-origin" });
		const data = await res.json().catch(() => ({}));
		if (!res.ok) {
			let msg = "";
			try { msg = JSON.parse(JSON.parse(data._server_messages)[0]).message; } catch (e) { msg = data.exception || ""; }
			throw new Error((t("upload_failed") + " " + String(msg).replace(/<[^>]*>/g, "")).trim());
		}
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
			// number / mobile boxes: spoken words become digits ("दहा" → 10, "साडे तीन" → 3.5, "10 kilo" → 10)
			if (L.got && (input.type === "number" || input.type === "tel" || /numeric|decimal|tel/.test(input.inputMode || ""))) {
				input.value = input.type === "tel" ? spokenDigits(L.got) : spokenNumber(L.got);
			}
			// search-and-pick boxes search after speaking too, like after typing
			input.dispatchEvent(new Event("input", { bubbles: true }));
			if (listening === L) listening = null;
			if (L.error && L.error !== "aborted") toast(micError(L.error), true);
			else if (!L.got && !L.error) toast(t("mic_nospeech"), true);
		};
		try { rec.start(); } catch (e) { listening = null; toast(micError(""), true); }
	}

	const MR_DIGITS = { "०": 0, "१": 1, "२": 2, "३": 3, "४": 4, "५": 5, "६": 6, "७": 7, "८": 8, "९": 9 };
	const WORD_NUM = { zero: 0, one: 1, two: 2, three: 3, four: 4, five: 5, six: 6, seven: 7, eight: 8, nine: 9, ten: 10,
		eleven: 11, twelve: 12, thirteen: 13, fourteen: 14, fifteen: 15, sixteen: 16, seventeen: 17, eighteen: 18, nineteen: 19,
		twenty: 20, thirty: 30, forty: 40, fifty: 50, sixty: 60, seventy: 70, eighty: 80, ninety: 90, hundred: 100,
		"शून्य": 0, "एक": 1, "दोन": 2, "तीन": 3, "चार": 4, "पाच": 5, "सहा": 6, "सात": 7, "आठ": 8, "नऊ": 9, "दहा": 10,
		"अकरा": 11, "बारा": 12, "तेरा": 13, "चौदा": 14, "पंधरा": 15, "सोळा": 16, "सतरा": 17, "अठरा": 18, "एकोणीस": 19, "वीस": 20,
		"पंचवीस": 25, "तीस": 30, "चाळीस": 40, "पन्नास": 50, "साठ": 60, "सत्तर": 70, "ऐंशी": 80, "नव्वद": 90, "शंभर": 100 };
	const MULT = { hundred: 100, thousand: 1000, lakh: 100000, "शंभर": 100, "हजार": 1000, "लाख": 100000 };
	function mrToAscii(text) { return String(text).replace(/[०-९]/g, (c) => MR_DIGITS[c]); }
	// "10 kilo" → 10, "two hundred fifty" → 250, "साडे तीन" → 3.5, "दीड" → 1.5, "अडीच" → 2.5
	function spokenNumber(text) {
		const s = mrToAscii(text).toLowerCase().replace(/,/g, "");
		const m = s.match(/-?\d+(\.\d+)?/);
		let half = /साडे|sade/.test(s) ? 0.5 : 0;
		if (/दीड/.test(s)) return "1.5";
		if (/अडीच/.test(s)) return "2.5";
		if (m) return String(Number(m[0]) + half);
		let total = 0, cur = 0, found = false;
		for (const w of s.split(/[\s-]+/)) {
			if (MULT[w] && w !== "hundred" && w !== "शंभर") { total += (cur || 1) * MULT[w]; cur = 0; found = true; }
			else if (w === "hundred" || w === "शंभर") { cur = (cur || 1) * 100; found = true; }
			else if (WORD_NUM[w] !== undefined) { cur += WORD_NUM[w]; found = true; }
			else if (w === "point" || w === "दशांश") { /* rare: ignore */ }
		}
		return found ? String(total + cur + half) : "";
	}
	// mobile numbers are spoken in groups ("98220 41234", "nine eight two two zero ..."): keep every digit in order
	function spokenDigits(text) {
		const s = mrToAscii(text).toLowerCase();
		let out = "";
		for (const w of s.split(/[\s,-]+/)) {
			if (/^\d+$/.test(w)) out += w;
			else if (WORD_NUM[w] !== undefined && WORD_NUM[w] < 10) out += WORD_NUM[w];
			else if (w === "double" && out) out += out.slice(-1);
		}
		return out;
	}
	// one mic + EN / मर switch next to any box (every 🎤 in the app uses this)
	function micBox(id, lang) {
		if (lang && !micLang[id]) micLang[id] = lang;
		return `<div class="sk-micbox"><button type="button" class="sk-mic" data-mic="${id}" title="${t("speak")}">🎤</button>
			<button type="button" class="sk-miclang" data-miclang="${id}">${(micLang[id] || (state.lang === "Marathi" ? "mr" : "en")) === "en" ? "EN" : "मर"}</button></div>`;
	}
	// mobile, e-mail and WhatsApp boxes get a 🎤 too (point 4): added after each screen is drawn
	function addMics(scope) {
		scope.querySelectorAll('input[type="tel"], input[type="email"]').forEach((inp) => {
			if (!inp.id || inp.dataset.mic === "1" || (inp.parentElement && inp.parentElement.querySelector(".sk-micbox"))) return;
			inp.dataset.mic = "1";
			inp.insertAdjacentHTML("afterend", micBox(inp.id, "en"));
			const row = inp.parentElement;
			if (row && !row.classList.contains("sk-input-row")) {
				const wrap = document.createElement("div");
				wrap.className = "sk-input-row";
				inp.before(wrap);
				wrap.append(inp, inp.nextElementSibling);
			}
		});
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
		const bar = state.viewAs ? `<div class="sk-viewbar"><span>👀 ${t("viewing")} ${esc(state.viewAs.name)} ${t("viewing_app")}</span>
			<button data-act="view-idea">💡</button><button data-act="view-exit">✕ ${t("exit_view")}</button></div>` : "";
		return bar + `<header class="sk-head">
			${state.view !== "home" ? `<button class="sk-back" data-go="home">‹</button>` : `<img src="/assets/sk_app/icons/icon-192.png" class="sk-logo" alt="SK">`}
			<div class="sk-title">${esc(title)}<small>${esc(whoAmI())}</small></div>
			<button class="sk-lang" data-act="lang">${t("lang")}</button>
		</header>`;
	}

	function fitHead() {
		const h = root.querySelector(".sk-head");
		if (h) document.body.style.paddingTop = h.offsetHeight + "px";
	}
	new MutationObserver(() => { fitHead(); addMics(root); }).observe(root, { childList: true, subtree: true });
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
		// point 15: red = late or must-do not done, amber = due today, blue = new, green ✓ = all done today
		const badge = { ...(h.badges || {}) };
		if (dueNow().length) badge.reminders = { n: dueNow().length, c: "red" };
		if (!badge.follow_up && (h.new_files || []).length) badge.follow_up = { n: h.new_files.length, c: "blue" };
		if (h.must_set_pin && !state.viewAs) return renderSetPin();
		const tile = (k) => {
			const m = badge[k];
			const o = m && typeof m === "object" ? m : m ? { n: m, c: "red" } : null;
			const dot = !o ? "" : o.c === "green" ? `<b class="sk-dot green">✓</b>` : `<b class="sk-dot ${o.c}">${esc(o.n)}</b>`;
			return `<button class="sk-tile ${o ? "c-" + o.c : ""} ${o && o.blink ? "blink" : ""}" data-go="${k}"><span class="sk-tile-icon">${ICON[k] || "•"}</span><span>${t(k)}</span>${dot}</button>`;
		};
		const plain = (keys) => `<div class="sk-tiles small">${keys.map(tile).join("")}</div>`;
		// point 13: the CEO's live dashboards sit in their own row on top
		const tiles = (keys) => {
			const dash = keys.filter((k) => k.startsWith("dash_"));
			const rest = keys.filter((k) => !k.startsWith("dash_"));
			return (dash.length ? `<h3 class="sk-h sk-fn-row">${t("live_dash")}</h3>${plain(dash)}${rest.length ? `<div class="sk-gap"></div>` : ""}` : "") + (rest.length ? plain(rest) : "");
		};
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

	// The CEO (point 20; HR until then): every login is made from the person's mobile number; the app gives a first PIN
	let loginOpts = null;
	async function renderLogins() {
		const people = await call("hr_people");
		root._people = people;
		const none = people.filter((p) => p.state === "none");
		const fnLabel = (f) => { const o = loginOpts && loginOpts.functions.find((x) => x.name === f); return o ? (o.label[state.lang] || o.label.English || f) : f; };
		const row = (p, i) => {
			const sub = [p.designation, p.mobile, p.functions.map(fnLabel).join(" + ")].filter(Boolean).join(" · ") +
				(p.roles && p.roles.length ? ` · ${t("erp_roles")}: ${p.roles.join(", ")}` : "");
			const warn = p.state === "active" && p.must_set_pin ? ` <span class="sk-due">${t("pin_set_pending")}</span>` : "";
			const btn = p.state === "none" ? `<button class="sk-chip on" data-act="login-new" data-i="${i}">+ ${t("make_login")}</button>`
				: p.state === "closed" ? `<button class="sk-chip" data-act="login-new" data-i="${i}">↺ ${t("make_login")}</button>`
				: `<button class="sk-chip" data-act="login-new" data-i="${i}">✏️ ${t("edit_login")}</button>
					<button class="sk-chip" data-act="login-reset" data-i="${i}">🔑 ${t("reset_pin")}</button>
					<button class="sk-chip" data-act="login-face" data-i="${i}">🙂 ${t("lk_reset")}</button>
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
			<button class="sk-btn wide" data-act="login-bulk-open">📋 ${t("bulk_logins")}</button>
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
			<p class="sk-big">${t("mobile")}: <b>${esc(r.mobile || "")}</b><br>${r.pin ? `${t("first_pin")}: <b>${esc(r.pin)}</b>` : t("keeps_password")}</p>
			<p class="sk-note">${t("pin_note")}</p>
			<button class="sk-btn ok wide" data-act="login-wa">💬 ${t("send")} WhatsApp</button>
			<button class="sk-btn wide" data-act="close-sheet">${t("done")}</button>`);
	}

	// many logins at once: HR pastes the staff list, one line per person
	function bulkSheet() {
		sheet(`<h3 class="sk-h">📋 ${t("bulk_logins")}</h3><p class="sk-note">${t("bulk_help")}</p>
			<textarea id="g-bulk" class="sk-bulk" rows="10" placeholder="Yogesh B. | 9970960806 | Stores | HR-EMP-00009"></textarea>
			<button class="sk-btn ok wide" data-act="login-bulk">${t("make_logins")}</button><button class="sk-btn wide" data-act="close-sheet">${t("back")}</button>`);
	}
	function bulkResult(rows) {
		root._bulk = rows;
		const ok = rows.filter((r) => !r.error).length;
		root.innerHTML = header(t("bulk_logins")) + `<main><p class="sk-note">✅ ${ok} / ${rows.length} ${t("logins_made")}. ${t("bulk_pin_note")}</p>
			<ul class="sk-list">${rows.map((r, i) => `<li class="sk-item ${r.error ? "k-lead_new" : ""}"><div><div class="sk-item-title">${esc(r.full_name)}</div>
				<div class="sk-item-meta">${esc(r.mobile)} · ${r.error ? `<span class="sk-due">${esc(r.error)}</span>` : r.pin ? `${t("first_pin")}: <b>${esc(r.pin)}</b>` : t("keeps_password")}</div></div>
				${r.pin ? `<button class="sk-chip on" data-act="login-bulk-wa" data-i="${i}">💬 WhatsApp</button>` : ""}</li>`).join("")}</ul>
			<button class="sk-btn wide" data-go="logins">${t("back")}</button></main>`;
	}

	function itemRow(i) {
		const due = i.due ? `<span class="sk-due">${t("due")} ${esc(i.due.slice(5, 16))}</span>` : "";
		const link = i.doctype && i.name ? (i.doctype.startsWith("CRM ") ? `/crm/${i.doctype === "CRM Lead" ? "leads" : "deals"}/${encodeURIComponent(i.name)}` : `/app/${i.doctype.toLowerCase().replace(/ /g, "-")}/${encodeURIComponent(i.name)}`) : "";
		let open = link ? `<a class="sk-open" href="${link}">›</a>` : "";
		if (i.doctype && i.doctype.startsWith("CRM ") && i.name) open = `<button class="sk-open" data-open="${esc(i.doctype)}" data-name="${esc(i.name)}">›</button>`;
		if (i.kind === "day_report") open = `<button class="sk-open" data-go="day_report">›</button>`;
		if (i.kind === "send_file") open = `<button class="sk-open" data-open="${esc(i.ref_doctype)}" data-name="${esc(i.ref_name)}">›</button>`;
		return `<li class="sk-item k-${esc(i.kind)}"><div><div class="sk-item-title">${esc(i.title)}</div><div class="sk-item-meta">${i.kind === "deal" && i.customer && i.customer !== i.title ? `👤 ${esc(i.customer)} · ` : ""}${i.kind === "deal" && i.status ? esc(i.status) + " · " : ""}${esc(i.kind.replace("_", " "))} · ${esc(i.minutes)} ${t("min")} ${due}</div></div>${open}</li>`;
	}

	async function renderMyDay() {
		const d = await call("my_day");
		if (!state.card || Date.now() - new Date(String(state.card.slot_start).replace(" ", "T")).getTime() > 10 * 60 * 1000) {
			state.card = await call("next_card", {}, true).catch(() => state.card);
		}
		const done = (d.done || []).map((x) => `<li class="sk-item k-done"><div><div class="sk-item-title">✓ ${esc(x.title)}</div><div class="sk-item-meta">${esc(hm(x.time))}</div></div></li>`).join("");
		S.att = d.attendance;
		root.innerHTML = header(t("my_day")) + `<main>${attLine(d.attendance)}${cardHtml(state.card || d.card)}
			<button class="sk-btn go wide" data-go="work_book">${t("did_extra")}</button>
			<h3 class="sk-h">${t("to_do")}</h3><ul class="sk-list">${d.items.map(itemRow).join("") || `<li class="sk-empty">${t("nothing")}</li>`}</ul>
			<h3 class="sk-h">✓ ${t("done_today")}</h3><ul class="sk-list">${done || `<li class="sk-empty">—</li>`}</ul></main>`;
	}

	// point 12: My Leads has tabs New today (the lead just made is on top, NEW) · To call · All
	let leadTab = "new_today";
	async function renderLeads(which) {
		const d = await call("my_leads");
		let rows = which === "my_deals" ? d.deals : d.leads;
		let tabs = "";
		if (which === "my_leads") {
			const today = new Date().toISOString().slice(0, 10);
			const local = (x) => { const c = new Date(String(x.created || "").replace(" ", "T")); return isNaN(c) ? "" : `${c.getFullYear()}-${pad2(c.getMonth() + 1)}-${pad2(c.getDate())}`; };
			const now = new Date(); const day = `${now.getFullYear()}-${pad2(now.getMonth() + 1)}-${pad2(now.getDate())}`;
			const groups = {
				new_today: rows.filter((r) => local(r) === day || (r.created || "").slice(0, 10) === today).sort((a, b) => String(b.created).localeCompare(String(a.created))),
				to_call: rows.filter((r) => r.kind === "lead_new" || (r.due && new Date(r.due.replace(" ", "T")) <= now)),
				all: rows,
			};
			if (!groups[leadTab].length && leadTab === "new_today") leadTab = groups.to_call.length ? "to_call" : "all";
			tabs = `<div class="cal-tabs">${Object.keys(groups).map((k) => `<button class="${leadTab === k ? "on" : ""}" data-ltab="${k}">${t(k)} ${groups[k].length}</button>`).join("")}</div>`;
			rows = groups[leadTab].map((r) => ({ ...r, title: (local(r) === day ? "🆕 " : "") + r.title }));
		}
		root.innerHTML = header(t(which)) + `<main>${tabs}<ul class="sk-list">${rows.map(itemRow).join("") || `<li class="sk-empty">${t("nothing")}</li>`}</ul></main>`;
	}

	// point 12: after Save the person sees where the lead went, its number, and what to do next
	function leadSaved(r) {
		state.view = "lead_saved";
		const now = new Date();
		root.innerHTML = header(t("new_lead")) + `<main><section class="sk-card sk-saved">
			<div class="sk-card-label">✅ ${t("lead_saved")}</div>
			<div class="sk-card-text">${esc(r.title)}${r.person && r.person !== r.title ? " · " + esc(r.person) : ""}</div>
			<div class="sk-card-meta">${t("lead_no")} <b>${esc(r.name)}</b> · ${t("owner")} ${esc((state.home && state.home.full_name) || "")} · ${pad2(now.getHours())}:${pad2(now.getMinutes())}</div>
			<div class="sk-card-meta">${[r.segment, r.source].filter(Boolean).map(esc).join(" · ")}</div></section>
			${r.mobile ? `<button class="sk-btn ok wide" data-contact="Call" data-doctype="CRM Lead" data-name="${esc(r.name)}" data-mobile="${esc(r.mobile)}">📞 ${t("call_now")}</button>
			<button class="sk-btn wide" data-contact="WhatsApp" data-doctype="CRM Lead" data-name="${esc(r.name)}" data-mobile="${esc(r.mobile)}">💬 WhatsApp</button>` : ""}
			<button class="sk-btn wide" data-open="CRM Lead" data-name="${esc(r.name)}">📄 ${t("open_lead")}</button>
			<a class="sk-btn wide" href="/crm/leads/${encodeURIComponent(r.name)}">${t("open_erp")}</a>
			<button class="sk-btn go wide" data-go="new_lead">＋ ${t("another_lead")}</button></main>`;
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
			${micBox(id)}</div></label>`;
	}

	// Every photo button (point 4): 📷 Camera · 🖼 Gallery / screenshot · 📄 PDF, a preview with ✕ / 🔄, the photo made
	// small on the phone (about 300 KB, paper stays readable) and sent at once in the background, retrying by itself
	const ANY_FILE = "image/*,application/pdf,.dwg,.dxf,.xlsx,.xls,.csv,.docx,.doc";
	function photoField(id, label, anyFile) {
		id = id || "f-photo";
		return `<div class="sk-field sk-photo"><span>${esc(label || t("photo"))}</span>
			<input id="${id}" type="file" class="sk-file" data-any="${anyFile ? 1 : 0}" accept="image/*,application/pdf" hidden>
			<div class="sk-row sk-wrap"><button type="button" class="sk-chip" data-pick="${id}" data-how="camera">📷 ${t("camera")}</button>
			<button type="button" class="sk-chip" data-pick="${id}" data-how="gallery">🖼 ${t("gallery")}</button>
			<button type="button" class="sk-chip" data-pick="${id}" data-how="file">📄 ${t("pdf_file")}</button></div>
			<div class="sk-preview" id="${id}-pv"></div></div>`;
	}
	function pickFile(id, how) {
		const inp = document.getElementById(id);
		if (!inp) return;
		inp.removeAttribute("capture");
		if (how === "camera") { inp.accept = "image/*"; inp.setAttribute("capture", "environment"); }
		else if (how === "gallery") inp.accept = "image/*";
		else inp.accept = inp.dataset.any === "1" ? ANY_FILE : "application/pdf,image/*";
		saveDraft(); // low-memory phones may close the page while the camera is open
		inp.click();
	}
	async function smallPhoto(file) {
		if (!/^image\/(jpeg|png|webp|heic|heif)/.test(file.type) || file.size < 400 * 1024) return file;
		try {
			const c = await shrink(file, 1600);
			const blob = await new Promise((ok) => c.toBlob(ok, "image/jpeg", 0.72));
			return blob && blob.size < file.size ? new File([blob], file.name.replace(/\.\w+$/, "") + ".jpg", { type: "image/jpeg" }) : file;
		} catch (e) { return file; }
	}
	async function uploadRetry(file, note) {
		for (let n = 0; ; n++) {
			try { return await upload(file); } catch (e) {
				if (n >= 3) throw e;
				if (note) note.textContent = "⏳ " + t("upload_retry");
				await new Promise((ok) => setTimeout(ok, 2000 * 2 ** n));
			}
		}
	}
	function photoPicked(inp) {
		const pv = document.getElementById(inp.id + "-pv");
		const f = inp.files[0];
		inp._up = null;
		if (!pv) return;
		if (!f) { pv.innerHTML = ""; return; }
		const isImg = f.type.startsWith("image/");
		pv.innerHTML = `${isImg ? `<img src="${URL.createObjectURL(f)}" alt="">` : `<div class="sk-filechip">📄 ${esc(f.name)} · ${Math.round(f.size / 1024)} KB</div>`}
			<div class="sk-row"><small class="sk-upnote">⏳ ${t("uploading")}</small>
			<button type="button" class="sk-chip" data-pick="${inp.id}" data-how="${isImg ? "camera" : "file"}">🔄 ${t("retake")}</button>
			<button type="button" class="sk-chip bad" data-unpick="${inp.id}">✕ ${t("remove")}</button></div>`;
		const note = pv.querySelector(".sk-upnote");
		inp._up = smallPhoto(f).then((small) => uploadRetry(small, note)).then((url) => { note.textContent = t("uploaded"); return url; },
			(e) => { note.textContent = "⚠ " + e.message; inp._up = null; throw e; });
		inp._up.catch(() => {});
	}
	// "Send to design" shows only for Cabin segments (the AI design pickup makes cabin drawings)
	root.addEventListener("change", (ev) => {
		if (ev.target.id !== "f-segment") return;
		const row = document.getElementById("f-design-row");
		const tree = (crmOpts && crmOpts.segment_tree) || {};
		if (row) row.hidden = !((tree.Cabin || []).includes(ev.target.value));
	});
	root.addEventListener("change", (ev) => { if (ev.target.classList && ev.target.classList.contains("sk-file")) { photoPicked(ev.target); photoNote(ev.target); } }, true);

	async function photoUrl(id) {
		const f = document.getElementById(id || "f-photo");
		if (!f || !f.files[0]) return null;
		return f._up ? f._up : uploadRetry(await smallPhoto(f.files[0]));
	}

	// a draft of the open form is kept on the phone; if the page was closed (camera on low-memory phones) it comes back
	const DRAFT = "sk_draft";
	function saveDraft() {
		if (!state.view || state.view === "home" || state.view === "detail") return;
		const values = {};
		root.querySelectorAll("main input[id], main textarea[id], main select[id]").forEach((el) => {
			if (el.type !== "file" && el.type !== "password" && el.value) values[el.id] = el.value;
		});
		try { localStorage.setItem(DRAFT, JSON.stringify({ view: state.view, at: Date.now(), values })); } catch (e) { /* private mode */ }
	}
	function clearDraftIfOther(view) {
		try { const d = JSON.parse(localStorage.getItem(DRAFT) || "null"); if (d && d.view !== view) clearDraft(); } catch (e) { /* fine */ }
	}
	function clearDraft() { try { localStorage.removeItem(DRAFT); } catch (e) { /* fine */ } }
	let draftTimer = null;
	root.addEventListener("input", () => { clearTimeout(draftTimer); draftTimer = setTimeout(saveDraft, 500); });
	async function restoreDraft() {
		let d = null;
		try { d = JSON.parse(localStorage.getItem(DRAFT) || "null"); } catch (e) { d = null; }
		if (!d || Date.now() - d.at > 20 * 60 * 1000 || !LIVE_VIEWS[d.view] || !Object.keys(d.values || {}).length) return;
		await go(d.view);
		Object.entries(d.values).forEach(([id, v]) => { const el = document.getElementById(id); if (el && !el.value) el.value = v; });
		toast(t("draft_back"));
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

	// Swati 26-Oct: from the Calls icon, Follow-up shows only calls to make now (new, late or due today); a search box
	// finds any customer by name, person or mobile
	let fuCalls = false, fuQuery = "";
	async function renderFollowUp() {
		let rows = await call("follow_up");
		const end = new Date(); end.setHours(23, 59, 59);
		if (fuCalls) rows = rows.filter((r) => r.mobile && (r.new || r.overdue || (r.due && new Date(String(r.due).replace(" ", "T")) <= end)));
		const q = fuQuery.toLowerCase();
		if (q) rows = rows.filter((r) => [r.title, r.person, r.mobile, r.name].join(" ").toLowerCase().includes(q));
		const li = rows.map((r) => `<li class="sk-fu ${r.overdue ? "late" : r.new ? "new" : ""}">
			<button class="sk-fu-main" data-open="${esc(r.doctype)}" data-name="${esc(r.name)}">
				<div class="sk-item-title">${esc(r.title)} ${r.new ? `<span class="sk-badge">${t("new_badge")}</span>` : ""}${r.overdue ? `<span class="sk-badge bad">${t("overdue")}</span>` : ""}</div>
				<div class="sk-item-meta">${esc(r.person || "")} · ${esc(r.status || "")} · ${r.doctype === "CRM Deal" ? t("deals") : t("leads")}</div>
				${r.next || r.due ? `<div class="sk-item-meta">${t("next")}: ${esc(r.next || "")} ${r.due ? "· " + when(r.due) : ""}</div>` : ""}
				${r.last ? `<div class="sk-item-meta">${t("last")}: ${esc(r.last.text)} · ${when(r.last.on)}</div>` : ""}
			</button>${contactButtons(r)}</li>`).join("");
		root.innerHTML = header(fuCalls ? `📞 ${t("follow_up")}` : t("follow_up")) + `<main>${fileBanners()}<button class="sk-btn go wide" data-go="new_lead">➕ ${t("new_lead")}</button>
			<div class="sk-input-row sk-gap"><input id="fu-q" type="search" placeholder="🔎 ${t("search")}" value="${esc(fuQuery)}">${micBox("fu-q")}</div>
			<ul class="sk-list sk-gap">${li || `<li class="sk-empty">${t("nothing")}</li>`}</ul></main>`;
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
			${(d.products || []).length ? `<h3 class="sk-h">${t("products_for")}</h3>${productStrip(d.products)}` : ""}
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

	// two levels like Tally (point 2): Cabin → Standard / LGSF / Modular, Non-Cabin → Machine Shifting / Job Work / Other
	function segmentSelect(id, tree, flat) {
		const groups = tree ? Object.entries(tree).map(([main, subs]) => `<optgroup label="${esc(t(main))}">${subs.map((x) => `<option>${esc(x)}</option>`).join("")}</optgroup>`).join("")
			: (flat || []).map((x) => `<option>${esc(x)}</option>`).join("");
		return `<label class="sk-field"><span>${t("segment")} *</span><select id="${id}" class="sk-select"><option value=""></option>${groups}</select></label>`;
	}

	async function renderNewLead() {
		const o = await options();
		const sel = (id, label, items) => `<label class="sk-field"><span>${esc(label)}</span><select id="${id}" class="sk-select"><option value=""></option>${(items || []).map((x) => `<option>${esc(x)}</option>`).join("")}</select></label>`;
		root.innerHTML = header(t("new_lead")) + `<main class="sk-form">
			${photoField("f-card", "📷 " + t("card_photo"))}
			${formField("f-first", t("cust_name"))}${formField("f-org", t("company"))}
			<label class="sk-field"><span>${t("mobile")}</span><div class="sk-input-row"><input id="f-mobile" type="tel"></div></label>
			<label class="sk-field"><span>${t("email")}</span><div class="sk-input-row"><input id="f-email" type="email"></div></label>
			${sel("f-source", t("source"), o.sources)}${segmentSelect("f-segment", o.segment_tree, o.segments)}${(o.products || []).length ? sel("f-product", t("product_asked"), o.products) : ""}
			<label class="sk-check" id="f-design-row" hidden><input id="f-design" type="checkbox" checked> ✏️ ${t("send_design")}</label>
			${formField("f-req", t("requirement"), true)}
			<button class="sk-btn ok wide" data-act="save-lead">${t("save")}</button>
			<details class="sk-gap"><summary>📄 ${t("upload_list")}</summary>${uploadBox()}</details></main>`;
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
			const up = (ev.target._up || uploadRetry(f)).then((u) => { cardUrl = u; return u; });
			let d = {};
			try { d = (await call("read_photo", { file_url: await up }, true)) || {}; } catch (e) { d = {}; }
			if (!fill(d)) {
				d = await readOnPhone(f, (st, pr) => { note.textContent = `⏳ ${t("photo_reading")} ${Math.round(pr * 100)}%`; });
				await up;
				if (!fill(d)) { toast(t("read_none"), true); return; }
			}
			toast(t("read_ok"));
			runCheck();
		} catch (e) { toast(t("read_none"), true); } finally { note.remove(); }
	}

	// Point 1: "Check before saving". Each value next to its ERPNext field: green ✓ fits, amber ⚠ suggestion, red ✗ needed.
	// Suggestions come from ERPNext (nearest supplier / customer, duplicate mobile or bill, GSTIN / plate format);
	// a picked suggestion is remembered for next time. The form's own Save still does the saving.
	const CHECKS = [
		{ anchor: "f-first", kind: "lead", ids: { first_name: "f-first", organization: "f-org", mobile_no: "f-mobile", email: "f-email", segment: "f-segment" },
			learn: { organization: "customer" } },
		{ anchor: "ns-name", kind: "supplier", ids: { supplier_name: "ns-name", gstin: "ns-gstin", mobile: "ns-mobile" }, learn: { supplier_name: "supplier" } },
		{ anchor: "b-no", kind: "bill", ids: { supplier: "b-sup", bill_no: "b-no", amount: "b-amt" }, learn: { supplier: "supplier" } },
		{ anchor: "d-vehicle", kind: "plate", ids: { vehicle_no: "d-vehicle" } },
	];
	const checkSpec = () => CHECKS.find((c) => document.getElementById(c.anchor));
	let checkTimer = null;
	async function runCheck() {
		const spec = checkSpec();
		if (!spec) return;
		const values = {};
		Object.entries(spec.ids).forEach(([k, id]) => { values[k] = val(id); });
		if (!Object.values(values).some(Boolean)) return;
		const d = await call("photo_check", { kind: spec.kind, values: JSON.stringify(values) }).catch(() => null);
		if (!d || !checkSpec()) return;
		let box = document.getElementById("chk-box");
		if (!box) {
			box = document.createElement("section");
			box.id = "chk-box";
			box.className = "sk-chkbox";
			const save = root.querySelector("main .sk-btn.ok, main .sk-btn.go");
			if (save) save.before(box); else root.querySelector("main").appendChild(box);
		}
		const icon = { green: "✓", amber: "⚠", red: "✗" };
		box.innerHTML = `<h3 class="sk-h">🔍 ${t("check_before")}</h3>${d.rows.map((r) => `<div class="sk-chk ${r.state}">
			<div class="sk-row"><b>${icon[r.state]}</b><span class="sk-grow">${esc(r.label)}: <b>${esc(r.value == null ? "" : r.value)}</b></span><small class="sk-muted">${esc(r.field)}</small></div>
			${r.note ? `<div class="sk-item-meta">${esc(r.note)}</div>` : ""}
			${(r.options || []).length ? `<div class="sk-row sk-wrap">${r.options.map((o) => `<button type="button" class="sk-chip" data-apply="${esc(spec.ids[r.field] || "")}" data-val="${esc(o)}" data-learn="${esc((spec.learn || {})[r.field] || "")}">${esc(o)}</button>`).join("")}</div>` : ""}
			</div>`).join("")}${d.red ? `<p class="sk-note bad">${t("check_red")}</p>` : `<p class="sk-note">${t("check_ok")}</p>`}`;
	}
	root.addEventListener("change", (ev) => {
		const spec = checkSpec();
		if (spec && Object.values(spec.ids).includes(ev.target.id)) { clearTimeout(checkTimer); checkTimer = setTimeout(runCheck, 300); }
	});
	// Bill / GST certificate photo: read it on the phone and fill the empty boxes, then check (free reader)
	async function readPaper(inp) {
		const f = inp.files[0];
		if (!f || !f.type.startsWith("image/")) return;
		const map = { "ns-photo": (d) => ({ "ns-name": d.organization, "ns-gstin": d.invoice && d.invoice.gstin, "ns-mobile": d.mobile_no }),
			"b-photo": (d) => ({ "b-no": d.invoice && d.invoice.number, "b-amt": d.invoice && d.invoice.total, "b-sup": d.organization }),
			"ex-photo": (d) => ({ "ex-amt": d.invoice && d.invoice.total }) };
		if (!map[inp.id]) return;
		try {
			const d = await readOnPhone(f, () => {});
			const gst = (d.invoice && d.invoice.gstin) || ((d.requirement || "").match(/\b\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]\b/) || [])[0];
			if (gst) d.invoice = { ...(d.invoice || {}), gstin: gst };
			Object.entries(map[inp.id](d)).forEach(([id, v]) => { const el = document.getElementById(id); if (el && v && !el.value) el.value = v; });
			runCheck();
		} catch (e) { /* reading is a help only; the person can type */ }
	}
	// Proof photos: where it goes, and a warning if it is too dark or blurred to read later
	const RECORD_OF = { receive: "Purchase Receipt (draft)", issue: "Stock Entry", dispatch: "Delivery Note", stock_count: "Stock Reconciliation",
		new_item: "Item", job_cards: "Job Card", my_jobs: "Job Card", progress_photos: "Work Order", non_conformance: "Non Conformance", my_fixes: "Non Conformance",
		inspect: "Quality Inspection", final_check: "Quality Inspection", dsi: "SK DSI Entry", problem: "SK Work Log", day_report: "SK Day Report",
		detail: "CRM note / file", new_lead: "CRM Lead", complaints: "Issue (complaint)", bills: "Purchase Invoice (draft)", suppliers: "Supplier",
		to_collect: "Payment Entry (draft)", to_pay: "Payment Entry (draft)", expenses: "Journal Entry (draft)", my_day: "Employee Checkin (selfie)",
		leave_expense: "Expense Claim" };
	async function photoQuality(file) {
		const img = await createImageBitmap(file);
		const c = document.createElement("canvas");
		c.width = 64; c.height = Math.max(1, Math.round(64 * img.height / img.width));
		const g = c.getContext("2d");
		g.drawImage(img, 0, 0, c.width, c.height);
		const px = g.getImageData(0, 0, c.width, c.height).data;
		const lum = [];
		for (let i = 0; i < px.length; i += 4) lum.push(0.299 * px[i] + 0.587 * px[i + 1] + 0.114 * px[i + 2]);
		const mean = lum.reduce((a, b) => a + b, 0) / lum.length;
		let edge = 0;
		for (let i = 1; i < lum.length; i++) edge += Math.abs(lum[i] - lum[i - 1]);
		edge /= lum.length;
		return mean < 45 ? "dark" : edge < 4 ? "blur" : "";
	}
	async function photoNote(inp) {
		const pv = document.getElementById(inp.id + "-pv");
		const f = inp.files[0];
		if (!pv || !f) return;
		const to = RECORD_OF[state.view];
		let warn = "";
		if (f.type.startsWith("image/")) { try { warn = await photoQuality(f); } catch (e) { warn = ""; } }
		const div = document.createElement("div");
		div.className = "sk-item-meta";
		div.innerHTML = [to ? `➜ ${t("goes_to")}: <b>${esc(to)}</b>` : "", warn ? `<span class="sk-amber">⚠ ${t("photo_" + warn)}</span>` : ""].filter(Boolean).join(" · ");
		if (div.innerHTML) pv.appendChild(div);
		readPaper(inp);
	}

	// Training: 1) My function (e.g. Sales Manual lessons) 2) App usage 3) customer FAQ; managers also see their team
	let lessons = [], trainTab = "My function";
	let faqQuery = "";
	async function renderTraining() {
		const mr = state.lang === "Marathi";
		const tabs = [["My function", t("my_function")], ["App usage", t("app_usage")], ["FAQ", t("faq")]];
		if (hasTeam()) tabs.push(["Team", t("team")]);
		const bar = `<div class="cal-tabs">${tabs.map(([k, l]) => `<button class="${trainTab === k ? "on" : ""}" data-train="${k}">${l}</button>`).join("")}</div>`;
		let body = "";
		if (trainTab === "FAQ") {
			// point 7: FAQ of each of my functions, search by voice, "Ask a question" to the function owner
			const d = await call("training_faq", faqQuery ? { q: faqQuery } : {});
			S.faqAsk = d.to_answer;
			body = `<div class="sk-input-row sk-gap"><input id="faq-q" type="search" placeholder="🔎 ${t("search")}" value="${esc(faqQuery)}">${micBox("faq-q")}</div>
				${d.to_answer.length ? `<h3 class="sk-h">❓ ${t("faq_to_answer")}</h3><ul class="sk-list">${d.to_answer.map((a, i) => `<li class="sk-item k-amber"><button class="sk-fu-main" data-act="faq-answer" data-i="${i}">
					<div class="sk-item-title">${esc(a.question)}</div><div class="sk-item-meta">${esc(a.by)}</div></button></li>`).join("")}</ul>` : ""}
				${libraryList(d.rows)}
				<button class="sk-btn go wide" data-act="faq-ask">❓ ${t("faq_ask")}</button>`;
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
				<div class="sk-input-row"><input id="c-${esc(r.name)}" placeholder="${t("comment")}" value="${esc(r.manager_comment || "")}">${micBox("c-" + r.name)}</div>
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
		root._week = d.days;
		let html = `<div class="sk-score sk-cal-head"><button class="sk-nav" data-week="${esc(d.start)}" data-step="-7">‹</button>
			<div><div>${t("week")} ${d.week_no} · ${esc(d.start.slice(8))}/${esc(d.start.slice(5, 7))} – ${esc(d.end.slice(8))}/${esc(d.end.slice(5, 7))}</div>
			<small>${d.orders_target ? `${t("orders")} ${lakh(d.orders)} / ${lakh(d.orders_target)} · ` : ""}${d.open_items} ${t("open_items")}</small></div>
			<button class="sk-nav" data-week="${esc(d.start)}" data-step="7">›</button></div>`;
		html += d.days.map((x) => {
			const chips = x.company.map((c) => `<span class="chip2 navy">${esc(c)}</span>`).join("") +
				x.events.map((e) => `<span class="chip2 yel">${e.time ? esc(e.time) + " " : ""}${esc(e.title)}</span>`).join("") +
				(x.orders ? `<span class="chip2 green">${t("order")} ${lakh(x.orders)}</span>` : "") + (x.dsi ? `<span class="chip2 green">DSI ✓</span>` : "") +
				(x.routine || []).map((r) => `<span class="chip2 navy">🔁 ${r.at ? esc(r.at) + " " : ""}${esc(r.title)}</span>`).join("") +
				x.due.map((i) => `<span class="chip2 ${i.overdue ? "red" : ""}"><button class="sk-link" ${i.doctype && i.doctype.startsWith("CRM ") ? `data-open="${esc(i.doctype)}" data-name="${esc(i.name)}"` : ""}>${i.overdue ? "⚠ " : ""}${i.moved ? "↪ " : ""}${esc(i.title)}</button>
					<button class="sk-link" data-move="${esc(i.key)}" data-title="${esc(i.title)}" title="${t("move_to")}">⇄</button></span>`).join("");
			const h = (m) => `${Math.floor(m / 60)}h${m % 60 ? " " + pad2(m % 60) : ""}`;
			const load = x.capacity ? `<span class="sk-item-meta ${x.over ? "sk-amber" : ""}">${t("load")} ${h(x.load)} / ${h(x.capacity)}</span>` : "";
			return `<div class="day ${x.today ? "today" : ""} ${x.working ? "" : "off"} ${x.over ? "over" : ""}"><h4><span>${t("d_" + x.day)} ${esc(x.date.slice(8))}</span><span class="sk-item-meta">${x.due.length} ${t("open_items")}</span>${load}</h4>${chips || `<span class="sk-item-meta">—</span>`}</div>`;
		}).join("");
		return html;
	}

	function moveSheet(key, title) {
		const days = (root._week || []).filter((x) => x.working && x.capacity);
		sheet(`<h3 class="sk-h">⇄ ${t("move_to")}</h3><p class="sk-note">${esc(title)}</p>
			<div class="sk-row sk-wrap">${days.map((x) => `<button class="sk-chip" data-moveday="${esc(x.date)}" data-key="${esc(key)}">${t("d_" + x.day)} ${esc(x.date.slice(8))}</button>`).join("")}
			<button class="sk-chip" data-moveday="" data-key="${esc(key)}">↺</button></div>
			<button class="sk-btn wide" data-act="close-sheet">${t("back")}</button>`);
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
			<button class="sk-btn go wide" data-act="call-follow">📞 ${t("follow_up")}</button>
			<button class="sk-btn wide sk-gap" data-act="call-add">➕ ${t("add_call")}</button>
			${team}<h3 class="sk-h">${t("history")}</h3><ul class="sk-list">${rows || `<li class="sk-empty">${t("nothing")}</li>`}</ul>
			${lockedRow(t("rec_locked"))}</main>`;
	}
	function addCallSheet() {
		const outs = (crmOpts && crmOpts.call_outcomes) || ["Talked", "No answer", "Busy", "Missed", "Call back later", "Wrong number"];
		sheet(`<h3 class="sk-h">➕ ${t("add_call")}</h3>
			<div class="sk-input-row"><input id="f-callq" type="search" placeholder="🔎 ${t("search")}" data-filter="f-callwho">${micBox("f-callq")}</div>${contactSelect("f-callwho")}
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
	// point 14: Team mailbox (cabin@ for the sales team, service@ for Aditya, acc@ Accounts, sales@ CEO, info@ HR) and
	// My customers (mails on my own leads / deals). Each team mail shows New → Taken by … → Replied / Lead made.
	let mailTab = "team";
	async function renderMail() {
		const team = await call("team_mail").catch(() => ({ boxes: [], mails: [] }));
		if (!team.boxes.length) mailTab = "mine";
		const tabs = team.boxes.length ? `<div class="cal-tabs"><button class="${mailTab === "team" ? "on" : ""}" data-mailtab="team">📥 ${t("team_box")}${team.new ? ` (${team.new})` : ""}</button>
			<button class="${mailTab === "mine" ? "on" : ""}" data-mailtab="mine">👤 ${t("my_customers")}</button></div>` : "";
		if (mailTab === "team") {
			S.tmail = team.mails;
			const chip = (m) => `<span class="chip2 ${m.status === "New" ? "red" : m.status === "Taken" ? "yel" : "green"}">${t("st_" + m.status)}${m.status === "Taken" && m.taken_by_name ? " · " + esc(m.taken_by_name) : ""}</span>`;
			root.innerHTML = header(t("mail")) + `<main>${tabs}<p class="sk-note">${team.boxes.map(esc).join(" · ")}</p>
				<ul class="sk-list">${team.mails.map((m, i) => `<li class="sk-item ${m.status === "New" ? "k-lead_new" : ""}"><button class="sk-fu-main" data-tmail="${i}">
					<div class="sk-item-title">${m.source ? `<span class="chip2 navy">${esc(m.source)}</span> ` : ""}${esc(m.subject || "")}</div>
					<div class="sk-item-meta">${esc(m.sender_full_name || m.sender || "")} · ${when(m.communication_date)}${m.has_attachment ? " · 📎" : ""} · ${chip(m)}</div>
					<div class="sk-item-meta">${esc(m.preview || "")}</div></button></li>`).join("") || `<li class="sk-empty">${t("nothing")}</li>`}</ul></main>`;
			return;
		}
		const d = await call("my_mail");
		root.innerHTML = header(t("mail")) + `<main>${tabs}${d.ready ? "" : `<div class="sk-locked">✉️ ${t("mail_not_ready")}</div>`}
			<ul class="sk-list">${d.mails.map((m) => `<li class="sk-item"><button class="sk-fu-main" data-open="${esc(m.reference_doctype)}" data-name="${esc(m.reference_name)}">
				<div class="sk-item-title">${m.sent_or_received === "Received" ? "📥" : "📤"} ${esc(m.subject || "")}</div>
				<div class="sk-item-meta">${esc(m.title)} · ${when(m.communication_date)}${m.has_attachment ? " · 📎" : ""}</div>
				<div class="sk-item-meta">${esc(m.preview || "")}</div></button></li>`).join("") || `<li class="sk-empty">${t("nothing")}</li>`}</ul></main>`;
	}
	async function teamMailSheet(i) {
		const m = S.tmail[i];
		const d = await call("team_mail_read", { comm: m.name });
		S.tmailOpen = d;
		const lead = d.reference_doctype && d.reference_doctype.startsWith("CRM ") && d.reference_name;
		sheet(`<h3 class="sk-h">✉️ ${esc(d.subject || "")}</h3><p class="sk-item-meta">${esc(d.from_name || d.sender || "")} → ${esc(d.box)} · ${esc(d.date.slice(0, 16))}</p>
			<div class="sk-libtext sk-mailtext">${esc(d.text)}</div>
			${d.files.map((f) => `<a class="sk-chip" href="${esc(f.file_url)}" target="_blank">📎 ${esc(f.file_name)}</a>`).join("")}
			<div class="sk-row sk-wrap sk-gap">
				${d.sk_mail_status !== "Taken" || d.sk_taken_by !== state.home.user ? `<button class="sk-chip on" data-act="tm-take" data-comm="${esc(d.name)}">✋ ${t("take")}</button>` : ""}
				${lead ? `<button class="sk-chip" data-open="${esc(d.reference_doctype)}" data-name="${esc(d.reference_name)}">📄 ${t("open_lead")}</button>`
					: `<button class="sk-chip on" data-act="tm-lead" data-comm="${esc(d.name)}">➕ ${t("make_lead_btn")}</button><button class="sk-chip" data-act="tm-notlead" data-comm="${esc(d.name)}">✕ ${t("not_lead")}</button>`}
			</div>
			${hasTeam() && d.people.length ? `<label class="sk-field"><span>${t("give_to")}</span><select id="tm-give" class="sk-select"><option value=""></option>${d.people.map((p) => `<option value="${esc(p.user)}">${esc(p.full_name || p.user)}</option>`).join("")}</select></label>
				<button class="sk-btn wide" data-act="tm-give" data-comm="${esc(d.name)}">👉 ${t("give_to")}</button>` : ""}
			${formField("tm-reply", t("reply_q"), true)}
			<button class="sk-btn ok wide" data-act="tm-reply" data-comm="${esc(d.name)}">✉️ ${t("reply")}</button>
			<button class="sk-btn wide" data-act="close-sheet">${t("back")}</button>`);
	}

	// CEO live dashboards (point 13): one page per function, live from ERPNext; number → its list → the full record
	let dashMonth = null, dashSeg = "", dashData = null;
	const shortMoney = (x) => {
		const v = Number(x || 0), a = Math.abs(v);
		return a >= 1e7 ? `Rs ${(v / 1e7).toFixed(2)} Cr` : a >= 1e5 ? `Rs ${(v / 1e5).toFixed(1)} L` : money(v);
	};
	function dashValue(kind, v) {
		if (v == null) return "—";
		return kind === "money" ? shortMoney(v) : kind === "pct" ? `${v}%` : Number(v).toLocaleString("en-IN");
	}
	function bars(rows) {
		const max = Math.max(1, ...rows.map((r) => Number(r.value || 0)));
		return `<div class="sk-vbars">${rows.map((r) => `<div class="sk-vbar" title="${esc(r.title)}: ${esc(r.value)}"><i style="height:${Math.round(Number(r.value || 0) * 100 / max)}%"></i><small>${esc(r.title)}</small></div>`).join("")}</div>`;
	}
	async function renderDash(key) {
		const d = await call("dash_page", { key, ...(dashMonth ? { month: dashMonth } : {}), ...(dashSeg ? { segment: dashSeg } : {}) });
		if (state.view !== "dash_" + key) return;
		dashData = d;
		const title = d.title[state.lang] || d.title.English;
		const m = new Date(d.month);
		const segs = ["machine_shifting", "job_work"].includes(key) ? "" : `<div class="sk-row sk-wrap">${[["", t("seg_all")], ["Cabin", t("seg_cabin")], ["Non-Cabin", t("seg_noncabin")]]
			.map(([k, label]) => `<button class="sk-chip ${dashSeg === k ? "on" : ""}" data-dashseg="${k}">${label}</button>`).join("")}</div>`;
		root.innerHTML = header(title) + `<main class="sk-dash">
			<div class="sk-row"><button class="sk-chip" data-dashmonth="-1">‹</button><b style="flex:1;text-align:center">${m.toLocaleString(state.lang === "Marathi" ? "mr-IN" : "en-IN", { month: "long", year: "numeric" })}</b><button class="sk-chip" data-dashmonth="1">›</button></div>
			${segs}
			<div class="sk-dash-cards">${d.cards.map((c, i) => {
				const diff = c.prev != null && c.kind === "money" && c.prev ? Math.round((c.value - c.prev) * 100 / Math.abs(c.prev)) : null;
				return `<button class="sk-dash-card ${c.c ? "c-" + c.c : ""} ${c.kind === "series" ? "wide" : ""}" data-dcard="${i}">
					<span class="sk-dash-label">${esc(c.label)}</span>
					${c.kind === "series" ? bars(c.rows || []) : c.kind === "list" ? `<span class="sk-dash-mini">${(c.rows || []).slice(0, 4).map((r) => `${esc(r.title)}: <b>${esc(typeof r.value === "number" && r.value > 9999 ? shortMoney(r.value) : r.value == null ? "" : r.value)}</b>`).join("<br>")}</span>`
						: `<b class="sk-dash-value">${dashValue(c.kind, c.value)}</b>`}
					${c.prev != null ? `<small>${t("vs_last")}: ${dashValue(c.kind, c.prev)}${diff != null ? ` (${diff >= 0 ? "▲" : "▼"} ${Math.abs(diff)}%)` : ""}</small>` : ""}</button>`;
			}).join("")}</div>
			<p class="sk-note">${t("dash_open")} ${t("swipe_hint")} · ${esc(d.refreshed_at)}</p></main>`;
	}
	function renderDashList(i) {
		const c = dashData.cards[i];
		const rows = c.rows || [];
		root.innerHTML = header(c.label) + `<main><button class="sk-btn wide" data-go="${esc(state.view)}">‹ ${esc(dashData.title[state.lang] || dashData.title.English)}</button>
			<ul class="sk-list">${rows.map((r, j) => `<li class="sk-item ${r.c ? "k-" + r.c : ""}"><button class="sk-fu-main" data-drow="${j}" data-dcardi="${i}">
				<div class="sk-item-title">${r.c === "red" ? "🔴 " : r.c === "amber" ? "🟠 " : r.c === "green" ? "🟢 " : ""}${esc(r.title)}</div>
				<div class="sk-item-meta">${esc(r.meta || "")}</div></button>
				${r.value != null ? `<b>${typeof r.value === "number" && Math.abs(r.value) > 9999 ? shortMoney(r.value) : esc(r.value)}</b>` : ""}</li>`).join("") || `<li class="sk-empty">${t("nothing")}</li>`}</ul></main>`;
	}
	function openDashRow(i, j) {
		const r = dashData.cards[i].rows[j];
		if (!r.doctype || !r.name) return;
		if (r.doctype === "CRM Lead" || r.doctype === "CRM Deal") { current = { doctype: r.doctype, name: r.name }; return go("detail"); }
		if (r.doctype === "User") return;
		window.open(`/app/${r.doctype.toLowerCase().replace(/ /g, "-")}/${encodeURIComponent(r.name)}`, "_blank");
	}
	// swipe left / right on a dashboard page: the next / previous function
	let touchX = null;
	root.addEventListener("touchstart", (ev) => { touchX = state.view.startsWith("dash_") && ev.touches.length === 1 ? ev.touches[0].clientX : null; }, { passive: true });
	root.addEventListener("touchend", (ev) => {
		if (touchX == null || !dashData || !state.view.startsWith("dash_")) return;
		const dx = ev.changedTouches[0].clientX - touchX;
		touchX = null;
		if (Math.abs(dx) < 80) return;
		const pages = dashData.pages, at = pages.indexOf(state.view.slice(5));
		const next = pages[(at + (dx < 0 ? 1 : -1) + pages.length) % pages.length];
		go("dash_" + next);
	}, { passive: true });

	// Customer complaints (point 5): register with photo / voice; the concerned person accepts, fixes, the customer confirms
	let cpTab = "mine";
	const cpChip = (r) => `<span class="chip2 ${r.late ? "red" : r.sk_stage === "Closed" ? "green" : r.sk_stage === "Fixed" ? "navy" : "yel"}">${t("st_" + r.sk_stage)}${r.late ? " · " + t("cp_late") : ""}</span>`;
	async function renderComplaints() {
		const d = await call("complaints_list", { tab: cpTab });
		S.cp = d.rows;
		const fns = state.home.functions || [];
		const tab = (k, label) => `<button class="${cpTab === k ? "on" : ""}" data-cptab="${k}">${label}</button>`;
		root.innerHTML = header(t("complaints")) + `<main>
			<div class="cal-tabs">${tab("mine", t("cp_mine"))}${tab("to_fix", `${t("cp_to_fix")}${d.to_fix ? ` (${d.to_fix})` : ""}`)}${fns.includes("Management") ? tab("all", t("cp_all")) : ""}</div>
			<button class="sk-btn ok wide" data-act="cp-new">${t("new_complaint")}</button>
			<ul class="sk-list sk-gap">${d.rows.map((r, i) => `<li class="sk-item ${r.late ? "k-red" : ""}"><button class="sk-fu-main" data-cp="${esc(r.name)}">
				<div class="sk-item-title">${esc(r.customer_name || r.customer || "")}: ${esc(r.issue_type || "")}</div>
				<div class="sk-item-meta">${cpChip(r)} · ${esc(r.concerned_name || r.sk_concerned_function || "")} · ${t("cp_fix_by")} ${esc(r.sk_fix_by)}</div>
				<div class="sk-item-meta">${esc(String(r.description || "").replace(/<[^>]*>/g, "").slice(0, 120))}</div></button></li>`).join("") || `<li class="sk-empty">${t("nothing")}</li>`}</ul></main>`;
	}
	async function renderNewComplaint() {
		const types = (await call("complaints_list", { tab: "mine" })).types;
		state.view = "complaints";
		root.innerHTML = header(t("new_complaint")) + `<main class="sk-form">
			<label class="sk-field"><span>${t("cp_customer")}</span><div class="sk-input-row"><input id="cp-cust" list="cp-cust-dl" autocomplete="off">${micBox("cp-cust")}</div><datalist id="cp-cust-dl"></datalist></label>
			<label class="sk-field"><span>${t("cp_order")}</span><select id="cp-order" class="sk-select"><option value=""></option></select></label>
			${pick("cp-type", t("cp_type"), types)}
			${formField("cp-text", t("cp_what"), true)}
			${photoField("cp-f1", "📷 " + t("cp_files"), true)}${photoField("cp-f2", "📷 " + t("cp_files"), true)}
			<button class="sk-btn ok wide" data-act="cp-save">${t("save")}</button></main>`;
	}
	async function complaintSheet(name) {
		const d = await call("complaint_detail", { name });
		const wa = d.mobile ? `https://wa.me/${waNumber(d.mobile)}?text=${encodeURIComponent(`${d.customer_name}: your complaint ${d.name} is now "${d.sk_stage}"${d.sk_fix_by ? `, fix by ${d.sk_fix_by}` : ""}. SK Ind Tech Solutions`)}` : "";
		const open = ["Registered", "Accepted", "Not OK"].includes(d.sk_stage);
		sheet(`<h3 class="sk-h">🛠️ ${esc(d.customer_name || d.customer)}</h3>
			<p class="sk-item-meta">${cpChip(d)} · ${esc(d.issue_type || "")} · ${esc(d.sk_sales_order || "")}</p>
			<div class="sk-libtext">${esc(String(d.description || "").replace(/<[^>]*>/g, ""))}</div>
			<p class="sk-item-meta">${t("cp_sent")} ${esc(d.concerned_name || "")} · ${t("cp_fix_by")} ${esc(d.sk_fix_by)}</p>
			${d.files.map((f) => `<a class="sk-chip" href="${esc(f.file_url)}" target="_blank">📎 ${esc(f.file_name)}</a>`).join("")}
			<ul class="sk-list">${d.steps.map((x) => `<li class="sk-item"><div><div class="sk-item-meta">${esc(x.when)}</div><div>${esc(x.text)}</div></div></li>`).join("")}</ul>
			${d.is_fixer && open ? `<label class="sk-field"><span>${t("cp_fix_by")}</span><input id="cp-date" type="date" value="${esc(d.sk_fix_by)}"></label>
				<button class="sk-btn go wide" data-act="cp-accept" data-name="${esc(d.name)}">✋ ${t("cp_accept")}</button>
				${formField("cp-done", t("cp_done_what"), true)}${photoField("cp-after", "📷 " + t("cp_after"))}
				<button class="sk-btn ok wide" data-act="cp-fixed" data-name="${esc(d.name)}">✅ ${t("cp_fixed")}</button>` : ""}
			${d.sk_stage === "Fixed" && !d.is_fixer ? `${formField("cp-note", t("cp_note"), true)}${photoField("cp-proof", "📷 WhatsApp / voice")}
				<button class="sk-btn ok wide" data-act="cp-ok" data-ok="1" data-name="${esc(d.name)}">👍 ${t("cp_ok")}</button>
				<button class="sk-btn wide" data-act="cp-ok" data-ok="0" data-name="${esc(d.name)}">👎 ${t("cp_not_ok")}</button>` : ""}
			${wa ? `<a class="sk-btn wide" href="${wa}" target="_blank">💬 ${t("cp_wa")}</a>` : ""}
			<button class="sk-btn wide" data-act="close-sheet">${t("back")}</button>`);
	}

	// Point 16: my Optick / thumb check-in on top of My Day; tap it for my month, selfie backup and "ask HR to fix"
	function attLine(a) {
		if (!a) return "";
		let text = "", c = a.state || "";
		if (a.in) text = `✓ ${t("att_in")} ${esc(a.in)} (${esc(a.source)})${a.out ? ` · ${t("att_out")} ${esc(a.out)}` : ""}${a.state === "amber" ? ` · ${t("att_late")}` : ""}`;
		else if (a.leave) text = `🌴 ${t("att_leave")} (${esc(a.leave)})`;
		else if (a.off) text = `🏖 ${t("att_off")}`;
		else if (a.state === "red") text = `✗ ${t("att_no_in")}`;
		else if (a.waiting_file) text = `⏳ ${t("att_wait_file")}`;
		else text = `🕘 ${t("att_late_after")} ${esc(a.late_after)}`;
		return `<button class="sk-attline ${c}" data-act="att-me">${text} ›</button>`;
	}
	function attSheet() {
		const a = S.att;
		if (!a) { toast(t("no_employee"), true); return; }
		const m = a.month || {};
		const days = (xs) => (xs || []).length ? ` · ${xs.join(", ")}` : "";
		sheet(`<h3 class="sk-h">🕘 ${t("att_my_month")}</h3>
			<ul class="sk-list">${li(t("att_present"), "", `<b>${m.present || 0}</b>`)}${li(t("att_late"), days(m.late_days).slice(3), `<b>${m.late || 0}</b>`)}
			${m.half_day ? li(t("att_half"), "", `<b>${m.half_day}</b>`) : ""}${li(t("att_leave"), days(m.leave_days).slice(3), `<b>${m.leave || 0}</b>`)}
			${li(t("att_absent"), days(m.absent_days).slice(3), `<b>${m.absent || 0}</b>`, m.absent ? "k-red" : "")}</ul>
			<h3 class="sk-h">${t("att_missed")}</h3>
			${photoField("att-selfie", "🤳 " + t("photo"))}
			<button class="sk-btn go wide" data-act="att-selfie">${t("att_selfie")} · ${esc(a.next || "IN")}</button>
			<label class="sk-field"><span>${t("ex_date")}</span><input id="att-day" type="date" value="${new Date().toISOString().slice(0, 10)}"></label>
			${formField("att-fix", t("att_fix_what"), true)}
			<button class="sk-btn wide" data-act="att-ask">${t("att_ask_fix")}</button>
			<button class="sk-btn wide" data-act="close-sheet">${t("back")}</button>`);
	}
	function where() {
		return new Promise((ok) => {
			if (!navigator.geolocation) return ok({});
			navigator.geolocation.getCurrentPosition((p) => ok({ lat: p.coords.latitude, lng: p.coords.longitude }), () => ok({}), { timeout: 8000, maximumAge: 60000 });
		});
	}

	// HR (Aarti): Today · Month · Upload the Optick / thumb machine file
	let attTab = "today", attMonth = "", attPreview = null;
	async function renderAttendance() {
		const tab = (k) => `<button class="${attTab === k ? "on" : ""}" data-atttab="${k}">${t("att_" + k)}</button>`;
		let body = "";
		if (attTab === "today") {
			const d = await call("hr_today");
			S.attFix = d.fix_requests;
			const g = d.groups;
			const person = (r, extra) => li(esc(r.name), extra, r.mobile && !r.in ? `<a class="sk-chip" href="tel:${esc(r.mobile)}">📞</a>` : "");
			const sec = (k, label, rows, fn, cls) => `<h3 class="sk-h ${cls || ""}">${label} · ${rows.length}</h3><ul class="sk-list">${rows.map(fn).join("") || `<li class="sk-empty">—</li>`}</ul>`;
			body = `<p class="sk-note">${esc(d.day)} · ${t("att_late_after")} ${esc(d.late_after)} · ${Object.entries(d.by_source).map(([k, v]) => `${esc(k)} ${v}`).join(" · ") || "—"}</p>
				${d.fix_requests.length ? sec("fix", "✋ " + t("att_fix_req"), d.fix_requests, (r, i) => li(esc(r.text), esc(r.date || ""), `<button class="sk-chip" data-act="att-fixsheet" data-i="${i}">${t("att_fix")}</button>`, "k-lead_new")) : ""}
				${sec("present", "✓ " + t("att_present"), g.present, (r) => person(r, `${esc(r.in)}${r.out ? " – " + esc(r.out) : ""} · ${esc(r.source || "")}`))}
				${sec("late", "⏰ " + t("att_late"), g.late, (r) => person(r, `${esc(r.in || "")} · ${esc(r.source || "")}`), "k-amber")}
				${sec("no_checkin", "✗ " + t("att_no_checkin"), g.no_checkin, (r) => person(r, d.uploaded_today ? "" : t("att_wait_file")))}
				${sec("on_leave", "🌴 " + t("att_leave"), g.on_leave, (r) => person(r, esc(r.leave_type || "")))}
				${g.off.length ? sec("off", "🏖 " + t("att_off"), g.off, (r) => person(r, "")) : ""}`;
		} else if (attTab === "month") {
			const d = await call("hr_month", attMonth ? { month: attMonth } : {});
			body = `<div class="sk-row"><button class="sk-chip" data-attmonth="-1">‹</button><b>${esc(d.month)}</b><button class="sk-chip" data-attmonth="1">›</button></div>
				<table class="sk-atttable"><tr><th></th><th>${t("att_present")}</th><th>${t("att_late")}</th><th>½</th><th>${t("att_leave")}</th><th>${t("att_absent")}</th></tr>
				${d.rows.map((r) => `<tr><td>${esc(r.name)}</td><td>${r.present}</td><td>${r.late}</td><td>${r.half_day}</td><td>${r.leave}</td><td class="${r.absent ? "bad" : ""}">${r.absent}</td></tr>`).join("")}</table>`;
		} else {
			const p = attPreview;
			body = `<div class="sk-form">${pick("att-device", t("att_device"), ["Optick", "Office thumb"])}
				${photoField("att-file", "📄 " + t("att_file"), true)}
				<button class="sk-btn go wide" data-act="att-preview">🔍 ${t("att_check_file")}</button></div>
				${p ? `<section class="sk-card"><div class="sk-card-text">${p.rows} ${t("att_rows")} (${esc(p.from)} – ${esc(p.to)}) · ${p.matched.length} ${t("att_matched")} ✓ · ${p.late} ${t("att_late")} · ${p.already} ${t("att_already")}</div></section>
				${p.not_found.length ? `<h3 class="sk-h k-amber">⚠ ${p.not_found.length} ${t("att_not_found")}</h3>${p.not_found.map((r, i) => `<label class="sk-field"><span>${esc(r.name)} · ID ${esc(r.id)} · ${esc(r.mobile)}</span>
					<select class="sk-select" id="att-m-${i}"><option value="">${t("att_skip")}</option>${p.employees.map((e) => `<option value="${esc(e.name)}" ${r.options[0] === e.name ? "selected" : ""}>${esc(e.employee_name)}</option>`).join("")}</select></label>`).join("")}` : ""}
				<ul class="sk-list">${p.matched.map((r) => li(`✓ ${esc(r.employee_name)}`, `${esc(r.name)} · ${esc(r.how)} · ${r.rows} ${t("att_rows")}`)).join("")}</ul>
				${p.missed_out.length ? `<h3 class="sk-h">⚠ ${p.missed_out.length} ${t("att_missed_out")}</h3><ul class="sk-list">${Object.entries(p.missed_out.reduce((a, r) => { (a[r.name] = a[r.name] || []).push(r.date.slice(8)); return a; }, {}))
					.map(([n, ds]) => li(`${esc(n)} · ${ds.length}`, ds.map(esc).join(", "))).join("")}</ul>` : ""}
				<button class="sk-btn ok wide" data-act="att-save">${t("att_save")}</button><div id="att-result"></div>` : ""}`;
		}
		root.innerHTML = header(t("attendance")) + `<main><div class="cal-tabs">${tab("today")}${tab("month")}${tab("upload")}</div>${body}</main>`;
		if (attTab === "upload" && attPreview) { const s = document.getElementById("att-device"); if (s) s.value = attPreview.device; }
	}
	function attFixSheet(r) {
		sheet(`<h3 class="sk-h">✋ ${esc(r.text)}</h3>
			<label class="sk-field"><span>${t("ex_date")}</span><input id="fx-day" type="date" value="${esc(r.date || "")}"></label>
			${pick("fx-status", t("att_status"), [{ value: "Present", label: t("att_present") }, { value: "Half Day", label: t("att_half") }, { value: "Absent", label: t("att_absent") }, { value: "Work From Home", label: "Work From Home" }])}
			${formField("fx-reason", t("att_reason"), true)}
			<button class="sk-btn ok wide" data-act="att-fix" data-employee="${esc(r.employee)}" data-todo="${esc(r.todo)}">${t("att_fix")}</button>
			<button class="sk-btn wide" data-act="close-sheet">${t("back")}</button>`);
	}

	// Everyone: Leave & Expense; managers approve their team's here (HR / CEO see all waiting)
	let lvTab = "leave";
	async function renderLeaveExpense() {
		const d = await call("leave_expense");
		S.lv = d;
		const chip = (st) => `<span class="chip2 ${/Approved|Paid/.test(st) ? "green" : /Rejected|Cancelled/.test(st) ? "red" : "yel"}">${esc(st)}</span>`;
		const tab = (k, label) => `<button class="${lvTab === k ? "on" : ""}" data-lvtab="${k}">${label}</button>`;
		let body = "";
		if (!d.employee && lvTab !== "approve") body = `<p class="sk-note">${t("no_employee")}</p>`;
		else if (lvTab === "leave") {
			body = `<div class="sk-row sk-wrap">${d.leave_types.filter((x) => x.balance !== null).map((x) => `<span class="chip2 navy">${esc(x.name)}: ${x.balance} ${t("lv_left")}</span>`).join("")}</div>
				<div class="sk-form">${pick("lv-type", t("lv_type"), d.leave_types.map((x) => ({ value: x.name, label: x.balance !== null ? `${x.name} (${x.balance} ${t("lv_left")})` : x.name })))}
				<label class="sk-field"><span>${t("lv_from")}</span><input id="lv-from" type="date"></label>
				<label class="sk-field"><span>${t("lv_to")}</span><input id="lv-to" type="date"></label>
				<label class="sk-check"><input id="lv-half" type="checkbox"> ${t("lv_half")}</label>
				${formField("lv-reason", t("lv_reason"), true)}
				<button class="sk-btn ok wide" data-act="lv-apply">${t("lv_apply")}</button></div>
				<h3 class="sk-h">${t("lv_mine")}</h3><ul class="sk-list">${d.my_leave.map((l) => li(`${esc(l.leave_type)} · ${esc(l.from_date)}${l.to_date !== l.from_date ? " – " + esc(l.to_date) : ""}`,
					`${l.total_leave_days || ""} · ${esc(l.description || "")}`, chip(l.status))).join("") || `<li class="sk-empty">—</li>`}</ul>`;
		} else if (lvTab === "expense") {
			body = `<div class="sk-form">${photoField("ex-photo", "📷 " + t("ex_bill"))}${pick("ex-type", t("ex_type"), d.expense_types)}
				<label class="sk-field"><span>${t("ex_amount")}</span><input id="ex-amt" type="number" inputmode="decimal" min="0"></label>
				<label class="sk-field"><span>${t("ex_date")}</span><input id="ex-date" type="date" value="${new Date().toISOString().slice(0, 10)}"></label>
				${formField("ex-note", t("ex_note"), true)}
				<button class="sk-btn ok wide" data-act="ex-claim">${t("ex_claim")}</button></div>
				<h3 class="sk-h">${t("ex_mine")}</h3><ul class="sk-list">${d.my_claims.map((c) => li(`${money(c.total_claimed_amount)} · ${esc(c.type || "")}`, `${esc(c.posting_date)} · ${esc(c.remark || "")}`,
					chip(c.docstatus === 1 ? c.status : c.approval_status))).join("") || `<li class="sk-empty">—</li>`}</ul>`;
		} else {
			const btns = (kind, name) => `<div class="sk-row"><button class="sk-chip ok" data-act="lv-decide" data-kind="${kind}" data-name="${esc(name)}" data-ok="1">${t("lv_approve")}</button>
				<button class="sk-chip bad" data-act="lv-decide" data-kind="${kind}" data-name="${esc(name)}" data-ok="0">${t("lv_reject")}</button></div>`;
			body = `<h3 class="sk-h">🌴 ${t("lv_leave")}</h3><ul class="sk-list">${d.leave_to_approve.map((l) => `<li class="sk-item"><div style="flex:1"><div class="sk-item-title">${esc(l.employee_name)}: ${esc(l.leave_type)}</div>
					<div class="sk-item-meta">${esc(l.from_date)}${l.to_date !== l.from_date ? " – " + esc(l.to_date) : ""} · ${l.total_leave_days || ""} · ${esc(l.description || "")}</div>${btns("leave", l.name)}</div></li>`).join("") || `<li class="sk-empty">—</li>`}</ul>
				<h3 class="sk-h">💸 ${t("lv_expense")}</h3><ul class="sk-list">${d.claims_to_approve.map((c) => `<li class="sk-item"><div style="flex:1"><div class="sk-item-title">${esc(c.employee_name)}: ${money(c.total_claimed_amount)}</div>
					<div class="sk-item-meta">${esc(c.type || "")} · ${esc(c.posting_date)} · ${esc(c.remark || "")} <a href="/app/expense-claim/${encodeURIComponent(c.name)}">📎</a></div>${btns("expense", c.name)}</div></li>`).join("") || `<li class="sk-empty">—</li>`}</ul>`;
		}
		root.innerHTML = header(t("leave_expense")) + `<main><div class="cal-tabs">${tab("leave", "🌴 " + t("lv_leave"))}${tab("expense", "💸 " + t("lv_expense"))}${tab("approve", `✅ ${t("lv_to_approve")}${d.to_approve ? ` (${d.to_approve})` : ""}`)}</div>${body}</main>`;
	}

	// View Member App (point 3): all members by function, last active; tap one to open their app as they see it
	let vmQuery = "";
	async function renderViewMember() {
		const d = await call("view_members");
		const q = vmQuery.toLowerCase();
		root.innerHTML = header(t("view_member")) + `<main><p class="sk-note">${t("view_hint")}</p>
			<div class="sk-input-row sk-gap"><input id="vm-q" type="search" placeholder="🔎 ${t("search")}" value="${esc(vmQuery)}">${micBox("vm-q")}</div>
			${d.groups.map((g) => {
				const people = g.people.filter((p) => !q || p.full_name.toLowerCase().includes(q));
				return people.length ? `<h3 class="sk-h">${esc((g.label && (g.label[state.lang] || g.label.English)) || g.function)}</h3><ul class="sk-list">${people.map((p) => `<li class="sk-item"><button class="sk-fu-main" data-act="view-enter" data-user="${esc(p.user)}" data-uname="${esc(p.full_name)}">
					<div class="sk-item-title">👤 ${esc(p.full_name)}</div><div class="sk-item-meta">${p.functions.map(esc).join(", ")} · ${t("last_active")}: ${esc(p.last_active || t("never"))}</div></button></li>`).join("")}</ul>` : "";
			}).join("")}</main>`;
	}
	async function enterView(user, name) {
		state.own = { home: state.home, lang: state.lang };
		state.viewAs = { user, name };
		crmOpts = null; contacts = null;
		try {
			state.view = "home";
			state.home = await call("home");
		} catch (e) { state.viewAs = null; state.home = state.own.home; throw e; }
		state.lang = state.home.language || "English";
		document.body.classList.add("sk-viewing");
		return go("home");
	}
	function exitView() {
		if (!state.viewAs) return go("home");
		state.viewAs = null;
		state.home = state.own.home; state.lang = state.own.lang;
		crmOpts = null; contacts = null;
		document.body.classList.remove("sk-viewing");
		return go("view_member");
	}

	// Customers by segment (point 2): the cabin team sees Cabin customers, Aditya Non-Cabin, Management both.
	// "Segment not set": Management, Rushi and Aditya tag old customers with one tap.
	let custTab = "mine", custSeg = "", custQuery = "";
	async function renderCustomers() {
		const d = await call("customers", { tab: custTab, q: custQuery, segment: custSeg });
		S.cust = d.rows;
		const tab = (k, label) => `<button class="${custTab === k ? "on" : ""}" data-custtab="${k}">${label}</button>`;
		const segChips = d.main === "Both" && custTab === "mine" ? `<div class="sk-row sk-wrap">${[["", t("seg_all")], ["Cabin", t("seg_cabin")], ["Non-Cabin", t("seg_noncabin")]]
			.map(([k, label]) => `<button class="sk-chip ${custSeg === k ? "on" : ""}" data-custseg="${k}">${label}</button>`).join("")}</div>` : "";
		const tagRow = (r, i) => Object.entries(d.tree).map(([main, subs]) => `<div class="sk-row sk-wrap"><span class="chip2 ${main === "Cabin" ? "navy" : "yel"}">${esc(t(main))}</span>${subs.map((x) =>
			`<button class="sk-chip" data-act="cust-tag" data-i="${i}" data-seg="${esc(x)}">${esc(x)}</button>`).join("")}</div>`).join("");
		root.innerHTML = header(t("customers")) + `<main>
			${d.can_tag ? `<div class="cal-tabs">${tab("mine", "🏠 " + (d.main === "Both" ? t("customers") : t(d.main)))}${tab("not_set", `❓ ${t("seg_not_set")}${d.not_set ? ` (${d.not_set})` : ""}`)}</div>` : ""}
			${segChips}
			<div class="sk-input-row sk-gap"><input id="cust-q" type="search" placeholder="🔎 ${t("search")}" value="${esc(custQuery)}">${micBox("cust-q")}</div>
			${custTab === "not_set" ? `<p class="sk-note">${t("tag_hint")} ${t("seen_by_mgmt")}</p>` : ""}
			${custTab === "not_set" && d.from_tally ? `<button class="sk-btn go wide" data-act="cust-tally">📒 ${t("tag_tally")} (${d.from_tally})</button>` : ""}
			<ul class="sk-list">${d.rows.map((r, i) => `<li class="sk-item"><div style="flex:1">
				<div class="sk-item-title">${esc(r.customer_name || r.name)}</div>
				<div class="sk-item-meta">${[r.segment ? `<span class="chip2 ${r.main === "Cabin" ? "navy" : "yel"}">${esc(r.segment)}</span>` : esc(r.customer_group || ""),
					r.mobile_no ? esc(r.mobile_no) : "", r.orders ? `${money(r.orders)} ${t("orders_word")}` : ""].filter(Boolean).join(" · ")}</div>
				${custTab === "not_set" ? tagRow(r, i) : ""}</div>
				${r.mobile_no ? `<a class="sk-chip" href="tel:${esc(r.mobile_no)}">📞</a>` : ""}</li>`).join("") || `<li class="sk-empty">${t("nothing")}</li>`}</ul></main>`;
	}

	// Lead Sources (Samir / SK): IndiaMART, JustDial and GeM from mails (free), the Excel upload, mailboxes set up or not
	async function renderLeadSources() {
		const d = await call("lead_sources_status");
		root.innerHTML = header(t("lead_sources")) + `<main>
			<p class="sk-note">${t("last_check")}: ${esc(d.last_scan ? d.last_scan.slice(0, 16) : "—")}</p>
			<button class="sk-btn go wide" data-act="ls-check">↻ ${t("check_now")}</button>
			<ul class="sk-list sk-gap">${d.sources.map((x) => li(`${x.on ? "🟢" : "⚪"} ${esc(x.source)}`,
				`${x.today} ${t("today")} · ${x.month} ${t("this_month2")}${x.last ? " · " + esc(x.last.slice(0, 16)) : ""}`,
				`<button class="sk-chip ${x.on ? "on" : ""}" data-act="ls-switch" data-setting="${esc(x.setting)}" data-on="${x.on ? 0 : 1}">${x.on ? t("on_word") : t("off_word")}</button>`)).join("")}
				${li(`<span class="sk-muted">🔒 ${t("pull_api")}</span>`, "", "", "sk-off")}</ul>
			${uploadBox()}
			<h3 class="sk-h">${t("mailboxes")}</h3><ul class="sk-list">${d.mailboxes.map((b) => li(esc(b.email), esc(b.who.join(", ")),
				b.set_up ? `<span class="chip2 green">✓ ${t("set_up")}</span>` : `<span class="chip2 red">${t("not_set_up")}</span>`, b.set_up ? "" : "k-lead_new")).join("")}</ul></main>`;
	}
	function uploadBox() {
		return `<div class="sk-form sk-gap">${photoField("ls-file", "📄 " + t("upload_list"), true)}
			<label class="sk-field"><span>${t("source_word")}</span><select id="ls-src" class="sk-select"><option>IndiaMART</option><option>JustDial</option><option>GeM</option><option>Other</option></select></label>
			<button class="sk-btn ok wide" data-act="ls-upload">⬆ ${t("upload_list")}</button><div id="ls-result"></div></div>`;
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
	// point 8: one card per product, used everywhere; the internal part is never put in a customer message
	function productMessage(c) {
		const mr = state.lang === "Marathi";
		return [(mr && c.title_marathi) || c.title, (mr && c.text_marathi) || c.text, c.sizes, c.file ? absUrl(c.file) : "", c.video_link, c.link]
			.filter(Boolean).join("\n");
	}
	function productStrip(cards) {
		S.pcards = cards;
		return `<div class="sk-pstrip">${cards.map((c, i) => `<div class="sk-pcard">${c.photos && c.photos[0] ? `<img src="${esc(c.photos[0])}" alt="">` : `<div class="sk-pph">📷</div>`}
			<b>${esc((state.lang === "Marathi" && c.title_marathi) || c.title)}</b>
			<button class="sk-chip on" data-act="p-send" data-i="${i}">💬 ${t("send")}</button></div>`).join("")}</div>`;
	}
	async function renderProducts() {
		const cat = await call("product_catalogue");
		const mr = state.lang === "Marathi";
		const all = [].concat(...Object.values(cat));
		S.pcards = all;
		return Object.entries(cat).map(([main, rows]) => `<h3 class="sk-h">${esc(t(main))}</h3><ul class="sk-list">${rows.map((c) => {
			const i = all.indexOf(c);
			if (!c.ready) return `<li class="sk-item sk-off"><div><div class="sk-item-title">${esc(c.title)}</div><div class="sk-item-meta">${t("card_missing")}</div></div></li>`;
			return `<li class="sk-item"><div class="sk-grow">${c.photos.length ? `<div class="sk-pstrip">${c.photos.slice(0, 5).map((p) => `<a href="${esc(p)}" target="_blank"><img class="sk-pthumb" src="${esc(p)}" alt=""></a>`).join("")}</div>` : ""}
				<div class="sk-item-title">${esc((mr && c.title_marathi) || c.title)}</div>
				${(mr && c.text_marathi) || c.text ? `<div class="sk-libtext">${esc((mr && c.text_marathi) || c.text)}</div>` : ""}
				${c.sizes ? `<div class="sk-libtext">📐 ${esc(c.sizes)}</div>` : ""}
				${c.internal_notes ? `<div class="sk-item-meta">🔒 ${esc(c.internal_notes)}</div>` : ""}
				<div class="sk-row sk-wrap">${c.file ? `<a class="sk-chip" href="${esc(c.file)}" target="_blank">📄 ${t("brochure")}</a>` : ""}${c.video_link ? `<a class="sk-chip" href="${esc(c.video_link)}" target="_blank">▶ Video</a>` : ""}
				<button class="sk-chip on" data-act="p-send" data-i="${i}">💬 ${t("send")}</button></div></div></li>`;
		}).join("") || `<li class="sk-empty">${t("nothing")}</li>`}</ul>`).join("");
	}
	async function renderLibrary() {
		const cats = ["Company", "Product", "Customer FAQ", "Message Template", "Sales Manual"];
		if (libCat === "Product") {
			const body = await renderProducts();
			root.innerHTML = header(t("library")) + `<main><div class="cal-tabs sk-wrap">${cats.map((c) => `<button class="${libCat === c ? "on" : ""}" data-libcat="${esc(c)}">${t("cat_" + c)}</button>`).join("")}</div>${body}</main>`;
			return;
		}
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
			${micBox(id)}</div><datalist id="${id}-dl"></datalist></label>`;
	}
	// search boxes: Follow-up list and the customer list in Add call
	let fuTimer = null;
	root.addEventListener("input", (ev) => {
		const el = ev.target;
		if (el.id === "cp-cust") {
			clearTimeout(fuTimer);
			fuTimer = setTimeout(async () => {
				const dl = document.getElementById("cp-cust-dl");
				const hit = dl && [...dl.options].find((x) => x.value === el.value);
				if (hit) {
					const o = await call("complaint_orders", { customer: el.value });
					const sel = document.getElementById("cp-order");
					if (sel) sel.innerHTML = o.orders.map((r) => `<option value="${esc(r.name)}">${esc(r.name)} · ${esc(r.items)} · ${esc(r.transaction_date)}</option>`).join("") + `<option value=""></option>`;
					return;
				}
				const d = await call("customers", { tab: "pick", q: el.value });
				if (dl) dl.innerHTML = d.rows.map((r) => `<option value="${esc(r.name)}">${esc(r.customer_name)}${r.segment ? " · " + esc(r.segment) : ""}</option>`).join("");
			}, 300);
			return;
		}
		if (el.id === "faq-q") { clearTimeout(fuTimer); fuTimer = setTimeout(() => { faqQuery = el.value; renderTraining().then(() => { const i = document.getElementById("faq-q"); if (i) { i.focus(); i.setSelectionRange(i.value.length, i.value.length); } }); }, 400); return; }
		if (el.id === "vm-q") { clearTimeout(fuTimer); fuTimer = setTimeout(() => { vmQuery = el.value; renderViewMember().then(() => { const i = document.getElementById("vm-q"); if (i) { i.focus(); i.setSelectionRange(i.value.length, i.value.length); } }); }, 300); return; }
		if (el.id === "cust-q") { clearTimeout(fuTimer); fuTimer = setTimeout(() => { custQuery = el.value; renderCustomers().then(() => { const i = document.getElementById("cust-q"); if (i) { i.focus(); i.setSelectionRange(i.value.length, i.value.length); } }); }, 400); return; }
		if (el.id === "fu-q") { clearTimeout(fuTimer); fuTimer = setTimeout(() => { fuQuery = el.value; renderFollowUp().then(() => { const i = document.getElementById("fu-q"); if (i) { i.focus(); i.setSelectionRange(i.value.length, i.value.length); } }); }, 400); return; }
		if (el.dataset && el.dataset.filter) {
			const q = el.value.toLowerCase();
			const sel = document.getElementById(el.dataset.filter);
			if (!sel) return;
			let first = null;
			[...sel.options].forEach((o) => { const hit = !o.value || o.text.toLowerCase().includes(q) || (o.dataset.mobile || "").includes(q); o.hidden = !hit; if (hit && o.value && !first) first = o; });
			if (q && first) sel.value = first.value;
		}
	});
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
			`${esc(r.item_code)} · ERPNext ${num(r.qty)}`, `<div class="sk-input-row sk-countbox">${qtyBox("c-q" + k, "", r.item_name)}${micBox("c-q" + k)}</div>`)).join("") || empty()}</ul>
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
			<label class="sk-field"><span>${t("rate")}</span><div class="sk-input-row">${qtyBox("q-rate")}${micBox("q-rate")}</div></label>
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

	// ---------- Finance (SK draft F06, 26-Oct-2026) ----------
	const MODES = ["Bank Draft", "Wire Transfer", "Cheque", "Cash", "UPI"];
	const payFields = (pre, amount) => `<label class="sk-field"><span>${t("amount")}</span>${qtyBox(pre + "-amt", amount)}</label>
		${pick(pre + "-mode", t("pay_mode"), MODES)}${formField(pre + "-ref", t("utr_no"))}
		<label class="sk-field"><span>${t("pay_date")}</span><input id="${pre}-date" type="date" class="sk-select" value="${new Date().toISOString().slice(0, 10)}"></label>
		${photoField(pre + "-photo", "📷 " + t("pay_proof"))}`;
	async function renderCash() {
		const c = await call("fin_cash");
		root.innerHTML = header(t("cash_today")) + `<main><section class="sk-card"><div class="sk-card-label">${t("bank_cash_now")}</div>
			<div class="sk-card-text">${money(c.total)}</div><div class="sk-card-meta">⬇ ${t("in_today")} ${money(c.in)} · ⬆ ${t("out_today")} ${money(c.out)}</div></section>
			<ul class="sk-list">${c.accounts.map((a) => li(esc(a.account_name), esc(a.account_type), `<b>${money(a.balance)}</b>`)).join("") || empty()}</ul>
			<h3 class="sk-h">${t("today_payments")}</h3><ul class="sk-list">${c.today.map((p) => li(esc(p.party_name || ""), `${esc(p.name)} · ${esc(p.mode_of_payment || "")} ${esc(p.reference_no || "")}`,
				`<b>${p.payment_type === "Pay" ? "⬆" : "⬇"} ${money(p.paid_amount)}</b>`)).join("") || empty()}</ul>
			${c.accounts.length ? "" : `<p class="sk-note">⚠ ${t("no_bank_yet")}</p>`}</main>`;
	}
	async function renderCollect() {
		S.dues = await call("fin_collect");
		const groups = [["d60_plus", t("over_60")], ["d31_60", t("d31_60")], ["d0_30", t("d0_30")], ["not_due", t("not_due")]];
		const row = (r) => { const i = S.dues.indexOf(r);
			return li(esc(r.customer_name), `${esc(r.name)} · ${t("due")} ${esc(r.due_date)}${r.days_late > 0 ? ` · <span class="sk-due">${r.days_late} ${t("days_late")}</span>` : ""}${r.promise ? `<br>🤝 ${esc(r.promise)}` : ""}`,
				`<div class="sk-col"><b>${money(r.outstanding_amount)}</b>${r.mobile ? `<a class="sk-chip" href="tel:${esc(r.mobile)}">📞</a><button class="sk-chip" data-act="fin-wa" data-i="${i}">💬</button>` : ""}
				<button class="sk-chip" data-act="fin-promise" data-i="${i}">🤝 ${t("promise")}</button><button class="sk-chip on" data-act="fin-recv" data-i="${i}">₹ ${t("received")}</button></div>`); };
		const total = S.dues.reduce((s, r) => s + r.outstanding_amount, 0);
		root.innerHTML = header(t("to_collect")) + `<main><p class="sk-note">${t("total_due")}: <b>${money(total)}</b> · ${S.dues.length} ${t("inv_n")}</p>
			${groups.map(([k, label]) => { const rows = S.dues.filter((r) => r.bucket === k); return rows.length ? `<h3 class="sk-h">${label} (${money(rows.reduce((s, r) => s + r.outstanding_amount, 0))})</h3><ul class="sk-list">${rows.map(row).join("")}</ul>` : ""; }).join("") || `<p class="sk-empty">${t("nothing")}</p>`}</main>`;
	}
	async function renderToPay(view) {
		const boss = view === "pay_approvals";
		S.bills = await call(boss ? "fin_pay_approvals" : "fin_to_pay");
		root.innerHTML = header(t(view)) + `<main>${boss ? "" : `<p class="sk-note">${t("pay_rule")}</p>`}<ul class="sk-list">${S.bills.map((b, i) => li(esc(b.supplier_name),
			`${esc(b.name)}${b.bill_no ? " · " + t("bill") + " " + esc(b.bill_no) : ""} · ${t("due")} ${esc(b.due_date)}${b.days_late > 0 ? ` · <span class="sk-due">${b.days_late} ${t("days_late")}</span>` : ""}`,
			`<div class="sk-col"><b>${money(b.outstanding_amount)}</b>${boss ? `<button class="sk-chip on" data-act="fin-approve" data-i="${i}">✓ ${t("approve")}</button>`
				: b.needs_ok && !b.approved ? `<button class="sk-chip" data-act="fin-ask" data-i="${i}">🙋 ${t("ask_sk")}</button>`
				: `<button class="sk-chip on" data-act="fin-pay" data-i="${i}">₹ ${t("paid")}</button>`}${b.approved ? `<span class="sk-chip on">SK ✓</span>` : ""}</div>`)).join("") || empty()}</ul></main>`;
	}
	async function renderBillsToPost() {
		S.fb = await call("fin_bills");
		root.innerHTML = header(t("bills_to_post")) + `<main><h3 class="sk-h">📷 ${t("bill_photos")} (${S.fb.photos.length})</h3>
			<ul class="sk-list">${S.fb.photos.map((p, i) => li(esc(p.supplier_name || p.reference_name), `${esc(p.description)}${p.photo ? ` · <a href="${esc(p.photo)}" target="_blank">📷 ${t("see_photo")}</a>` : ""}`,
				`<div class="sk-col"><button class="sk-chip on" data-act="fin-bill" data-i="${i}">${t("make_bill")}</button><button class="sk-chip" data-act="fin-bill-done" data-i="${i}">✓ ${t("already_done")}</button></div>`)).join("") || empty()}</ul>
			<h3 class="sk-h">📝 ${t("drafts_check")} (${S.fb.drafts.length})</h3>
			<ul class="sk-list">${S.fb.drafts.map((d, i) => li(esc(d.supplier_name), `${esc(d.name)}${d.bill_no ? " · " + esc(d.bill_no) : ""} · ${esc(d.posting_date)}`,
				`<div class="sk-col"><b>${money(d.grand_total)}</b><a class="sk-chip" href="/app/purchase-invoice/${encodeURIComponent(d.name)}">${t("check")}</a>
				<button class="sk-chip on" data-act="fin-post-pi" data-i="${i}">✓ ${t("post")}</button></div>`)).join("") || empty()}</ul></main>`;
	}
	async function renderInvoices() {
		S.fi = await call("fin_invoices");
		root.innerHTML = header(t("invoices")) + `<main><h3 class="sk-h">🚛 ${t("dispatched_no_invoice")} (${S.fi.to_bill.length})</h3>
			<ul class="sk-list">${S.fi.to_bill.map((d, i) => li(esc(d.customer_name), `${esc(d.name)} · ${esc(d.posting_date)}${d.vehicle_no ? " · " + esc(d.vehicle_no) : ""}${d.days > 0 ? ` · <span class="sk-due">${d.days} ${t("days_late")}</span>` : ""}`,
				`<div class="sk-col"><b>${money(d.grand_total)}</b><button class="sk-chip on" data-act="fin-make-inv" data-i="${i}">${t("make_invoice")}</button></div>`)).join("") || empty()}</ul>
			<h3 class="sk-h">📝 ${t("drafts_check")} (${S.fi.drafts.length})</h3>
			<ul class="sk-list">${S.fi.drafts.map((d, i) => li(esc(d.customer_name), `${esc(d.name)} · ${esc(d.posting_date)}`,
				`<div class="sk-col"><b>${money(d.grand_total)}</b><a class="sk-chip" href="/app/sales-invoice/${encodeURIComponent(d.name)}">${t("check")}</a>
				<button class="sk-chip on" data-act="fin-post-si" data-i="${i}">✓ ${t("post")}</button></div>`)).join("") || empty()}</ul></main>`;
	}
	async function renderExpenses() {
		S.claims = await call("fin_expenses");
		root.innerHTML = header(t("expenses")) + `<main><button class="sk-btn go wide" data-act="fin-voucher">📷 + ${t("petty_cash")}</button>
			<h3 class="sk-h">${t("claims_to_pay")}</h3><ul class="sk-list">${S.claims.map((c, i) => li(esc(c.employee_name), `${esc(c.name)} · ${esc(c.posting_date)}`,
				`<div class="sk-col"><b>${money(c.total_sanctioned_amount || c.grand_total)}</b><button class="sk-chip on" data-act="fin-pay-claim" data-i="${i}">₹ ${t("paid")}</button></div>`)).join("") || empty()}</ul></main>`;
	}
	async function renderSegmentPnl() {
		const p = await call("fin_segment_pnl");
		const pct = (r) => r.margin_pct == null ? "" : ` · ${r.margin_pct}%`;
		root.innerHTML = header(t("segment_pnl")) + `<main><p class="sk-note">${esc(p.from)} → ${esc(p.to)}</p>
			<section class="sk-card"><div class="sk-card-label">${t("this_month")}</div><div class="sk-card-text">${money(p.total.margin)}</div>
			<div class="sk-card-meta">${t("income")} ${money(p.total.income)} · ${t("cost")} ${money(p.total.cost)}</div></section>
			<ul class="sk-list">${p.rows.map((r) => li(esc(r.cost_center), `${t("income")} ${money(r.income)} · ${t("cost")} ${money(r.cost)}`,
				`<b class="${r.margin < 0 ? "sk-due" : ""}">${money(r.margin)}${pct(r)}</b>`)).join("") || empty()}</ul>
			<p class="sk-note">${t("pnl_note")}</p></main>`;
	}
	// ---------- Ledger-wise Accounts screens (SK / Shraddha, 26-Oct) ----------
	const FIN_LEDGER = { cash_today: "bank", to_collect: "receivable", to_pay: "payable", bills_to_post: "purchase", invoices: "sales",
		expenses: "journal", dir_expenses: "expenses" };
	const finTab = {};
	let finMonth = null; // "YYYY-MM-01"; empty = this month
	const short = (x) => String(x || "").replace(/ - [A-Z]+$/, "");
	function monthNav() {
		const d = finMonth ? new Date(finMonth) : new Date();
		const label = d.toLocaleDateString(state.lang === "Marathi" ? "mr-IN" : "en-IN", { month: "long", year: "numeric" });
		return `<div class="sk-score sk-cal-head"><button class="sk-nav" data-finmonth="-1">‹</button><div>${esc(label)}</div><button class="sk-nav" data-finmonth="1">›</button></div>`;
	}
	async function finScreen(view, work) {
		const kind = FIN_LEDGER[view];
		const tab = work ? finTab[view] || "ledger" : "ledger";
		const tabs = work ? `<div class="cal-tabs"><button class="${tab === "ledger" ? "on" : ""}" data-fintab="ledger" data-view="${view}">${t("ledger_wise")}</button>
			<button class="${tab === "work" ? "on" : ""}" data-fintab="work" data-view="${view}">${t("work_tab")}</button></div>` : "";
		if (tab === "work") {
			await work();
			const main = root.querySelector("main");
			if (main) main.insertAdjacentHTML("afterbegin", tabs);
			return;
		}
		const d = await call("fin_ledgers", { kind, ...(finMonth ? { month: finMonth } : {}) });
		S.ledger = { kind, rows: d.rows, view };
		let body;
		if (kind === "purchase" || kind === "sales") {
			body = d.rows.map((r, i) => li(esc(r.title || r.ledger), `${r.count} ${t("bills_n")}${r.returns ? ` · ${t("returns_n")} ${money(r.returns)}` : ""}${r.drafts ? ` · <span class="sk-due">${r.drafts} ${t("drafts_n")}</span>` : ""}`,
				`<div class="sk-col"><b>${money(r.net)}</b><button class="sk-chip" data-ledger="${i}">›</button></div>`)).join("");
			body = `<p class="sk-note">${t("bills_n")} ${money(d.total.bills)} · ${t("returns_n")} ${money(d.total.returns)} · <b>${t("net")} ${money(d.total.net)}</b></p><ul class="sk-list">${body || empty()}</ul>`;
		} else if (kind === "expenses") {
			const part = (g) => { const rows = d.rows.map((r, i) => [r, i]).filter(([r]) => r.group === g);
				return `<h3 class="sk-h">${t(g.toLowerCase())} (${money(rows.reduce((a, [r]) => a + r.amount, 0))})</h3><ul class="sk-list">${rows.map(([r, i]) => li(esc(short(r.ledger)),
					`<span class="chip2 ${r.segment === "Cabin" ? "navy" : r.segment === "Non-Cabin" ? "yel" : ""}">${esc(r.segment)}</span>`, `<div class="sk-col"><b>${money(r.amount)}</b><button class="sk-chip" data-ledger="${i}">›</button></div>`)).join("") || empty()}</ul>`; };
			body = `<p class="sk-note"><b>${money(d.total.amount)}</b></p>${part("Direct")}${part("Indirect")}`;
		} else {
			body = `<p class="sk-note">${t("opening")} ${money(d.total.opening * (kind === "payable" ? 1 : 1))} · ${t("dr")} ${money(d.total.debit)} · ${t("cr")} ${money(d.total.credit)} · <b>${t("closing")} ${money(d.total.closing)}</b></p>
				<ul class="sk-list">${d.rows.map((r, i) => li(esc(short(r.ledger)), `${t("opening")} ${money(r.opening)} · ${t("dr")} ${money(r.debit)} · ${t("cr")} ${money(r.credit)}`,
					`<div class="sk-col"><b class="${r.closing < 0 ? "sk-due" : ""}">${money(r.closing)}</b><button class="sk-chip" data-ledger="${i}">›</button></div>`)).join("") || empty()}</ul>`;
		}
		root.innerHTML = header(t(view)) + `<main>${tabs}${monthNav()}${body}</main>`;
	}
	async function renderLedgerEntries(i) {
		const r = S.ledger.rows[i];
		const kind = S.ledger.kind;
		const d = await call("fin_ledger_entries", { kind, ledger_name: r.ledger, ...(finMonth ? { month: finMonth } : {}) });
		const slug = (dt) => String(dt || "").toLowerCase().replace(/ /g, "-");
		const rows = (kind === "purchase" || kind === "sales")
			? d.rows.map((x) => li(`${x.is_return ? "↩ " : ""}${esc(x.name)}`, `${esc(x.posting_date)} · ${esc(x.status || "")}${x.docstatus === 0 ? ` · <span class="sk-due">${t("drafts_n")}</span>` : ""}`,
				`<div class="sk-col"><b>${money(x.grand_total)}</b><a class="sk-chip" href="/app/${slug(x.doctype)}/${encodeURIComponent(x.name)}">›</a></div>`)).join("")
			: d.rows.map((x) => li(`${esc(x.posting_date)} · ${esc(x.voucher_type)}`, `${esc(x.voucher_no)}${x.party ? " · " + esc(x.party) : ""}${x.remarks ? "<br>" + esc(x.remarks) : x.against ? "<br>" + esc(short(x.against)) : ""}`,
				`<div class="sk-col"><b>${x.debit ? t("dr") + " " + money(x.debit) : t("cr") + " " + money(x.credit)}</b><small>${money(x.balance * (d.sign || 1))}</small><a class="sk-chip" href="/app/${slug(x.voucher_type)}/${encodeURIComponent(x.voucher_no)}">›</a></div>`)).join("");
		state.view = "ledger_entries";
		root.innerHTML = header(short(r.title || r.ledger)) + `<main>${d.opening !== undefined ? `<p class="sk-note">${t("opening")} ${money(d.opening)} → <b>${t("closing")} ${money(d.closing)}</b></p>` : ""}
			<ul class="sk-list">${rows || empty()}</ul><button class="sk-btn wide" data-go="${esc(S.ledger.view)}">‹ ${t("back")}</button></main>`;
	}
	async function renderSegmentWise() {
		const p = await call("fin_segment_wise", finMonth ? { month: finMonth } : {});
		const name = (s) => (s === "Common" ? t("common_cost") : s);
		root.innerHTML = header(t("segment_pnl")) + `<main>${monthNav()}${p.rows.map((r) => `<section class="sk-card ${r.net < 0 ? "" : "sk-saved"}">
			<div class="sk-card-label">${esc(name(r.segment))} · ${t("net_pl")}</div><div class="sk-card-text ${r.net < 0 ? "sk-due" : ""}">${money(r.net)}${r.net_pct == null ? "" : ` · ${r.net_pct}%`}</div>
			<div class="sk-card-meta">${t("income")} ${money(r.income)} · ${t("direct")} ${money(r.direct)} · ${t("gross")} ${money(r.gross)} · ${t("indirect")} ${money(r.indirect)}</div></section>`).join("")}
			<p class="sk-note"><b>${t("net_pl")} ${money(p.total.net)}</b> · ${t("pnl_note")}</p></main>`;
	}
	async function renderMonthWise() {
		const tab = finTab.month_close || "ledger";
		const tabs = `<div class="cal-tabs"><button class="${tab === "ledger" ? "on" : ""}" data-fintab="ledger" data-view="month_close">${t("month_pl")}</button>
			<button class="${tab === "work" ? "on" : ""}" data-fintab="work" data-view="month_close">${t("closing_list")}</button></div>`;
		if (tab === "work") { await renderMonthClose(); root.querySelector("main").insertAdjacentHTML("afterbegin", tabs); return; }
		const p = await call("fin_month_wise");
		const mon = (m) => new Date(m + "-01").toLocaleDateString(state.lang === "Marathi" ? "mr-IN" : "en-IN", { month: "short", year: "2-digit" });
		root.innerHTML = header(t("month_close")) + `<main>${tabs}<div class="sk-table-wrap"><table class="sk-table"><tr><th></th><th>${t("income")}</th><th>${t("direct")}</th><th>${t("indirect")}</th><th>${t("net")}</th></tr>
			${p.rows.map((r) => `<tr><td>${esc(mon(r.month))}</td><td>${lakh(r.income)}</td><td>${lakh(r.direct)}</td><td>${lakh(r.indirect)}</td><td class="${r.net < 0 ? "sk-due" : ""}"><b>${lakh(r.net)}</b></td></tr>`).join("")}
			<tr><th>Σ</th><th>${lakh(p.total.income)}</th><th>${lakh(p.total.direct)}</th><th>${lakh(p.total.indirect)}</th><th>${lakh(p.total.net)}</th></tr></table></div>
			<p class="sk-note">${t("pnl_note")}</p></main>`;
	}

	async function renderMonthClose() {
		S.close = await call("fin_month_close");
		root.innerHTML = header(t("month_close")) + `<main><ul class="sk-list">${S.close.map((c, i) => li(`${c.done ? "✅" : c.late ? "🔴" : "⬜"} ${t("mc_" + c.key)}`,
			`${t("by_date")} ${esc(c.due)}${c.done ? ` · ${esc(c.by || "")} ${esc(c.on || "")}` : ""}`,
			`<button class="sk-chip ${c.done ? "" : "on"}" data-act="fin-tick" data-i="${i}">${c.done ? "↺" : "✓ " + t("done")}</button>`)).join("")}</ul></main>`;
	}

	async function finAct(act, el) {
		const i = Number(el.dataset.i);
		switch (act) {
			case "fin-wa": {
				const r = S.dues[i];
				const msg = `${t("wa_due_1")} ${r.customer_name},\n${t("wa_due_2")} ${r.name} ${t("wa_due_3")} ${money(r.outstanding_amount)} (${t("due")} ${r.due_date}).\n${t("wa_due_4")}\n- SK Ind Tech Solutions`;
				return window.open("https://wa.me/" + waNumber(r.mobile) + "?text=" + encodeURIComponent(msg), "_blank");
			}
			case "fin-promise": S.inv = S.dues[i];
				return sheet(`<h3 class="sk-h">🤝 ${esc(S.inv.customer_name)} · ${money(S.inv.outstanding_amount)}</h3>${formField("fp-text", t("what_customer_said"), true)}
					<label class="sk-field"><span>${t("promised_on")}</span><input id="fp-date" type="date" class="sk-select"></label>
					<button class="sk-btn ok wide" data-act="fin-promise-save">${t("save")}</button><button class="sk-btn wide" data-act="close-sheet">${t("back")}</button>`);
			case "fin-promise-save": el.disabled = true;
				await call("fin_promise", { sales_invoice: S.inv.name, text: val("fp-text"), promised_on: val("fp-date") || null }, true);
				closeSheet(); toast(t("saved")); return go("to_collect");
			case "fin-recv": S.inv = S.dues[i];
				return sheet(`<h3 class="sk-h">₹ ${esc(S.inv.customer_name)} · ${esc(S.inv.name)}</h3>${payFields("fr", S.inv.outstanding_amount)}
					<button class="sk-btn ok wide" data-act="fin-recv-save">${t("save_payment")}</button><button class="sk-btn wide" data-act="close-sheet">${t("back")}</button>`);
			case "fin-recv-save": {
				el.disabled = true;
				const r = await call("fin_receive", { reference_doctype: "Sales Invoice", reference_name: S.inv.name, amount: val("fr-amt"), mode: val("fr-mode") || null,
					reference_no: val("fr-ref") || null, reference_date: val("fr-date"), photo: await photoUrl("fr-photo") }, true);
				closeSheet(); toast(r.posted ? `✓ ${r.name}` : `${r.name}: ${t("kept_draft")}`, !r.posted); return go("to_collect");
			}
			case "fin-ask": await call("fin_ask_approval", { purchase_invoice: S.bills[i].name }, true); return toast(t("asked_sk"));
			case "fin-approve": await call("fin_approve_payment", { purchase_invoice: S.bills[i].name }, true); toast(t("approved")); return go("pay_approvals");
			case "fin-pay": S.bill = S.bills[i];
				return sheet(`<h3 class="sk-h">₹ ${esc(S.bill.supplier_name)} · ${esc(S.bill.name)}</h3>${payFields("fy", S.bill.outstanding_amount)}
					<button class="sk-btn ok wide" data-act="fin-pay-save">${t("save_payment")}</button><button class="sk-btn wide" data-act="close-sheet">${t("back")}</button>`);
			case "fin-pay-save": {
				el.disabled = true;
				const r = await call("fin_pay", { purchase_invoice: S.bill.name, amount: val("fy-amt"), mode: val("fy-mode") || null, reference_no: val("fy-ref") || null,
					reference_date: val("fy-date"), photo: await photoUrl("fy-photo") }, true);
				closeSheet(); toast(r.posted ? `✓ ${r.name}` : `${r.name}: ${t("kept_draft")}`, !r.posted); return go("to_pay");
			}
			case "fin-bill": S.photo = S.fb.photos[i];
				return sheet(`<h3 class="sk-h">🧾 ${esc(S.photo.supplier_name || "")}</h3><p class="sk-note">${esc(S.photo.description)}</p>
					${pick("fb-po", t("against_po"), S.photo.orders.map((o) => ({ value: o.name, label: `${o.name} · ${money(o.grand_total)} · ${o.transaction_date}` })))}
					${formField("fb-no", t("supplier_bill_no"))}<label class="sk-field"><span>${t("bill_date")}</span><input id="fb-date" type="date" class="sk-select" value="${new Date().toISOString().slice(0, 10)}"></label>
					<button class="sk-btn ok wide" data-act="fin-bill-save">${t("make_bill")}</button><button class="sk-btn wide" data-act="close-sheet">${t("back")}</button>
					${S.photo.orders.length ? "" : `<p class="sk-note">⚠ ${t("no_po_bill")}</p>`}`);
			case "fin-bill-save": {
				if (!val("fb-po")) return toast(t("pick_po"), true);
				el.disabled = true;
				const r = await call("fin_make_bill", { purchase_order: val("fb-po"), bill_no: val("fb-no"), bill_date: val("fb-date"), todo: S.photo.name }, true);
				closeSheet(); toast(`${r.name}: ${t("draft_made")}`); return go("bills_to_post");
			}
			case "fin-bill-done": await call("fin_bill_photo_done", { todo: S.fb.photos[i].name }, true); return go("bills_to_post");
			case "fin-post-pi": case "fin-post-si": {
				el.disabled = true;
				const d = act === "fin-post-pi" ? S.fb.drafts[i] : S.fi.drafts[i];
				const r = await call("fin_post", { doctype: act === "fin-post-pi" ? "Purchase Invoice" : "Sales Invoice", name: d.name }, true);
				toast(r.posted ? `✓ ${r.name} ${t("posted")}` : `${r.name}: ${r.reason || t("kept_draft")}`, !r.posted);
				return go(act === "fin-post-pi" ? "bills_to_post" : "invoices");
			}
			case "fin-make-inv": { el.disabled = true; const r = await call("fin_make_invoice", { delivery_note: S.fi.to_bill[i].name }, true); toast(`${r.name}: ${t("draft_made")}`); return go("invoices"); }
			case "fin-pay-claim": { el.disabled = true; const r = await call("fin_pay_expense", { expense_claim: S.claims[i].name }, true); toast(r.posted ? `✓ ${r.name}` : `${r.name}: ${t("kept_draft")}`, !r.posted); return go("expenses"); }
			case "fin-voucher": {
				const o = await call("fin_voucher_options");
				return sheet(`<h3 class="sk-h">📷 ${t("petty_cash")}</h3>${photoField("pv-photo", "📷 " + t("voucher_photo"))}${formField("pv-text", t("spent_on"), true)}
					<label class="sk-field"><span>${t("amount")}</span>${qtyBox("pv-amt")}</label>${pick("pv-exp", t("expense_head"), o.expense_accounts)}
					${pick("pv-cash", t("paid_from"), o.cash_accounts)}${pick("pv-cc", t("segment"), o.cost_centers)}
					<button class="sk-btn ok wide" data-act="fin-voucher-save">${t("save")}</button><button class="sk-btn wide" data-act="close-sheet">${t("back")}</button>`);
			}
			case "fin-voucher-save": {
				el.disabled = true;
				const r = await call("fin_petty_cash", { expense_account: val("pv-exp"), amount: val("pv-amt"), cash_account: val("pv-cash"), cost_center: val("pv-cc") || null,
					narration: val("pv-text"), photo: await photoUrl("pv-photo") }, true);
				closeSheet(); toast(r.posted ? `✓ ${r.name}` : `${r.name}: ${t("kept_draft")}`, !r.posted); return go("expenses");
			}
			case "fin-tick": { const c = S.close[i]; await call("fin_tick_close", { key: c.key, done: c.done ? 0 : 1 }, true); return go("month_close"); }
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

	// ---------- AI & ERP desk (Samir, points 9a / 9d / 9e) ----------
	async function renderInbox() {
		const d = await call("ai_inbox");
		S.inbox = d;
		const row = (x, i, working) => li(`${x.kind === "dsi" ? "💡" : "🚩"} ${esc(x.title)}`,
			`${esc(x.by)} · ${esc(x.date)} · ${esc(working ? x.category : x.type || "")}${working && x.due ? ` · ${t("due")} ${esc(x.due)}` : ""}`,
			working ? `<button class="sk-chip ok" data-aiclose="${esc(x.todo)}">✓</button>` : `<button class="sk-chip on" data-aisort="${i}">${t("sort_as")}</button>`,
			x.kind === "dsi" ? "" : "k-lead_new");
		root.innerHTML = header(t("improvement_inbox")) + `<main>
			<h3 class="sk-h">${t("inbox_new")} (${d.new.length})</h3><ul class="sk-list">${d.new.map((x, i) => row(x, i, false)).join("") || empty()}</ul>
			<h3 class="sk-h">${t("inbox_working")} (${d.working.length})</h3><ul class="sk-list">${d.working.map((x, i) => row(x, i, true)).join("") || empty()}</ul></main>`;
	}
	function aiSortSheet(i) {
		const x = S.inbox.new[i];
		sheet(`<h3 class="sk-h">${t("sort_as")}</h3><p class="sk-note">${esc(x.title)}<br><small>${esc(x.by)} · ${esc(x.date)}</small></p>
			${formField("ai-note", t("comment"))}
			<div class="sk-row sk-wrap">${S.inbox.categories.map((c) => `<button class="sk-chip ${c === "Not needed" ? "" : "on"}" data-aicat="${esc(c)}" data-i="${i}">${esc(c)}</button>`).join("")}</div>
			<button class="sk-btn wide" data-act="close-sheet">${t("back")}</button>`);
	}
	async function renderVisit() {
		const d = await call("ai_visit");
		root.innerHTML = header(t("dept_visits")) + `<main>
			<div class="sk-score"><div>${esc(d.department)}</div><small>${d.people.length} ${t("people_n2")} · ${d.not_today} ${t("not_today")}</small></div>
			<ul class="sk-list">${d.people.map((p) => li(esc(p.full_name), `${esc(p.function || "")} · ${p.today ? "✅ " + t("logged_today") : "⚠ " + t("not_today")} · DSI ${p.dsi_week}`, "", p.today ? "" : "k-lead_new")).join("") || empty()}</ul>
			<h3 class="sk-h">${t("problems_open")} (${d.problems.length})</h3>
			<ul class="sk-list">${d.problems.map((r) => li(esc(r.description), `${esc(r.problem_type || "")} · ${esc(r.date)}`)).join("") || empty()}</ul>
			${formField("ai-vnote", t("visit_note"), true)}<button class="sk-btn ok wide" data-act="ai-visit-note" data-dept="${esc(d.department)}">${t("save")}</button>
			<h3 class="sk-h">${t("last_notes")}</h3><ul class="sk-list">${d.notes.map((n) => li(esc(n.description), esc(n.date))).join("") || empty()}</ul>
			<h3 class="sk-h">${t("visit_plan")}</h3><ul class="sk-list">${d.plan.map((p) => li(t("d_" + ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"][p.day]), esc(p.department))).join("")}</ul></main>`;
	}
	async function renderGaps() {
		const rows = await call("ai_gaps");
		root.innerHTML = header(t("erp_gaps")) + `<main><ul class="sk-list">${rows.map((r) => li(esc(r.label),
			r.kind === "gap" ? `<b class="${r.count ? "sk-due" : ""}">${num(r.count)}</b> ${t("of_word")} ${num(r.of)}` : `${num(r.count)} ${t("made_word")}`,
			`<a class="sk-open" href="${esc(r.link)}">›</a>`, r.kind === "gap" && r.count ? "k-lead_new" : "")).join("") || empty()}</ul></main>`;
	}
	async function renderAppUsers() {
		const d = await call("ai_app_users");
		const lab = { today: "✅ " + t("logged_today"), earlier: "⚠ " + t("earlier"), never: "⛔ " + t("never") };
		root.innerHTML = header(t("app_users")) + `<main><div class="sk-score"><div>${d.today} / ${d.total}</div><small>${t("logged_today")}</small></div>
			<ul class="sk-list">${d.rows.map((r) => li(esc(r.full_name || r.user), `${esc(r.function || "")} · ${lab[r.state]}${r.last_login ? " · " + esc(r.last_login.slice(0, 16)) : ""}${r.first_pin ? " · " + t("first_pin_left") : ""}${r.problems ? ` · 🚩 ${r.problems}` : ""}`,
				"", r.state === "today" ? "" : "k-lead_new")).join("") || empty()}</ul></main>`;
	}
	async function renderChangeList() {
		const rows = await call("ai_change_list");
		const states = ["SK OK", "Building", "Testing", "Live"];
		root.innerHTML = header(t("change_list")) + `<main><ul class="sk-list">${rows.map((r) => `<li class="sk-item"><div class="sk-grow"><div class="sk-item-title">${r.no}. ${esc(r.title)}</div>
			<div class="sk-row sk-wrap">${states.map((s) => `<button class="sk-chip ${r.status === s ? "on" : ""}" data-chg="${r.no}" data-st="${esc(s)}">${esc(s)}</button>`).join("")}</div></div></li>`).join("")}</ul></main>`;
	}
	async function renderProjects() {
		const rows = await call("ai_projects");
		root.innerHTML = header(t("projects")) + `<main><ul class="sk-list">${rows.map((p) => li(esc(p.title || p.name),
			`${p.percent}% · ${p.open} ${t("open_tasks")}${p.late ? ` · <span class="sk-due">${p.late} ${t("late_tasks")}</span>` : ""}${p.end ? " · " + esc(p.end) : ""}`,
			`<a class="sk-open" href="/app/project/${encodeURIComponent(p.name)}">›</a>`)).join("") || empty()}</ul>
			<a class="sk-btn wide" href="/app/project/new">＋ ${t("projects")}</a></main>`;
	}
	async function renderTrainingProgress() {
		const rows = await call("ai_training");
		root.innerHTML = header(t("training_progress")) + `<main><ul class="sk-list">${rows.map((r) => `<li class="sk-kpi c-${r.done_pct >= 80 ? "green" : r.done_pct >= 50 ? "yellow" : "red"}">
			<div class="sk-kpi-top"><span>${esc(r.function)}</span><span>${r.done_pct}%</span></div><div class="sk-bar"><div style="width:${r.done_pct}%"></div></div>
			<div class="sk-kpi-num">${r.people} ${t("people_n2")} · ${r.lessons} ${t("lessons_n")} · ${r.finished} ${t("finished_n")}</div></li>`).join("") || empty()}</ul></main>`;
	}

	// opened from a link inside WhatsApp / Facebook: their small browsers often have no voice typing (point 4)
	function inAppBrowserBanner() {
		if (!/FBAN|FBAV|FB_IAB|Instagram|WhatsApp|; wv\)/i.test(navigator.userAgent) || document.querySelector(".sk-chrome")) return;
		const a = document.createElement("a");
		a.className = "sk-banner sk-chrome";
		a.href = `intent://${location.host}/sk#Intent;scheme=https;package=com.android.chrome;end`;
		a.textContent = "🌐 " + t("open_chrome");
		document.body.prepend(a);
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
		my_fixes: () => renderNcs("my_fixes"), inspect: () => renderInspect("inspect"), final_check: () => renderInspect("final_check"),
		cash_today: () => finScreen("cash_today", renderCash), to_collect: () => finScreen("to_collect", renderCollect),
		to_pay: () => finScreen("to_pay", () => renderToPay("to_pay")), pay_approvals: () => renderToPay("pay_approvals"),
		bills_to_post: () => finScreen("bills_to_post", renderBillsToPost), invoices: () => finScreen("invoices", renderInvoices),
		expenses: () => finScreen("expenses", renderExpenses), dir_expenses: () => finScreen("dir_expenses"),
		segment_pnl: renderSegmentWise, month_close: renderMonthWise,
		improvement_inbox: renderInbox, dept_visits: renderVisit, erp_gaps: renderGaps, app_users: renderAppUsers, change_list: renderChangeList,
		projects: renderProjects, training_progress: renderTrainingProgress, lead_sources: renderLeadSources, customers: renderCustomers, view_member: renderViewMember, complaints: renderComplaints,
		attendance: renderAttendance, leave_expense: renderLeaveExpense };
	["overview", "daily_review", "sales", "marketing", "machine_shifting", "job_work", "cr100", "finance", "manufacturing", "purchase",
		"store", "quality", "hr", "ai"].forEach((k) => { LIVE_VIEWS["dash_" + k] = () => renderDash(k); });

	const reported = new Set();
	function reportError(view, msg) {
		const key = view + msg;
		if (reported.has(key)) return;
		reported.add(key);
		call("report_screen_error", { view, message: String(msg).slice(0, 300) }, true).catch(() => {});
	}

	async function go(view) {
		stopListening(); // a mic left on keeps listening into the old screen (point 4)
		closeSheet();
		if (view === "erpnext_desk") { window.location.href = "/app"; return; }
		if (view !== state.view) clearDraftIfOther(view);
		state.view = view;
		if (view === "home") contacts = null;
		try {
			if (view === "home") {
				renderHome();
				// red counts change as jobs are done and checks are saved: refresh them quietly
				return call("home").then((h) => { if (reloadIfNew(h)) return; state.home = h; if (state.view === "home" && !document.querySelector(".sk-sheet")) renderHome(); }).catch(() => {});
			}
			const fn = LIVE_VIEWS[view];
			return fn ? await fn() : renderSoon(view);
		} catch (e) {
			if (view !== "home" && state.view === view) {
				root.innerHTML = header(t(view)) + `<main><p class="sk-note bad">⚠ ${esc(e.message)}</p>
					<button class="sk-btn wide" data-go="${esc(view)}">↻ ${t("refresh")}</button><button class="sk-btn wide" data-go="home">${t("back")}</button></main>`;
				reportError(view, e.message);
			} else toast(e.message, true);
		}
	}

	// view only: no call, WhatsApp or mail goes out in the member's name
	document.addEventListener("click", (ev) => {
		if (!state.viewAs) return;
		const a = ev.target.closest('a[href^="tel:"], a[href^="mailto:"], a[href*="wa.me"], a[href^="whatsapp:"], a[href^="sms:"]');
		if (a) { ev.preventDefault(); ev.stopPropagation(); toast(t("view_only")); }
	}, true);

	root.addEventListener("click", async (ev) => {
		const el = ev.target.closest("button, [data-go]");
		if (!el) return;
		try {
			if (el.dataset.go) { if (el.dataset.go === "follow_up") fuCalls = false; return go(el.dataset.go); }
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
			if (el.dataset.pick) return pickFile(el.dataset.pick, el.dataset.how);
			if (el.dataset.mailtab) { mailTab = el.dataset.mailtab; return go("mail"); }
			if (el.dataset.dcard !== undefined) return renderDashList(Number(el.dataset.dcard));
			if (el.dataset.drow !== undefined) return openDashRow(Number(el.dataset.dcardi), Number(el.dataset.drow));
			if (el.dataset.dashseg !== undefined) { dashSeg = el.dataset.dashseg; return go(state.view); }
			if (el.dataset.dashmonth) {
				const d = dashMonth ? new Date(dashMonth) : new Date();
				d.setDate(1); d.setMonth(d.getMonth() + Number(el.dataset.dashmonth));
				dashMonth = `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-01`;
				return go(state.view);
			}
			if (el.dataset.apply !== undefined) {
				const inp = document.getElementById(el.dataset.apply);
				if (inp) {
					const before = inp.value;
					inp.value = el.dataset.val;
					if (el.dataset.learn) call("photo_learn", { kind: el.dataset.learn, read_text: before, chosen: el.dataset.val }, true).catch(() => {});
					runCheck();
				}
				return;
			}
			if (el.dataset.cptab) { cpTab = el.dataset.cptab; return go("complaints"); }
			if (el.dataset.atttab) { attTab = el.dataset.atttab; return go("attendance"); }
			if (el.dataset.attmonth) {
				const d = new Date((attMonth || new Date().toISOString().slice(0, 7) + "-01") + "T00:00:00");
				d.setMonth(d.getMonth() + Number(el.dataset.attmonth));
				attMonth = `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-01`;
				return go("attendance");
			}
			if (el.dataset.lvtab) { lvTab = el.dataset.lvtab; return go("leave_expense"); }
			if (el.dataset.cp) return complaintSheet(el.dataset.cp);
			if (el.dataset.custtab) { custTab = el.dataset.custtab; return go("customers"); }
			if (el.dataset.custseg !== undefined) { custSeg = el.dataset.custseg; return go("customers"); }
			if (el.dataset.tmail !== undefined) return teamMailSheet(Number(el.dataset.tmail));
			if (el.dataset.fintab) { finTab[el.dataset.view] = el.dataset.fintab; return go(el.dataset.view); }
			if (el.dataset.ledger !== undefined) return renderLedgerEntries(Number(el.dataset.ledger));
			if (el.dataset.finmonth) {
				const d = finMonth ? new Date(finMonth) : new Date();
				d.setDate(1); d.setMonth(d.getMonth() + Number(el.dataset.finmonth));
				finMonth = `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-01`;
				return go(state.view);
			}
			if (el.dataset.unpick) { const inp = document.getElementById(el.dataset.unpick); inp.value = ""; return photoPicked(inp); }
			if (el.dataset.ltab) { leadTab = el.dataset.ltab; return go("my_leads"); }
			if (el.dataset.move) return moveSheet(el.dataset.move, el.dataset.title);
			if (el.dataset.moveday !== undefined) {
				await call("cal_move", { key: el.dataset.key, day: el.dataset.moveday || null }, true);
				closeSheet();
				toast(t("saved"));
				return go("calendar");
			}
			if (el.dataset.aisort) return aiSortSheet(Number(el.dataset.aisort));
			if (el.dataset.aicat) {
				const x = S.inbox.new[Number(el.dataset.i)];
				await call("ai_sort", { doctype: x.doctype, name: x.name, category: el.dataset.aicat, note: val("ai-note") || null }, true);
				closeSheet();
				toast(t("saved"));
				return go("improvement_inbox");
			}
			if (el.dataset.aiclose) {
				sheet(`<h3 class="sk-h">✅ ${t("works_close")}</h3>${formField("ai-fix", t("fix_note"), true)}
					<button class="sk-btn ok wide" data-act="ai-close" data-todo="${esc(el.dataset.aiclose)}">${t("save")}</button>
					<button class="sk-btn wide" data-act="close-sheet">${t("back")}</button>`);
				return;
			}
			if (el.dataset.chg) {
				await call("ai_set_change", { no: el.dataset.chg, status: el.dataset.st }, true);
				return go("change_list");
			}
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
			if (act && act.startsWith("fin-")) return await finAct(act, el);
			if (el.dataset.qok !== undefined) {
				const k = el.dataset.qok;
				root.querySelectorAll(`[data-qok="${k}"]`).forEach((c) => c.classList.remove("on"));
				el.classList.add("on");
				document.getElementById("q-note-wrap-" + k).hidden = el.dataset.v === "1";
				return;
			}
			if (act === "face-setup") {
				try {
					lockInfo = await faceSetup();
					closeSheet();
					toast("✓ " + t("lk_setup_done"));
				} catch (e) { toast(e.name === "NotAllowedError" ? t("lk_cancelled") : e.message, true); }
				return;
			}
			if (act === "login-face") {
				const p = root._people && root._people[Number(el.dataset.i)];
				if (!p || !confirm(`${p.name}: ${t("lk_reset_q")}`)) return;
				const r = await call("reset_face", { user: p.user }, true);
				toast(`✓ ${t("lk_reset_done")} (${r.reset})`);
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
			if (act === "login-bulk-open") return bulkSheet();
			if (act === "login-bulk") {
				el.disabled = true;
				const rows = await call("hr_bulk_logins", { text: val("g-bulk") }, true);
				closeSheet();
				return bulkResult(rows);
			}
			if (act === "login-bulk-wa") {
				const r = root._bulk[Number(el.dataset.i)];
				const msg = `${t("login_link")}: ${location.origin}/sk\n${t("mobile")}: ${r.mobile}\n${t("first_pin")}: ${r.pin}`;
				return window.open("https://wa.me/" + waNumber(r.mobile) + "?text=" + encodeURIComponent(msg), "_blank");
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
				if (state.viewAs) return go(state.view); // the member's own language setting is not changed
				await call("set_language", { language: state.lang }, true);
				state.card = await call("next_card", { force: 1 }, true);
				return go(state.view);
			}
			if (act === "save-dsi") {
				el.disabled = true;
				await call("add_dsi", { what_changed: val("f-what"), before_text: val("f-before"), after_text: val("f-after"), photo: await photoUrl() }, true);
				clearDraft();
				toast(t("saved"));
				return go("home");
			}
			if (act === "save-work") {
				el.disabled = true;
				const chip = root.querySelector(".sk-chip.on");
				await call("add_work", { description: val("f-desc"), entry_type: el.dataset.kind, problem_type: chip ? chip.dataset.ptype : null, photo: await photoUrl() }, true);
				toast(t("saved"));
				clearDraft();
				return go(el.dataset.kind === "Problem" ? "home" : "my_day");
			}
			if (act === "close-sheet") { pending = null; return closeSheet(); }
			if (act && act.startsWith("tm-")) {
				const comm = el.dataset.comm;
				el.disabled = true;
				if (act === "tm-take") await call("team_mail_take", { comm }, true);
				if (act === "tm-notlead") await call("team_mail_not_lead", { comm }, true);
				if (act === "tm-give") { if (!val("tm-give")) throw new Error(t("give_to")); await call("team_mail_give", { comm, to_user: val("tm-give") }, true); }
				if (act === "tm-reply") await call("team_mail_reply", { comm, message: val("tm-reply") }, true);
				if (act === "tm-lead") {
					const r = await call("team_mail_lead", { comm }, true);
					closeSheet();
					toast(`✅ ${t("lead_saved")}: ${r.lead}`);
					current = { doctype: "CRM Lead", name: r.lead };
					return go("detail");
				}
				closeSheet();
				toast(t("saved"));
				return go("mail");
			}
			if (act === "faq-ask") {
				sheet(`<h3 class="sk-h">❓ ${t("faq_ask")}</h3>${formField("faq-text", t("faq_q"), true)}
					<button class="sk-btn ok wide" data-act="faq-ask-send">${t("send")}</button><button class="sk-btn wide" data-act="close-sheet">${t("back")}</button>`);
				return;
			}
			if (act === "faq-ask-send") { const r = await call("training_ask", { question: val("faq-text") }, true); closeSheet(); toast(`${t("faq_sent")} ${r.owner}`); return; }
			if (act === "faq-answer") {
				const a = S.faqAsk[Number(el.dataset.i)];
				sheet(`<h3 class="sk-h">❓ ${esc(a.question)}</h3><p class="sk-item-meta">${esc(a.by)}</p>${formField("faq-ans", t("faq_answer"), true)}
					<label class="sk-row"><input type="checkbox" id="faq-add" checked> ${t("faq_add")}</label>
					<button class="sk-btn ok wide" data-act="faq-answer-send" data-todo="${esc(a.name)}">${t("send")}</button><button class="sk-btn wide" data-act="close-sheet">${t("back")}</button>`);
				return;
			}
			if (act === "faq-answer-send") {
				await call("training_answer", { todo: el.dataset.todo, text: val("faq-ans"), add_to_faq: document.getElementById("faq-add").checked ? 1 : 0 }, true);
				closeSheet(); toast(t("saved")); return go("training");
			}
			if (act === "p-send") return waTextSheet(productMessage(S.pcards[Number(el.dataset.i)]));
			if (act === "cp-new") return renderNewComplaint();
			if (act === "cp-save") {
				const cust = val("cp-cust");
				const o = [...document.querySelectorAll("#cp-cust-dl option")].find((x) => x.value === cust);
				if (!o) { toast(t("cp_pick_customer"), true); return; }
				el.disabled = true;
				try {
					const files = [await photoUrl("cp-f1"), await photoUrl("cp-f2")].filter(Boolean);
					const r = await call("complaint_new", { customer: cust, text: val("cp-text"), ctype: val("cp-type"), sales_order: val("cp-order"), files: JSON.stringify(files) }, true);
					clearDraft();
					toast(`${t("cp_sent")} ${r.person || r.function}`);
				} finally { el.disabled = false; }
				cpTab = "mine";
				return go("complaints");
			}
			if (act === "cp-accept") { await call("complaint_accept", { name: el.dataset.name, fix_by: val("cp-date") }, true); toast(t("saved")); return complaintSheet(el.dataset.name); }
			if (act === "cp-fixed") {
				el.disabled = true;
				try { await call("complaint_fixed", { name: el.dataset.name, note: val("cp-done"), photo: await photoUrl("cp-after") }, true); } finally { el.disabled = false; }
				closeSheet(); toast(t("saved")); return go("complaints");
			}
			if (act === "cp-ok") {
				await call("complaint_customer", { name: el.dataset.name, ok: el.dataset.ok, note: val("cp-note"), photo: await photoUrl("cp-proof") }, true);
				closeSheet(); toast(t("saved")); return go("complaints");
			}
			if (act === "att-me") return attSheet();
			if (act === "att-selfie") {
				const photo = await photoUrl("att-selfie");
				if (!photo) { toast(t("photo"), true); return; }
				el.disabled = true;
				try {
					const r = await call("attendance_selfie", { photo, ...(await where()) }, true);
					toast(`✓ ${r.log_type} ${r.time}`);
				} finally { el.disabled = false; }
				closeSheet(); return go("my_day");
			}
			if (act === "att-ask") {
				await call("attendance_ask_fix", { text: val("att-fix"), day: val("att-day") }, true);
				closeSheet(); toast(t("saved")); return;
			}
			if (act === "att-fixsheet") return attFixSheet(S.attFix[Number(el.dataset.i)]);
			if (act === "att-fix") {
				await call("hr_fix", { employee: el.dataset.employee, day: val("fx-day"), status: val("fx-status"), reason: val("fx-reason"), todo: el.dataset.todo }, true);
				closeSheet(); toast(t("saved")); return go("attendance");
			}
			if (act === "att-preview") {
				const url = await photoUrl("att-file");
				if (!url) { toast(t("att_file"), true); return; }
				el.disabled = true;
				try { attPreview = { ...(await call("hr_upload_preview", { file_url: url, device: val("att-device") || "Optick" }, true)), file_url: url }; } finally { el.disabled = false; }
				return go("attendance");
			}
			if (act === "att-save") {
				const p = attPreview, matches = {};
				p.not_found.forEach((r, i) => { const v = val("att-m-" + i); if (v) matches[r.id || r.mobile || r.name] = v; });
				el.disabled = true;
				try {
					const r = await call("hr_upload_save", { file_url: p.file_url, matches: JSON.stringify(matches), device: p.device }, true);
					document.getElementById("att-result").innerHTML = `<p class="sk-note">✅ ${r.checkins} ${t("att_made")} · ${r.attendance} ${t("att_att_made")} · ${r.missed_out} ${t("att_missed_out")}${r.not_matched ? ` · ${r.not_matched} ${t("att_skip")}` : ""}</p>
						${r.errors.map((x) => `<p class="sk-note bad">⚠ ${esc(x)}</p>`).join("")}`;
					attPreview = null;
				} finally { el.disabled = false; }
				return;
			}
			if (act === "lv-apply") {
				el.disabled = true;
				try {
					const r = await call("leave_apply", { leave_type: val("lv-type"), from_date: val("lv-from"), to_date: val("lv-to") || val("lv-from"),
						half_day: document.getElementById("lv-half").checked ? 1 : 0, reason: val("lv-reason") }, true);
					clearDraft(); toast(`${t("lv_sent")} ${r.approver || "HR"}`);
				} finally { el.disabled = false; }
				return go("leave_expense");
			}
			if (act === "ex-claim") {
				el.disabled = true;
				try {
					const r = await call("expense_claim", { expense_type: val("ex-type"), amount: val("ex-amt"), expense_date: val("ex-date"), note: val("ex-note"), photo: await photoUrl("ex-photo") }, true);
					clearDraft(); toast(`${t("lv_sent")} ${r.approver || "HR"}`);
				} finally { el.disabled = false; }
				return go("leave_expense");
			}
			if (act === "lv-decide") {
				el.disabled = true;
				try {
					const r = await call(el.dataset.kind === "leave" ? "leave_decide" : "expense_decide", { name: el.dataset.name, ok: el.dataset.ok }, true);
					toast(r.posted ? t("ex_posted") : r.status);
				} finally { el.disabled = false; }
				return go("leave_expense");
			}
			if (act === "view-enter") return enterView(el.dataset.user, el.dataset.uname);
			if (act === "view-exit") return exitView();
			if (act === "view-idea") {
				sheet(`<h3 class="sk-h">💡 ${esc(state.viewAs.name)} · ${esc(t(state.view))}</h3>${formField("vi-text", t("idea_q"), true)}
					<button class="sk-btn ok wide" data-act="view-idea-save">${t("save")}</button><button class="sk-btn wide" data-act="close-sheet">${t("back")}</button>`);
				return;
			}
			if (act === "view-idea-save") {
				await call("view_suggest", { member: state.viewAs.user, view: state.view, text: val("vi-text") }, true);
				closeSheet();
				toast(t("idea_sent"));
				return;
			}
			if (act === "cust-tally") {
				const r = await call("tag_customers_from_tally", {}, true);
				toast(`✓ ${t("seg_cabin")} ${r.cabin} · ${t("seg_noncabin")} ${r.non_cabin}`);
				return go("customers");
			}
			if (act === "cust-tag") {
				const r = S.cust[Number(el.dataset.i)];
				await call("tag_customer", { customer: r.name, segment: el.dataset.seg }, true);
				toast(t("saved"));
				return go("customers");
			}
			if (act === "ls-check") { const r = await call("lead_sources_check_now", {}, true); toast(`${r.made || 0} ${t("leads_made")}`); return go("lead_sources"); }
			if (act === "ls-switch") { await call("lead_sources_switch", { setting: el.dataset.setting, on: el.dataset.on }, true); return go("lead_sources"); }
			if (act === "ls-upload") {
				const url = await photoUrl("ls-file");
				if (!url) throw new Error(t("upload_list"));
				el.disabled = true;
				const r = await call("leads_upload", { file_url: url, source: val("ls-src") || "IndiaMART" }, true);
				document.getElementById("ls-result").innerHTML = `<p class="sk-note">✅ ${r.made} ${t("leads_made")} · ${r.added_to_old} ${t("added_old")} · ${r.skipped} ${t("skipped_n")}</p>`;
				el.disabled = false;
				return;
			}
			if (act === "ai-close") {
				el.disabled = true;
				await call("ai_close", { todo: el.dataset.todo, note: val("ai-fix") || null }, true);
				closeSheet();
				toast(t("saved"));
				return go("improvement_inbox");
			}
			if (act === "ai-visit-note") {
				el.disabled = true;
				await call("ai_visit_note", { department: el.dataset.dept, text: val("ai-vnote") }, true);
				toast(t("saved"));
				return go("dept_visits");
			}
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
			if (act === "call-follow") { fuCalls = true; fuQuery = ""; return go("follow_up"); }
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
				if (!val("f-segment")) { toast(t("pick_segment")); document.getElementById("f-segment").focus(); return; }
				el.disabled = true;
				const name = await call("new_lead", { first_name: val("f-first"), organization: val("f-org"), mobile_no: val("f-mobile"),
					email: val("f-email"), source: val("f-source"), segment: val("f-segment"), requirement: val("f-req"), photo: cardUrl, product: val("f-product") }, true);
				const dz = document.getElementById("f-design");
				if (dz && dz.checked && !document.getElementById("f-design-row").hidden) {
					const r = await call("lead_to_design", { name }, true).catch((e) => ({ sent: false, reason: e.message }));
					toast(r.sent ? `✏️ ${t("design_sent")} ${r.deal}` : `⚠ ${t("design_not_sent")} ${r.reason || ""}`, !r.sent);
				}
				cardUrl = null;
				clearDraft();
				return leadSaved({ name, title: val("f-org") || val("f-first"), person: val("f-first"), mobile: val("f-mobile"),
					segment: val("f-segment"), source: val("f-source") });
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


	// ---------- App lock (point 20, SK 26-Oct): face / finger only after set-up, locks after 30 min without use ----------
	const b64u = {
		dec: (s) => Uint8Array.from(atob(s.replace(/-/g, "+").replace(/_/g, "/") + "===".slice((s.length + 3) % 4)), (c) => c.charCodeAt(0)),
		enc: (buf) => btoa(String.fromCharCode(...new Uint8Array(buf))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, ""),
	};
	const canFace = async () => {
		try { return !!(window.PublicKeyCredential && await PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable()); } catch (e) { return false; }
	};
	let lockInfo = null, lastTouch = Date.now(), lockHit = false;
	["touchstart", "click", "keydown", "scroll"].forEach((ev) => document.addEventListener(ev, () => { lastTouch = Date.now(); }, { passive: true, capture: true }));
	async function faceUnlock() {
		const o = await call("face_options", { purpose: "unlock" }, true);
		const cred = await navigator.credentials.get({ publicKey: { challenge: b64u.dec(o.challenge), rpId: o.rpId, timeout: o.timeout,
			userVerification: "required", allowCredentials: o.allowCredentials.map((c) => ({ type: "public-key", id: b64u.dec(c.id) })) } });
		return call("face_unlock", { credential: { id: cred.id, rawId: b64u.enc(cred.rawId), type: cred.type, response: {
			clientDataJSON: b64u.enc(cred.response.clientDataJSON), authenticatorData: b64u.enc(cred.response.authenticatorData),
			signature: b64u.enc(cred.response.signature) } } }, true);
	}
	async function faceSetup() {
		const o = await call("face_options", { purpose: "setup" }, true);
		const cred = await navigator.credentials.create({ publicKey: { ...o, challenge: b64u.dec(o.challenge),
			user: { ...o.user, id: b64u.dec(o.user.id) }, excludeCredentials: (o.excludeCredentials || []).map((c) => ({ type: "public-key", id: b64u.dec(c.id) })) } });
		return call("face_setup", { credential: { id: cred.id, rawId: b64u.enc(cred.rawId), type: cred.type, response: {
			clientDataJSON: b64u.enc(cred.response.clientDataJSON), attestationObject: b64u.enc(cred.response.attestationObject) } } }, true);
	}
	function hideLock() {
		const el = document.getElementById("sk-lock");
		if (el) el.remove();
		lastTouch = Date.now();
	}
	// the lock covers the screen; what was typed or photographed under it stays (point 20: work kept as a draft)
	async function showLock(info) {
		if (state.viewAs) return;
		lockInfo = info || await fetch("/api/method/sk_app.api.lock_status", { headers: { Accept: "application/json" }, credentials: "same-origin" })
			.then((r) => r.json()).then((d) => d.message).catch(() => lockInfo);
		if (!lockInfo) return;
		let el = document.getElementById("sk-lock");
		if (!el) { el = document.createElement("div"); el.id = "sk-lock"; el.className = "sk-lock"; document.body.appendChild(el); }
		const face = lockInfo.has_key;
		el.innerHTML = `<div class="sk-lock-box"><div class="sk-lock-icon">🔒</div><h2>${t("lk_locked")}</h2>
			<p class="sk-note">${esc(lockInfo.name || "")}</p>
			${face ? `<p class="sk-big">👆 ${t("lk_touch")}</p><button class="sk-btn go wide" data-lock="face">🙂 ${t("lk_open_face")}</button>
				<p class="sk-note">${t("lk_ask_ceo")}</p>`
			: `<label class="sk-field"><span>${t("lk_pin")}</span><input id="lk-pin" type="password" inputmode="numeric" autocomplete="current-password" maxlength="8"></label>
				<button class="sk-btn go wide" data-lock="pin">${t("lk_open")}</button>`}
			<p class="sk-lock-msg" id="lk-msg"></p></div>`;
		if (face) setTimeout(() => el.querySelector("[data-lock=face]") && el.querySelector("[data-lock=face]").click(), 300);
	}
	async function afterUnlock(st) {
		lockInfo = st;
		hideLock();
		if (!state.home) await start();
		else if (lockHit) go(state.view); // a screen that could not load while locked opens now (typed forms are left as they are)
		lockHit = false;
		if (!st.has_key && await canFace()) faceSetupSheet();
	}
	function faceSetupSheet() {
		sheet(`<h3 class="sk-h">🙂 ${t("lk_setup")}</h3><p class="sk-note">${t("lk_setup_why")}</p>
			<button class="sk-btn go wide" data-act="face-setup">👆 ${t("lk_setup_now")}</button>`);
	}
	document.addEventListener("click", async (ev) => {
		const b = ev.target.closest("[data-lock]");
		if (!b) return;
		const msg = document.getElementById("lk-msg");
		b.disabled = true;
		try {
			if (b.dataset.lock === "face") await afterUnlock(await faceUnlock());
			else await afterUnlock(await call("unlock_pin", { pin: (document.getElementById("lk-pin") || {}).value || "" }, true));
		} catch (e) {
			if (msg) msg.textContent = e.name === "NotAllowedError" ? t("lk_cancelled") : e.message;
			if (/log in again/i.test(e.message)) setTimeout(() => location.reload(), 1500);
		}
		b.disabled = false;
	});
	document.addEventListener("keydown", (ev) => { if (ev.key === "Enter" && ev.target.id === "lk-pin") document.querySelector("[data-lock=pin]").click(); });
	// no touch for the lock time: lock (the server also locks by itself after that time)
	setInterval(() => {
		if (!lockInfo || !lockInfo.minutes || document.getElementById("sk-lock") || state.viewAs) return;
		if (Date.now() - lastTouch > lockInfo.minutes * 60 * 1000) call("lock_now", {}, true).catch(() => {}).finally(() => showLock());
	}, 20 * 1000);
	// every time the app is opened (not a reload of the open app): locked, unless the person has just logged in
	async function lockAtOpen() {
		const st = await fetch("/api/method/sk_app.api.lock_status", { headers: { Accept: "application/json" }, credentials: "same-origin" })
			.then((r) => r.json()).then((d) => d.message).catch(() => null);
		if (!st || !st.minutes) return false;
		lockInfo = st;
		let opened = false;
		try { opened = !!sessionStorage.getItem("sk_open"); sessionStorage.setItem("sk_open", "1"); } catch (e) { /* private mode */ }
		if (!opened && !st.locked && !st.just_unlocked) {
			await call("lock_now", {}, true).catch(() => {});
			st.locked = true;
		}
		if (st.locked) { showLock(st); return true; }
		if (!st.has_key && await canFace()) setTimeout(faceSetupSheet, 1500);
		return false;
	}

	async function start() {
		try {
			state.home = await call("home");
			state.lang = state.home.language || "English";
			state.card = state.home.card;
			renderHome();
			inAppBrowserBanner();
			restoreDraft().catch(() => {});
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
			const h = await call("home", null, false, true);
			if (reloadIfNew(h)) return;
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

	lockAtOpen().then((locked) => (locked ? null : start())).then(() => setTimeout(poll, 3000));
})();
