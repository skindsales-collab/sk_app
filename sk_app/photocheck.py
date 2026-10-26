"""Check before saving (change list point 1, SK 26-Oct-2026).

After a photo is read on the phone (free reader, nothing paid), the form shows each value next to its ERPNext field
with a colour: green ✓ fits ERPNext, amber ⚠ the app has a suggestion, red ✗ needed by ERPNext but missing or wrong.
Suggestions come from ERPNext itself: nearest Supplier / Customer / Item, duplicate mobile, duplicate bill number,
GSTIN / IFSC / number plate format. When a person picks a suggestion the app remembers it (SK Photo Match) and offers it
first next time. Nothing is saved to ERPNext by this check; the form's own Save does that, as before.
"""

import difflib
import re

import frappe

GSTIN = re.compile(r"^(\d{2})([A-Z]{5}\d{4}[A-Z])[1-9A-Z]Z[0-9A-Z]$")
IFSC = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$")
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[a-z]{2,}$", re.I)
HOME_STATE = "27"  # Maharashtra


def _row(field, label, value, state, note=None, options=None):
	return {"field": field, "label": label, "value": value, "state": state, "note": note, "options": options or []}


def _digits(v) -> str:
	d = re.sub(r"\D", "", str(v or ""))
	return d[2:] if len(d) == 12 and d.startswith("91") else d[1:] if len(d) == 11 and d.startswith("0") else d


def learned(kind: str, text: str) -> str | None:
	if not text:
		return None
	return frappe.db.get_value("SK Photo Match", {"kind": kind, "read_text": text.strip()[:140]}, "chosen", order_by="times desc")


def learn(user: str, kind: str, read_text: str, chosen: str) -> dict:
	"""The person picked a suggestion: remember it for next time."""
	if not (read_text or "").strip() or not (chosen or "").strip() or read_text.strip() == chosen.strip():
		return {"ok": False}
	name = frappe.db.get_value("SK Photo Match", {"kind": kind, "read_text": read_text.strip()[:140], "chosen": chosen.strip()[:140]})
	if name:
		frappe.db.set_value("SK Photo Match", name, "times", (frappe.db.get_value("SK Photo Match", name, "times") or 0) + 1)
	else:
		frappe.get_doc({"doctype": "SK Photo Match", "kind": kind, "read_text": read_text.strip()[:140], "chosen": chosen.strip()[:140],
			"user": user, "times": 1}).insert(ignore_permissions=True)
	return {"ok": True}


def _nearest(doctype: str, field: str, text: str, kind: str, n: int = 3) -> list[str]:
	"""Learned choice first, then the closest names in ERPNext."""
	out = []
	alias = learned(kind, text)
	if alias:
		out.append(alias)
	if not text:
		return out
	word = text.strip().split()[0][:12] if text.strip() else ""
	pool = frappe.get_all(doctype, filters={field: ["like", f"%{word}%"]}, pluck=field, limit=200) if word else []
	if len(pool) < 20:
		pool += frappe.get_all(doctype, pluck=field, limit=2000)
	for m in difflib.get_close_matches(text.strip(), list(dict.fromkeys(pool)), n=n, cutoff=0.6):
		if m not in out:
			out.append(m)
	return out[:n]


def check_lead(v: dict) -> list:
	rows = []
	name = (v.get("first_name") or "").strip()
	rows.append(_row("first_name", "Customer name", name, "green" if name else "red", None if name else "Needed by ERPNext"))
	org = (v.get("organization") or "").strip()
	if org:
		cust = _nearest("Customer", "customer_name", org, "customer")
		exact = org in cust
		rows.append(_row("organization", "Company", org, "green" if exact or not cust else "amber",
			None if exact or not cust else "Similar customer in ERPNext", [] if exact else cust))
	else:
		rows.append(_row("organization", "Company", "", "amber", "Empty: fine for a person, not for a company"))
	mobile = _digits(v.get("mobile_no"))
	if not mobile:
		rows.append(_row("mobile_no", "Mobile", "", "red", "Needed to call the customer"))
	elif len(mobile) != 10:
		rows.append(_row("mobile_no", "Mobile", v.get("mobile_no"), "red", "A mobile has 10 digits"))
	else:
		lead = frappe.db.get_value("CRM Lead", {"mobile_no": ["like", f"%{mobile}"]}, ["name", "lead_owner"], as_dict=True) \
			if frappe.db.exists("DocType", "CRM Lead") else None
		cust = frappe.db.get_value("Customer", {"mobile_no": ["like", f"%{mobile}"]}, "name")
		note = (f"Already a lead: {lead.name} ({frappe.utils.get_fullname(lead.lead_owner)})" if lead else
			f"Already a customer: {cust}" if cust else None)
		rows.append(_row("mobile_no", "Mobile", mobile, "amber" if note else "green", note))
	email = (v.get("email") or "").strip()
	if email:
		ok = bool(EMAIL.match(email))
		rows.append(_row("email", "Email", email, "green" if ok else "red", None if ok else "Not an e-mail address"))
	seg = v.get("segment")
	rows.append(_row("sk_segment", "Segment", seg or "", "green" if seg else "red", None if seg else "Pick Cabin or Non-Cabin"))
	return rows


