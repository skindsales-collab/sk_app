// Tally keys in ERPNext for the accounts team (SK 27-Oct-2026): F4 Contra, F5 Payment, F6 Receipt, F7 Journal,
// F8 Sales, F9 Purchase, Ctrl+F8 Sales Order, Ctrl+F9 Purchase Order, Alt+F5 Debit Note, Alt+F6 Credit Note (SK 27-Oct
// change), Alt+D Day Book, Alt+L Ledger, Alt+G Gateway,
// Alt+C Create Ledger, Alt+A Alter Ledger,
// Ctrl+A accept (save and post) on a voucher, Esc back to the Accounts Gateway from a voucher list.
(function () {
	const VOUCHERS = ["Payment Entry", "Journal Entry", "Sales Invoice", "Purchase Invoice"];
	const KEYS = {
		F4: ["Payment Entry", { payment_type: "Internal Transfer" }],
		F5: ["Payment Entry", { payment_type: "Pay" }],
		F6: ["Payment Entry", { payment_type: "Receive" }],
		F7: ["Journal Entry", {}],
		F8: ["Sales Invoice", {}],
		F9: ["Purchase Invoice", {}],
		"Ctrl+F8": ["Sales Order", {}],
		"Ctrl+F9": ["Purchase Order", {}],
		"Alt+F5": ["Purchase Invoice", { is_return: 1 }],
		"Alt+F6": ["Sales Invoice", { is_return: 1 }],
	};
	const accounts = () => frappe.boot && frappe.user && (frappe.user.has_role("Accounts User") || frappe.user.has_role("Accounts Manager"));
	document.addEventListener("keydown", (e) => {
		if (!window.frappe || !frappe.get_route || !accounts()) return;
		const name = (e.ctrlKey ? "Ctrl+" : "") + (e.altKey ? "Alt+" : "") + e.key;
		if (KEYS[name] && !e.shiftKey) {
			e.preventDefault();
			e.stopPropagation();
			const [dt, values] = KEYS[name];
			frappe.new_doc(dt, values);
			return;
		}
		if (e.altKey && !e.ctrlKey) {
			const k = (e.key || "").toLowerCase();
			const go = { d: "/app/query-report/Tally Day Book", l: "/app/query-report/Tally Ledger", g: "/app/accounts-gateway",
				c: "/app/accounts-gateway?create=1", a: "/app/accounts-gateway?alter=1" }[k];
			if (go) { e.preventDefault(); frappe.set_route(go); return; }
		}
		const route = frappe.get_route();
		// Ctrl+A on a voucher form = accept: save and post (submit), with ERPNext's own confirm
		if (e.ctrlKey && !e.shiftKey && (e.key === "a" || e.key === "A") && route[0] === "Form" && VOUCHERS.includes(route[1]) && window.cur_frm) {
			if (cur_frm.doc.docstatus !== 0) return;
			e.preventDefault();
			cur_frm.savesubmit();
			return;
		}
		if (e.key === "Escape" && route[0] === "List" && VOUCHERS.includes(route[1]) && !$(".modal.show").length) {
			frappe.set_route("accounts-gateway");
		}
	}, true);
})();
