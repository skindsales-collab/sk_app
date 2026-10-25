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
	const ICON = {
		my_day: "☀️", my_leads: "📞", my_deals: "🤝", my_kpi: "⭐", work_book: "📒", dsi: "💡", problem: "🚩",
		job_cards: "🛠️", inspections: "✅", stock_alerts: "📦", material_requests: "🧾", invoice_photo: "📷",
		collections: "💰", team_scorecards: "👥", site_checklist: "📋", ceo_view: "📊",
		calendar: "📅", follow_up: "🔔", new_lead: "➕", training: "🎓", day_report: "📝", team_reports: "🗂️",
		calls: "📞", whatsapp: "💬", mail: "✉️", reminders: "⏰", library: "🏢",
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

	function renderHome() {
		const h = state.home;
		const fn = h.home;
		const tiles = fn.tiles.map((k) => `<button class="sk-tile" data-go="${k}"><span class="sk-tile-icon">${ICON[k] || "•"}</span><span>${t(k)}</span></button>`).join("");
		const files = (h.new_files || []).map((f) => `<button class="sk-banner new" data-open="${esc(f.doctype)}" data-name="${esc(f.attached_to_name)}">📐 ${t("new_drawing")}: ${esc(f.title)}<br><small>${esc(f.file_name)}</small></button>`).join("");
		const report = !h.day_report_sent && new Date().getHours() >= 17 ? `<button class="sk-banner bad" data-go="day_report">📝 ${t("report_due")}</button>` : "";
		root.innerHTML = header("SK App") +
			`<main>${reminderBanners()}${files}${cardHtml(state.card)}<button class="sk-btn wide sk-addrem" data-act="reminder-new">⏰ + ${t("reminder")}</button>
			<div class="sk-tiles">${tiles}</div>${report}</main>`;
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
		root.innerHTML = header(t("my_day")) + `<main>${cardHtml(d.card)}<ul class="sk-list">${d.items.map(itemRow).join("") || `<li class="sk-empty">${t("nothing")}</li>`}</ul></main>`;
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
		root.innerHTML = header(t("follow_up")) + `<main><button class="sk-btn go wide" data-go="new_lead">➕ ${t("new_lead")}</button><ul class="sk-list sk-gap">${li || `<li class="sk-empty">${t("nothing")}</li>`}</ul></main>`;
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
		root.innerHTML = header(t("reminders")) + `<main><button class="sk-btn go wide" data-act="reminder-new">⏰ + ${t("reminder")}</button>
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

	const LIVE_VIEWS = { my_day: renderMyDay, my_leads: () => renderLeads("my_leads"), my_deals: () => renderLeads("my_deals"),
		my_kpi: renderKpi, dsi: renderDsi, work_book: () => renderWork("work_book"), problem: () => renderWork("problem"),
		follow_up: renderFollowUp, new_lead: renderNewLead, training: renderTraining, day_report: renderDayReport,
		team_reports: renderTeamReports, calendar: renderCalendar, detail: () => renderDetail(current.doctype, current.name),
		reminders: renderReminders, calls: renderCalls, whatsapp: renderWhatsApp, mail: renderMail, library: renderLibrary };

	async function go(view) {
		state.view = view;
		if (view === "home") contacts = null;
		try {
			if (view === "home") return renderHome();
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
			const act = el.dataset.act;
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
