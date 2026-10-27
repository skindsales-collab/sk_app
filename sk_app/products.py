"""Company products and services in every relevant place (change list point 8, SK 26-Oct-2026).

One product card per product / service, kept in ERPNext as SK Library Item (category Product) linked to its Item Group
and segment. Change it once and it changes everywhere: Company & Products, New Lead (pick the product), the lead /
deal page ("Products for this customer", one-tap share), and the complaint form. The internal part (price range,
delivery time, competitor notes) is shown to staff only and never put in a message to a customer. Item Groups without
a card yet still show by name, so the list is complete from day one; SK / Sales add photos, sizes and brochures.
"""

import frappe

from sk_app import segments

NON_CABIN_GROUPS = ("machine shifting", "general engineering", "job work", "maintenance", "transport")
SKIP_GROUPS = ("all item groups", "raw material", "consumable", "sub assemblies", "services", "products")


def main_of_group(group: str) -> str:
	return segments.NON_CABIN if any(w in (group or "").lower() for w in NON_CABIN_GROUPS) else segments.CABIN


def ensure_fields():
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	if frappe.db.exists("DocType", "CRM Lead"):
		field = {"fieldname": "sk_product", "label": "Product asked", "fieldtype": "Data", "insert_after": "sk_main_segment"}
		create_custom_fields({"CRM Lead": [field], "CRM Deal": [field]}, update=True)


def _photos(names: list[str]) -> dict:
	out = {}
	for f in frappe.get_all("File", filters={"attached_to_doctype": "SK Library Item", "attached_to_name": ["in", names or [""]]},
			fields=["attached_to_name", "file_url", "file_name"], order_by="creation asc"):
		if (f.file_name or "").lower().rsplit(".", 1)[-1] in ("jpg", "jpeg", "png", "webp"):
			out.setdefault(f.attached_to_name, []).append(f.file_url)
	return out


CARD_FIELDS = ["name", "title", "title_marathi", "item_group", "product", "text", "text_marathi", "sizes", "file", "link",
	"video_link", "internal_notes", "sequence"]


def catalogue(user: str | None = None, main: str | None = None) -> dict:
	"""{Cabin: [cards], Non-Cabin: [cards]}: every product card, then Item Groups that have no card yet."""
	cards = frappe.get_all("SK Library Item", filters={"enabled": 1, "category": "Product"}, fields=CARD_FIELDS,
		order_by="sequence asc, title asc", limit=0)
	photos = _photos([c.name for c in cards])
	have = {c.item_group for c in cards if c.item_group}
	out = {segments.CABIN: [], segments.NON_CABIN: []}
	for c in cards:
		c["photos"] = photos.get(c.name, [])
		c["main"] = main_of_group(c.item_group or c.title) if c.item_group else (segments.main_of(c.product) or segments.CABIN)
		c["ready"] = True
		out[c["main"]].append(c)
	for g in frappe.get_all("Item Group", filters={"is_group": 0}, pluck="name", order_by="name asc"):
		if g in have or any(g.lower().startswith(s) for s in SKIP_GROUPS):
			continue
		out[main_of_group(g)].append({"name": None, "title": g, "item_group": g, "ready": False, "photos": [], "main": main_of_group(g)})
	if main in out:
		return {main: out[main]}
	return out


def for_record(doctype: str, name: str) -> list[dict]:
	"""Cards for a lead / deal: the product asked first, then others of the same segment."""
	meta = frappe.get_meta(doctype)
	asked = frappe.db.get_value(doctype, name, "sk_product") if meta.has_field("sk_product") else None
	seg = frappe.db.get_value(doctype, name, "sk_segment") if meta.has_field("sk_segment") else None
	main = segments.main_of(seg) or segments.CABIN
	cards = [c for c in catalogue(main=main)[main] if c["ready"]]
	cards.sort(key=lambda c: (0 if asked and asked in (c["title"], c.get("item_group")) else 1, c.get("sequence") or 0))
	return [{k: c.get(k) for k in ("name", "title", "title_marathi", "text", "text_marathi", "sizes", "file", "link", "video_link", "photos")}
		for c in cards[:8]]


def names_for(main: str | None = None) -> list[str]:
	"""Product names for the New Lead / complaint pickers."""
	cat = catalogue(main=main if main in segments.TREE else None)
	return [c["title"] for rows in cat.values() for c in rows]
