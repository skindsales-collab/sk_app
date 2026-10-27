"""Standard cabin quotation (SK 27-Oct-2026: "make all quotations in the app / ERP only, for all cabins; for the same
requirement different users must give the same quote; use the earlier quote as the template").

- One rate card (SK Cabin Rate Card, only SK / System Manager edits it): base Rs per sq ft per cabin type (slabs by
  area), extra height, options, transport, crane, discount limits and terms. price() is the logic from the plan thread
  (cabin-quote/source/cabin_quote.py), unchanged, so the same requirement always gives the same price.
- The salesperson picks type, size, qty, options, km and crane; the price is worked out here and cannot be typed.
- Discount: a salesperson none, the sales manager up to 5 %, above that SK approves (the quote waits without it).
- Cabins outside the rate card (LGSF, modular, containers, very big) go to design; their price is the design BOM's.
- Every quotation keeps the rate card version, the requirement, its own number SK/CAB/26-27/<CUS>-NNN and revision.
- Print format "SK Cabin Quotation" = SK's quote template (header banner, red band, blue bars, navy table).
"""

import json
import math
import os

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, formatdate, getdate, nowdate

RATE_CARD = "SK Cabin Rate Card"
PRINT_FORMAT = "SK Cabin Quotation"
# service items for the quotation rows when no matching cabin item exists
CABIN_ITEM, OPTION_ITEM, TRANSPORT_ITEM = "SK-CABIN", "SK-CABIN-OPTION", "SK-TRANSPORT"
SERVICE_ITEMS = {CABIN_ITEM: "Standard cabin (as per quotation)", OPTION_ITEM: "Cabin option (as per quotation)",
	TRANSPORT_ITEM: "Transportation / crane (as per quotation)"}

ONES = "Zero One Two Three Four Five Six Seven Eight Nine Ten Eleven Twelve Thirteen Fourteen Fifteen Sixteen Seventeen Eighteen Nineteen".split()
TENS = "_ _ Twenty Thirty Forty Fifty Sixty Seventy Eighty Ninety".split()


def rate_card() -> dict:
	raw = frappe.db.get_single_value(RATE_CARD, "rate_card") if frappe.db.exists("DocType", RATE_CARD) else None
	if raw:
		rc = json.loads(raw)
		rc.setdefault("building", _bundled()["building"])  # card saved before the building section came (27-Oct)
		return rc
	return _bundled()


def _bundled() -> dict:
	with open(os.path.join(os.path.dirname(__file__), "data", "cabin_rate_card_v1.json")) as f:
		return json.load(f)


# ---------- price (same logic as the plan thread's reference) ----------

