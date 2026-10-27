"""PUF / EPS building quotation (labour camps, site offices, G+0 to G+2), from SK's "SK Quotation Calculator" Excel
(SK 27-Oct-2026: "for reference", then "Yes, add Building quote").

Same method as the Excel, so the app and the sheet give the same price:
- Area (sq ft) = W x L x 10.76 x floors + canopy / walkway (L x width x sides x floors x 10.76) + staircase (length x width x nos x 10.76).
- Structure rate = rate card (panel x floors) + zone adder + volume slab (on the quote's total area) - transport deduction
  (transport in client scope) - special discount; electrical Rs / sq ft added when in SK scope. SK (Management) alone may
  override the rate for a negotiated price.
- Internal cost (BOQ estimate) gives the margin; below the minimum margin or a special discount above the limit, SK approves.
- The rates live in the "building" part of the SK Cabin Rate Card, which only SK / System Manager edits.
"""

import json
import math

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, formatdate, nowdate

from sk_app import cabin_quote as cq

FLOORS = ["G+0", "G+1", "G+2"]
BUILDING_ITEM, ADDON_ITEM = "SK-BUILDING", "SK-BUILDING-ADDON"
ITEMS = {BUILDING_ITEM: "PUF / EPS prefab building (as per quotation)", ADDON_ITEM: "Building add-on item (as per quotation)"}


def _xround(x: float) -> int:
	"""Excel ROUND(x, 0): halves go up (Python's round() goes to even)."""
	return int(math.floor(x + 0.5))


def card(rc: dict | None = None) -> dict:
	return (rc or cq.rate_card())["building"]


def _block(blk: dict, b: dict) -> dict | None:
	L, W = flt(blk.get("length")), flt(blk.get("width"))
	if L <= 0 or W <= 0:
		return None
	f = FLOORS.index(blk.get("floors")) + 1 if blk.get("floors") in FLOORS else max(1, min(3, cint(blk.get("floors")) or 1))
	nos = max(1, cint(blk.get("nos")))
	k = b["sqm_to_sqft"]
	cw, cs = flt(blk.get("canopy_width")), cint(blk.get("canopy_sides"))
	sw, sl, sn = flt(blk.get("stair_width")), flt(blk.get("stair_length")), cint(blk.get("stairs"))
	room = W * L * k * f
	canopy = L * cw * cs * f * k
	stair = sl * sw * sn * k
	per = room + canopy + stair
	rd, rw = flt(blk.get("room_depth")) * 0.3048, flt(blk.get("room_width")) * 0.3048
	rows = max(1, _xround(W / rd)) if rd > 0 else 1
	along = max(1, _xround(L / rw)) if rw > 0 else 0
	per_floor = cint(blk.get("rooms_per_floor")) or rows * along
	rooms = per_floor * f * nos
	people = rooms * cint(blk.get("people"))
	return {"name": blk.get("name") or "Building", "code": blk.get("code") or "", "drawing": blk.get("drawing") or "",
		"L": L, "W": W, "H": flt(blk.get("height")) or 3 * f, "floors": f, "floors_label": FLOORS[f - 1], "nos": nos,
		"canopy_width": cw, "canopy_sides": cs, "stair_width": sw, "stair_length": sl, "stairs": sn,
		"room_area": room, "canopy_area": canopy, "stair_area": stair, "area_per": per, "area": per * nos,
		"room_size": f"{flt(blk.get('room_depth')):g}ft x {flt(blk.get('room_width')):g}ft" if rd and rw else "",
		"rows": rows, "along": along, "rooms_per_floor": per_floor, "rooms": rooms, "people_per_room": cint(blk.get("people")),
		"people": people, "beds": math.ceil(people / 2), "override": flt(blk.get("rate_override"))}


