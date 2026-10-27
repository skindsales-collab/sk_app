"""Company & Products library, customer FAQ, message templates and the Sales Manual on the phone.

Kept light for the phone: lists carry only titles and short text; a file opens only when tapped, and a section of
the big Sales Manual PDF is cut out on the server (only its pages are sent) and cached."""

import io
import json
import re

import frappe
from frappe import _
from frappe.utils import cint

LIST_FIELDS = ["name", "title", "title_marathi", "category", "product", "audience", "file", "link", "page_from", "page_to",
	"text", "text_marathi", "sequence"]
SECTION_CACHE_SECONDS = 24 * 60 * 60


def items(function: str, category: str | None = None) -> list[dict]:
	filters = {"enabled": 1, "function": ["in", ["All", function or "All"]]}
	if category:
		filters["category"] = category
	rows = frappe.get_all("SK Library Item", filters=filters, fields=LIST_FIELDS, order_by="category asc, sequence asc, title asc",
		limit=0)
	for r in rows:
		r["kind"] = "pages" if r.page_from else "file" if r.file else "link" if r.link else "text"
		r["open_url"] = (f"/api/method/sk_app.api.library_pdf?item={r.name}" if r.kind == "pages"
			else r.file if r.kind == "file" else r.link)
		r["sendable"] = r.audience == "Customer"
	return rows


def _manual_bytes(item) -> bytes:
	file_url = item.file or frappe.db.get_single_value("SK App Settings", "sales_manual")
	if not file_url:
		frappe.throw(_("The Sales Manual PDF is not uploaded yet (SK App Settings)."))
	name = frappe.db.get_value("File", {"file_url": file_url})
	if not name:
		frappe.throw(_("Manual file not found"))
	with open(frappe.get_doc("File", name).get_full_path(), "rb") as f:  # raw bytes: get_content() may decode to text
		return f.read()


_NAME = rb"/([^\s/\[\]()<>{}%]+)"
_DRAW_OPS = {"/XObject": _NAME + rb"\s+Do\b", "/Font": _NAME + rb"\s+[-\d.]+\s+Tf\b", "/ExtGState": _NAME + rb"\s+gs\b",
	"/Shading": _NAME + rb"\s+sh\b", "/Pattern": _NAME + rb"\s+(?:cs|CS|scn|SCN)\b"}


def _only_used(res, data: bytes):
	"""A copy of a resource list keeping only the pictures, fonts and styles this content draws with."""
	from pypdf.generic import DictionaryObject, NameObject

	res = res.get_object()
	new = DictionaryObject(dict(res.items()))
	for key, rx in _DRAW_OPS.items():
		if key in res:
			names = {"/" + n.decode("latin-1") for n in re.findall(rx, data)}
			new[NameObject(key)] = DictionaryObject({k: v for k, v in res[key].get_object().items() if k in names})
	return new


def _slim(page, seen: set):
	"""PowerPoint-made PDFs give every page one shared list of all the deck's pictures; without this a 2-page section
	carries the whole manual (4 MB instead of 0.3 MB). The page and each form it draws get only what they use."""
	from pypdf.generic import ArrayObject, DictionaryObject, IndirectObject, NameObject, StreamObject

	content = page.get_contents()
	stack = [(page, content.get_data() if content is not None else b"")]
	while stack:
		obj, data = stack.pop()
		if "/Resources" in obj:
			obj[NameObject("/Resources")] = _only_used(obj["/Resources"], data)
		todo = [v for k, v in obj.items() if k not in ("/Parent", "/Contents")]
		while todo:
			v = todo.pop()
			if isinstance(v, IndirectObject):
				if v.idnum in seen:
					continue
				seen.add(v.idnum)
				v = v.get_object()
				if isinstance(v, StreamObject) and "/Resources" in v:
					stack.append((v, v.get_data()))
					continue
			if isinstance(v, DictionaryObject):
				todo.extend(val for k, val in v.items() if k != "/Parent")
			elif isinstance(v, ArrayObject):
				todo.extend(v)


def section_pdf(item_name: str) -> tuple[bytes, str]:
	"""Only the pages of this library item, cut from the manual PDF (cached for a day)."""
	from pypdf import PdfReader, PdfWriter

	item = frappe.get_doc("SK Library Item", item_name)
	if not item.enabled or not item.page_from:
		frappe.throw(_("Not a manual section"))
	key = f"sk_lib_section:{item.name}:{item.modified}"
	cached = frappe.cache.get_value(key)
	if cached:
		return cached, item.title
	reader = PdfReader(io.BytesIO(_manual_bytes(item)))
	first = max(1, cint(item.page_from))
	last = min(len(reader.pages), cint(item.page_to) or first)
	writer = PdfWriter()
	for n in range(first - 1, last):
		writer.add_page(reader.pages[n])
	seen = set()
	for page in writer.pages:
		_slim(page, seen)
	out = io.BytesIO()
	writer.write(out)
	# the writer still holds the unused pictures; copying the pages once more keeps only what they draw
	final = PdfWriter()
	for page in PdfReader(io.BytesIO(out.getvalue())).pages:
		final.add_page(page)
	final.compress_identical_objects(remove_duplicates=True, remove_unreferenced=True)
	out = io.BytesIO()
	final.write(out)
	data = out.getvalue()
	frappe.cache.set_value(key, data, expires_in_sec=SECTION_CACHE_SECONDS)
	return data, item.title


def make_public(doc, method=None):
	"""Customer items are sent as links the customer opens without login, so their file must be public."""
	if doc.audience != "Customer" or not doc.file or not doc.file.startswith("/private/"):
		return
	name = frappe.db.get_value("File", {"file_url": doc.file})
	if name:
		f = frappe.get_doc("File", name)
		f.is_private = 0
		f.save(ignore_permissions=True)
		doc.file = f.file_url


def load_pack(content: str | bytes) -> dict:
	"""Add or update lessons (with their questions) and library items from a pack file (JSON) made by IT.
	Matching is by title, so loading the same pack again only updates."""
	pack = json.loads(content)
	counts = {"lessons": 0, "library": 0}
	library_names = {}
	for row in pack.get("library", []):
		name = frappe.db.get_value("SK Library Item", {"title": row["title"], "category": row.get("category", "Company")})
		doc = frappe.get_doc("SK Library Item", name) if name else frappe.new_doc("SK Library Item")
		doc.update({k: v for k, v in row.items() if k != "key"})
		doc.save(ignore_permissions=True)
		library_names[row.get("key") or row["title"]] = doc.name
		counts["library"] += 1
	for row in pack.get("lessons", []):
		name = frappe.db.get_value("SK Training Lesson", {"title": row["title"]})
		doc = frappe.get_doc("SK Training Lesson", name) if name else frappe.new_doc("SK Training Lesson")
		questions = row.get("questions", [])
		data = {k: v for k, v in row.items() if k not in ("questions", "library_key")}
		doc.update(data)
		if row.get("library_key") in library_names:
			doc.library_item = library_names[row["library_key"]]
		doc.set("questions", [])
		for q in questions:
			doc.append("questions", q)
		doc.save(ignore_permissions=True)
		counts["lessons"] += 1
	return counts


@frappe.whitelist(methods=["POST"])
def load_pack_now():
	"""Button on SK App Settings: load the attached pack."""
	frappe.only_for(("System Manager", "HR Manager", "Sales Manager"))
	file_url = frappe.db.get_single_value("SK App Settings", "library_pack")
	if not file_url:
		frappe.throw(_("Please attach the pack file first"))
	name = frappe.db.get_value("File", {"file_url": file_url})
	return load_pack(frappe.get_doc("File", name).get_content())
