"""Day Book like Tally (SK 27-Oct-2026): every voucher of the day with Tally voucher types."""

from frappe import _

from sk_app.tally import day_book


def execute(filters=None):
	filters = filters or {}
	columns = [
		{"label": _("Date"), "fieldname": "date", "fieldtype": "Date", "width": 100},
		{"label": _("Particulars"), "fieldname": "particulars", "fieldtype": "Data", "width": 260},
		{"label": _("Vch Type"), "fieldname": "vch_type", "fieldtype": "Data", "width": 110},
		{"label": _("Vch No."), "fieldname": "vch_no", "fieldtype": "Dynamic Link", "options": "voucher_type", "width": 170},
		{"label": _("Debit Amount"), "fieldname": "debit", "fieldtype": "Currency", "width": 130},
		{"label": _("Credit Amount"), "fieldname": "credit", "fieldtype": "Currency", "width": 130},
		{"label": _("Narration"), "fieldname": "narration", "fieldtype": "Data", "width": 260},
		{"label": _("Voucher Type"), "fieldname": "voucher_type", "fieldtype": "Data", "hidden": 1},
	]
	return columns, day_book(filters.get("from_date"), filters.get("to_date"), filters.get("company"))
