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
			card_photo: "Photo of visiting card / enquiry", reading: "Reading photo…", read_ok: "Filled from photo. Please check.",
			read_none: "Could not read. Please type.", cust_name: "Customer name", company: "Company", mobile: "Mobile",
			source: "Source", segment: "Segment", requirement: "Requirement", lesson_done: "I have done this lesson",
			done_tick: "Done", new_files: "New files on your leads", report_q: "What work did you do today?",
			problems_q: "Problems / help needed", plan_q: "Plan for tomorrow", captured: "Captured by the app today",
			cards_done: "Cards done", calls_made: "Calls", notes_added: "Notes", leads_created: "New leads",
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
			card_photo: "व्हिजिटिंग कार्ड / चौकशीचा फोटो", reading: "फोटो वाचत आहे…", read_ok: "फोटोवरून भरले. कृपया तपासा.",
			read_none: "वाचता आले नाही. कृपया टाईप करा.", cust_name: "ग्राहकाचे नाव", company: "कंपनी", mobile: "मोबाईल",
			source: "स्रोत", segment: "विभाग", requirement: "गरज", lesson_done: "मी हा धडा पूर्ण केला",
			done_tick: "पूर्ण", new_files: "तुमच्या लीडवर नवीन फाईल्स", report_q: "आज तुम्ही कोणते काम केले?",
			problems_q: "अडचणी / मदत हवी", plan_q: "उद्याचे नियोजन", captured: "आज ॲपने नोंदवलेले",
			cards_done: "कार्ड पूर्ण", calls_made: "कॉल", notes_added: "नोंदी", leads_created: "नवीन लीड",
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
		},
	};
	const ICON = {
		my_day: "☀️", my_leads: "📞", my_deals: "🤝", my_kpi: "⭐", work_book: "📒", dsi: "💡", problem: "🚩",
		job_cards: "🛠️", inspections: "✅", stock_alerts: "📦", material_requests: "🧾", invoice_photo: "📷",
		collections: "💰", team_scorecards: "👥", site_checklist: "📋", ceo_view: "📊",
		calendar: "📅", follow_up: "🔔", new_lead: "➕", training: "🎓", day_report: "📝", team_reports: "🗂️",
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
	function speakInto(input) {
		const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
		if (!SR) { toast("Voice not supported on this phone. Use the keyboard mic.", true); return; }
		const rec = new SR();
		const ml = micLang[input.id] || (state.lang === "Marathi" ? "mr" : "en");
		rec.lang = ml === "mr" ? "mr-IN" : "en-IN";
		rec.interimResults = false;
		rec.onresult = (e) => { input.value = (input.value ? input.value + " " : "") + e.results[0][0].transcript; };
		rec.onerror = () => toast("Could not hear. Try again.", true);
		rec.start();
	}

	function readAloud(text) {
		if (!window.speechSynthesis) return;
		const u = new SpeechSynthesisUtterance(text);
		u.lang = state.lang === "Marathi" ? "mr-IN" : "en-IN";
		speechSynthesis.cancel();
		speechSynthesis.speak(u);
	}

	function header(title) {
		return `<header class="sk-head">
			${state.view !== "home" ? `<button class="sk-back" data-go="home">‹ ${t("back")}</button>` : `<img src="/assets/sk_app/icons/icon-192.png" class="sk-logo" alt="SK">`}
			<div class="sk-title">${esc(title)}</div>
			<button class="sk-lang" data-act="lang">${t("lang")}</button>
		</header>`;
	}

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
		root.innerHTML = header((fn.label && (fn.label[state.lang] || fn.label.English)) || "SK App") +
			`<main><div class="sk-hello">${esc(h.full_name || h.user)}</div>${report}${files}${cardHtml(state.card)}<div class="sk-tiles">${tiles}</div></main>`;
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
		const [d, o] = await Promise.all([call("crm_detail", { doctype, name }), options()]);
		const doc = d.doc;
		current = { doctype, name, mobile: doc.mobile_no || doc.phone, email: doc.email };
		const statuses = (doctype === "CRM Lead" ? o.lead_statuses : o.deal_statuses) || [];
		const chips = statuses.map((s) => `<button class="sk-chip ${s.name === doc.status ? "on" : ""}" data-act="status" data-status="${esc(s.name)}">${esc(s.name)}</button>`).join("");
		const files = d.files.map((f) => `<li class="sk-item"><div><a class="sk-item-title" href="${esc(f.file_url)}" target="_blank">📎 ${esc(f.file_name)}</a><div class="sk-item-meta">${esc(f.owner)} · ${when(f.creation)}</div></div>
			<button class="sk-open ${f.for_customer ? "sk-send" : ""}" data-act="share-pdf" data-pdf="${esc(f.file_url)}" data-file="${esc(f.file_name)}" ${f.for_customer ? `data-fileid="${esc(f.name)}"` : ""}>${f.for_customer ? "💬 " + t("send") : "↗"}</button>
			${f.for_customer ? `<button class="sk-open sk-fix" data-act="correction" data-fileid="${esc(f.name)}" data-file="${esc(f.file_name)}">✏️</button>` : ""}</li>`).join("");
		const tasks = d.tasks.map((x) => `<li class="sk-item"><div><div class="sk-item-title">${esc(x.title)}</div><div class="sk-item-meta">${esc(x.status)} · ${when(x.due_date)}</div></div></li>`).join("");
		const calls = d.calls.map((x) => `<li class="sk-item"><div><div class="sk-item-title">📞 ${esc(x.type)} · ${esc(x.status)}</div><div class="sk-item-meta">${when(x.creation)}</div></div></li>`).join("");
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
				<button class="sk-btn ok wide" data-act="save-note">${t("add_note")}</button></div>
			${sec(t("quotations"), d.quotations.map((q) => erpDocRow("Quotation", q, mobile)).join(""))}
			${sec(t("sales_orders"), d.sales_orders.map((q) => erpDocRow("Sales Order", q, mobile)).join(""))}
			${sec(t("files"), files)}${sec(t("tasks"), tasks)}${sec(t("notes"), notes)}${sec(t("calls"), calls)}
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
		const outs = p.channel === "Call" ? ((crmOpts && crmOpts.call_outcomes) || ["Talked", "No answer", "Busy", "Call back later", "Wrong number"]) : [];
		sheet(`<h3 class="sk-h">${t("what_happened")} (${t(p.channel.toLowerCase())})</h3>
			<div class="sk-chips">${outs.map((x) => `<button class="sk-chip" data-ptype="${esc(x)}">${esc(x)}</button>`).join("")}</div>
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
	async function readCard(ev) {
		const f = ev.target.files[0];
		if (!f) return;
		try {
			toast(t("reading"));
			cardUrl = await upload(f);
			const d = await call("read_photo", { file_url: cardUrl }, true);
			const set = (id, v) => { const el = document.getElementById(id); if (el && v && !el.value) el.value = v; };
			set("f-first", d.first_name); set("f-org", d.organization); set("f-mobile", d.mobile_no); set("f-email", d.email); set("f-req", d.requirement);
			toast(d.first_name || d.organization || d.mobile_no ? t("read_ok") : t("read_none"), !(d.first_name || d.organization || d.mobile_no));
		} catch (e) { toast(e.message, true); }
	}

	// ---------- Training ----------
	let lessons = [];
	async function renderTraining() {
		lessons = await call("training_lessons");
		const mr = state.lang === "Marathi";
		root.innerHTML = header(t("training")) + `<main><ul class="sk-list">${lessons.map((l, i) => `<li class="sk-item"><button class="sk-fu-main" data-lesson="${i}">
			<div class="sk-item-title">${l.done ? "✅" : "🎓"} ${esc((mr && l.title_marathi) || l.title)}</div><div class="sk-item-meta">${esc(l.topic || "")} · ${esc(l.minutes || 2)} ${t("min")}</div></button></li>`).join("") || `<li class="sk-empty">${t("nothing")}</li>`}</ul></main>`;
	}

	function renderLesson(i) {
		const l = lessons[i];
		const mr = state.lang === "Marathi";
		state.view = "lesson";
		const video = l.video_url ? `<a class="sk-btn wide" href="${esc(l.video_url)}" target="_blank">▶ Video</a>` : "";
		// lesson HTML is written by HR / managers in ERPNext (SK Training Lesson)
		root.innerHTML = header((mr && l.title_marathi) || l.title) + `<main><div class="sk-lesson">${(mr && l.content_marathi) || l.content || ""}</div>${video}
			${l.done ? `<div class="sk-answered">✅ ${t("done_tick")}</div>` : `<button class="sk-btn ok wide" data-act="lesson-done" data-lesson="${esc(l.name)}">✓ ${t("lesson_done")}</button>`}
			<button class="sk-btn wide" data-go="training">‹ ${t("training")}</button></main>`;
	}

	// ---------- Day Report ----------
	function factChips(c) {
		const keys = ["cards_done", "calls_made", "notes_added", "leads_created", "work_entries"];
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

	const LIVE_VIEWS = { my_day: renderMyDay, my_leads: () => renderLeads("my_leads"), my_deals: () => renderLeads("my_deals"),
		my_kpi: renderKpi, dsi: renderDsi, work_book: () => renderWork("work_book"), problem: () => renderWork("problem"),
		follow_up: renderFollowUp, new_lead: renderNewLead, training: renderTraining, day_report: renderDayReport,
		team_reports: renderTeamReports, calendar: renderCalendar, detail: () => renderDetail(current.doctype, current.name) };

	async function go(view) {
		state.view = view;
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
			if (el.dataset.lesson && !el.dataset.act) return renderLesson(Number(el.dataset.lesson));
			if (el.dataset.contact) {
				const ch = el.dataset.contact;
				pending = { channel: ch, doctype: el.dataset.doctype, name: el.dataset.name, at: Date.now() };
				options().catch(() => null);
				if (ch === "Call") window.location.href = "tel:" + el.dataset.mobile;
				else if (ch === "WhatsApp") window.open("https://wa.me/" + waNumber(el.dataset.mobile), "_blank");
				else window.location.href = "mailto:" + el.dataset.email;
				return;
			}
			if (el.dataset.waPick !== undefined) {
				el.parentElement.querySelectorAll(".sk-chip").forEach((c) => c.classList.remove("on"));
				el.classList.add("on");
				document.getElementById("f-wa").value = el.dataset.waPick;
				if (!el.dataset.waPick) toast(t("no_number"), true);
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
			if (el.dataset.mic) return speakInto(document.getElementById(el.dataset.mic));
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
					outcome: chip ? chip.dataset.ptype : null, text: val("f-out"), photo: await photoUrl("f-outphoto") }, true);
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
				await call("training_done", { lesson: el.dataset.lesson }, true);
				toast(t("saved"));
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
		if (!document.hidden && pending && !root.querySelector(".sk-sheet-wrap") && Date.now() - pending.at > 1500) outcomeSheet(pending);
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
			if ((fresh.length || newCard) && state.view === "home") renderHome();
		} catch (e) { /* offline: try again later */ }
	}
	setInterval(poll, 60 * 1000);
	document.addEventListener("visibilitychange", () => { if (!document.hidden && !pending) poll(); });

	start();
})();
