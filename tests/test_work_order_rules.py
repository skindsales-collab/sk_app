"""Flow 5 Production: order line -> work order -> stage cards -> finished stock."""

from sk_app.writers.work_order_rules import all_done, card_problems, finish_qty, wo_problems


def keys(found):
	return [k for k, _w in found]


def test_work_order_needs_bom_order_qty_date():
	assert wo_problems("CAB-10x10", "BOM-CAB-10x10-001", 1, "SAL-ORD-2026-00130", None, "2026-11-20", False) == []
	# the order still a draft: the cabin's project is enough (SK 29-Oct)
	assert wo_problems("CAB-10x10", "BOM-1", 1, None, "PROJ-0101", "2026-11-20", False) == []
	assert keys(wo_problems(None, None, 0, None, None, None, True)) == ["wo_no_item", "wo_no_bom", "wo_no_qty", "wo_no_order",
		"wo_no_delivery_date", "wo_non_cabin"]


def test_stage_card_needs_station_and_done_photo():
	assert card_problems("MFG-WO-2026-00010", "Fabrication", "Fabrication - Ranjit", "Work In Progress", 0) == []
	assert card_problems("MFG-WO-2026-00010", "Fabrication", "Fabrication - Ranjit", "Completed", 2) == []
	assert keys(card_problems("MFG-WO-2026-00010", "Fabrication", "Fabrication - Ranjit", "Completed", 0)) == ["jc_done_no_photo"]
	assert keys(card_problems(None, None, None, "Open", 0)) == ["jc_no_work_order", "jc_no_operation", "jc_no_workstation"]


def test_cabin_finished_when_every_stage_done():
	done = {"status": "Completed", "docstatus": 1, "completed_qty": 1}
	open_ = {"status": "Open", "docstatus": 0, "completed_qty": 0}
	assert all_done([done, done])
	assert all_done([done, {"status": "Work In Progress", "docstatus": 0, "completed_qty": 1}])  # qty entered counts as done
	assert not all_done([done, open_])
	assert not all_done([])
	assert finish_qty(2, 0) == 2 and finish_qty(1, 1) == 0 and finish_qty(1, 3) == 0
