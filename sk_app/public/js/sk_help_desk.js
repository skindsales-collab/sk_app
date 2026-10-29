// SK 28-Oct: ❓ help on every ERPNext page. SK 29-Oct: the question goes to the Problem / Suggestion desk (an ERPNext
// Issue for AI & ERP) with the page's name and a screenshot; Claude drafts the answer; the reply comes back to the
// person and can go into the FAQ.
(function () {
	const MR = () => (frappe.boot && frappe.boot.lang || "").startsWith("mr");
	const T = (en, mr) => (MR() ? mr : en);
	function page() {
		const route = (frappe.get_route_str && frappe.get_route_str()) || location.pathname;
		const title = (document.title || "").replace(/\s*\|.*$/, "").trim();
		return ("ERPNext: " + [title, route].filter(Boolean).join(" · ")).slice(0, 50);
	}
	function ask() {
		const where = page();
		const d = new frappe.ui.Dialog({
			title: "❓ " + T("Ask about this page", "या पानाबद्दल विचारा"),
			fields: [
				{ fieldtype: "HTML", fieldname: "where", options: `<p class="text-muted">${T("Page", "पान")}: <b>${frappe.utils.escape_html(where)}</b></p>` },
				{ fieldtype: "Small Text", fieldname: "question", label: T("What is the problem or question?", "अडचण किंवा प्रश्न काय आहे?"), reqd: 1 },
				{ fieldtype: "Attach Image", fieldname: "shot", label: T("Screenshot (Windows: Win + Shift + S, then save or paste)", "स्क्रीनशॉट (Windows: Win + Shift + S)") },
			],
			primary_action_label: T("Send", "पाठवा"),
			primary_action(v) {
				d.disable_primary_action();
				frappe.call({ method: "sk_app.api.desk_send", type: "POST", args: { kind: "Question", area: "App / ERPNext", text: v.question, photo: v.shot || null, screen: where } })
					.then((r) => { d.hide(); frappe.show_alert({ message: T("Sent", "पाठवले") + ` ${(r.message || {}).issue || ""}. ` + T("The answer comes to your ToDo and the SK App.", "उत्तर ToDo आणि SK App मध्ये मिळेल."), indicator: "green" }); })
					.always(() => d.enable_primary_action());
			},
		});
		d.show();
	}
	function addButton() {
		if (document.getElementById("sk-desk-help") || !frappe.session || frappe.session.user === "Guest") return;
		const b = document.createElement("button");
		b.id = "sk-desk-help";
		b.type = "button";
		b.title = "Help / question";
		b.textContent = "❓";
		Object.assign(b.style, { position: "fixed", right: "18px", bottom: "18px", zIndex: 1020, width: "44px", height: "44px", borderRadius: "22px",
			border: "0", background: "#14213d", color: "#fff", fontSize: "20px", boxShadow: "0 3px 10px rgba(0,0,0,.25)", cursor: "pointer" });
		b.addEventListener("click", ask);
		document.body.appendChild(b);
	}
	if (window.frappe && frappe.ready) frappe.ready(addButton);
	else document.addEventListener("DOMContentLoaded", addButton);
	$(document).on("app_ready", addButton);
})();