def _cost(x: dict, b: dict, panel: str, elec: bool) -> float:
	"""Internal BOQ cost of one structure (Calc rows 44-82)."""
	c = b["cost"]
	L, W, H, f = x["L"], x["W"], x["H"], x["floors"]
	foot = L * W
	built = foot * f
	walk = L * x["canopy_width"] * x["canopy_sides"] * f
	wall = 2 * (L + W) * H * (1 - b["opening_pct"])
	part = ((x["along"] - 1) * W + (x["rows"] - 1) * L) * H if x["along"] > 0 else 0
	roof = foot * (1 + b["roof_proj"])
	board = foot * max(f - 1, 0)
	chq = L * x["canopy_width"] * x["canopy_sides"] * max(f - 1, 0)
	canopy = L * x["canopy_width"] * x["canopy_sides"]
	steel = built * b["steel_kg_m2"] + walk * b["steel_kg_walk"]
	doors = x["rooms_per_floor"] * f
	eps = panel == "EPS"
	return (steel * c["steel_kg"] + wall * c["wall_eps" if eps else "wall_puf"] + part * c["part_eps" if eps else "part_puf"]
		+ roof * c["roof_eps" if eps else "roof_puf"] + board * c["board"] + chq * c["chq"] + canopy * c["canopy"] + doors * c["door"]
		+ doors * b["windows_per_room"] * c["window"] + (x["stairs"] * c["stair"] if f > 1 else 0) + (doors * c["elec_room"] if elec else 0)
		+ foot * c["flash"] + built * c["fasten"] + x["area_per"] * c["erect_sqft"])


def price(req: dict, rc: dict | None = None, may_override: bool = False) -> dict:
	"""req: panel, electrical, transport, zone, special_discount (Rs/sq ft), blocks [...], addons {item: qty}."""
	rc = rc or cq.rate_card()
	b = card(rc)
	panel = req.get("panel") if req.get("panel") in b["base_rate"] else "PUF"
	elec, transport = bool(req.get("electrical", True)), bool(req.get("transport", True))
	zone = req.get("zone") if req.get("zone") in b["zones"] else next(iter(b["zones"]))
	disc = max(0.0, flt(req.get("special_discount")))
	blocks = [x for x in (_block(blk, b) for blk in (req.get("blocks") or [])[:3]) if x]
	if not blocks:
		frappe.throw(_("Please give the length and width (m) of at least one building"))
	total_area = sum(x["area"] for x in blocks)
	slab = 0
	for start, adj in b["volume_slabs"]:
		if total_area >= start:
			slab = adj
	direct = 0.0
	for x in blocks:
		base = b["base_rate"][panel][x["floors"] - 1]
		x["base"], x["zone_add"], x["slab"] = base, b["zones"][zone]["adder"], slab
		x["transport_ded"] = 0 if transport else -b["transport_deduction"]
		x["discount"] = -disc
		x["computed_rate"] = base + x["zone_add"] + slab + x["transport_ded"] - disc
		x["rate"] = x["override"] if (may_override and x["override"] > 0) else x["computed_rate"]
		x["elec_rate"] = b["elec_rate"] if elec else 0
		x["total_rate"] = x["rate"] + x["elec_rate"]
		x["value"] = x["total_rate"] * x["area"]
		direct += _cost(x, b, panel, elec) * x["nos"]
	addons = []
	for item, qty in (req.get("addons") or {}).items():
		if item in b["addons"] and flt(qty) > 0:
			a = b["addons"][item]
			addons.append({"item": item, "size": a["size"], "unit": a["unit"], "qty": flt(qty), "rate": a["rate"],
				"amount": flt(qty) * a["rate"], "cost": flt(qty) * a["cost"]})
	structure = sum(x["value"] for x in blocks)
	addon_value = sum(a["amount"] for a in addons)
	total = structure + addon_value
	trips = math.ceil(total_area / b["sqft_per_trip"]) if transport else 0
	tcost = trips * b["zones"][zone]["truck"]
	all_direct = direct + tcost + b["cost"]["design"] + sum(a["cost"] for a in addons)
	cost = all_direct * (1 + b["overheads"])
	margin = (total - cost) / total if total else 0
	per_sqft = (direct + tcost + b["cost"]["design"]) * (1 + b["overheads"]) / total_area
	why = []
	if margin < b["min_margin"]:
		why.append(_("margin {0}% is below the minimum {1}%").format(round(margin * 100, 1), round(b["min_margin"] * 100)))
	if disc > b["max_disc_sqft"]:
		why.append(_("special discount Rs {0}/sq ft is above Rs {1}/sq ft").format(f"{disc:g}", b["max_disc_sqft"]))
	return {"kind": "building", "rate_card": rc["version"] + " / " + b["version"], "panel": panel, "electrical": elec, "transport": transport,
		"zone": zone, "special_discount": disc, "blocks": blocks, "addons": addons, "total_area": total_area, "structure": structure,
		"addon_value": addon_value, "total": total, "gst_pct": b["gst"] * 100, "gst": total * b["gst"], "grand_total": total * (1 + b["gst"]),
		"avg_rate": structure / total_area, "rooms": sum(x["rooms"] for x in blocks), "people": sum(x["people"] for x in blocks),
		"beds": sum(x["beds"] for x in blocks), "trips": trips, "cost": cost, "margin": margin,
		"min_rate": per_sqft / (1 - b["target_margin"]), "approval": why}


