"""Pure rules of the one Stock Entry writer (Flow 4 Store: material given to a job)."""

TO_JOB = "Material Transfer for Manufacture"


def issue_rows(items: list[dict], source: dict, fallback: str | None, wip: str, card_rows: dict) -> tuple[list[dict], bool]:
	"""Rows of the issue: from the job's source store for the item (else the fallback) to the job's WIP store. Rows tie
	to the job card's material rows only when every item is on the card (ERPNext 16, SK 27-Oct); else to the job only."""
	use_card = bool(card_rows) and all(i["item_code"] in card_rows for i in items)
	rows = [{"item_code": i["item_code"], "qty": float(i["qty"]), "s_warehouse": i.get("warehouse") or source.get(i["item_code"]) or fallback,
		"t_warehouse": wip, **({"job_card_item": card_rows[i["item_code"]]} if use_card else {})} for i in items]
	return rows, use_card


def problems(purpose: str, rows: list[dict], work_order: str | None, remarks: str | None) -> list:
	"""Every issue to a job names the job, every line has item, qty and both stores, and says who took it."""
	out = []
	if not rows or any(not r.get("item_code") or float(r.get("qty") or 0) <= 0 for r in rows):
		out.append(("issue_no_items", "Every line needs an item and a quantity"))
	if purpose == TO_JOB and not work_order:
		out.append(("issue_no_job", "Material given to a job without the job (Work Order)"))
	if purpose in (TO_JOB, "Material Transfer") and any(not r.get("s_warehouse") or not r.get("t_warehouse") for r in rows):
		out.append(("issue_no_store", "A line has no from / to store"))
	if purpose == TO_JOB and not (remarks or "").strip():
		out.append(("issue_no_taker", "The issue does not say who took the material"))
	return out
