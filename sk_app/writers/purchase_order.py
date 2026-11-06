"""The one Purchase Order writer (linear flow map, Flow 3 Purchase). A PO from the chosen supplier quote and a PO made
straight from an approved requisition end the same way: linked to the CEO-approved requisition rows, saved, and either
placed or kept for the CEO when it is over 10% above the approved value. Used on the New path of Purchase; the rules
also run on every Purchase Order saved in ERPNext or through SK Hub (SK 4-Nov: same checks from any door)."""

import frappe
from frappe import _
from frappe.utils import flt, fmt_money

from sk_app.core.rules import report
from sk_app.writers.purchase_order_rules import ceo_reason, problems

APPROVED = "Approved"


def _rows(po) -> list[dict]:
	return [{"item_code": r.item_code, "qty": flt(r.qty), "rate": flt(r.rate), "material_request": r.material_request,
		"approved": bool(r.material_request and frappe.db.get_value("Material Request", r.material_request, "sk_approval") == APPROVED)}
		for r in po.get("items") or []]


def write(po, user: str, *, is_ceo: bool, ceos: list[str], limit: float, link_requests, approved_value, todo, try_submit, draft_reason) -> dict:
	"""Returns the app's result dict (name, posted, needs_approval, grand_total, why). The helpers are requisition's and
	store's own, passed in so there is one path and the tested pieces stay where they are."""
	link_requests(po)
	for_order = bool(po.get("sk_sales_order"))  # a service job for a customer order: the order is the request (Flow sheet 6-Nov)
	if any(not r.material_request for r in po.items) and not is_ceo and not for_order:
		frappe.throw(_("No CEO-approved purchase requisition for: {0}. Raise a requisition first.").format(
			", ".join(sorted({r.item_code for r in po.items if not r.material_request}))))
	po.flags.ignore_permissions = True
	po.insert()  # on_validate checks it, as for a PO made in ERPNext or by Claude
	po.calculate_taxes_and_totals()
	why = ceo_reason(0 if for_order else sum(1 for r in po.items if not r.material_request), approved_value(po), flt(po.net_total), flt(po.grand_total), limit)
	if why and not is_ceo:  # the CEO's own PO needs no second approval
		po.db_set("sk_needs_ceo", 1)
		po.add_comment("Comment", _("Waits for CEO: {0}").format(_(why)))
		for a in ceos:
			if a != user:
				todo(a, "Purchase Order", po.name, _("Approve PO {0}: {1} for {2} ({3})").format(po.name, po.supplier_name,
					fmt_money(po.grand_total, currency=po.currency), _(why)))
		return {"name": po.name, "posted": False, "needs_approval": True, "grand_total": po.grand_total, "why": _(why)}
	posted = try_submit(po)
	return {"name": po.name, "posted": posted, "reason": draft_reason(), "needs_approval": False, "grand_total": po.grand_total}


def on_validate(doc, method=None):
	"""Every Purchase Order on the New path of Purchase: supplier, date, lines with qty and rate, approved requisition."""
	from sk_app.core.switch import use_new
	from sk_app.requisition import _is_ceo

	if doc.docstatus == 1 or not use_new("Purchase", doc.owner or frappe.session.user):
		return
	found = problems(_rows(doc), doc.supplier, doc.schedule_date, _is_ceo(doc.owner or frappe.session.user), bool(doc.get("sk_sales_order")))
	report("Purchase", doc, found, title=_("Purchase order data missing"))
