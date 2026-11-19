"""Every essential ERPNext step of the sales-to-factory flow done in the app by its owner (SK 26-Oct: "every essential
action which needs to be performed in the ERP flow must come in the app"). The gaps found in the live data were:
no Quotation, Customer or Sales Order made from the app and no Work Order for the factory. So:

	CRM Deal → Customer (Sales) → Quotation (Sales, PDF to the customer) → Sales Order when the order comes (Sales)
	→ Confirm order (Sales manager / CEO submits it) → Work Order per cabin (Production)

Each step is an ordinary ERPNext document made under the person's own login, so ERPNext's own permissions and
validations apply and every action leaves its data (TLC SAS: proof of each action)."""

import frappe
from sk_app import store_screens
from frappe import _
from frappe.utils import add_days, flt, getdate, nowdate

from sk_app import crm, store
from sk_app.core.switch import use_new


def _deal(name: str) -> dict:
	crm._check("CRM Deal", name)
	meta = frappe.get_meta("CRM Deal")
	fields = [f for f in ("name", "organization", "lead_name", "mobile_no", "email", "deal_owner", "erpnext_customer", "sk_customer_name",
		"sk_segment", "sk_no_gstin") if f == "name" or meta.has_field(f)]
	return frappe.db.get_value("CRM Deal", name, fields, as_dict=True)

def customer_of(deal: str) -> str | None:
	d = _deal(deal)
	if d.get("erpnext_customer") and frappe.db.exists("Customer", d.erpnext_customer):
		return d.erpnext_customer
	if frappe.get_meta("Customer").has_field("crm_deal"):
		return frappe.db.get_value("Customer", {"crm_deal": deal})
	return None

GST_TERMS = "GST @ 18% extra as applicable."

def gst_terms(terms: str | None) -> str:
	"""SK 28-Oct: quotes show no GST amount, only the rate: totals stay before GST and the terms say GST is extra."""
	terms = (terms or "").strip()
	return terms if "gst" in terms.lower() else (terms + "<br>" if terms else "") + GST_TERMS

def _rate(item_code: str) -> float:
	price_list = frappe.db.get_single_value("Selling Settings", "selling_price_list") or "Standard Selling"
	return flt(frappe.db.get_value("Item Price", {"item_code": item_code, "price_list": price_list, "selling": 1}, "price_list_rate"))

def _attach_po(file_url: str, sales_order: str, user: str):
	crm._attach(file_url, "Sales Order", sales_order, user)

def _warehouses(company: str) -> dict:
	"""Work-in-progress and finished-goods stores of the company (ERPNext's standard names), else the default store."""
	abbr = frappe.db.get_value("Company", company, "abbr")
	default = frappe.db.get_value("Warehouse", {"company": company, "is_group": 0, "warehouse_name": "Stores"}) or frappe.db.get_value(
		"Warehouse", {"company": company, "is_group": 0})
	pick = lambda name: name if frappe.db.exists("Warehouse", name) else default  # noqa: E731
	return {"wip_warehouse": pick(f"Work In Progress - {abbr}"), "fg_warehouse": pick(f"Finished Goods - {abbr}"), "source_warehouse": default}
