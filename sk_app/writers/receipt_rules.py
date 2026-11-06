"""Pure rules of the one Purchase Receipt writer (Flow 3 step 4 / Flow 4 Store: material in only against a PO)."""


def received_rows(po_rows: list[dict], got: dict) -> list[dict]:
	"""po_rows: [{name, item_code, qty}] from the PO; got: {po row name or item_code: qty received}. Rows with a
	quantity received, at that quantity (all PO rows when nothing was typed)."""
	out = []
	for r in po_rows:
		q = got.get(r.get("name"), got.get(r.get("item_code"), r.get("qty"))) if got else r.get("qty")
		if float(q or 0) > 0:
			out.append({**r, "qty": float(q)})
	return out


def problems(rows: list[dict], is_return: bool, is_ceo: bool, bill_no: str | None) -> list:
	"""rows: [{item_code, qty, purchase_order}]. Store receives only against a PO (SK 27-Oct), every line has a
	quantity, and the supplier's challan / bill number is on the receipt."""
	out = []
	if not rows or any(float(r.get("qty") or 0) <= 0 for r in rows):
		out.append(("receipt_no_qty", "Every line needs the quantity received"))
	if not is_return and not is_ceo and any(not r.get("purchase_order") for r in rows):
		out.append(("receipt_no_po", "Material received without a Purchase Order: use Came without PO"))
	if not (bill_no or "").strip():
		out.append(("receipt_no_challan", "The supplier's challan / bill number is missing"))
	return out
