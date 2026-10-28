"""Item inputs for Store and Purchase (SK 28-Oct-2026 review list Rev 1, points 11-13 and 19, approved).

- A list typed, spoken ("C channel 20 nos, MS plate 5 kg") or read from a photo of a handwritten list becomes up to 20
  requisition rows, each matched to an ERP item for the person to check before sending.
- Item search matches every word, so "c channel 100" finds "C-Channel 100x50" (the old search needed the exact text).
- Photo match (free, on the phone): the phone turns a material photo into a small signature (shape + colour). The first
  time, the person picks the item and that photo becomes the item's sample; next time a photo suggests the closest
  items to confirm. Up to 5 samples per item are kept on the Item (sk_photo_samples).
"""

import json
import re

import frappe
from frappe import _
from frappe.utils import flt

from sk_app.store import need

USERS = ("Stores", "Purchase", "Management", "HR", "Production", "Quality", "Accounts")
MAX_ROWS = 20
FIELD = "sk_photo_samples"
MAX_SAMPLES = 5

UNITS = r"(nos?|numbers?|pcs?|pieces?|kgs?|kilos?|kilograms?|mtrs?|meters?|metres?|m|ft|feet|foot|ltrs?|litres?|liters?|sets?|boxes|box|" \
	r"rolls?|sheets?|bags?|lengths?|नग|किलो|मीटर|फूट|लिटर|सेट|पोती|बॅग|शीट)"
MR_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
WORD_NUM = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
	"eleven": 11, "twelve": 12, "fifteen": 15, "twenty": 20, "twenty five": 25, "thirty": 30, "forty": 40, "fifty": 50, "hundred": 100,
	"एक": 1, "दोन": 2, "तीन": 3, "चार": 4, "पाच": 5, "सहा": 6, "सात": 7, "आठ": 8, "नऊ": 9, "दहा": 10, "बारा": 12, "पंधरा": 15,
	"वीस": 20, "पंचवीस": 25, "तीस": 30, "चाळीस": 40, "पन्नास": 50, "शंभर": 100}


def ensure_setup():
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	create_custom_fields({"Item": [{"fieldname": FIELD, "label": "SK App photo samples", "fieldtype": "Small Text", "read_only": 1,
		"hidden": 1, "insert_after": "image", "description": "Photo signatures kept by the SK App to suggest this item from a photo"}]}, update=True)


# ---------- item search by words ----------

def _words(text: str) -> list[str]:
	text = re.sub(r"(\d)\s*[x×*]\s*(\d)", r"\1 \2", (text or "").lower())  # 100x50 → 100 50
	return [w for w in re.split(r"[\s\-_/,()]+", text) if w and w != "."]


def find_items(text: str, limit: int = 8) -> list[dict]:
	"""Items whose name / code / description has every word; if none, the ones with the most words."""
	words = _words(text)
	if not words:
		return []
	cond = " and ".join(["concat_ws(' ', item_name, item_code, ifnull(description, '')) like %s"] * len(words))
	args = [f"%{w}%" for w in words]
	rows = frappe.db.sql(f"""select item_code, item_name, stock_uom from `tabItem` where disabled = 0 and is_stock_item = 1 and {cond}
		order by length(item_name) asc limit {int(limit)}""", args, as_dict=True)
	if not rows:
		score = " + ".join(["(concat_ws(' ', item_name, item_code) like %s)"] * len(words))
		rows = frappe.db.sql(f"""select item_code, item_name, stock_uom, ({score}) as hits from `tabItem` where disabled = 0 and is_stock_item = 1
			having hits > 0 order by hits desc, length(item_name) asc limit {int(limit)}""", args, as_dict=True)
	return [_with_stock(r) for r in rows]


def _with_stock(r) -> dict:
	qty = frappe.db.sql("select sum(actual_qty) from `tabBin` where item_code = %s", r.item_code)[0][0]
	return {"item_code": r.item_code, "item_name": r.item_name, "uom": r.stock_uom, "stock": flt(qty)}


def search(user: str, q: str | None) -> list[dict]:
	need(user, *USERS)
	return find_items(q or "")


# ---------- a list (typed / spoken / read from a photo) → rows ----------

def _to_number(text: str) -> float | None:
	m = re.search(r"\d+(?:\.\d+)?", text)
	if m:
		return flt(m.group(0))
	low = text.lower().strip()
	return flt(WORD_NUM[low]) if low in WORD_NUM else None


