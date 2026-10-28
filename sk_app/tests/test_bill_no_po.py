"""SK 27-Oct (Yogesh): bills from the store's receipt; and the job card picker showed only the number, not the customer
and cabin size. Since SK's purchase flow (27-Oct evening) there is no receipt or bill without a PO: material without a PO
goes through an urgent requisition → CEO → PO first."""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import nowdate

from sk_app import finance, purchase, requisition, store
from sk_app.tests import test_finance as tf
from sk_app.tests.test_store_purchase import BOSS, BUY_U, RAW, STORE_U, SUPPLIER, run, setup_data


class TestBillNoPo(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		tf.TestFinance.setUpClass.__func__(tf.TestFinance)
		setup_data(cls)
		frappe.db.commit()

	def _receipt(self, qty, rate=120, bill_no=None):
		"""Material came without PO → urgent requisition → CEO → PO → received against it."""
		r = run(STORE_U, requisition.raise_request, [{"item_code": RAW, "qty": qty}], without_po=1, supplier=SUPPLIER, bill_no=bill_no)
		run(BOSS, requisition.decide, r["name"], 1)
		po = run(BUY_U, requisition.po_from_request, r["name"], SUPPLIER, {RAW: rate})
		if po["needs_approval"]:
			run(BOSS, purchase.decide, po["name"], True)
		item = frappe.db.get_value("Purchase Order Item", {"parent": po["name"]}, "name")
		return run(STORE_U, store.receive, po["name"], [{"po_detail": item, "qty": qty}], bill_no=bill_no)

	def _photo_task(self):
		todo = frappe.get_doc({"doctype": "ToDo", "allocated_to": tf.ACC, "reference_type": "Supplier", "reference_name": SUPPLIER,
			"description": "Supplier bill from test (no PO)"}).insert(ignore_permissions=True)
		return todo.name

	def test_bill_from_receipt(self):
		pr = self._receipt(3, bill_no="LB-9")
		doc = frappe.get_doc("Purchase Receipt", pr["name"])
		self.assertEqual(doc.supplier_delivery_note, "LB-9")
		self.assertEqual((doc.owner, doc.modified_by), (STORE_U, STORE_U))  # saved by the system, kept in Yogesh's name
		self.assertTrue(run(STORE_U, store.post_receipt, doc.name)["posted"])
		todo = self._photo_task()
		b = run(tf.ACC, finance.bills_to_post)
		photo = next(p for p in b["photos"] if p["name"] == todo)
		self.assertIn(doc.name, [x["name"] for x in photo["receipts"]])
		r = run(tf.ACC, finance.make_bill, None, "LB-9", nowdate(), todo, None, doc.name)
		pi = frappe.get_doc("Purchase Invoice", r["name"])
		self.assertEqual((pi.items[0].purchase_receipt, pi.items[0].qty, pi.bill_no), (doc.name, 3, "LB-9"))

	def test_no_receipt_or_bill_without_po(self):
		self.assertRaises(frappe.ValidationError, run, STORE_U, store.receive, None, [{"item_code": RAW, "qty": 3}], supplier=SUPPLIER, reason="x")
		with self.assertRaises(frappe.ValidationError):
			run(tf.ACC, finance.make_bill, None, "TY-1", nowdate(), self._photo_task(), None, None, [{"item_code": RAW, "qty": 2, "rate": 250}])

	def test_cabin_size_label(self):
		self.assertEqual(store.cabin_size("Prod-0013-12ft x 10ft x 8.6ft"), "12ft x 10ft x 8.6ft")
		self.assertEqual(store.cabin_size("Prod-0009-30ft x 10ft"), "30ft x 10ft")
		self.assertEqual(store.cabin_size("Paint"), "Paint")
		self.assertEqual(store.job_card_cabin(None), "")

	def test_store_posts_its_receipt(self):
		"""SK 27-Oct: Yogesh's receipt stayed a draft (no stock); Store checks and posts it in the app."""
		pr = self._receipt(2, rate=150)
		self.assertIn(pr["name"], [r["name"] for r in run(STORE_U, store.receipts_to_post)])
		r = run(STORE_U, store.post_receipt, pr["name"])
		self.assertTrue(r["posted"], r.get("reason"))
		doc = frappe.get_doc("Purchase Receipt", pr["name"])
		self.assertEqual((doc.docstatus, doc.items[0].rate, doc.owner), (1, 150, STORE_U))
		extra = self._receipt(2, rate=150)
		run(STORE_U, store.drop_receipt, extra["name"])
		self.assertFalse(frappe.db.exists("Purchase Receipt", extra["name"]))
		with self.assertRaises(frappe.ValidationError):
			run(STORE_U, store.drop_receipt, pr["name"])
