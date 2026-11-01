"""Minimum input (SK 1-Nov-2026, skill sk-app-minimum-input): the person gives only what only they know; the app fills
the rest from what ERPNext already has. Pure functions (no Frappe imports) so they can be unit tested anywhere; the
callers (gates, store, logins) use them and still keep every essential ERPNext field filled before saving.
"""

import re
from collections import Counter

# GST state code (first 2 digits of a GSTIN) -> state name as ERPNext / India Compliance spell it
STATE_OF_CODE = {"01": "Jammu and Kashmir", "02": "Himachal Pradesh", "03": "Punjab", "04": "Chandigarh", "05": "Uttarakhand",
	"06": "Haryana", "07": "Delhi", "08": "Rajasthan", "09": "Uttar Pradesh", "10": "Bihar", "11": "Sikkim", "12": "Arunachal Pradesh",
	"13": "Nagaland", "14": "Manipur", "15": "Mizoram", "16": "Tripura", "17": "Meghalaya", "18": "Assam", "19": "West Bengal",
	"20": "Jharkhand", "21": "Odisha", "22": "Chhattisgarh", "23": "Madhya Pradesh", "24": "Gujarat",
	"26": "Dadra and Nagar Haveli and Daman and Diu", "27": "Maharashtra", "29": "Karnataka", "30": "Goa", "31": "Lakshadweep Islands",
	"32": "Kerala", "33": "Tamil Nadu", "34": "Puducherry", "35": "Andaman and Nicobar Islands", "36": "Telangana",
	"37": "Andhra Pradesh", "38": "Ladakh"}
GSTIN_RE = re.compile(r"^[0-9]{2}[A-Z0-9]{10}[0-9A-Z]{3}$")


def state_from_gstin(gstin) -> str | None:
	"""Maharashtra for 27AAAC..., None when the GSTIN is not valid."""
	g = str(gstin or "").strip().upper()
	return STATE_OF_CODE.get(g[:2]) if GSTIN_RE.match(g) else None


def _words(text) -> list[str]:
	return [w for w in re.split(r"[^a-z0-9]+", str(text or "").lower()) if len(w) > 1 and not w.isdigit()]


def guess_item_defaults(name, items) -> dict:
	"""Item group and unit for a new item from the items already in ERPNext with similar names.
	items: [(item_name, item_group, stock_uom)]. Most shared words wins; ties go to the most common group / unit."""
	want = set(_words(name))
	scored = []
	for item_name, group, uom in items or []:
		common = len(want & set(_words(item_name)))
		if common:
			scored.append((common, group, uom))
	if not scored:
		return {"item_group": None, "uom": None}
	best = max(s[0] for s in scored)
	top = [s for s in scored if s[0] == best]
	group = Counter(g for _c, g, _u in top if g).most_common(1)
	uom = Counter(u for _c, _g, u in top if u).most_common(1)
	return {"item_group": group[0][0] if group else None, "uom": uom[0][0] if uom else None}


# words in an Employee's designation / department -> SK App function
ROLE_WORDS = (
	(("sales", "marketing", "business development"), "Sales"),
	(("store", "stores", "warehouse", "inventory"), "Stores"),
	(("purchase", "procurement", "buyer"), "Purchase"),
	(("production", "fabrication", "welder", "fitter", "painter", "assembly", "supervisor", "electrician", "helper"), "Production"),
	(("quality", "qc", "inspection"), "Quality"),
	(("account", "accounts", "finance", "cashier"), "Accounts"),
	(("hr", "human resource", "admin", "office"), "HR"),
	(("design", "draughtsman", "draftsman", "cad"), "Design"),
	(("machine shifting", "service", "rigging"), "Machine Shifting"),
	(("erp", "it", "ai", "software"), "AI"),
)


def functions_from_role(designation=None, department=None, allowed=None) -> list[str]:
	"""SK App functions for a new login from the Employee's designation / department (HR only confirms)."""
	text = " " + " ".join(_words(f"{designation or ''} {department or ''}")) + " "
	out = []
	for words, fn in ROLE_WORDS:
		if any(f" {w} " in text for w in words) and fn not in out and (allowed is None or fn in allowed):
			out.append(fn)
	return out
