"""SK Tax Invoice print (SK 29-Oct-2026, Shraddha: "Invoice details of consignee (Ship to) and Buyer (Bill to) not
mentioned in ERP Next Invoice format").

GST tax invoice on SK's name plate (same header as the cabin quotation): seller with GSTIN, invoice no. / date, place of
supply, Bill to (buyer) and Ship to (consignee) side by side with name, address, state code and GSTIN, items with HSN,
taxable value and CGST / SGST / IGST rate and amount, totals and amount in words. Invoices are tax invoices, so the GST
amounts are shown (quotations show only the GST %).

When an invoice has no address picked (the Tally invoices of 28-Oct), the customer's own Billing / Shipping address in
ERPNext is used, so adding the address to the customer fixes the print of old invoices too. Ship to falls back to the
Bill to address. The gate (gates.check_sales_invoice) stops a new invoice being submitted without the buyer's address.
"""

import frappe
from frappe.utils import cint, flt, formatdate

from sk_app.cabin_quote import inr, words

PRINT_FORMAT = "SK Tax Invoice"
ADDRESS_FIELDS = ["name", "address_title", "address_line1", "address_line2", "city", "state", "pincode", "country",
	"gstin", "gst_state_number", "phone", "email_id", "address_type", "is_primary_address", "is_shipping_address"]


def ensure_setup():
	html = "{{ sk_tax_invoice_html(doc) }}"
	if frappe.db.exists("Print Format", PRINT_FORMAT):
		frappe.db.set_value("Print Format", PRINT_FORMAT, {"html": html, "disabled": 0})
	else:
		frappe.get_doc({"doctype": "Print Format", "name": PRINT_FORMAT, "doc_type": "Sales Invoice", "module": "SK App",
			"custom_format": 1, "print_format_type": "Jinja", "standard": "No", "html": html, "margin_top": 0, "margin_left": 0,
			"margin_right": 0}).insert(ignore_permissions=True)
	from frappe.custom.doctype.property_setter.property_setter import make_property_setter

	make_property_setter("Sales Invoice", None, "default_print_format", PRINT_FORMAT, "Data", validate_fields_for_doctype=False)


# ---------- addresses ----------

def _address(name: str | None) -> dict | None:
	if not name:
		return None
	meta = frappe.get_meta("Address")
	return frappe.db.get_value("Address", name, [f for f in ADDRESS_FIELDS if f == "name" or meta.has_field(f)], as_dict=True)


def party_address(customer: str | None, shipping: bool = False) -> dict | None:
	"""The customer's own address in ERPNext: for Ship to the shipping one first, else the primary / billing one."""
	if not customer:
		return None
	names = frappe.get_all("Dynamic Link", filters={"link_doctype": "Customer", "link_name": customer, "parenttype": "Address"},
		pluck="parent")
	rows = [a for a in (_address(n) for n in names) if a]
	if not rows:
		return None
	if shipping:
		ship = [a for a in rows if cint(a.get("is_shipping_address")) or a.get("address_type") == "Shipping"]
		if ship:
			return ship[0]
	primary = frappe.db.get_value("Customer", customer, "customer_primary_address")
	rows.sort(key=lambda a: (a.name != primary, not cint(a.get("is_primary_address")), a.get("address_type") != "Billing"))
	return rows[0]


def parties(doc) -> tuple[dict | None, dict | None, bool]:
	"""(bill to, ship to, ship to is the same place as bill to)."""
	bill = _address(doc.get("customer_address")) or party_address(doc.customer)
	ship = _address(doc.get("shipping_address_name")) or party_address(doc.customer, shipping=True) or bill
	return bill, ship, bool(bill and ship and bill.name == ship.name)


# ---------- print ----------

def _esc(x) -> str:
	return frappe.utils.escape_html(str(x or ""))


STATE_CODES = {"Jammu and Kashmir": "01", "Himachal Pradesh": "02", "Punjab": "03", "Chandigarh": "04", "Uttarakhand": "05",
	"Haryana": "06", "Delhi": "07", "Rajasthan": "08", "Uttar Pradesh": "09", "Bihar": "10", "Sikkim": "11", "Arunachal Pradesh": "12",
	"Nagaland": "13", "Manipur": "14", "Mizoram": "15", "Tripura": "16", "Meghalaya": "17", "Assam": "18", "West Bengal": "19",
	"Jharkhand": "20", "Odisha": "21", "Chhattisgarh": "22", "Madhya Pradesh": "23", "Gujarat": "24",
	"Dadra and Nagar Haveli and Daman and Diu": "26", "Maharashtra": "27", "Karnataka": "29", "Goa": "30", "Lakshadweep Islands": "31",
	"Kerala": "32", "Tamil Nadu": "33", "Puducherry": "34", "Andaman and Nicobar Islands": "35", "Telangana": "36",
	"Andhra Pradesh": "37", "Ladakh": "38"}


