// SK 28-Oct-2026: one button for Accounts to post the Tally invoices: cancel each old journal entry, submit its invoice
(function () {
	const settings = (frappe.listview_settings["Sales Invoice"] = frappe.listview_settings["Sales Invoice"] || {});
	const erpnext_onload = settings.onload;
	settings.onload = function (listview) {
		if (erpnext_onload) erpnext_onload.apply(this, arguments);
		if (!["Accounts Manager", "Accounts User", "System Manager"].some((r) => frappe.user.has_role(r))) return;
		listview.page.add_inner_button(__("Post Tally invoices"), () => {
			frappe.call("sk_app.tally_invoices.pending").then(({ message: n }) => {
				if (!n) return frappe.msgprint(__("No Tally invoices are waiting."));
				frappe.confirm(
					__("Post {0} Tally invoices? For each one the old journal entry is cancelled and the invoice is submitted.", [n]),
					() => frappe.call({ method: "sk_app.tally_invoices.post_all", type: "POST" }).then(() =>
						frappe.show_alert({ message: __("Posting started. A message shows here when it is done (1–3 minutes)."), indicator: "blue" }, 10)
					)
				);
			});
		});
	};
})();
