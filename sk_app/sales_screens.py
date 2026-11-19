"""Sales screens (reads only; the Sales writers are writers/lead.py, writers/customer.py, writers/quotation.py, writers/order.py).
Lead / deal options, follow-up list, detail, files to send, share links, deal customer column.
Plan A step 6 (SK 9-Nov): split out of crm.py and erp_flow.py; names unchanged. crm.py keeps the helpers the Sales writers share."""

from frappe import _
from frappe.utils import add_to_date, get_datetime, now_datetime, strip_html
from sk_app import lead_status
from sk_app.crm import CALL_OUTCOMES, CRM_DOCTYPES, CUSTOMER_FIELD, DETAIL_FIELDS, PDF_DOCTYPES, SENT_STATUS, SHARE_DAYS, _check, _closed, _customer_gaps, _design_status_field, _erp_docs, _files, _for_customer, _gate, _last_activity, _open_tasks_by_doc, _pdf, _product_names, _products, _quote_pending, _sent_files, installed
from sk_app.segments import SUB_SEGMENTS as SEGMENTS
from sk_app.segments import TREE as SEGMENT_TREE
import frappe


def options() -> dict:
	if not installed():
		return {"crm": False}
	return {
		"crm": True,
		"lead_statuses": lead_status.app_statuses(),  # SK 27-Oct: his 8 steps
		# SK 1-Nov: the stage "Sent to Design" did nothing; design is sent by itself now (quote_pickup), so it is not offered
		"deal_statuses": frappe.get_all("CRM Deal Status", filters={"name": ["!=", SENT_STATUS]}, fields=["name", "type"], order_by="position asc"),
		"sources": frappe.get_all("CRM Lead Source", pluck="name", order_by="name asc"),
		"segments": SEGMENTS,
		"segment_tree": SEGMENT_TREE,
		"products": _product_names(),
		"call_outcomes": CALL_OUTCOMES,
	}

def label(doctype: str, name: str) -> str:
	"""Customer · product for a lead / deal, never the CRM number when a name is known (SK 26-Oct point 7)."""
	if doctype not in ("CRM Lead", "CRM Deal") or not name or not frappe.db.exists(doctype, name):
		return name or ""
	meta = frappe.get_meta(doctype)
	fields = [f for f in ("organization", "lead_name", "first_name", "sk_customer_name", "sk_product", "sk_segment") if meta.has_field(f)]
	v = frappe.db.get_value(doctype, name, fields, as_dict=True) or {}
	who = v.get("organization") or v.get("sk_customer_name") or v.get("lead_name") or v.get("first_name") or name
	what = v.get("sk_product") or v.get("sk_segment")
	return f"{who} · {what}" if what else who

def follow_up(user: str, for_manager: bool = False) -> list[dict]:
	"""All open leads and deals of the user with their next due action, overdue first.
	for_manager: read for the person's manager (Team Leads), who may not hold CRM rights on others' records."""
	# people outside Sales / Marketing (Accounts, Store, factory ...) have no CRM access: nothing to follow up
	if not installed() or not frappe.has_permission("CRM Lead", "read", user=user):
		return []
	get = frappe.get_all if for_manager else frappe.get_list
	now = now_datetime()
	tasks = _open_tasks_by_doc(user)
	rows = []
	closed_leads = _closed("CRM Lead Status")
	from sk_app.cold_calls import not_cold

	lead_filters = {"lead_owner": user, "converted": 0, **not_cold()}
	if closed_leads:
		lead_filters["status"] = ["not in", closed_leads]
	for r in get("CRM Lead", filters=lead_filters, limit_page_length=0, order_by="modified desc",
			fields=["name", "lead_name", "organization", "status", "mobile_no", "phone", "email", "source",
				"response_by", "first_responded_on", "creation"]):
		task = tasks.get(("CRM Lead", r.name))
		due, why = None, None
		if task and task.due_date:
			due, why = task.due_date, task.title
		elif not r.first_responded_on:
			due, why = r.response_by or add_to_date(r.creation, minutes=5), _("First call")
		rows.append({"doctype": "CRM Lead", "name": r.name, "title": r.organization or r.lead_name or r.name,
			"person": r.lead_name, "status": r.status, "mobile": r.mobile_no or r.phone, "email": r.email,
			"source": r.source, "due": due, "next": why, "new": not r.first_responded_on})
	closed_deals = _closed("CRM Deal Status")
	deal_filters = {"deal_owner": user}
	if closed_deals:
		deal_filters["status"] = ["not in", closed_deals]
	for r in [] if not frappe.has_permission("CRM Deal", "read", user=user) else get("CRM Deal", filters=deal_filters, limit_page_length=0, order_by="modified desc",
			fields=["name", "organization", "lead_name", "status", "mobile_no", "phone", "email", "next_step",
				"expected_closure_date", "deal_value"]):
		task = tasks.get(("CRM Deal", r.name))
		due, why = (task.due_date, task.title) if task and task.due_date else (r.expected_closure_date, r.next_step)
		rows.append({"doctype": "CRM Deal", "name": r.name, "title": r.organization or r.lead_name or r.name,
			"person": r.lead_name, "status": r.status, "mobile": r.mobile_no or r.phone, "email": r.email,
			"due": due, "next": why or r.next_step, "value": r.deal_value, "new": False})
	for dt in CRM_DOCTYPES:
		last = _last_activity(dt, [r["name"] for r in rows if r["doctype"] == dt])
		for r in rows:
			if r["doctype"] == dt and r["name"] in last:
				r["last"] = last[r["name"]]
	for r in rows:
		r["overdue"] = bool(r["due"] and get_datetime(r["due"]) < now)
	far = get_datetime("2999-12-31")
	rows.sort(key=lambda r: (not r["overdue"], not r["new"], get_datetime(r["due"]) if r["due"] else far))
	return rows