def check_gstin(gstin: str) -> dict:
	g = re.sub(r"\s", "", (gstin or "").upper())
	if not g:
		return _row("gstin", "GSTIN", "", "amber", "No GSTIN: only for unregistered suppliers")
	m = GSTIN.match(g)
	if not m:
		return _row("gstin", "GSTIN", g, "red", "GSTIN has 15 characters, like 27ABCDE1234F1Z5")
	dup = frappe.db.get_value("Supplier", {"gstin": g}, "name") if frappe.db.has_column("Supplier", "gstin") else None
	if dup:
		return _row("gstin", "GSTIN", g, "red", f"Already in ERPNext: {dup}", [dup])
	state = "Maharashtra" if m.group(1) == HOME_STATE else f"state code {m.group(1)} (outside Maharashtra: IGST)"
	return _row("gstin", "GSTIN", g, "green", f"{state} · PAN {m.group(2)}")


def check_supplier(v: dict) -> list:
	name = (v.get("supplier_name") or "").strip()
	near = _nearest("Supplier", "supplier_name", name, "supplier") if name else []
	exact = name in near
	rows = [_row("supplier_name", "Supplier name", name, "red" if not name else "red" if exact else "amber" if near else "green",
		"Needed by ERPNext" if not name else "Already in ERPNext" if exact else "Similar supplier in ERPNext: same one?" if near else None, near),
		check_gstin(v.get("gstin"))]
	mobile = _digits(v.get("mobile"))
	if mobile:
		rows.append(_row("mobile", "Mobile", mobile, "green" if len(mobile) == 10 else "red", None if len(mobile) == 10 else "A mobile has 10 digits"))
	if v.get("ifsc"):
		ifsc = v["ifsc"].strip().upper()
		rows.append(_row("ifsc", "IFSC", ifsc, "green" if IFSC.match(ifsc) else "red", f"Bank code {ifsc[:4]}" if IFSC.match(ifsc) else "IFSC is 11 characters, 5th is 0"))
	return rows


def check_bill(v: dict) -> list:
	sup = (v.get("supplier") or "").strip()
	rows = []
	if sup and frappe.db.exists("Supplier", sup):
		rows.append(_row("supplier", "Supplier", sup, "green"))
	else:
		near = _nearest("Supplier", "supplier_name", sup, "supplier") if sup else []
		rows.append(_row("supplier", "Supplier", sup, "amber" if near else "red", "Pick the supplier from ERPNext" if sup else "Needed by ERPNext", near))
		sup = near[0] if near else sup
	bill = (v.get("bill_no") or "").strip()
	if not bill:
		rows.append(_row("bill_no", "Bill no", "", "red", "Needed to stop double entry"))
	else:
		dup = frappe.db.get_value("Purchase Invoice", {"supplier": sup, "bill_no": bill, "docstatus": ["<", 2]}, "name") if sup else None
		rows.append(_row("bill_no", "Bill no", bill, "red" if dup else "green", f"Already entered: {dup}" if dup else None))
	amt = frappe.utils.flt(v.get("amount"))
	if amt and sup:
		pos = frappe.get_all("Purchase Order", filters={"supplier": sup, "docstatus": 1, "per_billed": ["<", 100]},
			fields=["name", "grand_total"], limit=20)
		hit = [p.name for p in pos if abs(frappe.utils.flt(p.grand_total) - amt) <= max(1, amt * 0.02)]
		rows.append(_row("grand_total", "Bill total", amt, "green" if hit else "amber",
			f"Matches {hit[0]}" if hit else ("No open PO with this amount" if pos else "No open PO for this supplier"), hit))
	elif not amt:
		rows.append(_row("grand_total", "Bill total", "", "red", "Needed"))
	return rows


def check_plate(v: dict) -> list:
	raw = re.sub(r"[^A-Z0-9]", "", (v.get("vehicle_no") or "").upper())
	if not raw:
		return [_row("vehicle_no", "Vehicle no", "", "red", "Needed for the Delivery Note")]
	m = re.match(r"^([A-Z]{2})(\d{1,2})([A-Z]{0,3})(\d{1,4})$", raw)
	if not m:
		return [_row("vehicle_no", "Vehicle no", v.get("vehicle_no"), "red", "Like MH 12 AB 1234")]
	nice = " ".join(x for x in (m.group(1), m.group(2).zfill(2), m.group(3), m.group(4).zfill(4)) if x)
	same = nice == (v.get("vehicle_no") or "").strip().upper()
	return [_row("vehicle_no", "Vehicle no", v.get("vehicle_no"), "green" if same else "amber", None if same else "Written the ERPNext way", [] if same else [nice])]


CHECKS = {"lead": check_lead, "supplier": check_supplier, "bill": check_bill, "plate": check_plate}


def check(user: str, kind: str, values: dict) -> dict:
	fn = CHECKS.get(kind)
	if not fn:
		frappe.throw(frappe._("Unknown check"))
	rows = fn(values or {})
	return {"rows": rows, "red": sum(1 for r in rows if r["state"] == "red"), "amber": sum(1 for r in rows if r["state"] == "amber")}