def public(p: dict, user: str) -> dict:
	"""What the salesperson sees: cost and margin only for the sales manager and SK."""
	if cq.max_discount(user) < 5:
		p = {k: v for k, v in p.items() if k not in ("cost", "margin", "min_rate")}
	return p


def options(user: str) -> dict:
	rc = cq.rate_card()
	b = card(rc)
	return {"version": b["version"], "panels": list(b["base_rate"]), "floors": FLOORS, "zones": list(b["zones"]),
		"addons": [{"item": k, **v} for k, v in b["addons"].items()], "delivery": b["delivery"], "payment": b["payment"],
		"max_disc_sqft": b["max_disc_sqft"], "may_override": cq.max_discount(user) >= 100}


def ensure_setup():
	if not frappe.db.exists("DocType", "Quotation"):
		return
	uom = "Square Foot" if frappe.db.exists("UOM", "Square Foot") else "Nos"
	group = frappe.db.get_value("Item Group", {"is_group": 0, "name": ["like", "%Service%"]}) or frappe.db.get_value("Item Group", {"is_group": 0})
	for code, name in ITEMS.items():
		if not frappe.db.exists("Item", code) and group:
			frappe.get_doc({"doctype": "Item", "item_code": code, "item_name": name, "item_group": group, "is_stock_item": 0,
				"include_item_in_manufacturing": 0, "stock_uom": uom if code == BUILDING_ITEM else "Nos", "description": name}).insert(ignore_permissions=True)