def detail(doctype: str, name: str) -> dict:
	_check(doctype, name)
	meta = frappe.get_meta(doctype)
	fields = [f for f in DETAIL_FIELDS[doctype] + ["sk_segment", "sk_product", "sk_cold"] if f == "name" or meta.has_field(f)]
	doc = frappe.db.get_value(doctype, name, fields, as_dict=True)
	ref = {"reference_doctype": doctype, "reference_docname": name}
	deal = None
	if doctype == "CRM Deal":
		deal = doc
	elif doc.get("converted"):
		deal = frappe.db.get_value("CRM Deal", {"lead": name}, ["name", "erpnext_customer"], as_dict=True)
	notes = frappe.get_all("FCRM Note", filters=ref, fields=["title", "content", "owner", "creation"],
		order_by="creation desc", limit=30)
	# CRM comments (design questions, drawing corrections) shown with the notes, newest first
	for c in frappe.get_all("Comment", filters={"reference_doctype": doctype, "reference_name": name, "comment_type": "Comment"},
			fields=["content", "owner", "creation"], order_by="creation desc", limit=30):
		text = strip_html(c.content or "")
		notes.append(frappe._dict(title="💬 " + text[:80], content=text, owner=c.owner, creation=c.creation))
	notes.sort(key=lambda n: n.creation, reverse=True)
	for n in notes:
		n["content"] = strip_html(n.content or "")[:1000]
	field = _design_status_field(doctype)
	if field:
		doc["design_status"] = frappe.db.get_value(doctype, name, field)
	from sk_app import erp_flow, gates

	erp = _erp_docs(deal)
	customer = erp_flow.customer_of(deal["name"]) if deal else None
	from sk_app import view_member

	return {"by_ceo": name in view_member.on_behalf_names(doctype), 
		"gate": _gate(doctype, name),
		"customer": customer and _customer_gaps(customer),
		"doctype": doctype,
		"doc": doc,
		"notes": notes,
		"tasks": frappe.get_all("CRM Task", filters=ref, fields=["name", "title", "status", "due_date", "assigned_to"],
			order_by="due_date asc", limit=30),
		"calls": frappe.get_all("CRM Call Log", filters=ref, fields=["type", "status", "duration", "caller", "creation"],
			order_by="creation desc", limit=30),
		"files": _files(doctype, name) + (_files("CRM Deal", deal["name"]) if deal and doctype == "CRM Lead" else []),
		"deal": deal and deal["name"],
		"products": _products(doctype, name),
		**erp,
		"quote_pending": _quote_pending(deal),
		"crm_url": f"/crm/{'leads' if doctype == 'CRM Lead' else 'deals'}/{name}",
	}

