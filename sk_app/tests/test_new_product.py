"""SK 27-Oct: Shraddha adds "Cabin 10 x 30 x 8.8, subcontracted to AI Portable Cabin" in one line: the size variant with
the ERPNext name, the vendor matched (spelling forgiven), or the next product number."""

import frappe
from frappe.tests import IntegrationTestCase

from sk_app import new_product
from sk_app.tests import test_finance as tf
from sk_app.tests.test_store_purchase import run

TPL, ATTR, VENDOR = "Prod-0909", "SK Test Office Size", "SK Test Ai Portable Cabin"


class TestNewProduct(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		tf.TestFinance.setUpClass.__func__(tf.TestFinance)
		if not frappe.db.exists("Item Attribute", ATTR):
			frappe.get_doc({"doctype": "Item Attribute", "attribute_name": ATTR, "item_attribute_values": [
				{"attribute_value": f"{ATTR} 20ft x 10ft x 8.6ft", "abbr": "20ft x 10ft x 8.6ft"}]}).insert()
		if not frappe.db.exists("Item", TPL):
			frappe.get_doc({"doctype": "Item", "item_code": TPL, "item_name": "SK Test Office Cabin", "item_group": frappe.db.get_value("Item Group", {"is_group": 0}),
				"stock_uom": "Nos", "has_variants": 1, "attributes": [{"attribute": ATTR}]}).insert()
		if not frappe.db.exists("Supplier", VENDOR):
			frappe.get_doc({"doctype": "Supplier", "supplier_name": VENDOR, "supplier_group": frappe.db.get_value("Supplier Group", {"is_group": 0})}).insert()
		frappe.db.commit()

	def test_read_line(self):
		d = run(tf.ACC, new_product.read, "new product Cabin 10 x 30 x 8.8 subcontrcted to SK test AI Poratable cabin")
		self.assertEqual((d["length"], d["width"], d["height"]), (30, 10, 8.8))
		self.assertEqual(d["vendor"], VENDOR)
		self.assertTrue(d["subcontracted"])
		self.assertEqual(new_product.preview(TPL, 30, 10, 8.8)["item_code"], f"{TPL}-30ft x 10ft x 8.8ft")
		self.assertIsNone(new_product.match_supplier("Totally Different Vendor"))

	def test_make_variant_and_new_number(self):
		r = run(tf.ACC, new_product.make, TPL, 30, 10, 8.8, VENDOR)
		self.assertEqual(r["item_code"], f"{TPL}-30ft x 10ft x 8.8ft")
		it = frappe.get_doc("Item", r["item_code"])
		self.assertEqual((it.variant_of, it.is_purchase_item), (TPL, 1))
		self.assertEqual([s.supplier for s in it.supplier_items], [VENDOR])
		self.assertIn("Subcontracted", it.description)
		again = run(tf.ACC, new_product.make, TPL, 30, 10, 8.8, VENDOR)  # same size again: no duplicate
		self.assertFalse(again["new"])
		nxt = new_product.next_number()
		r2 = run(tf.ACC, new_product.make, None, None, None, None, None, "SK Test New Vendor Co", "SK Test Site Pod")
		self.assertEqual(r2["item_code"], nxt)
		self.assertTrue(frappe.db.exists("Supplier", r2["vendor"]))
