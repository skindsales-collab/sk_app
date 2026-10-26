import frappe
from frappe.tests import IntegrationTestCase

from sk_app import logins, production, quality
from sk_app.tests.test_store_purchase import FG, RAW, TestStorePurchase, app_user, run

BOSS_P = "sk_test_babasaheb@example.com"
QC = "sk_test_satish@example.com"
WS = "SK Test Fabrication - Ranjit"
WS2 = "SK Test Painting - Babu"
OPS = ("SK Fabrication", "SK Final Inspection")
CABIN = "SK Test Office Cabin 20x10"


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
		r = run(self.ranjit, production.done, jcs[0], [], 4, "Roof ridge purlin one short")
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
		run(self.ranjit, production.done, jcs[0])
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
		run(self.ranjit, production.done, jcs[1])
		p = run(QC, quality.pending)
		self.assertTrue(any(x["reference_name"] == jcs[1] for x in p["final"]))

	def test_others_cannot_use_production(self):
		self.assertRaises(frappe.PermissionError, run, "sk_test_buyer@example.com", production.job_cards)
		self.assertRaises(frappe.PermissionError, run, self.ranjit, quality.pending)