def split_line(chunk: str) -> tuple[str, float]:
	"""("C channel 100x50", 20) from "C channel 100x50 20 nos". The quantity is the number before a unit, else the last
	number that is not a size (100x50, 2.5mm), else 1."""
	text = chunk.translate(MR_DIGITS).strip(" .-:")
	for w, n in sorted(WORD_NUM.items(), key=lambda x: -len(x[0])):
		text = re.sub(rf"(?<!\w){re.escape(w)}(?!\w)", str(n), text, flags=re.I)
	m = re.search(rf"(\d+(?:\.\d+)?)\s*{UNITS}(?!\w)", text, flags=re.I)
	if m and not re.search(r"[x×*]\s*$", text[:m.start()]):
		qty = flt(m.group(1))
		item = (text[:m.start()] + " " + text[m.end():]).strip()
		return re.sub(r"\s+", " ", item), qty
	nums = [x for x in re.finditer(r"(?<![x×*\d.])(\d+(?:\.\d+)?)(?![\d.]*\s*(?:x|×|\*|mm|cm|inch|\"))", text)]
	if nums:
		last = nums[-1]
		item = (text[:last.start()] + " " + text[last.end():]).strip()
		if item:
			return re.sub(r"\s+", " ", item), flt(last.group(1))
	return re.sub(r"\s+", " ", text), 1.0


def parse_list(user: str, text: str) -> dict:
	need(user, *USERS)
	chunks = [c.strip() for c in re.split(r"[\n;,]+|\s+(?:and|आणि|व)\s+|\s+&\s+", text or "") if c.strip()]
	rows = []
	for c in chunks[:MAX_ROWS]:
		item_text, qty = split_line(c)
		if not item_text:
			continue
		choices = find_items(item_text, 5)
		top = choices[0] if choices else {}
		rows.append({"text": c, "said": item_text, "qty": qty, "item_code": top.get("item_code"), "item_name": top.get("item_name"),
			"uom": top.get("uom"), "stock": top.get("stock"), "choices": choices})
	return {"rows": rows, "more": max(0, len(chunks) - MAX_ROWS), "max": MAX_ROWS}


# ---------- photo samples ----------

def _clean_sig(sig) -> dict:
	sig = json.loads(sig) if isinstance(sig, str) else sig
	d = str((sig or {}).get("d") or "")
	h = [flt(x) for x in (sig or {}).get("h") or []]
	if not re.fullmatch(r"[0-9a-f]{16}", d) or len(h) != 64:
		frappe.throw(_("Photo could not be read, please take it again"))
	return {"d": d, "h": [round(x, 4) for x in h]}


def distance(a: dict, b: dict) -> float:
	"""0 = same photo, 1 = nothing alike: shape (difference hash) and colour (histogram) half each."""
	shape = bin(int(a["d"], 16) ^ int(b["d"], 16)).count("1") / 64
	colour = sum(abs(x - y) for x, y in zip(a["h"], b["h"])) / 2
	return round(0.5 * shape + 0.5 * min(colour, 1), 4)


def _samples(item_code: str) -> list[dict]:
	raw = frappe.db.get_value("Item", item_code, FIELD)
	try:
		return json.loads(raw) if raw else []
	except ValueError:
		return []


def match(user: str, sig, limit: int = 5) -> dict:
	need(user, *USERS)
	sig = _clean_sig(sig)
	if not frappe.get_meta("Item").has_field(FIELD):
		return {"rows": [], "first_time": True}
	best = {}
	for r in frappe.get_all("Item", filters={"disabled": 0, FIELD: ["is", "set"]}, fields=["item_code", FIELD], limit=0):
		try:
			samples = json.loads(r.get(FIELD) or "[]")
		except ValueError:
			continue
		for s in samples:
			d = distance(sig, s)
			if d < best.get(r.item_code, (2, None))[0]:
				best[r.item_code] = (d, s.get("file"))
	ranked = sorted(best.items(), key=lambda x: x[1][0])[:limit]
	rows = []
	for code, (d, file) in ranked:
		r = frappe.db.get_value("Item", code, ["item_code", "item_name", "stock_uom"], as_dict=True)
		rows.append({**_with_stock(r), "score": round((1 - d) * 100), "photo": file})
	return {"rows": rows, "first_time": not rows}


def save_sample(user: str, item_code: str, sig, file_url: str | None = None) -> dict:
	"""The person said which item the photo shows: the photo is kept as a sample (the newest 5)."""
	need(user, *USERS)
	if not frappe.db.exists("Item", item_code):
		frappe.throw(_("Unknown item"))
	sig = _clean_sig(sig)
	samples = [s for s in _samples(item_code) if distance(s, sig) > 0.02]  # the same photo again is not kept twice
	samples = ([{**sig, "file": file_url, "by": user}] + samples)[:MAX_SAMPLES]
	frappe.db.set_value("Item", item_code, FIELD, json.dumps(samples, separators=(",", ":")), update_modified=False)
	if file_url and not frappe.db.get_value("Item", item_code, "image"):
		frappe.db.set_value("Item", item_code, "image", file_url, update_modified=False)
	return {"item_code": item_code, "samples": len(samples)}