def new_files(user: str, hours: int = 48) -> list[dict]:
	"""Files (drawings, photos, PDFs) others attached to the user's open leads and deals recently."""
	if not installed():
		return []
	names = [(r["doctype"], r["name"], r["title"]) for r in follow_up(user)]
	if not names:
		return []
	titles = {(dt, n): t for dt, n, t in names}
	cutoff = add_to_date(now_datetime(), hours=-hours)
	out = []
	for dt in CRM_DOCTYPES:
		docnames = [n for d, n, _t in names if d == dt]
		if not docnames:
			continue
		for f in frappe.get_all("File", filters={"attached_to_doctype": dt, "attached_to_name": ["in", docnames],
				"owner": ["!=", user], "creation": [">=", cutoff], "is_folder": 0},
				fields=["name", "file_name", "file_url", "attached_to_name", "creation", "owner"], order_by="creation desc", limit=20):
			out.append(frappe._dict({**f, "doctype": dt, "title": titles[(dt, f.attached_to_name)]}))
	return out

def files_to_send(user: str, hours: int = 48) -> list[dict]:
	"""Customer PDFs (e.g. the AI's customer drawing) newly attached to the user's leads / deals and not yet sent."""
	sent = _sent_files(user)
	return [f for f in new_files(user, hours) if _for_customer(f.file_name) and f.name not in sent]

def on_file_attached(doc, method=None):
	"""A customer PDF (e.g. the AI's drawing) was attached to a lead / deal: alert its owner at once, not at the next hourly card."""
	if doc.attached_to_doctype not in CRM_DOCTYPES or not doc.attached_to_name or not _for_customer(doc.file_name):
		return
	field = "lead_owner" if doc.attached_to_doctype == "CRM Lead" else "deal_owner"
	owner = frappe.db.get_value(doc.attached_to_doctype, doc.attached_to_name, field)
	if owner and owner != doc.owner and frappe.db.exists("SK App User", {"user": owner, "enabled": 1}):
		frappe.enqueue("sk_app.writers.lead.alert_owner", user=owner, enqueue_after_commit=True, queue="short")

def own_file_content(user: str, file_url: str) -> tuple[bytes, str]:
	"""Bytes and media type of an image the user just uploaded (for Claude to read a visiting card)."""
	name = frappe.db.get_value("File", {"file_url": file_url, "owner": user})
	if not name:
		frappe.throw(_("File not found"), frappe.PermissionError)
	ext = file_url.rsplit(".", 1)[-1].lower()
	media = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp", "gif": "image/gif"}.get(ext)
	if not media:
		frappe.throw(_("Please send a photo (JPG or PNG)"))
	content = frappe.get_doc("File", name).get_content()
	if len(content) > 5 * 1024 * 1024:
		frappe.throw(_("Photo is too large (max 5 MB)"))
	return content, media

def share_link(doctype: str, name: str) -> dict:
	"""Absolute PDF link a customer can open without login (Frappe Document Share Key, valid 30 days)."""
	if doctype not in PDF_DOCTYPES:
		frappe.throw(_("Only Quotation and Sales Order PDFs can be sent"))
	if not frappe.has_permission(doctype, "read", name):
		frappe.throw(_("No access to {0}").format(name), frappe.PermissionError)
	doc = frappe.get_doc(doctype, name)
	key = doc.get_document_share_key(expires_on=frappe.utils.add_days(frappe.utils.today(), SHARE_DAYS))
	url = frappe.utils.get_url(f"{_pdf(doctype, name)}&key={key}")
	party = doc.get("customer_name") or doc.get("party_name") or doc.get("customer") or ""
	return {"url": url, "file_name": f"{name}.pdf", "pdf": _pdf(doctype, name),
		"message": _("Dear {0}, please find {1} {2} from SK Ind Tech Solutions: {3}").format(party, _(doctype), name, url)}

def deal_customer_name(doc) -> str | None:
	"""The person the salesperson talks to (primary contact, else the lead's name), else the company."""
	contacts = doc.get("contacts") or []
	primary = next((c for c in contacts if c.get("is_primary")), contacts[0] if contacts else None)
	person = (primary and primary.get("full_name")) or " ".join(x for x in (doc.get("first_name"), doc.get("last_name")) if x) \
		or doc.get("lead_name")
	if not person and doc.get("lead"):
		lead = frappe.db.get_value("CRM Lead", doc.lead, ["first_name", "last_name", "lead_name"], as_dict=True) or {}
		person = lead.get("lead_name") or " ".join(x for x in (lead.get("first_name"), lead.get("last_name")) if x)
	return (person or doc.get("organization") or "").strip()[:140] or None