def _w99(n):
	return ONES[n] if n < 20 else TENS[n // 10] + ("-" + ONES[n % 10] if n % 10 else "")


def words(n: int) -> str:
	parts = []
	for div, name in ((10**7, "Crore"), (10**5, "Lakh"), (1000, "Thousand"), (100, "Hundred")):
		if n >= div:
			parts.append(f"{words(n // div) if div == 10**7 else _w99(n // div)} {name}")
			n %= div
	if n:
		parts.append(_w99(n))
	return " ".join(parts) or "Zero"


def inr(x) -> str:
	s = str(int(round(flt(x))))
	if len(s) > 3:
		head, tail = s[:-3], s[-3:]
		head = ",".join([head[max(0, i - 2):i] for i in range(len(head), 0, -2)][::-1])
		s = head + "," + tail
	return "₹" + s


def ftin(ft: float) -> str:
	f, i = int(ft), round((ft - int(ft)) * 12)
	return f"{f}'" + (f"-{i}\"" if i else "")


def price(req: dict, rc: dict | None = None) -> dict:
	"""req: type, length, width, height (ft), qty, options {key: qty}, km, crane, transport. Returns lines + total."""
	rc = rc or rate_card()
	if req.get("type") not in rc["types"]:
		frappe.throw(_("This cabin type is not in the rate card: send it to design, the price comes from the design BOM"))
	t = rc["types"][req["type"]]
	L, W = flt(req.get("length")), flt(req.get("width"))
	H, qty = flt(req.get("height")) or rc["standard_height_ft"], cint(req.get("qty")) or 1
	if L <= 0 or W <= 0:
		frappe.throw(_("Please give the length and width"))
	if L > 40 or W > 12:
		frappe.throw(_("Over 40 ft long or 12 ft wide in one module: send it to design, the price comes from the design BOM"))
	area = L * W
	if "fixed" in t:
		key = f"{int(L)}x{int(W)}"
		if key not in t["fixed"]:
			frappe.throw(_("{0} has a fixed price only for {1}: send other sizes to design").format(t["label"], ", ".join(t["fixed"])))
		unit, basis = t["fixed"][key], f"fixed price {key}"
	else:
		rate = next(r for upto, r in t["slabs"] if area <= upto)
		rate += max(0.0, H - rc["standard_height_ft"]) * rc["extra_height_per_ft_per_sqft"]
		unit = max(area * rate, t.get("min", 0))
		basis = f"{area:g} sq ft x {inr(rate)}"
	step = rc["round_to"]
	unit = math.ceil(unit / step) * step
	size = f"{ftin(L)} x {ftin(W)} x {ftin(H)}"
	lines = [{"kind": "cabin", "desc": f"{t['label']} {size} (L x W x H), as per specification below", "qty": qty, "unit": "No.", "rate": unit, "basis": basis}]
	for key, n in (req.get("options") or {}).items():
		if not n or key not in rc["options"]:
			continue
		o = rc["options"][key]
		per_cabin = flt(n) if o["unit"] in ("each", "running ft") else (area if n is True or flt(n) == 1 else flt(n))
		lines.append({"kind": "option", "key": key, "desc": o["label"], "qty": per_cabin * qty,
			"unit": {"each": "No.", "running ft": "Rft"}.get(o["unit"], "Sq ft"), "rate": o["rate"]})
	tr = rc["transport"]
	km = flt(req.get("km"))
	trip = tr["upto_20ft"] if L <= 20 else tr["upto_40ft"]
	trip += max(0.0, km - tr["free_km"]) * tr["extra_per_km_per_cabin"]
	if req.get("transport", True):
		lines.append({"kind": "transport", "desc": f"Transportation from our Talegaon plant to your site ({km:g} km)", "qty": qty, "unit": "Trip", "rate": round(trip)})
	if req.get("crane"):
		lines.append({"kind": "transport", "desc": "Hydra / crane for unloading and placing at site", "qty": qty, "unit": "Trip", "rate": tr["crane_per_trip"]})
	for ln in lines:
		ln["amount"] = ln["qty"] * ln["rate"]
	total = sum(ln["amount"] for ln in lines)
	return {"lines": lines, "total": total, "rate_card": rc["version"], "area": area, "label": t["label"], "size": size, "qty": qty}


def options(user: str | None = None) -> dict:
	"""For the app's quote screen: cabin types, options, limits."""
	rc = rate_card()
	return {"version": rc["version"], "types": [{"key": k, "label": v["label"], "sizes": list(v.get("fixed", {}))} for k, v in rc["types"].items()],
		"options": [{"key": k, "label": v["label"], "unit": v["unit"], "rate": v["rate"]} for k, v in rc["options"].items()],
		"design_types": rc.get("design_price_types", []), "height": rc["standard_height_ft"], "max_discount": max_discount(user) if user else 0,
		"terms": rc["terms"]}


# ---------- who may give a discount ----------

def max_discount(user: str) -> float:
	from sk_app.day_report import _team
	from sk_app.logins import profile_functions

	rc = rate_card()
	if user == "Administrator" or "Management" in profile_functions(user):
		return 100.0
	if _team(user):
		return flt(rc["discount"].get("sales_manager_pct"))
	return flt(rc["discount"].get("salesperson_pct"))


# ---------- the quotation ----------

def ensure_setup():
	"""Rate card, custom fields on Quotation, service items and the print format (on migrate)."""
	if not frappe.db.exists("DocType", "Quotation"):
		return
	if frappe.db.exists("DocType", RATE_CARD) and not frappe.db.get_single_value(RATE_CARD, "rate_card"):
		rc = _bundled()
		doc = frappe.get_single(RATE_CARD)
		doc.version, doc.rate_card, doc.note = rc["version"], json.dumps(rc, indent=1, ensure_ascii=False), rc.get("note")
		doc.flags.ignore_permissions = True
		doc.save()
	elif frappe.db.exists("DocType", RATE_CARD) and "building" not in json.loads(frappe.db.get_single_value(RATE_CARD, "rate_card")):
		doc = frappe.get_single(RATE_CARD)  # SK's PUF/EPS building calculator (27-Oct) joins the same card, so SK edits one place
		rc = json.loads(doc.rate_card)
		rc["building"] = _bundled()["building"]
		doc.rate_card = json.dumps(rc, indent=1, ensure_ascii=False)
		doc.flags.ignore_permissions = True
		doc.save()
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	create_custom_fields({"Quotation": [
		{"fieldname": "sk_quote_ref", "label": "SK Quote No.", "fieldtype": "Data", "insert_after": "party_name", "read_only": 1, "in_list_view": 1},
		{"fieldname": "sk_rev", "label": "Revision", "fieldtype": "Int", "insert_after": "sk_quote_ref", "read_only": 1},
		{"fieldname": "sk_rate_card", "label": "Rate card version", "fieldtype": "Data", "insert_after": "sk_rev", "read_only": 1},
		{"fieldname": "sk_discount_pct", "label": "Discount asked %", "fieldtype": "Percent", "insert_after": "sk_rate_card", "read_only": 1},
		{"fieldname": "sk_discount_status", "label": "Discount status", "fieldtype": "Select", "options": "\nRequested\nApproved\nRejected",
			"insert_after": "sk_discount_pct", "read_only": 1},
		{"fieldname": "sk_cabin_request", "label": "Cabin requirement", "fieldtype": "Code", "options": "JSON", "insert_after": "sk_discount_status",
			"read_only": 1, "hidden": 1},
	]}, update=True)
	group = frappe.db.get_value("Item Group", {"is_group": 0, "name": ["like", "%Service%"]}) or frappe.db.get_value("Item Group", {"is_group": 0})
	for code, name in SERVICE_ITEMS.items():
		if not frappe.db.exists("Item", code) and group:
			frappe.get_doc({"doctype": "Item", "item_code": code, "item_name": name, "item_group": group, "is_stock_item": 0,
				"include_item_in_manufacturing": 0, "stock_uom": "Nos", "description": name}).insert(ignore_permissions=True)
	if not frappe.db.exists("Print Format", PRINT_FORMAT):
		frappe.get_doc({"doctype": "Print Format", "name": PRINT_FORMAT, "doc_type": "Quotation", "module": "SK App", "custom_format": 1,
			"print_format_type": "Jinja", "standard": "No", "html": "{{ sk_cabin_quote_html(doc) }}", "margin_top": 0, "margin_left": 0,
			"margin_right": 0}).insert(ignore_permissions=True)
	from frappe.custom.doctype.property_setter.property_setter import make_property_setter

	make_property_setter("Quotation", None, "default_print_format", PRINT_FORMAT, "Data", validate_fields_for_doctype=False)
	from sk_app import building_quote

	building_quote.ensure_setup()


def _cabin_item(rc: dict, typ: str, L: float, W: float) -> str:
	"""The matching Prod-00xx size variant when ERPNext has one, else the template-free service item."""
	for prefix in rc["types"][typ].get("items", []):
		hit = frappe.db.get_value("Item", {"name": ["like", f"{prefix}-{L:g}ft x {W:g}ft%"], "has_variants": 0, "disabled": 0})
		if hit:
			return hit
	return CABIN_ITEM


def _cust_code(customer: str) -> str:
	name = frappe.db.get_value("Customer", customer, "customer_name") or customer
	letters = "".join(w[0] for w in name.replace("-", " ").split() if w[:1].isalpha()).upper()
	return (letters or name[:3].upper())[:3].ljust(3, "X")


def _fy() -> str:
	d = getdate(nowdate())
	y = d.year if d.month >= 4 else d.year - 1
	return f"{str(y)[2:]}-{str(y + 1)[2:]}"


def _new_ref(customer: str, kind: str = "CAB") -> str:
	base = f"SK/{kind}/{_fy()}/{_cust_code(customer)}-"
	n = frappe.db.count("Quotation", {"sk_quote_ref": ["like", base + "%"]}) + 1
	ref = f"{base}{n:03d}"
	while frappe.db.exists("Quotation", {"sk_quote_ref": ref}):
		n += 1
		ref = f"{base}{n:03d}"
	return ref


def open_quotes(customer: str) -> list[dict]:
	"""Open cabin quotes of this customer (offer to revise instead of making a new one)."""
	return frappe.get_all("Quotation", filters={"quotation_to": "Customer", "party_name": customer, "docstatus": ["<", 2],
		"status": ["not in", ["Ordered", "Lost", "Expired"]], "sk_quote_ref": ["is", "set"]},
		fields=["name", "sk_quote_ref", "sk_rev", "grand_total", "net_total", "transaction_date", "docstatus"], order_by="creation desc")


def _customer_for(user: str, deal=None, lead=None, customer=None) -> tuple[str, str | None]:
	from sk_app import crm, erp_flow

	if lead and not deal:
		crm._check("CRM Lead", lead, "write")
		seg = frappe.db.get_value("CRM Lead", lead, "sk_segment") if frappe.get_meta("CRM Lead").has_field("sk_segment") else None
		deal, reason = crm._to_deal(user, lead, seg)
		if not deal:
			frappe.throw(reason)
	if deal:
		return erp_flow.make_customer(user, deal)["name"], deal
	if customer and frappe.db.exists("Customer", customer):
		return customer, None
	frappe.throw(_("Open the lead or deal to make its quotation"))


def make(user: str, req: dict, deal=None, lead=None, customer=None, discount_pct=0, revise=None, contact=None) -> dict:
	"""Make (or revise) the cabin quotation. The price comes from the rate card only."""
	rc = rate_card()
	p = price(req, rc)
	customer, deal = _customer_for(user, deal, lead, customer)
	disc = max(0.0, flt(discount_pct))
	allowed = max_discount(user)
	old = frappe.get_doc("Quotation", revise) if revise else None
	if old and old.party_name != customer:
		frappe.throw(_("That quotation is for another customer"))
	rows = []
	main = _cabin_item(rc, req["type"], flt(req["length"]), flt(req["width"]))
	for ln in p["lines"]:
		code = main if ln["kind"] == "cabin" else OPTION_ITEM if ln["kind"] == "option" else TRANSPORT_ITEM
		rows.append({"item_code": code, "qty": ln["qty"], "rate": ln["rate"], "description": ln["desc"],
			"uom": "Nos" if ln["unit"] in ("No.", "Trip") else None})
	for r in rows:
		if not r["uom"]:
			r.pop("uom")
	if old and old.docstatus == 0:
		doc = old
		doc.set("items", [])
		doc.sk_rev = cint(old.sk_rev) + 1
	else:
		doc = frappe.new_doc("Quotation")
		doc.update({"quotation_to": "Customer", "party_name": customer})
		doc.sk_quote_ref = old.sk_quote_ref if old else _new_ref(customer)
		doc.sk_rev = cint(old.sk_rev) + 1 if old else 0
	for r in rows:
		doc.append("items", r)
	doc.transaction_date = nowdate()
	doc.valid_till = add_days(nowdate(), cint(rc["terms"].get("validity_days")) or 15)
	doc.ignore_pricing_rule = 1
	doc.sk_rate_card = rc["version"]
	doc.sk_cabin_request = json.dumps(req)
	doc.sk_discount_pct = disc
	doc.terms = _terms(rc)
	if deal and doc.meta.has_field("crm_deal"):
		doc.crm_deal = deal
	if contact and doc.meta.has_field("contact_person") and frappe.db.exists("Contact", contact):
		doc.contact_person = contact
	need_ok = disc > allowed
	doc.additional_discount_percentage = 0 if need_ok else disc
	doc.apply_discount_on = "Net Total"
	doc.sk_discount_status = "Requested" if need_ok else ("Approved" if disc else "")
	doc.flags.ignore_permissions = True
	doc.save()
	if need_ok:
		_ask_discount(user, doc, disc)
	if deal:
		_deal_to_quotation(deal)
	return {"name": doc.name, "ref": doc.sk_quote_ref, "rev": doc.sk_rev, "net_total": doc.net_total, "grand_total": doc.grand_total,
		"discount_waiting": need_ok, "pdf": _pdf(doc.name), "rate_card": rc["version"]}


def _terms(rc: dict) -> str:
	t = rc["terms"]
	return "<br>".join([f"Prices are in INR and exclude GST. GST @ {t['gst_pct']}% is charged extra.", f"Payment: {t['payment']}.",
		f"Delivery: {t['delivery']}.", f"Validity: {t['validity_days']} days from the date of this quotation.",
		f"Price as per SK standard rate card {rc['version']}."])


def _pdf(name: str) -> str:
	return f"/api/method/frappe.utils.print_format.download_pdf?doctype=Quotation&name={name}&format={PRINT_FORMAT.replace(' ', '%20')}"


def _deal_to_quotation(deal: str):
	"""Lead status flow (SK 27-Oct): the deal moves to Quotation."""
	if not frappe.db.exists("DocType", "CRM Deal Status"):
		return
	status = next((s for s in frappe.get_all("CRM Deal Status", pluck="name") if "quot" in s.lower() or "proposal" in s.lower()), None)
	if status:
		frappe.db.set_value("CRM Deal", deal, "status", status)


def _bosses() -> list[str]:
	from sk_app.logins import profile_functions

	return [u for u in frappe.get_all("SK App User", filters={"enabled": 1}, pluck="user") if "Management" in profile_functions(u)]


def _ask_discount(user: str, doc, disc: float | None, why: str | None = None):
	what = f"Discount {disc:g}% asked on {doc.sk_quote_ref} ({doc.customer_name}, {inr(doc.net_total)} before discount)" if disc is not None \
		else f"Approval needed on {doc.sk_quote_ref} ({doc.customer_name}, {inr(doc.net_total)}): {why}"
	for boss in _bosses():
		frappe.get_doc({"doctype": "ToDo", "allocated_to": boss, "assigned_by": user, "reference_type": "Quotation", "reference_name": doc.name,
			"priority": "High", "date": nowdate(), "description": f"{what}. Approve or reject in the app: Quote discounts."}).insert(ignore_permissions=True)


def discount_requests(user: str) -> list[dict]:
	_boss_only(user)
	rows = frappe.get_all("Quotation", filters={"sk_discount_status": "Requested", "docstatus": 0},
		fields=["name", "sk_quote_ref", "customer_name", "net_total", "sk_discount_pct", "owner", "transaction_date"], order_by="creation desc")
	for r in rows:  # building quotes: why SK must look (margin / discount per sq ft)
		r["why"] = frappe.db.get_value("ToDo", {"reference_type": "Quotation", "reference_name": r.name, "status": "Open"}, "description") or ""
	return rows


def decide_discount(user: str, quotation: str, ok: int) -> dict:
	_boss_only(user)
	doc = frappe.get_doc("Quotation", quotation)
	if doc.sk_discount_status != "Requested" or doc.docstatus != 0:
		frappe.throw(_("No discount is waiting on this quotation"))
	if cint(ok):
		if flt(doc.sk_discount_pct):
			doc.additional_discount_percentage = flt(doc.sk_discount_pct)
			doc.apply_discount_on = "Net Total"
		doc.sk_discount_status = "Approved"
	else:
		doc.sk_discount_status = "Rejected"
	doc.flags.ignore_permissions = True
	doc.save()
	for td in frappe.get_all("ToDo", filters={"reference_type": "Quotation", "reference_name": quotation, "status": "Open"}, pluck="name"):
		frappe.db.set_value("ToDo", td, "status", "Closed")
	return {"name": doc.name, "status": doc.sk_discount_status, "grand_total": doc.grand_total}


def _boss_only(user: str):
	from sk_app.logins import profile_functions

	if user != "Administrator" and "Management" not in profile_functions(user) and "System Manager" not in frappe.get_roles(user):
		frappe.throw(_("Only SK approves a bigger discount"), frappe.PermissionError)


# ---------- the print (SK's quote template) ----------

SPEC = [
	"Structure: GI / MS base frame on 150 mm legs; floor / door sill 250 mm above ground; no steps.",
	"Walls: outside 0.9 mm MS corrugated (trapezoidal, vertical rib) sheet, white with blue bottom band; inside MDF / board finish on GI sections.",
	"Roof: two-side slope, ridge 150 mm above eaves, corrugated sheet; clear internal height 2340 mm.",
	"Floor: 18 mm cement fibre board on base frame.",
	"Door: MS frame door clad in the same corrugated sheet, L-drop (lever) handle with lock and SS aldrop with padlock hasp.",
	"Windows: aluminium sliding windows with grill and mesh; 150 mm sajja above every door and window.",
	"Electrical: concealed wiring with MCB, LED lights, fan and 5/15 A sockets as per drawing; AC (if any) high on the back wall.",
	"Painting: epoxy primer + PU / epoxy finish; colours as RAL numbers to be confirmed by you.",
]
SK_SCOPE = [
	"Customer drawing (GA) for your approval before manufacturing.",
	"Manufacturing at our Talegaon plant, painting and pre-dispatch inspection.",
	"Transportation to your site as per the price schedule.",
	"Placing the cabin on your prepared base and electrical handover.",
]
CUST_SCOPE = [
	"Level, compacted ground or plinth / concrete blocks at the location, ready before delivery.",
	"Clear access for the truck and crane up to the placing point.",
	"Incoming power supply up to the cabin MCB; water and drain lines (for toilets).",
	"Unloading crane / hydra, unless included in the price schedule.",
	"Any local permissions, union / Mathadi charges.",
]
EXCL = [
	"Air conditioner units, furniture and other items not listed in the price schedule.",
	"Civil work, foundation, plinth, earthing pit and external cabling.",
	"Any change after drawing approval will be charged extra.",
]
CSS = """
.skq{font-family:'Liberation Sans',Arial,sans-serif;font-size:9.6pt;color:#222}
.skq .hdr{width:100%}
.skq .band{background:#C8233C;color:#fff;font-weight:bold;text-align:center;padding:5px;font-size:10.5pt}
.skq .addr td{border:0;vertical-align:top;padding:2px}
.skq .k{font-style:italic;color:#777;width:95px;display:inline-block}
.skq .subj{color:#1D4F86;font-weight:bold;font-size:11pt;margin:10px 0 4px}
.skq .bar{background:#2A6EB4;color:#fff;font-weight:bold;padding:4px 6px;margin:12px 0 4px;text-transform:uppercase}
.skq table.p{border-collapse:collapse;width:100%}
.skq table.p th{background:#1D4F86;color:#fff;padding:4px}
.skq table.p td{border:1px solid #BFBFBF;padding:4px}
.skq .c{text-align:center}.skq .r{text-align:right}.skq .b{font-weight:bold}
.skq tr.tot td{background:#FFF2CC;font-weight:bold}.skq tr.gst td{background:#F2F2F2;font-weight:bold}
.skq .words{color:#1D4F86;font-weight:bold;font-style:italic;margin:5px 0}
.skq ol{margin:2px 0 2px 22px;padding:0}.skq li{margin:2px 0}
"""


def _esc(x) -> str:
	return frappe.utils.escape_html(str(x or ""))


def quote_html(doc) -> str:
	"""Jinja print format body: {{ sk_cabin_quote_html(doc) }}."""
	req = json.loads(doc.get("sk_cabin_request") or "null") or {}
	if req.get("kind") == "building":
		from sk_app import building_quote

		return building_quote.quote_html(doc, req)
	cabin = bool(req)
	ref = doc.get("sk_quote_ref") or doc.name
	rev = f"R{cint(doc.get('sk_rev'))}"
	date = formatdate(doc.transaction_date, "dd-MMM-yyyy")
	contact = doc.get("contact_display") or ""
	cust = doc.customer_name or doc.party_name
	city = ""
	if doc.get("customer_address"):
		city = frappe.db.get_value("Address", doc.customer_address, "city") or ""
	to = (f"{_esc(contact)} Sir / Madam<br>" if contact else "") + f"<b>{_esc(cust)}</b>" + (f"<br>{_esc(city)}" if city else "")
	rows = "".join(
		f"<tr><td class=c>{i}</td><td>{d.description or d.item_name}</td><td class=c>{flt(d.qty):g}</td><td class=c>{_esc(d.uom)}</td>"
		f"<td class=r>{inr(d.rate)}</td><td class='r b'>{inr(d.amount)}</td></tr>" for i, d in enumerate(doc.items, 1))
	disc = f"<tr><td colspan=5 class=r>Discount{f' {flt(doc.additional_discount_percentage):g}%' if doc.additional_discount_percentage else ''}</td><td class=r>- {inr(doc.discount_amount)}</td></tr>" if flt(doc.discount_amount) else ""
	li = lambda xs: "<ol>" + "".join(f"<li>{x}</li>" for x in xs) + "</ol>"  # noqa: E731
	if cabin:
		t = frappe._dict(req)
		subject = f"Quotation for supply of {cint(t.qty) or 1} no. {doc.items[0].description.split(' (L x W x H)')[0] if doc.items else 'cabin'}"
		intro = "Thank you for your enquiry. As requested, please find our offer for the portable cabin as per our standard specification."
	else:
		subject = f"Quotation for {_esc(doc.items[0].item_name) if doc.items else ''}"
		intro = "Thank you for your enquiry. Please find our offer below."
	sections = [f"<div class=bar>1. Price schedule (INR)</div><table class=p><tr><th>Sr.</th><th>Description</th><th>Qty</th><th>Unit</th><th>Unit price</th><th>Amount</th></tr>{rows}{disc}"
		f"<tr class=tot><td colspan=5 class=r>Total (excl. GST)</td><td class=r>{inr(doc.net_total)}</td></tr>"
		f"<tr class=gst><td colspan=5 class=r>GST @ 18%</td><td class=r>Extra</td></tr></table>"
		f"<div class=words>Amount in words (excl. GST): Rupees {words(int(round(flt(doc.net_total))))} Only</div>"]
	n = 2
	if cabin:
		short = _esc(cust.split(" ")[0] if cust else "Customer")
		for title, xs in (("Technical specification", SPEC), ("Scope of work – SK Ind Tech", SK_SCOPE), (f"{_esc(cust)} scope" if cust else f"{short} scope", CUST_SCOPE), ("Exclusions", EXCL)):
			sections.append(f"<div class=bar>{n}. {title}</div>{li(xs)}")
			n += 1
	if doc.terms:
		sections.append(f"<div class=bar>{n}. Commercial terms</div><div>{doc.terms}</div>")
	owner = frappe.db.get_value("User", doc.owner, "full_name") or doc.owner
	header = frappe.utils.get_url("/assets/sk_app/images/sk-quote-header.png")
	return f"""<style>{CSS}</style><div class=skq><img class=hdr src="{header}">
<div class=band>QUOTATION &nbsp; | &nbsp; Ref: {_esc(ref)} &nbsp; | &nbsp; Date: {date} &nbsp; | &nbsp; Rev: {rev}</div>
<table class=addr style="width:100%;margin:12px 0 8px"><tr><td>To,<br>{to}</td><td style="width:45%"><span class=k>Quotation No.</span><b>{_esc(ref)}</b><br>
<span class=k>Date</span><b>{date}</b><br><span class=k>Revision</span><b>{rev}</b><br><span class=k>Valid till</span><b>{formatdate(doc.valid_till, "dd-MMM-yyyy") if doc.valid_till else ""}</b></td></tr></table>
<div class=subj>Subject: {_esc(subject)}</div><p>Dear Sir / Madam,<br>{intro}</p>
{"".join(sections)}
<p>We hope our offer is in line with your requirement and look forward to your valued order.</p>
<p><b>For SK Ind Tech Solutions Pvt Ltd</b><br><br><br><b>Authorised Signatory</b><br>{_esc(owner)}<br>
Phone: +91 97672 13521 | E-mail: skind.sales@gmail.com | GSTIN 27ABBCS4285J1ZZ</p></div>"""


def sk_cabin_quote_html(doc) -> str:
	"""Jinja method for the print format (hooks: jinja methods)."""
	return quote_html(doc)
