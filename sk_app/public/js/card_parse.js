/* Free photo reading: turn the text the phone read from any photo (visiting card, enquiry letter or email, WhatsApp
   screenshot, IndiaMART lead, typed note) into name / company / mobile / email / requirement / source / segment.
   Mobile and email are found reliably by their shape; the rest is a best guess the salesperson checks. */
(function (root) {
	const COMPANY = /\b(pvt|private|ltd|limited|llp|industries|industry|industrial|enterprises?|engineering|engineers|solutions|corporation|corp|company|co\.|works|traders|trading|infra|infrastructure|constructions?|builders|developers|technologies|technology|tech|systems|services|group|associates|sons|fabricators?|manufacturing|logistics|projects|realty|estates?)\b/gi;
	const ROLE = /\b(manager|director|engineer|proprietor|owner|partner|ceo|cfo|coo|md|head|executive|officer|purchase|procurement|sales|marketing|founder|gm|supervisor|in-?charge|architect|consultant|president|vp|admin|accounts|hr|chairman)\b/i;
	const ADDRESS = /\b(road|rd\.?|street|st\.|nagar|plot|no\.|sector|midc|phase|floor|near|opp\.?|building|bldg|gali|lane|chowk|pune|mumbai|thane|nashik|nagpur|india|maharashtra|pin|dist\.?|tal\.?|area|park|estate|complex)\b|\d{6}/i;
	const EMAIL = /[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i;
	const WEB = /(www\.|https?:|\.com\b|\.in\b|\.co\b|\.net\b|\.org\b)/i;

	function phones(text) {
		const out = [];
		const found = text.replace(/[Oo](?=\d)|(?<=\d)[Oo]/g, "0").match(/\+?\d[\d \t\-().]{8,}\d/g) || [];
		for (const raw of found) {
			let d = raw.replace(/\D/g, "");
			if (d.length === 12 && d.startsWith("91")) d = d.slice(2);
			if (d.length === 11 && d.startsWith("0")) d = d.slice(1);
			if (d.length === 20) { out.push(d.slice(0, 10), d.slice(10)); continue; } // two numbers on one line
			if (d.length === 10) out.push(d);
		}
		return out;
	}

	// a pure address line (no size or product in it) is not the requirement
	function ADDRESS_ONLY(l) {
		return ADDRESS.test(l) && !/^\s*(?:location|site|delivery|place)\b/i.test(l) &&
			!/\d+\s*[x×*]\s*\d+|cabin|container|toilet|shifting|machine|\bnos?\b|material|spec|panel|sheet|board|\bmm\b|\bgi\b|\bms\b|puf|door|roof/i.test(l);
	}

	function titleCase(s) {
		return s.toLowerCase().replace(/\b[a-z]/g, (c) => c.toUpperCase());
	}

	function clean(line) {
		return line.replace(/[|_~`^*=<>{}[\]\\]/g, " ").replace(/\s{2,}/g, " ").trim();
	}

	// "Name: Ramesh Patil", "Company - Patil Infra", "Contact person : ..." on forms, letters and lead emails
	const LABELS = {
		name: /^(?:customer\s*name|contact\s*person|name|buyer(?:\s*name)?|from|sender|kind\s*attn\.?|attn\.?)\s*[:\-–]\s*(.+)$/i,
		company: /^(?:company(?:\s*name)?|firm|organi[sz]ation|m\/s\.?)\s*[:\-–.]?\s*(.+)$/i,
	};
	// our own name on a customer's PO or a supplier's bill is never the party: "SK IND TECH", "SK (IND) TECH" (SK 27-Oct test)
	const OWN = /\bsk\s*\(?\s*ind\.?\s*\)?\s*tech/i;
	const BUYER = /\b(?:buyer|bill(?:ed)?\s*to|consignee|ship(?:ped)?\s*to|customer\s*(?:name|details))\b/i;
	const SIGN_OFF = /^(?:regards|thanks(?: (?:&|and) regards)?|thank you|warm regards|best regards|yours (?:faithfully|truly|sincerely))\b[,.!]*$/i;
	// What the customer wants: sizes, quantities, products, place and date lines
	const NEED = /(\d+(?:\.\d+)?\s*(?:'|ft|feet|mtr|m)?\s*[x×*]\s*\d+)|\b(\d+\s*(?:nos?\.?|units?|qty|pcs|sets?))\b|\b(cabins?|containers?|porta\s*cabin|portable|office|toilets?|washrooms?|security|guard|room|kiosk|pods?|labour\s*camp|colony|site\s*office|godown|warehouse|shed|shifting|relocation|machine|rigging|dismantl\w*|job\s*work|fabrication|ac\b|air\s*condition\w*|insulat\w*|puf|location|site|deliver\w*|required|requirement|need|enquiry|inquiry|quotation|quote|rent|hire|purchase|buy|budget|urgent|material|spec\w*|make|brand|grade|gauge|thick\w*|mm|sq\.?\s*ft|sqft|rmt|kg|tons?|gi|ms|ss|acp|puf|eps|rockwool|glass\s*wool|ply\w*|cement\s*(?:fiber|fibre)?\s*board|board|sheet|corrugated|panel|frame|channel|pipe|tube|angle|i-?beam|chassis|door|window|flooring|vinyl|tiles?|paint|colou?r|ral|roof|wall|floor|ceiling|electrical|wiring|lights?|fans?|switch\w*|plumbing|wash\s*basin|wc|drawing|dwg|elevation|plan|section|height|length|width|qty|quantity)\b/i;
	const SOURCES = [[/indiamart/i, "indiamart"], [/just\s*dial/i, "justdial"], [/tradeindia/i, "tradeindia"], [/\bgem\b|gem\.gov/i, "gem"],
		[/whatsapp/i, "whatsapp"], [/website|web\s*enquiry/i, "website"], [/facebook|instagram/i, "facebook"],
		[/^\s*(?:from|to|subject)\s*:.*$/im, "email"]];
	const SEGMENTS = [[/shifting|relocat|rigging|dismantl|machine\s*mov/i, "shifting"], [/job\s*work/i, "job work"], [/labou?r\s*(?:camp|colony)|modular\s*(?:building|block)|g\s*\+\s*1/i, "labour camp"],
		[/\blgsf\b|light\s*gauge/i, "lgsf"],
		[/cabin|container|porta|portable|toilet|washroom|kiosk|\bpods?\b|site\s*office|labour\s*camp|security\s*(?:cabin|room)|office/i, "cabin"]];

	// Purchase / sale invoice or bill: the key facts on top, then the item lines
	const GSTIN = /\b\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]\b/g;
	// the phone often reads the GSTIN's "Z" as 2 or 7: "27ESSPK5070A12M" is 27ESSPK5070A1ZM
	const GSTIN_LOOSE = /\b\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z][Z27][0-9A-Z]\b/g;
	const fixGstin = (g) => g.slice(0, 13) + "Z" + g.slice(14);
	// Tally-style bill head: "Invoice No      Dated" with the values on the next line under them
	function underLabel(raw, label) {
		for (let i = 0; i < raw.length - 1; i++) {
			const m = raw[i].match(label);
			if (!m) continue;
			const col = m.index;
			for (let j = i + 1; j < Math.min(raw.length, i + 3); j++) {
				const tok = [...raw[j].matchAll(/\S+/g)].find((x) => x.index >= col - 6 && x.index <= col + 18);
				if (tok) return tok[0].replace(/[|,]$/, "");
			}
		}
		return "";
	}
	function sellerOf(raw) {
		const stop = raw.findIndex((l) => BUYER.test(l));
		const head = raw.slice(0, stop > 0 ? stop : 8);
		for (const l of head) {
			const chunk = clean(l.trim().split(/\s{3,}/)[0] || "");
			if (!chunk || OWN.test(chunk) || /invoice|original|duplicate|triplicate|recipient|page|gstin|^\W*$/i.test(chunk)) continue;
			if ((chunk.match(/[A-Za-z]{2,}/g) || []).length >= 2 && !/\d{3,}/.test(chunk)) return chunk;
		}
		return "";
	}
	function invoiceFacts(text, lines, raw, own) {
		if (!/tax\s*invoice|invoice\s*(?:no|number|#|date)|bill\s*(?:no|of\s*supply)|gstin|grand\s*total|e-?way\s*bill/i.test(text)) return null;
		const val = (rx) => { const m = text.match(rx); return m ? m[1].trim() : ""; };
		const amount = (s) => s ? s.replace(/[^\d.,]/g, "").replace(/,/g, "").replace(/\.$/, "") : "";
		// the seller's GSTIN: found before the buyer / consignee block, never our own
		const up = (raw || lines).map((l) => l.toUpperCase().replace(/O(?=\d)/g, "0"));
		const stop = up.findIndex((l) => BUYER.test(l));
		const ownG = new Set((own && own.gstins) || []);
		const found = [];
		up.forEach((l, i) => (l.match(GSTIN_LOOSE) || []).forEach((g) => {
			g = fixGstin(g);
			if (!ownG.has(g) && !OWN.test(l) && !(stop >= 0 && i > stop)) found.push(g);
		}));
		const gstins = [...new Set(found)];
		let total = amount(val(/(?:grand\s*total|total\s*amount|net\s*amount|amount\s*payable|invoice\s*(?:value|total)|total\s*(?:rs\.?|inr|₹))\s*[:\-]?\s*(?:rs\.?|inr|₹)?\s*([\d,]+(?:\.\d{1,2})?)/i));
		if (!total) {  // Tally: "Total   2 pcs   7,354.00": the last amount on the Total line
			const tl = lines.find((l) => /^\W*\d?\W*total\b/i.test(l) && /\d[\d,]*\.\d{2}/.test(l));
			if (tl) total = amount((tl.match(/\d[\d,]*\.\d{2}/g) || []).pop());
		}
		const items = lines.filter((l) => /[A-Za-z]{3}/.test(l) && (l.match(/\d+(?:[.,]\d+)*/g) || []).length >= 2 &&
			!ADDRESS_ONLY(l) && !new RegExp(GSTIN.source).test(l.toUpperCase()) && !/invoice|gstin|total|cgst|sgst|igst|bank|ifsc|a\/c|phone|mob|pin|date|state\s*code/i.test(l)).slice(0, 15);
		return {
			number: val(/(?:invoice|bill)\s*(?:no\.?|number|#)\s*[:\-.]?\s*([A-Z0-9][A-Z0-9\/\-]*\d[A-Z0-9\/\-]*)/i) || underLabel(raw || [], /invoice\s*no/i),
			date: val(/(?:invoice\s*)?date(?:d)?\s*[:\-.]?\s*(\d{1,2}[\/\-.](?:\d{1,2}|[A-Za-z]{3})[\/\-.]\d{2,4})/i)
				|| (underLabel(raw || [], /\bdated\b/i).match(/^\d{1,2}[\/\-.](?:\d{1,2}|[A-Za-z]{3})[\/\-.]\d{2,4}$/) || [""])[0],
			seller: sellerOf(raw || lines),
			gstin: gstins.join(", "),
			total: total,
			items: items,
		};
	}

	// HR (SK 27-Oct): PAN card, Aadhaar, printed joining form. Bank details are never taken (confidential).
	const PAN = /\b[A-Z]{5}[0-9O]{4}[A-Z]\b/;
	const DATE = /\d{1,2}\s*[\/\-.]\s*\d{1,2}\s*[\/\-.]\s*\d[\d ]{1,4}\d/;
	// a date the phone read half ("0/12/2024") is left for the person to type
	const normDate = (s) => {
		const d = (s || "").replace(/\s+/g, ""), m = d.match(/^(\d{1,2})[\/\-.](\d{1,2})[\/\-.](\d{2}|\d{4})$/);
		return m && +m[1] >= 1 && +m[1] <= 31 && +m[2] >= 1 && +m[2] <= 12 ? d : "";
	};
	function personFacts(text, lines) {
		if (!/date\s*of\s*birth|\bbirth\b|aadha?a?r|income\s*tax|personal\s*information|joining\s*date|emergency/i.test(text) && !PAN.test(text)) return null;
		const after = (rx) => { const m = text.match(rx); return m ? m[1] : ""; };
		let name = "";
		const at = lines.findIndex((l) => /^\W*name\W*$/i.test(l));  // label under the value (PAN card, printed forms)
		if (at > 0 && /^[A-Za-z][A-Za-z.' ]+$/.test(lines[at - 1]) && lines[at - 1].split(/\s+/).length >= 2) name = lines[at - 1];
		const lab = lines.map((l) => l.match(/^\W*(?:full\s*)?name(?:\s*of\s*(?:the\s*)?(?:employee|candidate))?\s*[:\-]\s*([A-Za-z][A-Za-z.' ]{2,})$/i)).find(Boolean);
		if (!name && lab) name = lab[1];
		const pan = ((text.toUpperCase().match(PAN) || [""])[0]).replace(/(?<=^[A-Z]{5}\d{0,3})O/g, "0");
		const aad = (after(/aadha?a?r[^\d\n]{0,25}([\d ]{12,16})/i) || (text.match(/\b\d{4}\s\d{4}\s\d{4}\b/) || [""])[0]).replace(/\D/g, "");
		const dobLine = text.match(new RegExp("(?:birth|\\bdob\\b)[^\\d]{0,25}(" + DATE.source + ")", "i"));
		const joinLine = lines.find((l) => /joining|date\s*of\s*join/i.test(l));
		const joinDates = joinLine ? joinLine.match(new RegExp(DATE.source, "g")) || [] : [];
		const addr = lines.findIndex((l) => /^\W*(?:current|present|residential|local)?\s*address\b/i.test(l) && !/permanent/i.test(l));
		let address = addr >= 0 ? lines[addr].replace(/^\W*(?:current|present|residential|local)?\s*address\s*[:\-]?\s*/i, "") : "";
		if (addr >= 0 && lines[addr + 1] && !/[:]|bank|account|ifsc|aadha|gender|marital|phone|email|education|birth/i.test(lines[addr + 1])) address += " " + lines[addr + 1];
		const em = text.match(/emergency\s*(?:contact\s*)?(?:number|no\.?|phone|mobile)[^\d\n]{0,10}(\+?\d[\d \-]{8,}\d)\s*(?:\(([^)]+)\))?/i);
		const emNo = em ? phones(em[1])[0] || "" : "";
		return {
			name: name ? titleCase(name.trim()) : "",
			pan: PAN.test(pan) ? pan : "",
			aadhaar: aad.length === 12 ? aad : "",
			dob: dobLine ? normDate(dobLine[1]) : "",
			joining: joinDates.length ? normDate(joinDates[joinDates.length - 1]) : "",
			gender: (after(/gender[^\n]*?\b(male|female)\b/i) || "").replace(/^./, (c) => c.toUpperCase()),
			address: clean(address).replace(/\|/g, "").trim(),
			emergency_mobile: emNo,
			emergency_name: em && em[2] ? em[2].trim() : "",
			education: clean(after(/educat\w*\s*[:\-]?\s*([^\n|]+)/i) || after(/edicat\w*\s*[:\-]?\s*([^\n|]+)/i)),
		};
	}

	function parseCard(text, own) {
		text = String(text || "");
		const raw = text.split(/\n/).filter((l) => l.replace(/[^A-Za-z0-9]/g, "").length >= 2);
		let lines = text.split(/\n/).map(clean).filter((l) => l.replace(/[^A-Za-z0-9]/g, "").length >= 2);
		const labelled = { name: "", company: "" };
		for (const l of lines) {
			for (const k in LABELS) {
				const m = l.match(LABELS[k]);
				if (m && !labelled[k] && !EMAIL.test(m[1]) && !/\d{5,}/.test(m[1].replace(/\s/g, ""))) labelled[k] = m[1].trim();
			}
		}
		const signAt = lines.findIndex((l) => SIGN_OFF.test(l));
		const signName = signAt >= 0 && lines[signAt + 1] ? lines[signAt + 1].replace(/^\(|\)$/g, "") : "";
		const email = (String(text).match(EMAIL) || [""])[0].toLowerCase();
		const nums = phones(String(text));
		const mobile = nums.find((n) => /^[6-9]/.test(n)) || nums[0] || "";
		const plain = (l) => !EMAIL.test(l) && !WEB.test(l) && !/\d{5,}/.test(l.replace(/\s/g, "")) && !OWN.test(l) &&
			!/invoice|bill\s*(?:to|of)|ship\s*to|gstin|total|challan|quotation|purchase\s*order|e-?way/i.test(l);
		let company = "", best = 0;
		for (const l of lines) {
			if (!plain(l)) continue;
			const hits = (l.match(COMPANY) || []).length;
			if (hits > best) { best = hits; company = l; }
		}
		if (labelled.company) company = labelled.company;
		let name = labelled.name.replace(/<.*$/, "").trim();
		const isName = (l) => plain(l) && l !== company && !ROLE.test(l) && !ADDRESS.test(l) && !(l.match(COMPANY) || []).length &&
			/^[A-Za-z][A-Za-z.' ]+$/.test(l) && l.split(/\s+/).length >= 2 && l.split(/\s+/).length <= 4;
		const roleAt = lines.findIndex((l) => ROLE.test(l) && plain(l));
		if (!name && signName && isName(signName)) name = signName;
		if (!name && roleAt > 0 && isName(lines[roleAt - 1])) name = lines[roleAt - 1];
		if (!name && roleAt >= 0 && roleAt + 1 < lines.length && isName(lines[roleAt + 1])) name = lines[roleAt + 1];
		if (!name) name = lines.find(isName) || "";
		// Requirement: the lines that say what is needed; on a card there are none, so it stays empty
		const used = new Set([company, name, labelled.name, labelled.company, signName].filter(Boolean));
		const need = lines.filter((l) => NEED.test(l) && !/^indiamart buy lead$/i.test(l) && !used.has(l) && !EMAIL.test(l) && !WEB.test(l) && !LABELS.name.test(l) &&
			!ADDRESS_ONLY(l)).slice(0, 15).join("\n");
		const find = (list) => (list.find(([rx]) => rx.test(text)) || [])[1] || "";
		const inv = invoiceFacts(text, lines, raw, own);
		const person = inv ? null : personFacts(text, lines);
		if (inv && inv.seller) company = inv.seller;
		if (person && person.name) name = person.name;
		const mobiles = person ? nums.filter((n) => n !== person.emergency_mobile && /^[6-9]/.test(n)) : [];
		let requirement = person ? "" : need;
		if (inv) {
			const head = ["Invoice", inv.number && `No ${inv.number}`, inv.date && `Date ${inv.date}`, inv.gstin && `GSTIN ${inv.gstin}`,
				inv.total && `Total ₹${inv.total}`].filter(Boolean).join(" · ");
			requirement = [head, ...inv.items].join("\n");
		}
		return {
			first_name: name && !inv ? titleCase(name) : "",
			organization: person ? "" : company.replace(/\s+([.,])/g, "$1"),
			mobile_no: person ? mobiles[0] || "" : mobile,
			email: email,
			requirement: requirement.slice(0, 1000),
			source: inv ? "" : find(SOURCES),
			segment: inv ? "" : find(SEGMENTS),
			invoice: inv,
			person: person,
		};
	}

	// SK 14-Nov: New Lead for an existing customer. ERPNext's data wins where it has some; what the person typed stays
	// where ERPNext has nothing (same rule as sk_app/writers/lead_rules.fill_from_existing, tested on both sides).
	function fillFromExisting(typed, pick) {
		const out = {};
		[["organization", "customer_name"], ["first_name", "contact"], ["mobile_no", "mobile"], ["email", "email"], ["segment", "segment"]]
			.forEach(([key, src]) => { if (pick[src]) out[key] = pick[src]; });
		if (pick.customer_name && !pick.contact && !((typed && typed.first_name) || "").trim()) out.first_name = pick.customer_name;
		out.no_gstin = pick.customer_name && !pick.gstin ? 1 : 0;
		out.source = "Existing Customer";
		return out;
	}

	// SK 20-Nov "free camera reading": a customer PO or a bill / petty-cash voucher read on the phone (no paid AI).
	// Only fields with a clear label or shape are filled; the person checks them before saving.
	const MONTHS = { jan: 1, feb: 2, mar: 3, apr: 4, may: 5, jun: 6, jul: 7, aug: 8, sep: 9, sept: 9, oct: 10, nov: 11, dec: 12 };
	const DATE_RE = /(\d{1,2})[\/\-.](\d{1,2})[\/\-.](\d{2,4})|(\d{1,2})[\s\-]*([A-Za-z]{3,9})[\s\-,]*(\d{2,4})|(\d{4})-(\d{2})-(\d{2})/;
	function isoDate(text) {
		const m = String(text || "").match(DATE_RE);
		if (!m) return "";
		let d, mo, y;
		if (m[1]) { d = +m[1]; mo = +m[2]; y = +m[3]; }
		else if (m[4]) { d = +m[4]; mo = MONTHS[m[5].toLowerCase().slice(0, m[5].toLowerCase().startsWith("sept") ? 4 : 3)] || 0; y = +m[6]; }
		else { y = +m[7]; mo = +m[8]; d = +m[9]; }
		if (y < 100) y += 2000;
		if (!(d >= 1 && d <= 31 && mo >= 1 && mo <= 12 && y >= 2000 && y <= 2100)) return "";
		return `${y}-${String(mo).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
	}
	function lines(text) { return String(text || "").split(/\r?\n/).map((l) => l.replace(/\s+/g, " ").trim()).filter(Boolean); }
	function labelled(ls, label, pick) {
		for (let i = 0; i < ls.length; i++) {
			const m = ls[i].match(label);
			if (!m) continue;
			const after = ls[i].slice(m.index + m[0].length).replace(/^[\s:.#\-]+/, "");
			const v = pick(after) || (i + 1 < ls.length ? pick(ls[i + 1]) : "");
			if (v) return v;
		}
		return "";
	}
	function money(s) {
		const nums = (String(s || "").match(/\d{1,3}(?:,\d{2,3})+(?:\.\d{1,2})?|\d+\.\d{1,2}|\d{2,}/g) || [])
			.map((x) => Number(x.replace(/,/g, ""))).filter((n) => n > 0 && n < 1e9);
		return nums.length ? Math.max(...nums) : 0;
	}
	function parseDoc(text, kind) {
		const ls = lines(text);
		if (kind === "po") {
			const po_no = labelled(ls, /\b(?:p\.?\s?o\.?|purchase\s+order|order)\s*(?:no|number|#)\.?/i,
				(s) => { const m = s.match(/[A-Z0-9][A-Z0-9\/\-]{2,}/i); return m && /\d/.test(m[0]) ? m[0] : ""; });
			const po_date = labelled(ls, /\b(?:p\.?\s?o\.?\s*date|order\s*date|dated|date)\b/i, isoDate);
			const delivery_date = labelled(ls, /\b(?:delivery\s*(?:date|by|schedule)?|del\.?\s*date|required\s*by|schedule\s*date|due\s*date)\b/i, isoDate);
			return { po_no, po_date, delivery_date };
		}
		// bill / voucher
		const amount = labelled(ls, /\b(?:grand\s*total|net\s*(?:amount|payable)|total\s*(?:amount|payable|rs\.?|inr)?|amount\s*payable|amount)\b/i, (s) => money(s) || "")
			|| money(ls.filter((l) => /₹|rs\.?|inr/i.test(l)).join(" ")) || "";
		const date = labelled(ls, /\b(?:invoice|bill|voucher)?\s*date\b/i, isoDate) || isoDate(text);
		const party = ls.slice(0, 6).find((l) => COMPANY.test(l) && !/invoice|bill|gstin|phone|mob/i.test(l));
		COMPANY.lastIndex = 0;
		return { amount: amount ? String(amount) : "", date, paid_to: party || "", what: "" };
	}

	root.skParseCard = parseCard;
	root.skParseDoc = parseDoc;
	root.skFillFromExisting = fillFromExisting;
	if (typeof module !== "undefined") module.exports = { parseCard, phones, fillFromExisting, parseDoc, isoDate };
})(typeof window !== "undefined" ? window : globalThis);
