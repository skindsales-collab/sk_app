// SK 23-Nov (approved): "Payment failed / returned" on a submitted payment or bank entry: makes a draft reversing entry.
(function () {
	const add = (frm) => {
		if (frm.doc.docstatus !== 1) return;
		if (frm.doctype === "Journal Entry" && !["Bank Entry", "Cash Entry"].includes(frm.doc.voucher_type)) return;
		frm.add_custom_button(__("Payment failed / returned"), () => {
			frappe.prompt([{ fieldname: "reason", fieldtype: "Data", label: __("What happened (e.g. cheque bounced, NEFT returned)"), reqd: 1 }],
				(v) => frappe.call({ method: "sk_app.bank_return.payment_returned", args: { doctype: frm.doctype, name: frm.doc.name, reason: v.reason },
					freeze: true, callback: (r) => { if (r.message) { frappe.show_alert(__("Draft reversal {0}: check and submit it", [r.message.name])); frappe.set_route("Form", "Journal Entry", r.message.name); } } }),
				__("Payment failed / returned"), __("Make draft reversal"));
		}, __("Actions"));
	};
	["Payment Entry", "Journal Entry"].forEach((dt) => frappe.ui.form.on(dt, { refresh: add }));
})();