def set_deal_customer(doc, method=None):
	if doc.meta.has_field(CUSTOMER_FIELD):
		doc.set(CUSTOMER_FIELD, deal_customer_name(doc))
	# SK 14-Nov (PR G): a deal of an existing customer keeps that customer (from its own link or its lead's), so the
	# quote / order go on the old ERPNext customer and no second one is made
	from sk_app.gates import CUSTOMER_LINK

	if doc.meta.has_field("erpnext_customer") and not doc.get("erpnext_customer"):
		cust = doc.get(CUSTOMER_LINK) if doc.meta.has_field(CUSTOMER_LINK) else None
		if not cust and doc.get("lead") and frappe.get_meta("CRM Lead").has_field(CUSTOMER_LINK):
			cust = frappe.db.get_value("CRM Lead", doc.lead, CUSTOMER_LINK)
		if cust and frappe.db.exists("Customer", cust):
			doc.erpnext_customer = cust
			if doc.meta.has_field(CUSTOMER_LINK):
				doc.set(CUSTOMER_LINK, cust)


# ---------- Plan A (SK 9-Nov): moved here unchanged from erp_flow.py ----------
from frappe.utils import flt, getdate
from sk_app import store
import frappe


def orders_to_plan(user: str) -> list[dict]:
	"""For Production: confirmed orders whose items have no Work Order yet, with the BOM that will be used."""
	from sk_app.store import need

	need(user, "Production", "Management")
	out = []
	wo_projects = set(frappe.get_all("Work Order", filters={"docstatus": ["<", 2], "project": ["is", "set"]}, pluck="project"))
	for so in frappe.get_all("Sales Order", filters={"docstatus": 1, "status": ["not in", ["Closed", "Completed", "On Hold"]]},
			fields=["name", "customer_name", "delivery_date", "base_net_total", "project"], order_by="delivery_date asc", limit=0):
		if so.project and so.project in wo_projects:  # cabin already started through its Project (SK 29-Oct)
			continue
		for it in frappe.get_all("Sales Order Item", filters={"parent": so.name}, fields=["name", "item_code", "item_name", "qty", "delivery_date"]):
			made = flt(frappe.db.sql("""select sum(qty) from `tabWork Order` where sales_order=%s and sales_order_item=%s and docstatus<2""",
				(so.name, it.name))[0][0])
			if made >= flt(it.qty):
				continue
			bom = frappe.db.get_value("BOM", {"item": it.item_code, "is_default": 1, "is_active": 1, "docstatus": 1})
			out.append({"sales_order": so.name, "so_item": it.name, "customer": so.customer_name, "item_code": it.item_code,
				"item_name": it.item_name, "qty": flt(it.qty) - made, "delivery_date": str(it.delivery_date or so.delivery_date or ""),
				"bom": bom, "late": bool(so.delivery_date and getdate(so.delivery_date) < getdate())})
	return out


