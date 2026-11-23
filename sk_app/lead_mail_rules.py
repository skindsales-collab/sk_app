"""Pure rules for leads that come by mail (IndiaMART, JustDial, plain e-mail). PR D (SK 15-Nov "go").

The 14-Nov finding on live: 71 empty leads named "Enquiry" (63 with no phone, e-mail or requirement), JustDial leads saved
without the mobile, "Purchase" taken as a person's name from purchase@..., and every lead put under Cabin. Root cause of
the empty ones: IndiaMART mails carry only "Dear User" in their text part; the buyer's data is in the HTML part, which
the reader never looked at. No frappe here, so these rules are tested on the real mail texts."""

import re

# a sender display name that is a role or a mailbox, not a person (never becomes the contact person's name)
ROLE_WORDS = {"purchase", "purchases", "sales", "info", "admin", "accounts", "account", "hr", "office", "enquiry", "enquiries", "inquiry",
	"marketing", "store", "stores", "support", "contact", "mail", "noreply", "no-reply", "team", "procurement", "projects", "project",
	"engineering", "works", "tender", "tenders", "customer care", "customercare", "md", "director", "manager", "ceo"}
PUBLIC_MAIL = {"gmail.com", "yahoo.com", "yahoo.in", "yahoo.co.in", "hotmail.com", "outlook.com", "rediffmail.com", "live.com", "icloud.com", "ymail.com"}
CABIN_WORDS = ("cabin", "container", "porta", "prefab", "bunk", "site office", "security", "toilet", "kiosk", "guard room", "lgsf", "labour camp",
	"labor camp", "modular", "colony", "shelter", "hut", "room")
NON_CABIN_WORDS = ("machine shifting", "shifting", "rigging", "dismantl", "relocation", "job work", "machining", "crane", "erection", "ballscrew",
	"ball screw", "reconditioning", "overhaul")


def pick_text(text_part: str | None, html_text: str | None) -> str:
	"""The mail text to read: the plain part when it really holds the mail, else the HTML part stripped to text.
	IndiaMART's plain part is only 'Dear User' (78 of 106 mails on 15-Nov)."""
	plain = (text_part or "").strip()
	html = (html_text or "").strip()
	if len(plain) >= 80 or (plain and len(plain) >= len(html)):
		return plain
	return html or plain


def squeeze(text: str) -> str:
	return re.sub(r"[ \t\xa0]+", " ", (text or "").replace("&nbsp;", " ")).strip()


def parse_indiamart(subject: str | None, text: str) -> dict:
	"""IndiaMART 'Business Enquiry' mail (one line once the HTML is stripped):
	'... searching for <product>. Below are the requirement details :<k>:<v>... Below are the Buyer details : ...
	Regards<Name><Company>, <City> - <PIN>, <State>, IndiaMobile: +91-<10 digits>Email: <mail>'.
	Returns what was found: first_name, organization, city, mobile_no, email, requirement (product + details)."""
	t = squeeze(text)
	out: dict = {}
	m = re.search(r"Enquiry for (.+?) from (.+?)\s*$", (subject or "").strip(), re.I)
	product, name = (m.group(1).strip(), m.group(2).strip()) if m else (None, None)
	if not product:
		p = re.search(r"searching for (.+?)\.", t)
		product = p.group(1).strip() if p else None
	details = re.search(r"requirement details\s*:\s*(.+?)(?:\s*Call\s*Chat|Below are the Buyer details|Regards)", t, re.I)
	req = [x for x in (product, details.group(1).strip() if details else None) if x]
	if req:
		out["requirement"] = " · ".join(req)[:1000]
	mob = re.search(r"Mobile\s*:\s*(\+?[\d\- ]{10,16})", t, re.I)
	if mob:
		digits = re.sub(r"\D", "", mob.group(1))[-10:]
		if len(digits) == 10 and digits[0] in "6789":
			out["mobile_no"] = digits
	em = re.search(r"Email\s*:\s*([\w.+-]+@[\w-]+\.[\w.]+)", t, re.I)
	if em:
		out["email"] = em.group(1)
	tail = re.search(r"Regards\s*(.+?)(?:Mobile\s*:|Email\s*:|$)", t, re.I)
	if tail:
		who = tail.group(1).strip()
		if name and who.lower().startswith(name.lower()):
			who = who[len(name):].strip(" ,")
		elif not name:
			name = who.split(",")[0].strip()[:80] or None
			who = ""
		parts = [p.strip() for p in who.split(",")]
		if parts and parts[0] and parts[0].lower() not in ("india", "maharashtra"):
			company = parts[0]
			if company.lower() != (name or "").lower():
				out["organization"] = company[:140]
		city = next((re.sub(r"\s*-\s*\d{6}.*$", "", p).strip() for p in parts[1:] if re.search(r"-\s*\d{6}", p)), None)
		if city:
			out["city"] = city[:80]
	if name:
		out["first_name"] = name[:80]
	return out


