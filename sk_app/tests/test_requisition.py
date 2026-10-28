"""SK 27-Oct purchase flow: requisition (Planned / Urgent) → CEO approval → PO from it → receipt against the PO."""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import flt

from sk_app import purchase, requisition, store
from sk_app.tests.test_store_purchase import BOSS, BUY_U, RAW, STORE_U, SUPPLIER, run, setup_data


class TestRequisition(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		setup_data(cls)  # same users, item, supplier and stock

	def test_form_info_and_cabin_list(self):
		info = run(STORE_U, requisition.item_info, RAW)
		self.assertGreaterEqual(info["stock"], 1)
		self.assertIn("min_order_qty", info)
		self.assertIsInstance(run(BUY_U, requisition.cabins), list)

	def test_requisition_waits_for_ceo_then_po_and_receipt(self):
		r = run(STORE_U, requisition.raise_request, [{"item_code": RAW, "qty": 6}], "Urgent", cabin="CAB-7", note="roof job")
		mr = frappe.get_doc("Material Request", r["name"])
		self.assertEqual((mr.docstatus, mr.sk_approval, mr.sk_priority, mr.sk_cabin), (0, "Waiting CEO", "Urgent", "CAB-7"))
		self.assertTrue(frappe.db.exists("ToDo", {"allocated_to": BOSS, "reference_name": mr.name, "status": "Open"}))
		# nobody else can submit it in ERPNext
		mr.flags.ignore_permissions = True
		with self.assertRaises(frappe.ValidationError), frappe.tests.classes.context_managers.set_user(BUY_U):
			mr.submit()
		row = next(x for x in run(BOSS, requisition.to_approve) if x["name"] == mr.name)
		self.assertIn("quotes", row["items"][0])  # urgent: second quote / last rate shown
		self.assertEqual([t["stage"] for t in run(STORE_U, requisition.track) if t["name"] == mr.name], ["waiting_ceo"])
		run(BOSS, requisition.decide, mr.name, 1)
		self.assertEqual(frappe.db.get_value("Material Request", mr.name, ["docstatus", "sk_approval"]), (1, "Approved"))
		est = flt(frappe.db.get_value("Material Request Item", {"parent": mr.name}, "rate")) or 100
		po = run(BUY_U, requisition.po_from_request, mr.name, SUPPLIER, {RAW: est})
		self.assertFalse(po["needs_approval"], po)
		self.assertTrue(po["posted"], frappe.get_all("Comment", filters={"reference_name": po["name"]}, pluck="content"))
		self.assertEqual(frappe.db.get_value("Purchase Order Item", {"parent": po["name"]}, "material_request"), mr.name)
		self.assertEqual([t["stage"] for t in run(STORE_U, requisition.track) if t["name"] == mr.name], ["po_made"])
		pos = run(STORE_U, store.open_purchase_orders)
		mine = next(p for p in pos if p["name"] == po["name"])
		pr = run(STORE_U, store.receive, po["name"], [{"po_detail": mine["items"][0]["name"], "qty": 6}])
		self.assertTrue(run(STORE_U, store.post_receipt, pr["name"])["posted"])

	def test_po_far_above_approved_value_goes_back_to_ceo(self):
		r = run(STORE_U, requisition.raise_request, [{"item_code": RAW, "qty": 2}], "Planned")
		run(BOSS, requisition.decide, r["name"], 1)
		est = flt(frappe.db.get_value("Material Request Item", {"parent": r["name"]}, "rate")) or 100
		po = run(BUY_U, requisition.po_from_request, r["name"], SUPPLIER, {RAW: est * 2 + 50})
		self.assertTrue(po["needs_approval"])
		self.assertTrue(any(p.name == po["name"] for p in run(BOSS, purchase.approvals)))

	def test_no_po_without_requisition_and_no_receipt_without_po(self):
		q = run(BUY_U, purchase.add_quote, SUPPLIER, "SK Test Cabin 10x8", 1, 50)
		self.assertRaises(frappe.ValidationError, run, BUY_U, purchase.make_po, q["name"])
		self.assertRaises(frappe.ValidationError, run, STORE_U, store.receive, None, [{"item_code": RAW, "qty": 1}], supplier=SUPPLIER, reason="came")

	def test_came_without_po_and_reject(self):
		self.assertRaises(frappe.ValidationError, run, STORE_U, requisition.raise_request, [{"item_code": RAW, "qty": 1}], without_po=1)
		r = run(STORE_U, requisition.raise_request, [{"item_code": RAW, "qty": 3}], "Planned", without_po=1, supplier=SUPPLIER, bill_no="CH-9")
		mr = frappe.get_doc("Material Request", r["name"])
		self.assertEqual((mr.sk_priority, mr.sk_without_po, mr.sk_supplier), ("Urgent", 1, SUPPLIER))
		row = next(x for x in run(BOSS, requisition.to_approve) if x["name"] == mr.name)
		self.assertEqual(row["sk_supplier"], SUPPLIER)
		self.assertRaises(frappe.ValidationError, run, BOSS, requisition.decide, mr.name, 0)  # reason needed
		run(BOSS, requisition.decide, mr.name, 0, "buy from regular vendor")
		self.assertEqual(frappe.db.get_value("Material Request", mr.name, ["docstatus", "sk_approval"]), (0, "Rejected"))
		self.assertTrue(frappe.db.exists("ToDo", {"allocated_to": STORE_U, "reference_name": mr.name}))

	def test_only_raisers_and_ceo(self):
		self.assertRaises(frappe.PermissionError, run, BUY_U, requisition.to_approve)
		self.assertRaises(frappe.PermissionError, run, BUY_U, requisition.decide, "x", 1)
