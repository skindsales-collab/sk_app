// SK 23-Nov (approved, "safe cancel"): after a document is cancelled in ERPNext, ask at once whether to make the corrected
// copy (Amend), so an entry such as a salary journal is not left cancelled by mistake. "Not now" leaves it cancelled.
(function () {
	const DOCTYPES = ["Journal Entry", "Payment Entry", "Sales Invoice", "Purchase Invoice", "Quotation", "Sales Order",
		"Purchase Order", "Delivery Note", "Purchase Receipt", "Stock Entry", "Material Request", "Salary Slip", "Expense Claim",
		"Stock Reconciliation", "Work Order"];
	DOCTYPES.forEach((dt) => frappe.ui.form.on(dt, {
		after_cancel(frm) {
			if (!frm.perm[0] || !frm.perm[0].amend) return;
			const d = new frappe.ui.Dialog({
				title: __("{0} is cancelled", [frm.doc.name]),
				fields: [{ fieldtype: "HTML", options: `<p>${__("Was this cancelled to correct it? Make the corrected copy now (Amend). It opens as a draft with the same details; fix it and submit.")}</p>
					<p class="text-muted">${__("If it was cancelled on purpose (wrong entry, payment returned), choose Not now.")}</p>` }],
				primary_action_label: __("Amend now"),
				primary_action() { d.hide(); frm.amend_doc(); },
				secondary_action_label: __("Not now"),
				secondary_action() { d.hide(); },
			});
			d.show();
		},
	}));
})();