def make(user: str, req: dict, deal=None, lead=None, customer=None, revise=None, contact=None) -> dict:
	rc = cq.rate_card()
	b = card(rc)
	p = price(req, rc, may_override=cq.max_discount(user) >= 100)
	customer, deal = cq._customer_for(user, deal, lead, customer)
	old = frappe.get_doc("Quotation", revise) if revise else None
	if old and old.party_name != customer:
		frappe.throw(_("That quotation is for another customer"))
	if old and old.docstatus == 0:
		doc = old
		doc.set("items", [])
		doc.sk_rev = cint(old.sk_rev) + 1
	else:
		doc = frappe.new_doc("Quotation")
		doc.update({"quotation_to": "Customer", "party_name": customer})
		doc.sk_quote_ref = old.sk_quote_ref if old else cq._new_ref(customer, "BLD")
		doc.sk_rev = cint(old.sk_rev) + 1 if old else 0
	for x in p["blocks"]:
		doc.append("items", {"item_code": BUILDING_ITEM, "qty": round(x["area"], 2), "rate": x["total_rate"],
			"description": f"{x['name']}{' (' + x['code'] + ')' if x['code'] else ''}, {x['floors_label']}, {x['L']:g} x {x['W']:g} x {x['H']:g} m, "
			f"{x['nos']} no(s), {p['panel']} panel"})
	for a in p["addons"]:
		doc.append("items", {"item_code": ADDON_ITEM, "qty": a["qty"], "rate": a["rate"], "uom": "Nos", "description": f"{a['item']} ({a['size']})"})
	doc.transaction_date = nowdate()
	doc.valid_till = add_days(nowdate(), cint(b["validity_days"]) or 10)
	doc.ignore_pricing_rule = 1
	doc.sk_rate_card = p["rate_card"]
	keep = {k: v for k, v in p.items() if k not in ("cost", "margin", "min_rate")}
	keep.update({"delivery": req.get("delivery") or b["delivery"][0], "payment": req.get("payment") or b["payment"][0], "req": req})
	doc.sk_cabin_request = json.dumps(keep)
	doc.sk_discount_pct = 0
	doc.additional_discount_percentage = 0
	doc.terms = ""
	if deal and doc.meta.has_field("crm_deal"):
		doc.crm_deal = deal
	if contact and doc.meta.has_field("contact_person") and frappe.db.exists("Contact", contact):
		doc.contact_person = contact
	need_ok = bool(p["approval"])
	doc.sk_discount_status = "Requested" if need_ok else ""
	doc.flags.ignore_permissions = True
	doc.save()
	if need_ok:
		cq._ask_discount(user, doc, None, "; ".join(p["approval"]))
	if deal:
		cq._deal_to_quotation(deal)
	return {"name": doc.name, "ref": doc.sk_quote_ref, "rev": doc.sk_rev, "net_total": doc.net_total, "grand_total": doc.grand_total,
		"discount_waiting": need_ok, "approval": p["approval"], "pdf": cq._pdf(doc.name), "rate_card": p["rate_card"]}


# ---------- print (SK's quote template, the Excel's sections) ----------

def _m(x) -> str:
	return f"{flt(x):,.2f}".rstrip("0").rstrip(".")