def _state(a: dict) -> str:
	state = (a.get("state") or "").strip()
	code = a.get("gst_state_number") or STATE_CODES.get(state) or (a.get("gstin") or "")[:2]
	return f"{_esc(state)}{f', Code {_esc(code)}' if code else ''}" if state else ""


def _party_html(title: str, name: str, a: dict | None, gstin: str | None, same: bool = False) -> str:
	lines = [f"<div class=pt>{title}</div><b>{_esc(name)}</b>"]
	if a:
		place = " - ".join(x for x in (_esc((a.get("city") or "").strip()), _esc(a.get("pincode"))) if x)
		lines += [_esc(x) for x in (a.get("address_line1"), a.get("address_line2")) if (x or "").strip()]
		if place:
			lines.append(place)
		if _state(a):
			lines.append(f"<span class=k>State</span>{_state(a)}")
		gstin = a.get("gstin") or gstin
		if a.get("phone"):
			lines.append(f"<span class=k>Phone</span>{_esc(a.phone)}")
	else:
		lines.append("<span class=miss>Address not in ERPNext: add it to the customer, then print again</span>")
	lines.append(f"<span class=k>GSTIN</span><b>{_esc(gstin) if gstin else 'Unregistered'}</b>")
	if same:
		lines.append("<i class=mut>(same as Bill to)</i>")
	return "<br>".join(lines)


def _gst(doc) -> dict:
	"""Rate and amount per GST head for each item row (India Compliance keeps them on the row), plus totals."""
	heads = [h for h in ("igst", "cgst", "sgst", "cess") if any(flt(i.get(f"{h}_amount")) for i in doc.items)]
	if not heads:  # no India Compliance values on the rows: take the tax table as it is
		heads = [h for h in ("cgst", "sgst", "igst") if any((t.get("gst_tax_type") or "") == h for t in doc.get("taxes") or [])]
	return {"heads": heads, "total": {h: sum(flt(i.get(f"{h}_amount")) for i in doc.items) for h in heads}}


def _bank(company: str) -> str:
	if not frappe.db.exists("DocType", "Bank Account"):
		return ""
	meta = frappe.get_meta("Bank Account")
	fields = [f for f in ("bank", "bank_account_no", "branch_code", "account_name") if meta.has_field(f)]
	acc = frappe.get_all("Bank Account", filters={"is_company_account": 1, "company": company, "disabled": 0}, fields=fields,
		order_by="is_default desc", limit=1) if meta.has_field("is_company_account") else []
	if not acc:
		return ""
	a = acc[0]
	return (f"<b>Bank details</b><br>Bank: {_esc(a.get('bank'))}<br>A/c no.: {_esc(a.get('bank_account_no'))}"
		+ (f"<br>IFSC: {_esc(a.get('branch_code'))}" if a.get("branch_code") else ""))