# ---------- SK 14-Nov (PR G): New Lead for an existing customer shows the old data while typing ----------
def existing_customers(q: str, n: int = 8) -> list[dict]:
	"""What already exists for the typed text (3+ letters of a company, or a mobile / GSTIN): ERPNext Customers (name,
	mobile, GSTIN), CRM organizations, old CRM Leads and Deals (company, person, mobile, e-mail), best match first, each
	with the data the New Lead form needs: contact person, mobile, e-mail, GSTIN, segment, salesperson, last order /
	activity. Picking one fills the form and links the Customer, so nothing is typed twice and no second customer is made."""
	from sk_app import segments
	from sk_app.writers.lead_rules import customer_match_keys, rank_matches

	q = (q or "").strip()
	if len(q) < 2:
		return []
	like = f"%{q}%"
	digits = customer_match_keys(q, None)["mobile10"] or ("".join(ch for ch in q if ch.isdigit()) if sum(ch.isdigit() for ch in q) >= 6 else "")
	meta = frappe.get_meta("Customer")
	fields = ["name", "customer_name", "customer_group", "modified"] + [f for f in ("gstin", "gst_category", "mobile_no", "email_id") if meta.has_field(f)]
	or_filters = [["customer_name", "like", like]]
	if digits:
		or_filters.append(["mobile_no", "like", f"%{digits}%"])
	if meta.has_field("gstin") and len(q) >= 5:
		or_filters.append(["gstin", "like", f"{q.upper()}%"])
	rows = {c.customer_name: c for c in frappe.get_all("Customer", filters={"disabled": 0}, or_filters=or_filters, fields=fields, limit=40)}
	orgs = {}
	if frappe.db.exists("DocType", "CRM Organization"):
		for o in frappe.get_all("CRM Organization", filters={"organization_name": ["like", like]}, fields=["name", "organization_name"], limit=40):
			orgs[o.organization_name] = o.name
	names = list(rows) + [o for o in orgs if o not in rows]
	# a customer found by its mobile or GSTIN comes first; the rest by how well the name matches
	by_number = [nm for nm in rows if (digits and digits in (rows[nm].get("mobile_no") or "")) or (len(q) >= 5 and (rows[nm].get("gstin") or "").upper().startswith(q.upper()))]
	ranked = by_number + rank_matches(q, names, n)
	out = []
	for name in dict.fromkeys(ranked):
		c = rows.get(name)
		item = {"type": "Customer" if c else "Organization", "record_doctype": "Customer" if c else "CRM Organization", "record": c.name if c else orgs.get(name),
			"customer": c and c.name, "customer_name": name, "organization": orgs.get(name), "gstin": c and c.get("gstin"), "gst_category": c and c.get("gst_category"),
			"segment": c and segments.SEGMENT_OF_GROUP.get(c.customer_group), "mobile": c and c.get("mobile_no"), "email": c and c.get("email_id"),
			"contact": None, "contacts": [], "salesperson": None, "last_order": None, "status": None, "owner": None, "last_activity": c and str(c.modified)[:10]}
		if c:
			links = frappe.get_all("Dynamic Link", filters={"link_doctype": "Customer", "link_name": c.name, "parenttype": "Contact"}, pluck="parent", limit=5)
			for ct in frappe.get_all("Contact", filters={"name": ["in", links or [""]]}, fields=["first_name", "last_name", "mobile_no", "email_id"], order_by="modified desc"):
				person = " ".join(x for x in (ct.first_name, ct.last_name) if x).strip()
				item["contacts"].append({"name": person, "mobile": ct.mobile_no, "email": ct.email_id})
			if item["contacts"]:
				first = item["contacts"][0]
				item["contact"] = first["name"] or None
				item["mobile"] = item["mobile"] or first["mobile"]
				item["email"] = item["email"] or first["email"]
			so = frappe.get_all("Sales Order", filters={"customer": c.name, "docstatus": ["<", 2]}, fields=["name", "transaction_date", "owner"],
				order_by="transaction_date desc", limit=1)
			if so:
				team = frappe.get_all("Sales Team", filters={"parenttype": "Sales Order", "parent": so[0].name}, pluck="sales_person")
				item["salesperson"] = ", ".join(team) or frappe.utils.get_fullname(so[0].owner)
				item["last_order"] = str(so[0].transaction_date)
		out.append(item)
	out += _old_crm_matches(q, like, digits, {o["customer_name"] for o in out}, n)
	return out[:n]


def _old_crm_matches(q: str, like: str, digits: str, seen: set, n: int) -> list[dict]:
	"""Old CRM leads / deals of the same company or mobile (SK's case: lead CRM-LEAD-2026-00639 for Rothe Erde)."""
	from sk_app.writers.lead_rules import rank_matches

	out = []
	for doctype, person_field, owner_field in (("CRM Lead", "first_name", "lead_owner"), ("CRM Deal", "lead_name", "deal_owner")):
		if not frappe.db.exists("DocType", doctype):
			continue
		meta = frappe.get_meta(doctype)
		or_filters = [["organization", "like", like], [person_field, "like", like]]
		if digits:
			or_filters += [["mobile_no", "like", f"%{digits}%"]]
		if "@" in q:
			or_filters.append(["email", "like", like])
		fields = [f for f in ("name", "organization", person_field, "status", owner_field, "mobile_no", "email", "modified", "sk_segment", "sk_customer")
			if f in ("name", "status", "modified") or meta.has_field(f)]
		rows = frappe.get_all(doctype, or_filters=or_filters, fields=fields, order_by="modified desc", limit=20)
		labels = {f"{r.get('organization') or r.get(person_field) or r.name}": r for r in rows}
		order = rank_matches(q, list(labels), n) if not digits else list(labels)
		for label in order:
			r = labels[label]
			if r.get("organization") in seen:
				continue
			out.append({"type": "Lead" if doctype == "CRM Lead" else "Deal", "record_doctype": doctype, "record": r.name, "customer": r.get("sk_customer"),
				"customer_name": r.get("organization") or label, "organization": None, "gstin": None, "gst_category": None, "segment": r.get("sk_segment"),
				"mobile": r.get("mobile_no"), "email": r.get("email"), "contact": r.get(person_field) if r.get("organization") else None, "contacts": [],
				"salesperson": None, "last_order": None, "status": r.get("status"), "owner": frappe.utils.get_fullname(r.get(owner_field)) if r.get(owner_field) else None,
				"last_activity": str(r.modified)[:10]})
	return out[:n]
