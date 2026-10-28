"""Tally sales → Sales Invoices in one click (SK 28-Oct-2026: "cancel all je & submit invoice with some simple click").

Apr–Oct Tally sales came in as Journal Entries. SK Hub made a draft Sales Invoice (series SINV-.YY.-) for each one; its
remarks say "cancel ACC-JV-… first, then submit this invoice". The "Post Tally invoices" button on the Sales Invoice list
does exactly that for every such draft: cancel the journal entry, then submit the invoice, so the sale is never counted
twice. Each pair runs on its own; one that fails stays as it was and is listed with the reason.
"""

import re

import frappe

ROLES = ("Accounts Manager", "Accounts User", "System Manager")
JE_IN_REMARKS = re.compile(r"cancel (ACC-JV-\d{4}-\d+) first")


def _drafts():
	return frappe.get_all("Sales Invoice", filters={"docstatus": 0, "naming_series": "SINV-.YY.-", "remarks": ["like", "%then submit this invoice%"]},
		fields=["name", "remarks"], order_by="posting_date asc, name asc")


@frappe.whitelist()
def pending():
	"""How many Tally drafts are waiting (for the button's confirm text)."""
	frappe.only_for(ROLES)
	return len(_drafts())


@frappe.whitelist(methods=["POST"])
def post_all():
	frappe.only_for(ROLES)
	frappe.enqueue("sk_app.tally_invoices.run", queue="long", timeout=3600, user=frappe.session.user, enqueue_after_commit=True)
	return len(_drafts())


def run(user):
	frappe.set_user(user)
	done, failed = [], []
	for row in _drafts():
		m = JE_IN_REMARKS.search(row.remarks or "")
		je = m.group(1) if m else None
		try:
			frappe.db.savepoint("tally_pair")
			if je and frappe.db.get_value("Journal Entry", je, "docstatus") == 1:
				frappe.get_doc("Journal Entry", je).cancel()
			frappe.get_doc("Sales Invoice", row.name).submit()
			frappe.db.commit()
			done.append(row.name)
		except Exception as e:
			frappe.db.rollback(save_point="tally_pair")
			frappe.clear_messages()
			failed.append(f"{row.name} ({je or 'no JE'}): {frappe.utils.strip_html(str(e))[:200]}")
	msg = f"Tally invoices posted: {len(done)}. Not posted: {len(failed)}."
	if failed:
		msg += "<br>" + "<br>".join(failed)
	frappe.publish_realtime("msgprint", {"message": msg, "title": "Post Tally invoices"}, user=user)
	# also in the bell, in case the page was closed while it ran
	frappe.get_doc({"doctype": "Notification Log", "for_user": user, "type": "Alert", "document_type": "Sales Invoice",
		"subject": f"Tally invoices posted: {len(done)}, not posted: {len(failed)}", "email_content": msg}).insert(ignore_permissions=True)
	frappe.db.commit()
