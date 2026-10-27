// Accounts Gateway, like Gateway of Tally (SK 27-Oct-2026): four sections, Tally names, arrow keys + Enter, Tally keys.
frappe.pages["accounts-gateway"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: __("Accounts Gateway"), single_column: true });
	const $body = $(`<div class="sk-gw"><div class="sk-gw-loading">${__("Loading")}…</div></div>`).appendTo(page.body);
	frappe.dom.set_style(`
		.sk-gw{max-width:880px;margin:12px auto;border:1px solid #9bb3d6;background:#eef4fc;border-radius:6px;overflow:hidden}
		.sk-gw-head{background:#0b2a5b;color:#fff;display:flex;justify-content:space-between;padding:10px 14px;font-weight:700;font-size:15px;border-left:12px solid #c8102e}
		.sk-gw-cols{display:grid;grid-template-columns:1fr 1fr;gap:4px 28px;padding:10px 18px 16px}
		@media (max-width:700px){.sk-gw-cols{grid-template-columns:1fr}}
		.sk-gw-sec{color:#1f62b3;font-weight:700;border-bottom:1px solid #9bb3d6;margin:10px 0 4px;letter-spacing:.04em}
		.sk-gw-it{display:grid;grid-template-columns:26px 1fr auto;align-items:center;gap:6px;padding:4px 6px;border-radius:4px;cursor:pointer;color:#1d2433}
		.sk-gw-it small{display:block;color:#5b6577;font-size:11px}
		.sk-gw-it b{font-weight:600}
		.sk-gw-it kbd{font-size:10px;background:#4a5f82;color:#fff;border:0;border-radius:3px;padding:1px 5px}
		.sk-gw-it.on,.sk-gw-it:hover{background:#ffd54a}
		.sk-gw-help{padding:6px 14px 10px;color:#5b6577;font-size:12px}
	`);
	let items = [];
	let at = 0;
	const open = (it) => {
		if (!it) return;
		if (it.key === "create_ledger") return createLedger();
		if (it.key === "alter_ledger") return alterLedger();
		if (it.key === "approvals") return pendingList();
		if (it.key === "more_reports") return moreReports();
		if (it.key === "month_close") return frappe.set_route("query-report", "Profit and Loss Statement");
		frappe.set_route(it.url);  // "/app/payment-entry/new?payment_type=Pay": the query becomes the new voucher's values
	};
	let data = null;
	frappe.call("sk_app.tally.desk_gateway").then((r) => {
		data = r.message;
		items = [];
		const sec = (s) => `<div class="sk-gw-sec">${__(s.section).toUpperCase()}</div>` + s.items.map((it) => {
			items.push(it);
			return `<div class="sk-gw-it" data-i="${items.length - 1}"><span>${it.icon}</span><span><b>${frappe.utils.escape_html(it.label)}</b>${it.note ? `<small>${frappe.utils.escape_html(it.note)}</small>` : ""}</span>${it.keys ? `<kbd>${it.keys}</kbd>` : "<span></span>"}</div>`;
		}).join("");
		const s = data.sections;
		$body.html(`<div class="sk-gw-head"><span>SK IND TECH SOLUTIONS | ${__("Accounts Gateway")}</span><span>${data.fy}</span></div>
			<div class="sk-gw-cols"><div>${sec(s[0])}${sec(s[1])}</div><div>${sec(s[2])}${sec(s[3])}</div></div>
			<div class="sk-gw-help">↑ ↓ ${__("to move")}, Enter ${__("to open")} · F4 Contra · F5 Payment · F6 Receipt · F7 Journal · F8 Sales · F9 Purchase · Alt+D Day Book · Alt+L Ledger · Ctrl+A ${__("accept")} · Esc ${__("back here")}</div>`);
		mark(0);
		wrapper.sk_options();
	});
	// Alt+C / Alt+A / Pending from anywhere: /app/accounts-gateway?create=1 (also when the page is already open)
	wrapper.sk_options = () => {
		const ro = frappe.route_options || {};
		if (!data || !(ro.create || ro.alter || ro.pending)) return;
		frappe.route_options = null;
		if (ro.create) createLedger();
		else if (ro.alter) alterLedger();
		else pendingList();
	};
	const mark = (i) => {
		at = Math.max(0, Math.min(items.length - 1, i));
		$body.find(".sk-gw-it").removeClass("on").filter(`[data-i="${at}"]`).addClass("on");
	};
	$body.on("click", ".sk-gw-it", (e) => open(items[Number(e.currentTarget.dataset.i)]));
	$(document).on("keydown.skgw", (e) => {
		if (frappe.get_route()[0] !== "accounts-gateway" || $(".modal.show").length || $(e.target).is("input,textarea,select")) return;
		if (e.key === "ArrowDown") { mark(at + 1); e.preventDefault(); }
		else if (e.key === "ArrowUp") { mark(at - 1); e.preventDefault(); }
		else if (e.key === "Enter") { open(items[at]); e.preventDefault(); }
	});

	function createLedger() {
		const kinds = [["Customer (Sundry Debtor)", "Customer"], ["Supplier (Sundry Creditor)", "Supplier"], ["Bank / Cash / Expense / Income ledger", "Account"]];
		const d = new frappe.ui.Dialog({ title: __("Create Ledger"), fields: [{ fieldname: "kind", fieldtype: "Select", label: __("Ledger under"), reqd: 1,
			options: kinds.map((k) => k[0]).join("\n"), default: kinds[0][0] }],
			primary_action_label: __("Create"), primary_action: (v) => { d.hide(); frappe.new_doc(kinds.find((k) => k[0] === v.kind)[1]); } });
		d.show();
	}
	function alterLedger() {
		const d = new frappe.ui.Dialog({ title: __("Alter Ledger"), fields: [{ fieldname: "q", fieldtype: "Data", label: __("Ledger name") }, { fieldname: "list", fieldtype: "HTML" }] });
		const show = frappe.utils.debounce((q) => frappe.call("sk_app.tally.desk_find_ledger", { q }).then((r) => {
			d.fields_dict.list.$wrapper.html((r.message || []).map((x) => `<div class="sk-gw-it" data-dt="${x.doctype}" data-name="${frappe.utils.escape_html(x.name)}"><span>📒</span><span><b>${frappe.utils.escape_html(x.title)}</b><small>${frappe.utils.escape_html(x.group || "")}</small></span><span></span></div>`).join("") || `<p class="text-muted">${q.length < 2 ? __("Type 2 letters") : __("No ledger found")}</p>`);
		}), 300);
		d.fields_dict.q.$input.on("input", (e) => show(e.target.value));
		d.fields_dict.list.$wrapper.on("click", ".sk-gw-it", (e) => { d.hide(); frappe.set_route("Form", e.currentTarget.dataset.dt, e.currentTarget.dataset.name); });
		d.show();
	}
	function pendingList() {
		frappe.call("sk_app.tally.desk_pending").then((r) => {
			const rows = r.message || [];
			const d = new frappe.ui.Dialog({ title: __("Pending Approvals") + ` (${rows.length})`, fields: [{ fieldname: "list", fieldtype: "HTML" }], size: "large" });
			d.fields_dict.list.$wrapper.html(rows.map((x) => `<div class="sk-gw-it" data-dt="${x.doctype}" data-name="${frappe.utils.escape_html(x.name)}"><span>⏰</span><span><b>${x.vch_type} · ${frappe.utils.escape_html(x.name)}</b><small>${x.date} · ${frappe.utils.escape_html(x.by)}</small></span><span>${format_currency(x.amount)}</span></div>`).join("") || `<p class="text-muted">${__("Nothing pending")}</p>`);
			d.fields_dict.list.$wrapper.on("click", ".sk-gw-it", (e) => { d.hide(); frappe.set_route("Form", e.currentTarget.dataset.dt, e.currentTarget.dataset.name); });
			d.show();
		});
	}
	function moreReports() {
		const d = new frappe.ui.Dialog({ title: __("Display More Reports"), fields: [{ fieldname: "list", fieldtype: "HTML" }] });
		d.fields_dict.list.$wrapper.html((data.more || []).map((x) => `<div class="sk-gw-it" data-url="${x.url}"><span>📄</span><span><b>${frappe.utils.escape_html(x.label)}</b></span><span></span></div>`).join(""));
		d.fields_dict.list.$wrapper.on("click", ".sk-gw-it", (e) => { d.hide(); frappe.set_route(e.currentTarget.dataset.url); });
		d.show();
	}
};

frappe.pages["accounts-gateway"].on_page_show = function (wrapper) {
	if (wrapper.sk_options) wrapper.sk_options();
};