def invoice_html(doc) -> str:
	bill, ship, same = parties(doc)
	gstin_buyer = doc.get("billing_address_gstin") or (frappe.db.get_value("Customer", doc.customer, "gstin") if doc.customer else None)
	g = _gst(doc)
	heads = g["heads"]
	label = {"igst": "IGST", "cgst": "CGST", "sgst": "SGST", "cess": "Cess"}
	head_th = "".join(f"<th colspan=2>{label[h]}</th>" for h in heads)
	sub_th = "".join("<th>%</th><th>Amount</th>" for _h in heads)
	rows = []
	for i, d in enumerate(doc.items, 1):
		taxable = flt(d.get("taxable_value")) or flt(d.net_amount)
		desc = _esc(d.item_name)
		if d.description and frappe.utils.strip_html(d.description).strip() != (d.item_name or "").strip():
			desc += f"<div class=mut>{d.description}</div>"
		tax = "".join(f"<td class=c>{flt(d.get(f'{h}_rate')):g}</td><td class=r>{inr2(d.get(f'{h}_amount'))}</td>" for h in heads)
		rows.append(f"<tr><td class=c>{i}</td><td>{desc}</td><td class=c>{_esc(d.get('gst_hsn_code'))}</td><td class=c>{flt(d.qty):g}</td>"
			f"<td class=c>{_esc(d.uom)}</td><td class=r>{inr2(d.net_rate or d.rate)}</td><td class=r>{inr2(taxable)}</td>{tax}</tr>")
	taxable_total = sum(flt(d.get("taxable_value")) or flt(d.net_amount) for d in doc.items)
	tot_tax = "".join(f"<td></td><td class=r>{inr2(g['total'][h])}</td>" for h in heads)
	summary = [("Taxable value", taxable_total)]
	gst_rows = {t.get("gst_tax_type"): t for t in doc.get("taxes") or [] if t.get("gst_tax_type")}
	for h in heads:
		rate = flt(gst_rows[h].rate) if h in gst_rows else 0
		summary.append((f"{label[h]}{f' @ {rate:g}%' if rate else ''}", g["total"][h] or flt(gst_rows.get(h, {}).get("tax_amount"))))
	for t in doc.get("taxes") or []:
		if not t.get("gst_tax_type") and flt(t.tax_amount):
			summary.append((_esc(t.description), flt(t.tax_amount)))
	if flt(doc.discount_amount):
		summary.append(("Discount", -flt(doc.discount_amount)))
	if flt(doc.rounding_adjustment):
		summary.append(("Rounding off", flt(doc.rounding_adjustment)))
	total = flt(doc.rounded_total) or flt(doc.grand_total)
	summary_html = "".join(f"<tr><td>{k}</td><td class=r>{inr2(v)}</td></tr>" for k, v in summary)
	tax_total = sum(g["total"].values()) or flt(doc.total_taxes_and_charges)
	seller = _address(doc.get("company_address"))
	seller_gstin = doc.get("company_gstin") or (seller or {}).get("gstin") or ""
	seller_lines = [_esc(x) for x in ((seller or {}).get("address_line1"), (seller or {}).get("address_line2")) if (x or "").strip()]
	if seller:
		seller_lines.append(" - ".join(x for x in (_esc(seller.city), _esc(seller.pincode)) if x))
		if _state(seller):
			seller_lines.append(f"<span class=k>State</span>{_state(seller)}")
	seller_lines.append(f"<span class=k>GSTIN</span><b>{_esc(seller_gstin)}</b>")
	if len(seller_gstin) == 15:
		seller_lines.append(f"<span class=k>PAN</span>{_esc(seller_gstin[2:12])}")
	date = lambda d: formatdate(d, "dd-MMM-yyyy") if d else ""  # noqa: E731
	info = [("Invoice No.", f"<b>{_esc(doc.name)}</b>"), ("Date", f"<b>{date(doc.posting_date)}</b>"),
		("Place of supply", _esc(doc.get("place_of_supply"))), ("Reverse charge", "Yes" if cint(doc.get("is_reverse_charge")) else "No")]
	if doc.get("po_no"):
		info.append(("Buyer's PO", _esc(doc.po_no) + (f" dt. {date(doc.po_date)}" if doc.get("po_date") else "")))
	if doc.get("due_date"):
		info.append(("Due date", date(doc.due_date)))
	if doc.get("ewaybill"):
		info.append(("e-Way bill", _esc(doc.ewaybill)))
	if doc.get("vehicle_no"):
		info.append(("Vehicle no.", _esc(doc.vehicle_no)))
	irn = f"<div class=irn>IRN: {_esc(doc.irn)}</div>" if doc.get("irn") else ""
	title = "CREDIT NOTE" if cint(doc.get("is_return")) else "DEBIT NOTE" if cint(doc.get("is_debit_note")) else "TAX INVOICE"
	copy = _esc(doc.get("invoice_copy") or "Original for Recipient")
	header = frappe.utils.get_url("/assets/sk_app/images/sk-quote-header.png")
	terms = f"<div class=bar>Terms</div><div>{doc.terms}</div>" if doc.get("terms") else ""
	return f"""<style>{CSS}</style><div class=skq><img class=hdr src="{header}">
<div class=band>{title} &nbsp; | &nbsp; {copy}</div>{irn}
<table class=box><tr><td style="width:55%"><div class=pt>Seller</div><b>SK Ind Tech Solutions Pvt Ltd</b><br>{"<br>".join(seller_lines)}</td>
<td>{"<br>".join(f"<span class=k>{k}</span>{v}" for k, v in info)}</td></tr>
<tr><td>{_party_html("Bill to (Buyer)", doc.customer_name or doc.customer, bill, gstin_buyer)}</td>
<td>{_party_html("Ship to (Consignee)", (ship or {}).get("address_title") or doc.customer_name or doc.customer, ship, gstin_buyer, same)}</td></tr></table>
<table class=p><tr><th rowspan=2>Sr.</th><th rowspan=2 style="width:30%">Description</th><th rowspan=2>HSN / SAC</th><th rowspan=2>Qty</th><th rowspan=2>Unit</th>
<th rowspan=2>Rate</th><th rowspan=2>Taxable value</th>{head_th}</tr><tr>{sub_th}</tr>{"".join(rows)}
<tr class=tot><td colspan=6 class=r>Total</td><td class=r>{inr2(taxable_total)}</td>{tot_tax}</tr></table>
<table class=sum><tr><td class=w>
<div class=words>Amount in words: Rupees {words(int(round(total)))} Only</div>
<div class=words2>GST in words: Rupees {words(int(round(tax_total)))} Only</div><br>{_bank(doc.company)}</td>
<td><table class=p>{summary_html}<tr class=tot><td>Invoice total</td><td class=r>{inr2(total)}</td></tr></table></td></tr></table>
{terms}
<table class=sign><tr><td><b>Declaration</b><br>We declare that this invoice shows the actual price of the goods / services described and
that all particulars are true and correct.</td><td class=r><b>For SK Ind Tech Solutions Pvt Ltd</b><br><br><br><br>Authorised Signatory</td></tr></table>
<div class=foot>This is a computer generated invoice. | SK Ind Tech Solutions Pvt Ltd</div></div>"""


