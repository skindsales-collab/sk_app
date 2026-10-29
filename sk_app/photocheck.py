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
		from sk_app.store import material_pos

		pos = frappe.get_all("Purchase Order", filters={"supplier": sup, "docstatus": 1, "per_billed": ["<", 100], **material_pos()},
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


def _party(doctype: str, field: str, label: str, text: str, kind: str):
	"""A supplier / customer / item box: green when it is the ERPNext name, else the nearest names to pick."""
	text = (text or "").strip()
	if text and frappe.db.exists(doctype, text):
		return _row(field, label, text, "green"), text
	near = _nearest(doctype, "item_name" if doctype == "Item" else "supplier_name" if doctype == "Supplier" else "customer_name", text, kind) if text else []
	return _row(field, label, text, "amber" if near else "red", f"Pick the {label.lower()} from ERPNext" if text else "Needed by ERPNext", near), (near[0] if near else text)


def _amount(field, label, v, limit=None):
	amt = frappe.utils.flt(v)
	if amt <= 0:
		return _row(field, label, v or "", "red", "Needed, more than 0")
	if limit and amt > limit:
		return _row(field, label, amt, "amber", f"Above ₹{limit:,.0f}: SK approves it")
	return _row(field, label, amt, "green")


def _date(field, label, v):
	from frappe.utils import date_diff, getdate, nowdate

	if not v:
		return _row(field, label, "", "red", "Needed")
	days = date_diff(nowdate(), getdate(v))
	if days < 0:
		return _row(field, label, v, "red", "Date is in the future")
	return _row(field, label, v, "amber" if days > 30 else "green", "Bill older than 30 days" if days > 30 else None)


def check_expense(v: dict) -> list:
	"""Expense claim from a bill photo (HR Leave & Expense icon)."""
	from sk_app.purchase import po_limit

	return [_row("expense_type", "Expense type", v.get("expense_type") or "", "green" if v.get("expense_type") else "red",
		None if v.get("expense_type") else "Pick the type: ERPNext needs it"),
		_amount("amount", "Amount", v.get("amount"), po_limit()), _date("expense_date", "Bill date", v.get("expense_date"))]


def check_voucher(v: dict) -> list:
	"""Petty cash voucher (Accounts)."""
	text = (v.get("spent_on") or "").strip()
	return [_row("remark", "Spent on", text, "green" if len(text) >= 4 else "red", None if len(text) >= 4 else "Say what it was for (ERPNext remark)"),
		_amount("amount", "Amount", v.get("amount")),
		_row("account", "Expense head", v.get("account") or "", "green" if v.get("account") else "red", None if v.get("account") else "Pick the expense ledger")]


def check_quote(v: dict) -> list:
	"""Supplier quote (Purchase · Get Rates): supplier and item as in ERPNext, rate against the last rate paid."""
	sup_row, _sup = _party("Supplier", "supplier", "Supplier", v.get("supplier"), "supplier")
	item_row, item = _party("Item", "item_code", "Item", v.get("item"), "item")
	rate = frappe.utils.flt(v.get("rate"))
	rows = [sup_row, item_row]
	if rate <= 0:
		rows.append(_row("rate", "Rate", v.get("rate") or "", "red", "Needed"))
	else:
		code = item if frappe.db.exists("Item", item or "") else frappe.db.get_value("Item", {"item_name": item}, "name") if item else None
		last = frappe.db.get_value("Item", code, "last_purchase_rate") if code else None
		if last:
			diff = round((rate - frappe.utils.flt(last)) * 100 / frappe.utils.flt(last))
			rows.append(_row("rate", "Rate", rate, "amber" if abs(diff) > 15 else "green", f"Last rate ₹{frappe.utils.flt(last):,.2f} ({diff:+d}%)"))
		else:
			rows.append(_row("rate", "Rate", rate, "green", "No earlier rate in ERPNext"))
	return rows


def check_receive(v: dict) -> list:
	"""Receipt without a PO (Stores): supplier and item as in ERPNext, a quantity, and why there is no PO."""
	sup_row, _s = _party("Supplier", "supplier", "Supplier", v.get("supplier"), "supplier")
	item_row, _i = _party("Item", "item_code", "Item", v.get("item"), "item")
	qty = frappe.utils.flt(v.get("qty"))
	why = (v.get("reason") or "").strip()
	return [sup_row, item_row, _row("qty", "Quantity", v.get("qty") or "", "green" if qty > 0 else "red", None if qty > 0 else "Needed"),
		_row("remarks", "Why no PO", why, "green" if why else "red", None if why else "Purchase needs the reason")]


def _numbers(line: str) -> list[float]:
	return [float(x.replace(",", "")) for x in re.findall(r"\d[\d,]*\.?\d*", line or "") if x.replace(",", "").replace(".", "", 1).isdigit()]


def _best_line(name: str, lines: list[str]) -> tuple[str | None, float]:
	words = [w for w in re.findall(r"[a-z0-9]+", (name or "").lower()) if len(w) > 2]
	best, score = None, 0.0
	for ln in lines:
		low = ln.lower()
		hit = sum(1 for w in words if w in low) / len(words) if words else 0
		r = max(hit, difflib.SequenceMatcher(None, (name or "").lower(), low[: len(name or "") + 10]).ratio())
		if r > score:
			best, score = ln, r
	return best, score


def check_receipt(v: dict) -> list:
	"""Material received against a PO (Stores, SK 26-Oct): the supplier's invoice photo is read and each PO item is
	looked for on it, so the quantity entered matches the bill; bill lines that are not on the PO are shown too."""
	po = v.get("po")
	if not po or not frappe.db.exists("Purchase Order", po):
		return []
	doc = frappe.get_doc("Purchase Order", po)
	lines = [ln.strip() for ln in (v.get("text") or "").splitlines() if len(ln.strip()) > 3]
	rows, used = [], set()
	bill = (v.get("bill_no") or "").strip()
	if bill:
		dup = frappe.db.get_value("Purchase Receipt", {"supplier": doc.supplier, "supplier_delivery_note": bill, "docstatus": ["<", 2]}, "name")
		rows.append(_row("bill_no", "Supplier bill no", bill, "red" if dup else "green", f"Already received: {dup}" if dup else None))
	else:
		rows.append(_row("bill_no", "Supplier bill no", "", "amber", "Type the bill / challan number from the photo"))
	for k, it in enumerate(doc.items):
		entered = frappe.utils.flt(v.get(f"qty_{k}"))
		field = f"qty_{k}"
		if not lines:
			rows.append(_row(field, it.item_name, entered, "green" if entered > 0 else "amber", None if entered > 0 else "Not received?"))
			continue
		line, score = _best_line(it.item_name, lines)
		if score < 0.5:
			rows.append(_row(field, it.item_name, entered, "red" if entered > 0 else "amber",
				"Not found on the bill photo: check before saving" if entered > 0 else "Not on this bill"))
			continue
		used.add(line)
		nums = [n for n in _numbers(line) if 0 < n < 100000]
		same = any(abs(n - entered) < 0.001 for n in nums)
		pending = frappe.utils.flt(it.qty) - frappe.utils.flt(it.received_qty)
		guess = next((n for n in nums if abs(n - pending) < 0.001 or abs(n - frappe.utils.flt(it.qty)) < 0.001), None)
		if same:
			rows.append(_row(field, it.item_name, entered, "green", "Same as the bill"))
		else:
			opts = [str(int(guess) if guess and guess == int(guess) else guess)] if guess else []
			rows.append(_row(field, it.item_name, entered, "amber", f"Bill line: {line[:60]}", opts))
	extra = [ln for ln in lines if ln not in used and _numbers(ln) and re.search(r"[A-Za-z]{4,}", ln)]
	for ln in extra[:4]:
		near = _nearest("Item", "item_name", re.sub(r"[\d.,]+", " ", ln).strip(), "item", n=2)
		if near:
			rows.append(_row("extra", "On the bill, not on the PO", ln[:60], "amber", "Add it in ERPNext? Ask Purchase", near))
	return rows


CHECKS = {"lead": check_lead, "receipt": check_receipt, "supplier": check_supplier, "bill": check_bill, "plate": check_plate, "expense": check_expense,
	"voucher": check_voucher, "quote": check_quote, "receive": check_receive}


def check(user: str, kind: str, values: dict) -> dict:
	fn = CHECKS.get(kind)
	if not fn:
		frappe.throw(frappe._("Unknown check"))
	rows = fn(values or {})
	return {"rows": rows, "red": sum(1 for r in rows if r["state"] == "red"), "amber": sum(1 for r in rows if r["state"] == "amber")}
