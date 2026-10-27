"""SK 27-Oct (Yogesh): material came without a PO, so the bill could not be made; and the job card picker showed only
the number, not the customer and cabin size."""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import nowdate

from sk_app import finance, store
from sk_app.tests import test_finance as tf
from sk_app.tests.test_store_purchase import RAW, STORE_U, SUPPLIER, run


class TestBillNoPo(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		tf.TestFinance.setUpClass.__func__(tf.TestFinance)
		frappe.db.commit()

	def _photo_task(self):
		todo = frappe.get_doc({"doctype": "ToDo", "allocated_to": tf.ACC, "reference_type": "Supplier", "reference_name": SUPPLIER,
			"description": "Supplier bill from test (no PO)"}).insert(ignore_permissions=True)
		return todo.name

	def test_bill_from_receipt_without_po(self):
		pr = run(STORE_U, store.receive, None, [{"item_code": RAW, "qty": 3}], supplier=SUPPLIER, reason="urgent local buy", bill_no="LB-9")
		doc = frappe.get_doc("Purchase Receipt", pr["name"])
		self.assertEqual(doc.supplier_delivery_note, "LB-9")
		doc.items[0].rate = 120
		doc.flags.ignore_permissions = True
		doc.save()
		doc.submit()
		todo = self._photo_task()
		b = run(tf.ACC, finance.bills_to_post)
		photo = next(p for p in b["photos"] if p["name"] == todo)
		self.assertIn(doc.name, [x["name"] for x in photo["receipts"]])
		r = run(tf.ACC, finance.make_bill, None, "LB-9", nowdate(), todo, None, doc.name)
		pi = frappe.get_doc("Purchase Invoice", r["name"])
		self.assertEqual((pi.items[0].purchase_receipt, pi.items[0].qty, pi.bill_no), (doc.name, 3, "LB-9"))

	def test_bill_typed_without_po_or_receipt(self):
		todo = self._photo_task()
		r = run(tf.ACC, finance.make_bill, None, "TY-1", nowdate(), todo, None, None, [{"item_code": RAW, "qty": 2, "rate": 250}, {"item_code": "", "qty": 1}])
		pi = frappe.get_doc("Purchase Invoice", r["name"])
		self.assertEqual((pi.supplier, len(pi.items), pi.net_total, pi.docstatus), (SUPPLIER, 1, 500, 0))
		with self.assertRaises(frappe.ValidationError):
			run(tf.ACC, finance.make_bill, None, "TY-2", nowdate(), self._photo_task(), None, None, [])

	def test_cabin_size_label(self):
		self.assertEqual(store.cabin_size("Prod-0013-12ft x 10ft x 8.6ft"), "12ft x 10ft x 8.6ft")
		self.assertEqual(store.cabin_size("Prod-0009-30ft x 10ft"), "30ft x 10ft")
		self.assertEqual(store.cabin_size("Paint"), "Paint")
		self.assertEqual(store.job_card_cabin(None), "")
