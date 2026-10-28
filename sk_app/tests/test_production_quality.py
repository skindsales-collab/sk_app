import frappe
from frappe.tests import IntegrationTestCase

from sk_app import logins, production, quality, sub_bills
from sk_app.tests.test_store_purchase import BOSS, FG, RAW, TestStorePurchase, app_user, run

BOSS_P = "sk_test_babasaheb@example.com"
QC = "sk_test_satish@example.com"
RUSHI = "sk_test_rushi@example.com"
WS = "SK Test Fabrication - Ranjit"
WS2 = "SK Test Painting - Babu"
OPS = ("SK Fabrication", "SK Final Inspection")
CABIN = "SK Test Office Cabin 20x10"
OK = [{"specification": "Length x width", "ok": 1}, {"specification": "Weld visual", "ok": 1}]  # worker's own check sheet


class TestProductionQuality(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		TestStorePurchase.setUpClass.__func__(TestStorePurchase)  # company, items, stock
		cls.company = TestStorePurchase.company
		abbr = frappe.db.get_value("Company", cls.company, "abbr")
		app_user(BOSS_P, "Production", ["Employee"])
		app_user(QC, "Quality", ["Employee"])
		for ws in (WS, WS2):
			if not frappe.db.exists("Workstation", ws):
				frappe.get_doc({"doctype": "Workstation", "workstation_name": ws}).insert()
		for op in OPS:
			if not frappe.db.exists("Operation", op):
				frappe.get_doc({"doctype": "Operation", "name": op, "workstation": WS}).insert()
		# subcontractors: one login per workstation, made the way HR makes it
		cls.ranjit = cls._sub("9876500051", "Ranjit T", WS)
		cls.babu = cls._sub("9876500052", "Babu T", WS2)
		if not frappe.db.exists("Item", CABIN):
			frappe.get_doc({"doctype": "Item", "item_code": CABIN, "item_name": CABIN, "item_group": frappe.db.get_value("Item Group", {"is_group": 0}, "name"),
				"stock_uom": "Nos", "is_stock_item": 1, "valuation_rate": 100}).insert()
		if not frappe.db.exists("BOM", {"item": CABIN, "docstatus": 1}):
			bom = frappe.get_doc({"doctype": "BOM", "item": CABIN, "company": cls.company, "quantity": 1, "with_operations": 1,
				"items": [{"item_code": RAW, "qty": 2, "rate": 100}],
				"operations": [{"operation": OPS[0], "workstation": WS, "time_in_mins": 60, "sequence_id": 1},
					{"operation": OPS[1], "workstation": WS, "time_in_mins": 30, "sequence_id": 2}]})
			bom.insert()
			bom.submit()
		if not frappe.db.exists("Quality Inspection Template", "QIT-OP-SK Fabrication"):
			for p in ("Length x width", "Weld visual"):
				if not frappe.db.exists("Quality Inspection Parameter", p):
					frappe.get_doc({"doctype": "Quality Inspection Parameter", "parameter": p}).insert()
			frappe.get_doc({"doctype": "Quality Inspection Template", "quality_inspection_template_name": "QIT-OP-SK Fabrication",
				"item_quality_inspection_parameter": [{"specification": "Length x width"}, {"specification": "Weld visual"}]}).insert()
		quality.ensure_setup()
		sub_bills.ensure_setup()
		app_user(RUSHI, "Sales", ["Employee"])
		frappe.db.set_single_value("SK App Settings", "sub_bill_checker", RUSHI)
		cls.wip, cls.fgw = f"Work In Progress - {abbr}", f"Finished Goods - {abbr}"
		frappe.db.commit()

	@classmethod
	def _sub(cls, mobile, name, ws):
		u = frappe.db.get_value("User", {"mobile_no": mobile})
		if u:
			return u
		frappe.set_user("Administrator")
		return logins.make_login("Administrator", mobile, ["Subcontractor"], full_name=name, workstation=ws)["user"]

	def _work_order(self):
		wo = frappe.get_doc({"doctype": "Work Order", "production_item": CABIN, "qty": 1, "company": self.company,
			"bom_no": frappe.db.get_value("BOM", {"item": CABIN, "docstatus": 1}), "wip_warehouse": self.wip, "fg_warehouse": self.fgw,
			"source_warehouse": TestStorePurchase.stores})
		wo.get_items_and_operations_from_bom()  # what the Work Order form does when the BOM is picked
		wo.insert()
		wo.submit()
		jcs = frappe.get_all("Job Card", filters={"work_order": wo.name}, pluck="name", order_by="sequence_id asc")
		if not jcs:  # older settings: make job cards the way the Work Order button does
			from erpnext.manufacturing.doctype.work_order.work_order import create_job_card

			for op in wo.operations:
				create_job_card(wo, {"operation": op.operation, "workstation": op.workstation, "for_quantity": wo.qty, "sequence_id": op.sequence_id,
					"row_id": op.name}, auto_create=True)
			jcs = frappe.get_all("Job Card", filters={"work_order": wo.name}, pluck="name", order_by="sequence_id asc")
		return wo, jcs

	def test_subcontractor_sees_only_own_jobs_and_finishes_one(self):
		wo, jcs = self._work_order()
		mine = {j.name for j in run(self.ranjit, production.job_cards)}
		self.assertTrue(set(jcs) <= mine)
		self.assertFalse(set(jcs) & {j.name for j in run(self.babu, production.job_cards)})
		self.assertRaises(frappe.PermissionError, run, self.babu, production.start, jcs[0])
		run(self.ranjit, production.start, jcs[0])
		self.assertEqual(frappe.db.get_value("Job Card", jcs[0], "status"), "Work In Progress")
		r = run(self.ranjit, production.done, jcs[0], [], 4, "Roof ridge purlin one short", OK)
		self.assertEqual(frappe.db.get_value("Job Card", jcs[0], "status"), "Completed")
		self.assertTrue(frappe.db.exists("ToDo", {"allocated_to": QC, "reference_name": jcs[0]}))
		self.assertTrue(frappe.db.exists("Comment", {"reference_name": jcs[0], "content": ["like", "%Workers used: 4%"]}))
		self.assertIn("posted", r)
		board = {w["name"]: w for w in run(BOSS_P, production.order_board)}
		self.assertEqual(board[wo.name]["stages"][0]["state"], "done")
		self.assertTrue(board[wo.name]["no_order"])

	def test_need_material_by_item_or_by_voice(self):
		wo, jcs = self._work_order()
		r = run(self.ranjit, production.need_material, [{"item_code": RAW, "qty": 5}], jcs[0])
		mr = frappe.get_doc("Material Request", r["request"])
		self.assertEqual(mr.work_order, wo.name)
		self.assertEqual(mr.items[0].qty, 5)
		r = run(self.ranjit, production.need_material, [], jcs[0], spoken="ajun 5 C channel pahije")
		self.assertTrue(r["task"])

	def test_stage_check_rejects_and_opens_non_conformance(self):
		wo, jcs = self._work_order()
		run(self.ranjit, production.done, jcs[0], checks=OK)
		p = run(QC, quality.pending)
		self.assertTrue(any(x["reference_name"] == jcs[0] for x in p["stage"]))
		tpl = quality.guess_template("Job Card", OPS[0])
		self.assertEqual(tpl, "QIT-OP-SK Fabrication")
		points = [{"specification": c.specification, "ok": 1} for c in run(QC, quality.checklist, tpl)]
		points[1].update(ok=0)
		self.assertRaises(frappe.ValidationError, run, QC, quality.save, "Job Card", jcs[0], CABIN, points, tpl)
		points[1]["note"] = "porosity at corner"
		r = run(QC, quality.save, "Job Card", jcs[0], CABIN, points, tpl)
		self.assertEqual(r["status"], "Rejected")
		nc = frappe.get_doc("Non Conformance", r["non_conformance"])
		self.assertTrue(frappe.db.exists("ToDo", {"reference_name": nc.name, "allocated_to": self.ranjit, "status": "Open"}))
		self.assertTrue(any(n["name"] == nc.name for n in run(self.ranjit, quality.open_ncs)))
		self.assertFalse(any(n["name"] == nc.name for n in run(self.babu, quality.open_ncs)))
		run(self.ranjit, quality.close_nc, nc.name, "Ground and welded again")
		self.assertEqual(frappe.db.get_value("Non Conformance", nc.name, "status"), "Resolved")
		self.assertFalse(any(x["reference_name"] == jcs[0] for x in run(QC, quality.pending)["stage"]))

	def test_final_stage_goes_to_final_check(self):
		wo, jcs = self._work_order()
		run(self.ranjit, production.done, jcs[1], checks=OK)
		p = run(QC, quality.pending)
		self.assertTrue(any(x["reference_name"] == jcs[1] for x in p["final"]))

	def test_worker_self_check_then_quality_check(self):
		"""SK 28-Oct: no Done without the worker's check sheet; it is a draft on the Job Card, shown to Quality, never a pass."""
		wo, jcs = self._work_order()
		sheet = run(self.ranjit, production._card_for, jcs[0]) and quality.self_sheet(jcs[0])
		self.assertEqual([p.specification for p in sheet["points"]], ["Length x width", "Weld visual"])
		self.assertEqual(len(quality.self_sheet(jcs[1])["points"]), len(quality.SELF_POINTS))  # no template: standard list
		self.assertRaises(frappe.ValidationError, run, self.ranjit, production.done, jcs[0])
		self.assertRaises(frappe.ValidationError, run, self.ranjit, production.done, jcs[0], checks=[{"specification": "Weld visual", "ok": 0}])
		self.assertNotEqual(frappe.db.get_value("Job Card", jcs[0], "status"), "Completed")
		r = run(self.ranjit, production.done, jcs[0], checks=[OK[0], {"specification": "Weld visual", "ok": 0, "note": "one spatter left"}])
		qi = frappe.get_doc("Quality Inspection", r["self_check"])
		self.assertEqual((qi.sk_self_check, qi.docstatus, qi.status, qi.inspected_by), (1, 0, "Rejected", self.ranjit))
		row = next(x for x in run(QC, quality.pending)["stage"] if x["reference_name"] == jcs[0])
		self.assertEqual(row["self_check"]["name"], qi.name)
		self.assertEqual([p.status for p in row["self_check"]["points"]], ["Accepted", "Rejected"])
		self.assertTrue(frappe.db.exists("ToDo", {"allocated_to": QC, "reference_name": jcs[0], "description": ["like", "%1 Not OK%"]}))
		r = run(QC, quality.save, "Job Card", jcs[0], CABIN, OK, "QIT-OP-SK Fabrication")
		self.assertEqual(r["status"], "Accepted")
		self.assertFalse(any(x["reference_name"] == jcs[0] for x in run(QC, quality.pending)["stage"]))
		self.assertEqual(frappe.db.get_value("Quality Inspection", qi.name, "docstatus"), 0)

	def test_others_cannot_use_production(self):
		self.assertRaises(frappe.PermissionError, run, "sk_test_buyer@example.com", production.job_cards)
		self.assertRaises(frappe.PermissionError, run, self.ranjit, quality.pending)

	def test_electrical_points(self):
		"""SK 26-Oct: points done per cabin by type with a photo; total kept on the Job Card's entry; other workstations blocked."""
		ws = "SK Test Electrical - Satish"
		if not frappe.db.exists("Workstation", ws):
			frappe.get_doc({"doctype": "Workstation", "workstation_name": ws}).insert()
		wo, jcs = self._work_order()
		frappe.db.set_value("Job Card", jcs[0], "workstation", ws)
		listed = run(QC, production.el_jobs)
		self.assertIn(jcs[0], [j["name"] for j in listed["jobs"]])
		self.assertNotIn(jcs[1], [j["name"] for j in listed["jobs"]])
		r = run(QC, production.save_el_points, jcs[0], {"light": 6, "fan": 2, "socket_5a": 4, "earthing": 1, "fan_bad": 9})
		self.assertEqual(r["total_points"], 13)
		r = run(QC, production.save_el_points, jcs[0], {"light": 8, "fan": -3})  # same cabin again: corrected, not added
		self.assertEqual(r["total_points"], 8)
		self.assertEqual(frappe.db.count("SK Electrical Points", {"job_card": jcs[0]}), 1)
		self.assertEqual(frappe.db.get_value("SK Electrical Points", {"job_card": jcs[0]}, "work_order"), wo.name)
		self.assertGreaterEqual(run(QC, production.el_jobs)["month_total"], 8)
		with self.assertRaises(frappe.PermissionError):
			run(self.ranjit, production.save_el_points, jcs[0], {"light": 1})

	def _passed_job(self):
		wo, jcs = self._work_order()
		run(self.ranjit, production.done, jcs[0], checks=OK)
		run(QC, quality.save, "Job Card", jcs[0], CABIN, OK, "QIT-OP-SK Fabrication")
		return jcs[0]

	def _rate(self, supplier, value):
		item = sub_bills.service_item(OPS[0])
		frappe.db.delete("Item Price", {"price_list": sub_bills.PRICE_LIST, "item_code": item})
		frappe.get_doc({"doctype": "Item Price", "price_list": sub_bills.PRICE_LIST, "item_code": item, "supplier": supplier,
			"price_list_rate": value}).insert()

	def test_subcontractor_bill_rushi_then_ceo_then_payable(self):
		"""SK 28-Oct: rate sheet x cabin sq ft after Quality passes; Rushi checks, CEO approves, then posted (payable)."""
		sup = sub_bills.supplier_of(WS)
		self.assertEqual(frappe.db.get_value("Supplier", sup, "supplier_name"), "Ranjit T")
		self._rate(sup, 25)
		jc = self._passed_job()
		name = sub_bills.bill_of(jc)
		self.assertTrue(name)
		pi = frappe.get_doc("Purchase Invoice", name)
		self.assertEqual((pi.docstatus, pi.sk_bill_stage, pi.supplier), (0, sub_bills.CHECKER, sup))
		self.assertEqual((pi.items[0].qty, pi.items[0].rate), (200, 25))  # 20x10 cabin
		self.assertEqual(sub_bills.make_bill(jc), name)  # once per job card
		# not posted before approvals, even from ERPNext
		self.assertRaises(frappe.ValidationError, run, self.ranjit, lambda u: sub_bills.check_submit(frappe.get_doc("Purchase Invoice", name)))
		self.assertRaises(frappe.PermissionError, run, BOSS_P, sub_bills.to_approve)
		self.assertIn(name, [b["name"] for b in run(RUSHI, sub_bills.to_approve)])
		self.assertRaises(frappe.PermissionError, run, self.ranjit, sub_bills.decide, name, 1)
		# discussion: the bill waits until the subcontractor answers
		run(RUSHI, sub_bills.discuss, name, "Roof done twice?")
		self.assertTrue(frappe.db.exists("ToDo", {"allocated_to": self.ranjit, "reference_name": name, "status": "Open"}))
		mine = {b["name"]: b for b in run(self.ranjit, sub_bills.my_bills)}
		self.assertEqual(mine[name]["question"], "Roof done twice?")
		self.assertRaises(frappe.ValidationError, run, RUSHI, sub_bills.decide, name, 1)
		run(self.ranjit, sub_bills.reply, name, "No, only once")
		r = run(RUSHI, sub_bills.decide, name, 1)
		self.assertEqual(r["stage"], sub_bills.CEO)
		self.assertRaises(frappe.PermissionError, run, RUSHI, sub_bills.decide, name, 1)
		self.assertTrue(run(BOSS, sub_bills.badges).get("sub_bills"))
		r = run(BOSS, sub_bills.decide, name, 1)
		self.assertEqual(r["stage"], sub_bills.APPROVED)
		self.assertTrue(r["posted"], frappe.get_all("Comment", filters={"reference_name": name}, pluck="content"))
		self.assertEqual(frappe.db.get_value("Purchase Invoice", name, "docstatus"), 1)
		self.assertGreater(frappe.db.get_value("Purchase Invoice", name, "outstanding_amount"), 0)

	def test_subcontractor_bill_reject_and_no_rate(self):
		sup = sub_bills.supplier_of(WS)
		self._rate(sup, 0)
		jc = self._passed_job()
		name = sub_bills.bill_of(jc)
		self.assertRaises(frappe.ValidationError, run, RUSHI, sub_bills.decide, name, 1)  # no rate in the sheet
		self.assertRaises(frappe.ValidationError, run, RUSHI, sub_bills.decide, name, 0)  # reject needs a reason
		run(RUSHI, sub_bills.decide, name, 0, "Job not finished")
		self.assertEqual(frappe.db.get_value("Purchase Invoice", name, "sk_bill_stage"), sub_bills.REJECTED)

	def test_rejected_job_makes_no_bill_and_size_parse(self):
		wo, jcs = self._work_order()
		run(self.ranjit, production.done, jcs[0], checks=OK)
		run(QC, quality.save, "Job Card", jcs[0], CABIN, [OK[0], {"specification": "Weld visual", "ok": 0, "note": "gap"}])
		self.assertFalse(sub_bills.bill_of(jcs[0]))
		self.assertEqual(sub_bills.sqft("ABC · 12ft x 10ft x 8.6ft"), 120)
		self.assertEqual(sub_bills.sqft("no size"), 0)