def inr2(x) -> str:
	"""₹ with Indian commas and paise (a tax invoice shows paise)."""
	x = flt(x, 2)
	sign = "-" if x < 0 else ""
	paise = int(round(abs(x) * 100)) % 100
	return f"{sign}{inr(int(abs(x)))}.{paise:02d}"


def sk_tax_invoice_html(doc) -> str:
	"""Jinja method for the print format (hooks: jinja methods)."""
	return invoice_html(doc)


CSS = """
.skq{font-family:'Liberation Sans',Arial,sans-serif;font-size:8.8pt;color:#222}
.skq .hdr{width:100%}
.skq .band{background:#C8233C;color:#fff;font-weight:bold;text-align:center;padding:5px;font-size:10.5pt;margin-bottom:6px}
.skq .irn{font-size:7.5pt;color:#555;margin:-3px 0 4px}
.skq table{border-collapse:collapse;width:100%}
.skq table.box td{border:1px solid #BFBFBF;vertical-align:top;padding:5px 6px;line-height:1.45}
.skq .pt{background:#2A6EB4;color:#fff;font-weight:bold;padding:2px 6px;margin:-5px -6px 4px;text-transform:uppercase;font-size:8pt}
.skq .k{font-style:italic;color:#777;width:112px;display:inline-block;white-space:nowrap}
.skq .miss{color:#C8233C;font-weight:bold}
.skq .mut{color:#666;font-size:8pt}
.skq table.p{margin-top:8px}
.skq table.p th{background:#1D4F86;color:#fff;padding:3px 4px;border:1px solid #1D4F86;font-size:8pt}
.skq table.p td{border:1px solid #BFBFBF;padding:3px 4px;vertical-align:top}
.skq .c{text-align:center}.skq .r{text-align:right}
.skq tr.tot td{background:#FFF2CC;font-weight:bold}
.skq table.sum td{vertical-align:top;border:0;padding:0}.skq table.sum td.w{width:58%;padding:10px 10px 0 0}
.skq .words{color:#1D4F86;font-weight:bold;font-style:italic}
.skq .words2{color:#1D4F86;font-style:italic;margin-top:3px}
.skq .bar{background:#2A6EB4;color:#fff;font-weight:bold;padding:3px 6px;margin:10px 0 4px;text-transform:uppercase}
.skq table.sign{margin-top:14px}.skq table.sign td{border:1px solid #BFBFBF;padding:6px;vertical-align:top;width:50%}
.skq .foot{text-align:center;color:#777;font-size:7.5pt;margin-top:6px}
"""
