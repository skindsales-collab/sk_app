"""Pure rules of the one CRM Lead writer."""

from sk_app.gate_rules import lead_missing


def shape(data: dict) -> dict:
	"""The lead's fields the one way: trimmed, blanks as None, a placeholder name only when nothing is known."""
	s = lambda k: (str(data.get(k) or "")).strip() or None
	return {"first_name": s("first_name") or "Enquiry", "organization": s("organization"), "mobile_no": s("mobile_no"),
		"email": s("email"), "source": s("source"), "sk_segment": s("segment"), "sk_product": (s("product") or "")[:140] or None,
		"lead_owner": s("owner")}


def problems(shaped: dict) -> list:
	return [("lead_" + k, w) for k, w in lead_missing(shaped)]


# ---- Site Checklist (Machine Shifting survey, SK 10-Nov): 8 yes/no points, saved as one note + photo on the deal ----
SITE_CHECKS = [
	("weight", "Machine weight and size known", "मशीनचे वजन व आकार माहीत"),
	("path", "Path and floor checked (width, height, load)", "रस्ता व फरशी तपासली (रुंदी, उंची, भार)"),
	("crane", "Crane / hydra can reach the machine", "क्रेन / हायड्रा मशीनपर्यंत पोहोचते"),
	("power", "Power can be cut and isolated", "वीज बंद व वेगळी करता येते"),
	("dismantle", "Dismantling needed", "डिस्मॅन्टलिंग लागेल"),
	("contact", "Customer's site contact noted", "साईटवरील ग्राहकाचा संपर्क नोंदवला"),
	("permit", "Work permit / safety rules known", "वर्क परमिट / सुरक्षा नियम माहीत"),
	("date", "Work date window agreed", "कामाची तारीख ठरली"),
]


def site_checklist_missing(answers: dict, photo) -> list:
	"""Mandatory gate: every point answered Yes / No and at least one site photo."""
	out = [label for key, label, _mr in SITE_CHECKS if (answers or {}).get(key) not in ("Yes", "No")]
	if not photo:
		out.append("Site photo")
	return out


def site_checklist_text(answers: dict, note: str | None = None) -> str:
	lines = ["Site checklist"] + [f"{'✔' if answers.get(key) == 'Yes' else '✘'} {label}: {answers.get(key)}" for key, label, _mr in SITE_CHECKS]
	if (note or "").strip():
		lines.append(f"Note: {note.strip()}")
	return "\n".join(lines)


# ---- Won = order exists (SK 14-Nov, KF-05180): a deal marked Won by hand without a Sales Order is a rule gap ----
def deal_won_gap(was_won: bool, is_won: bool, from_order: bool, has_order: bool) -> list:
	"""Problems when a deal's status turns Won. from_order = the app / an ERPNext order submit is setting it (always fine);
	has_order = a submitted Sales Order of this deal exists."""
	if not is_won or was_won or from_order or has_order:
		return []
	return [("deal_won_without_order", "Deal marked Won without a Sales Order: make the order from the deal (the order marks it Won), "
		"or keep the deal at Negotiations until the PO comes")]


# ---- New Lead for an existing customer (SK 14-Nov): the old data appears while typing, nothing is typed twice ----
def rank_matches(q: str, names: list[str], n: int = 8) -> list[str]:
	"""Names that start with the typed text first, then a word that starts with it, then anywhere inside
	("rothe" must put Rothe Erde before Mittal brothers)."""
	q = (q or "").strip().lower()
	if len(q) < 2:
		return []
	tiers = ([], [], [])
	for name in dict.fromkeys(n_ for n_ in names if n_):
		low = name.lower()
		if low.startswith(q):
			tiers[0].append(name)
		elif any(w.startswith(q) for w in low.replace(",", " ").replace("(", " ").split()):
			tiers[1].append(name)
		elif q in low:
			tiers[2].append(name)
	return (tiers[0] + tiers[1] + tiers[2])[:n]


def fill_from_existing(typed: dict, pick: dict) -> dict:
	"""The form values after picking an existing customer: ERPNext's data wins where it has some; what the person
	typed stays where ERPNext has nothing. Returns only the fields to set."""
	out = {}
	for key, src in (("organization", "customer_name"), ("first_name", "contact"), ("mobile_no", "mobile"), ("email", "email"), ("segment", "segment")):
		if pick.get(src):
			out[key] = pick[src]
	if pick.get("customer_name") and not pick.get("contact") and not (typed.get("first_name") or "").strip():
		out["first_name"] = pick["customer_name"]
	out["no_gstin"] = 1 if pick.get("customer_name") and not pick.get("gstin") else 0
	out["source"] = "Existing Customer"
	return out


