"""Pure rules of the one Purchase Order writer (Flow 3 Purchase: requisition -> CEO approval -> PO -> receipt)."""


def ceo_reason(rows_without_request: int, approved_value: float, net_total: float, grand_total: float, limit: float) -> str | None:
	"""Why a PO waits for the CEO, else None (SK 28-Oct option 1: only when over 10% above the approved value)."""
	if rows_without_request:
		return "no approved requisition for some items"
	if approved_value <= 0:
		return "no estimate on the requisition" if grand_total > limit else None
	if net_total > approved_value * 1.10:
		return f"{round((net_total / approved_value - 1) * 100)}% above the approved value"
	return None


def problems(items: list[dict], supplier: str | None, schedule_date, is_ceo: bool) -> list:
	"""items: [{item_code, qty, rate, material_request, approved}]. Every PO names its supplier and delivery date, every
	line has qty and rate, and (unless the CEO makes it) every line comes from a CEO-approved requisition."""
	out = []
	if not supplier:
		out.append(("po_no_supplier", "The purchase order has no supplier"))
	if not schedule_date:
		out.append(("po_no_date", "The purchase order has no required-by date"))
	if not items or any(not i.get("item_code") or float(i.get("qty") or 0) <= 0 for i in items):
		out.append(("po_no_items", "Every line needs an item and a quantity"))
	if any(float(i.get("rate") or 0) <= 0 for i in items):
		out.append(("po_zero_rate", "A line has no rate"))
	missing = sorted({i["item_code"] for i in items if i.get("item_code") and not (i.get("material_request") and i.get("approved"))})
	if missing and not is_ceo:
		out.append(("po_without_request", "No CEO-approved requisition for: " + ", ".join(missing)))
	return out
