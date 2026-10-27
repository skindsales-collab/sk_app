"""SK 27-Oct: Shraddha takes a photo of a bill / e-invoice (and of every other entry) and submits; a supplier bill then
follows Bills to Post (Make bill), the others wait as her photo entries with the ERPNext entry to make."""

import frappe
from frappe.tests import IntegrationTestCase

from sk_app import finance
from sk_app.tests import test_finance as tf
from sk_app.tests.test_store_purchase import SUPPLIER, run


class TestPhotoEntry(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		tf.TestFinance.setUpClass.__func__(tf.TestFinance)
		frappe.db.commit()

	def _photo(self, name):
		f = frappe.get_doc({"doctype": "File", "file_name": name, "content": b"bill photo test", "is_private": 1}).insert(ignore_permissions=True)
		frappe.db.set_value("File", f.name, "owner", tf.ACC)
		return f.file_url

	def test_supplier_bill_photo_goes_to_bills_to_post(self):
		run(tf.ACC, finance.photo_entry, "supplier_bill", self._photo("einv-1.txt"), SUPPLIER, None, 1180, "EI-77")
		b = run(tf.ACC, finance.bills_to_post)
		row = next(p for p in b["photos"] if p["reference_name"] == SUPPLIER and "EI-77" in p["description"])
		self.assertTrue(row["photo"])
		with self.assertRaises(frappe.ValidationError):
			run(tf.ACC, finance.photo_entry, "supplier_bill", self._photo("einv-2.txt"), None)

	def test_other_entries_wait_with_erpnext_link(self):
		r = run(tf.ACC, finance.photo_entry, "money_in", self._photo("utr-1.txt"), None, "Test Customer", 50000, "UTR123")
		rows = run(tf.ACC, finance.photo_entries)
		row = next(x for x in rows if x["name"] == r["todo"])
		self.assertEqual(row["kind"], "money_in")
		self.assertIn("payment_type=Receive", row["erp_url"])
		self.assertIn("UTR123", row["text"])
		self.assertTrue(row["photo"])
		run(tf.ACC, finance.done_bill_photo, r["todo"])
		self.assertNotIn(r["todo"], [x["name"] for x in run(tf.ACC, finance.photo_entries)])
		with self.assertRaises(frappe.ValidationError):
			run(tf.ACC, finance.photo_entry, "money_in", None)
