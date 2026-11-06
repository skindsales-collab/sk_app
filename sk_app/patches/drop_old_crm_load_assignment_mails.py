"""One-time clean-up (SK 6-Nov night): the old CRM load of 6-Nov queued one "assigned a new task" e-mail per loaded lead;
73 of them ended in status Error on the mail server's hourly limit and SK's login may not delete Email Queue rows.
Only those rows go: status Error, made on 6-Nov after 20:00 IST, subject of that assignment. Older error rows (some were
real customer mails, 17-29 Oct) are not touched."""

import frappe


def execute():
	if not frappe.db.table_exists("Email Queue"):
		return
	names = frappe.get_all("Email Queue", filters={"status": "Error", "creation": [">=", "2026-11-06 20:00:00"],
		"message": ["like", "%Administrator assigned a new task CRM Lead%"]}, pluck="name")
	for name in names:
		frappe.delete_doc("Email Queue", name, ignore_permissions=True, force=True)
	if names:
		frappe.db.commit()