def sender_name(display: str | None, email: str | None, organization: str | None = None) -> tuple[str | None, str | None]:
	"""(contact person, company) from a mail sender. A role word ('Purchase', 'Sales', 'Info') or the mailbox's local
	part is never a person: the company comes from the mail domain instead (gurudattaforging.com -> Gurudattaforging)."""
	name = squeeze(display or "")
	addr = (email or "").strip().lower()
	local, _at, domain = addr.rpartition("@")
	# a role word, the address itself, or a company mailbox's local part ("purchase" at a company domain) is not a person
	if name and (name.lower() in ROLE_WORDS or re.fullmatch(r"[\w.+-]+@[\w.-]+", name) or (name.lower() == local and domain not in PUBLIC_MAIL)):
		name = ""
	company = squeeze(organization or "")
	if not company and domain and domain not in PUBLIC_MAIL and "." in domain:
		company = domain.split(".")[0].replace("-", " ").title()
	if not name and company:
		return None, company
	return (name or None), (company or None)


def segment_or_none(text: str | None) -> str | None:
	"""Sub-segment only when the words say it; otherwise None, and the sales owner sets it when the product is known
	(SK 14-Nov: every mail lead went under Cabin by default)."""
	low = (text or "").lower()
	if "job work" in low or "machining" in low:
		return "Job Work"
	if any(w in low for w in NON_CABIN_WORDS):
		return "Machine Shifting"
	if "lgsf" in low or "light gauge" in low or "sgsf" in low:
		return "LGSF"
	if "labour camp" in low or "labor camp" in low or "modular" in low or "colony" in low:
		return "Modular / Labour Camp"
	if any(w in low for w in CABIN_WORDS):
		return "Standard Cabin (GI / ACP)"
	return None


def has_contact(data: dict) -> bool:
	"""A lead needs a way to reach the customer: a mobile or an e-mail. Without both it is not saved (logged instead)."""
	digits = re.sub(r"\D", "", str(data.get("mobile_no") or ""))
	return len(digits) >= 10 or "@" in str(data.get("email") or "")


# SK 23-Nov (approved, low-orders review): mails that are never a customer enquiry and never a "Customer mail" task:
# our own boxes, salary / PF / ESIC / payroll mails, passwords and log-in codes.
PRIVATE_WORDS = ("salary", "payslip", "pay slip", "payroll", "provident fund", "epfo", " pf ", "pf contribution", "uan ", "esic",
	"password", "otp", "one time password", "verification code", "login code", "bonus", "form 16", "tds certificate")


def private_or_internal(sender: str | None, subject: str | None, own_boxes=()) -> bool:
	"""True for our own mail and payroll / password mails (no lead, no task, nothing shown to sales)."""
	s = (sender or "").strip().lower()
	if not s or s.endswith("@skind.tech") or s in {b.lower() for b in own_boxes or ()}:
		return True
	subj = f" {(subject or '').lower()} "
	return any(w in subj for w in PRIVATE_WORDS)