def customer_match_keys(mobile: str | None, email: str | None) -> dict:
	"""How an incoming lead (mail, portal, phone) is matched to an existing Customer: the last 10 digits of the mobile and
	the e-mail's domain (never gmail / yahoo / hotmail style public domains)."""
	digits = "".join(ch for ch in (mobile or "") if ch.isdigit())[-10:]
	domain = (email or "").strip().lower().rpartition("@")[2]
	if domain in PUBLIC_MAIL or "." not in domain:
		domain = ""
	return {"mobile10": digits if len(digits) == 10 else "", "domain": domain}


PUBLIC_MAIL = {"gmail.com", "yahoo.com", "yahoo.in", "yahoo.co.in", "hotmail.com", "outlook.com", "rediffmail.com", "live.com", "icloud.com", "ymail.com"}


# ---- who gets a lead from a portal / mail (SK 16-Nov, KF-05541): IndiaMART -> its owner, JustDial -> its owner ----
OWNER_FIELDS = {"IndiaMART": ("lead_owner_indiamart", "lead_owner_digital"), "JustDial": ("lead_owner_justdial", "lead_owner_digital")}


def owner_fields(source: str | None, non_cabin: bool) -> tuple[str, ...]:
	"""SK App Settings fields to try in order for the lead's owner. Non-Cabin words win over the portal; a portal lead
	goes to that portal's owner, else the fallback digital owner; everything else to the cabin owner."""
	if non_cabin:
		return ("lead_owner_noncabin",) + OWNER_FIELDS.get(source or "", ()) + ("lead_owner_cabin",)
	return OWNER_FIELDS.get(source or "", ()) + ("lead_owner_cabin",)


# SK 20-Nov "CNA - no deal": a note only sends a lead for its quote (deal) when it carries a real talk or the requirement;
# a no-answer note (CNA, busy, switched off, call back ...) never does
import re as _re

NO_TALK = _re.compile(r"\b(c\.?\s?n\.?\s?a|not\s+answer\w*|no\s+answer|did\s*n.?t\s+(pick|answer)|not\s+pick\w*|not\s+reachable|"
	r"unreachable|switch\w*\s+off|busy|ringing|call\s*back|no\s+response|not\s+respond\w*|missed|wrong\s+number|"
	r"out\s+of\s+(coverage|service)|voice\s*mail)\b", _re.I)
REQUIREMENT = _re.compile(r"\d+\s*(ft|feet|')?\s*[x×*]\s*\d+|\b(cabin|container|toilet|office|security|kiosk|porta|shifting|"
	r"machine|qty|nos?|units?|size|requirement|require|need|quotation|quote|rate|price|budget|site|drawing|puf|acp|gi\b|frp)", _re.I)


def note_moves_to_quote(text: str | None, photo: bool = False, talked: bool = False) -> bool:
	"""True when a note / call may send the lead for its quote: a photo, a real talk, or requirement words, and never
	a no-answer note (CNA etc.), even when it names the product."""
	t = (text or "").strip()
	if t and NO_TALK.search(t) and not talked:
		return False
	return bool(photo or talked or (t and REQUIREMENT.search(t)))


# SK 20-Nov (Swati, Irfan Ansari deal 00168): the cabin requirement words fill the ticks the design reads, and an amount
# typed in "Annual Revenue" is the customer's budget. Only ever sets a tick or an empty box; never clears what was given.
TICKS = (("custom_toilet_required", _re.compile(r"\b(toilet|wash\s*room|washroom|w\.?c\.?|bath(room)?|urinal|lavatory)\b", _re.I)),
	("custom_ac_required", _re.compile(r"\b(a\.?c\.?|air\s*condition\w*|split\s*ac)\b", _re.I)),
	("custom_furniture_required", _re.compile(r"\b(furniture|table|chair|workstation|cupboard|rack)\b", _re.I)))


def cabin_fill(deal: dict) -> dict:
	"""Fields to set on a Cabin deal from what the salesperson already wrote: ticks from the requirement text,
	the budget (and the expected value) from an amount typed in Annual Revenue."""
	text = " ".join(str(deal.get(f) or "") for f in ("custom_special_requirements", "sk_product", "custom_design_notes_sales"))
	out = {f: 1 for f, rx in TICKS if not deal.get(f) and rx.search(text)}
	amount = deal.get("annual_revenue") or 0
	if amount and not deal.get("custom_customer_budget"):
		out["custom_customer_budget"] = amount
		if not deal.get("expected_deal_value"):
			out["expected_deal_value"] = amount
	return out

