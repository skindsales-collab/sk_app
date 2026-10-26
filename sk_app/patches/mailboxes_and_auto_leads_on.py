"""Change list point 14 (SK, 26-Oct-2026): switch on the free auto leads from IndiaMART / JustDial / GeM mails and
fill the team mailbox list once. They can be switched off later on the app's Lead Sources page."""

import frappe

from sk_app.mailbox import DEFAULT_MAP


def execute():
	for field in ("auto_leads", "indiamart_mail", "justdial_mail", "gem_mail"):
		frappe.db.set_single_value("SK App Settings", field, 1)
	if not frappe.db.get_single_value("SK App Settings", "mailbox_map"):
		frappe.db.set_single_value("SK App Settings", "mailbox_map", DEFAULT_MAP)
	# owners by name when nobody is set yet (SK: digital → Pranali, cabin → Rushi, machine shifting / job work → Aditya)
	for field, names in (("lead_owner_digital", ("pranali",)), ("lead_owner_cabin", ("rishikesh", "rushi")),
			("lead_owner_noncabin", ("aditya",))):
		if frappe.db.get_single_value("SK App Settings", field):
			continue
		for u in frappe.get_all("SK App User", filters={"enabled": 1}, fields=["user", "full_name"]):
			if any((u.full_name or "").lower().startswith(n) for n in names):
				frappe.db.set_single_value("SK App Settings", field, u.user)
				break