def quote_html(doc, d: dict) -> str:
	b = card()
	esc, inr = cq._esc, cq.inr
	ref, rev = doc.get("sk_quote_ref") or doc.name, f"R{cint(doc.get('sk_rev')):02d}"
	date = formatdate(doc.transaction_date, "dd-MMM-yyyy")
	cust = doc.customer_name or doc.party_name
	contact = doc.get("contact_display") or ""
	to = (f"{esc(contact)} Sir / Madam<br>" if contact else "") + f"<b>{esc(cust)}</b>"
	if doc.get("customer_address"):
		to += f"<br>{esc(frappe.db.get_value('Address', doc.customer_address, 'city') or '')}"
	waiting = {"Requested": "WAITING FOR SK APPROVAL: DO NOT SEND", "Rejected": "NOT APPROVED BY SK: DO NOT SEND"}.get(doc.get("sk_discount_status"))
	tr = " + Transport" if d["transport"] else ""
	rows, i = "", 0
	for x in d["blocks"]:
		i += 1
		rows += (f"<tr><td class=c>{i}</td><td>{esc(x['name'])}{'<br>(' + esc(x['code']) + ')' if x['code'] else ''}<br>{x['floors_label']}</td>"
			f"<td class=c>{x['L']:.2f} x {x['W']:.2f} x {x['H']:.1f} m</td><td class=r>{_m(round(x['area_per'], 2))}</td><td class=c>{x['nos']}</td>"
			f"<td class=r>{_m(x['rate'])}</td><td class=r>{_m(x['elec_rate']) if x['elec_rate'] else 'Excluded'}</td><td class=r>{_m(x['total_rate'])}</td>"
			f"<td class='r b'>{inr(x['value'])}</td></tr>")
	for a in d["addons"]:
		i += 1
		rows += (f"<tr><td class=c>{i}</td><td>{esc(a['item'])}</td><td class=c>{esc(a['size'])}</td><td></td><td class=c>{_m(a['qty'])}</td>"
			f"<td></td><td></td><td class=r>{_m(a['rate'])}</td><td class='r b'>{inr(a['amount'])}</td></tr>")
	price = (f"<table class=p><tr><th>Sr.</th><th>Description</th><th>Structure size (L x W x H)</th><th>Sq ft / structure</th><th>Qty (Nos)</th>"
		f"<th>Structure rate ₹/sq ft<br>(Supply + Erection{tr} + Plinth Dwg)</th><th>Electrical ₹/sq ft</th><th>Total rate ₹/sq ft</th><th>Amount ₹</th></tr>{rows}"
		f"<tr class=tot><td colspan=3>Total built-up area (sq ft)</td><td class=r>{_m(round(d['total_area'], 2))}</td><td colspan=4 class=r>Total (before GST)</td><td class=r>{inr(doc.net_total)}</td></tr>"
		f"<tr class=gst><td colspan=3>Capacity: {d['rooms']} rooms / {d['people']} people</td><td colspan=5 class=r>GST @ {d['gst_pct']:g}%</td><td class=r>{inr(doc.net_total * d['gst_pct'] / 100)}</td></tr>"
		f"<tr class=tot><td colspan=8 class=r>Grand total (incl. GST)</td><td class=r>{inr(doc.net_total * (1 + d['gst_pct'] / 100))}</td></tr></table>"
		f"<div class=words>Amount in words (excl. GST): Rupees {cq.words(int(round(flt(doc.net_total))))} Only</div>")
	sk_scope = "Supply + Erection" + (" + Electrical" if d["electrical"] else "") + tr + " + Plinth Drawing"
	cl_scope = ("Construction of plinth at site, " + ("" if d["transport"] else "Transportation, ") + ("" if d["electrical"] else "Electrical work, ")
		+ "Supply of electricity at workspace, furniture, Unloading of material at site, safe and secured storage place for material, Erection team accommodation.")
	terms = (f"<p><b>● What will be in our scope</b><br>{sk_scope}</p><p><b>● What will be in your scope</b><br>{cl_scope}</p>"
		f"<p><b>● Delivery time</b><br>{esc(d.get('delivery'))}</p><p><b>● Payment</b><br>{esc(d.get('payment'))}</p>"
		f"<p><b>● Taxes</b><br>GST @ {d['gst_pct']:g}% extra on total cost. TCS is applicable on sale of goods as per section 206 C (1H) from 01-10-2020.</p>"
		f"<p><b>● Other terms</b><br>{esc(b['other_terms'])}<br>Offer validity: {b['validity_days']} days from date of quotation.</p>")
	area = ""
	for x in d["blocks"]:
		area += (f"<tr><td>{esc(x['name'])}: room area</td><td class=r>{x['W']:g}</td><td class=r>{x['L']:g}</td><td class=c>{x['floors_label']}</td><td></td><td class=c>x {x['floors']}</td><td class=r>{_m(round(x['room_area'], 2))}</td></tr>"
			f"<tr><td>Canopy / walkway area</td><td class=r>{x['canopy_width']:g}</td><td class=r>{x['L']:g}</td><td class=c>{x['floors_label']}</td><td class=c>{x['canopy_sides']}</td><td class=c>x {x['floors'] * x['canopy_sides']}</td><td class=r>{_m(round(x['canopy_area'], 2))}</td></tr>"
			f"<tr><td>Staircase area</td><td class=r>{x['stair_width']:g}</td><td class=r>{x['stair_length']:g}</td><td></td><td class=c>{x['stairs']}</td><td class=c>x {x['stairs']}</td><td class=r>{_m(round(x['stair_area'], 2))}</td></tr>"
			f"<tr class=gst><td colspan=6>Total area per structure: {esc(x['name'])}</td><td class=r>{_m(round(x['area_per'], 2))}</td></tr>")
	area = (f"<table class=p><tr><th>Block / item</th><th>Width (m)</th><th>Length (m)</th><th>Floors</th><th>Sides / Nos</th><th>Multiplier</th><th>Area (sq ft)</th></tr>{area}</table>"
		f"<p style='color:#777'>Area method: room area = W x L x 10.76 x floors; canopy / walkway = L x width x sides x floors x 10.76; staircase = length x width x nos x 10.76.</p>")
	cap = "".join(f"<tr><td>{esc(x['name'])}</td><td class=c>{x['room_size']}</td><td class=c>{x['rooms']}</td><td class=c>{x['people_per_room']}</td>"
		f"<td class=c>{x['people']}</td><td class=c>{x['beds']}</td></tr>" for x in d["blocks"])
	cap = f"<table class=p><tr><th>Block</th><th>Room size</th><th>Total rooms</th><th>People per room</th><th>Total people</th><th>Double bunk beds</th></tr>{cap}</table>"
	spec = ""
	for s in b["spec"]:
		text = s[d["panel"]]
		if s["part"].lower().startswith("electrical") and not d["electrical"]:
			text = "Electrical work is not in our scope."
		spec += f"<tr><td class=b style='width:32%'>{esc(s['part'])}</td><td>{esc(text)}</td></tr>"
	spec = f"<table class=p><tr><th>Part name</th><th>Specification details</th></tr>{spec}</table>"
	li = lambda xs: "<ul>" + "".join(f"<li>{esc(t)}</li>" for t in xs) + "</ul>"  # noqa: E731
	owner = frappe.db.get_value("User", doc.owner, "full_name") or doc.owner
	sp = b.get("sales_team", {}).get(owner) or {}
	sign = (f"<b>{esc(owner)}</b><br>{esc(sp.get('designation') or '')}<br>SK Ind Tech Solutions Pvt. Ltd.<br>"
		f"Mail id - {esc(sp.get('email') or 'cabin@skind.tech')}<br>Phone No - {esc(sp.get('phone') or '8432533555')}")
	header = frappe.utils.get_url("/assets/sk_app/images/sk-quote-header.png")
	stamp = f"<div class=band style='background:#7a0000'>{waiting}</div>" if waiting else ""
	bar = lambda n, t: f"<div class=bar>{n}. {t}</div>"  # noqa: E731
	return f"""<style>{cq.CSS} .skq table.p td,.skq table.p th{{font-size:8.6pt}} .skq ul{{margin:2px 0 2px 18px;padding:0}}</style><div class=skq>
<img class=hdr src="{header}">{stamp}
<div class=band>QUOTATION &nbsp; | &nbsp; Ref: {esc(ref)} &nbsp; | &nbsp; Date: {date} &nbsp; | &nbsp; Rev: {rev}</div>
<table class=addr style="width:100%;margin:12px 0 8px"><tr><td>To,<br>{to}</td><td style="width:45%"><span class=k>Quotation No.</span><b>{esc(ref)} {rev}</b><br>
<span class=k>Date</span><b>{date}</b><br><span class=k>Valid till</span><b>{formatdate(doc.valid_till, "dd-MMM-yyyy") if doc.valid_till else ""}</b><br>
<span class=k>Panel</span><b>{d['panel']}</b></td></tr></table>
<div class=subj>Offer details as below</div>
{bar(1, "Price schedule (INR)")}{price}
{bar(2, "Scope, delivery, payment and terms")}{terms}
{bar(3, "Sq ft calculation details")}{area}
{bar(4, "Capacity details")}{cap}
{bar(5, "Technical specification of structure")}{spec}
{bar(6, "Damages")}{li(b['damages'])}
{bar(7, "General terms and conditions")}{li(b['general_terms'])}
<p>We see great potential in your firm and are looking forward to a healthy business relationship.<br>Let us know how you want to take this further.</p>
<p>Best Regards,<br><br>{sign}<br>GSTIN 27ABBCS4285J1ZZ</p></div>"""
