// Copyright (c) 2026, SK Ind Tech Solutions Pvt Ltd

frappe.ui.form.on("SK App Settings", {
	refresh(frm) {
		if (!frappe.user.has_role("System Manager")) return;
		frm.add_custom_button(__("Load Sales team"), () => {
			frappe.confirm(__("Set up the Sales pilot people and their KPI targets? Existing targets are kept."), () => {
				frappe.call({ method: "sk_app.setup.load_sales_pilot_now", freeze: true }).then((r) => {
					const res = r.message || {};
					let msg = __("Set up: {0}", [(res.set_up || []).join(", ") || "-"]);
					if ((res.user_not_found || []).length) {
						msg += "<br>" + __("User not found: {0}", [res.user_not_found.join(", ")]);
					}
					frappe.msgprint({ title: __("Sales team"), message: msg, indicator: "green" });
				});
			});
		});
	},
});
