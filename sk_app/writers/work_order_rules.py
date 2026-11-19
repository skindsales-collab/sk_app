"""Pure rules of the one Production line (linear flow map, Flow 5): order line -> Work Order -> Job Cards (stages) ->
worker's Done with photo -> finished cabin in stock. Rebuild 7-Nov-2026."""

DONE = ("Completed",)
OPEN_WO = ("Completed", "Stopped", "Closed", "Cancelled")  # work order statuses that are no longer in production


def wo_problems(production_item, bom, qty, sales_order, project, delivery_date, non_cabin: bool) -> list:
	"""Every work order is for a cabin item with a BOM, comes from a customer order (or the cabin's project while the
	order is still a draft, SK 29-Oct), has a quantity and the customer's delivery date."""
	out = []
	if not production_item:
		out.append(("wo_no_item", "The work order has no item"))
	if not bom:
		out.append(("wo_no_bom", "No BOM for this cabin yet: Design must make and submit the BOM first"))
	if float(qty or 0) <= 0:
		out.append(("wo_no_qty", "The work order has no quantity"))
	if not sales_order and not project:
		out.append(("wo_no_order", "The work order is not linked to a customer order or cabin project"))
	if not delivery_date:
		out.append(("wo_no_delivery_date", "The customer's delivery date is missing"))
	if non_cabin:
		out.append(("wo_non_cabin", "A Non-Cabin order (machine shifting, job work) has no factory work order"))
	return out


def card_problems(work_order, operation, workstation, status, photos: int) -> list:
	"""Every stage card names its work order, stage and workstation; a stage marked done carries at least one photo."""
	out = []
	if not work_order:
		out.append(("jc_no_work_order", "The job card has no work order"))
	if not operation:
		out.append(("jc_no_operation", "The job card has no stage (operation)"))
	if not workstation:
		out.append(("jc_no_workstation", "The job card has no workstation (who does it)"))
	if status in DONE and int(photos or 0) <= 0:
		out.append(("jc_done_no_photo", "Stage marked done without a photo"))
	return out


def all_done(cards: list[dict]) -> bool:
	"""cards: [{status, docstatus, completed_qty}] of one work order; the cabin is finished when every stage is done."""
	return bool(cards) and all(c.get("docstatus") == 1 or c.get("status") in DONE or float(c.get("completed_qty") or 0) > 0 for c in cards)


def finish_qty(wo_qty, produced) -> float:
	"""What is still to be booked into finished stock."""
	return max(float(wo_qty or 0) - float(produced or 0), 0)
