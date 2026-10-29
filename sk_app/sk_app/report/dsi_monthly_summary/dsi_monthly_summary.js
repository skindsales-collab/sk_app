// DSI Monthly Summary (SK 29-Oct-2026): from April of this financial year to today by default
frappe.query_reports["DSI Monthly Summary"] = {
	filters: [
		{ fieldname: "from_date", label: __("From Date"), fieldtype: "Date", reqd: 1,
			default: (() => { const d = frappe.datetime.str_to_obj(frappe.datetime.get_today()); return `${d.getMonth() < 3 ? d.getFullYear() - 1 : d.getFullYear()}-04-01`; })() },
		{ fieldname: "to_date", label: __("To Date"), fieldtype: "Date", reqd: 1, default: frappe.datetime.get_today() },
		{ fieldname: "function", label: __("Function / Role"), fieldtype: "Data" },
		{ fieldname: "user", label: __("User"), fieldtype: "Link", options: "User" },
	],
};
