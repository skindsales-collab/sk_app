"""SK 28-Oct review list Rev 1, batch 3: a list typed / spoken / read from a photo becomes requisition rows (points 11-13),
every word of the search may be anywhere, up to 20 items, and material found from a photo after its first sample (19)."""

import json

import frappe
from frappe.tests import IntegrationTestCase

from sk_app import item_input, requisition, store
from sk_app.tests.test_store_purchase import RAW, STORE_U, run, setup_data

SIG = {"d": "f0f0f0f00f0f0f0f", "h": [0.0] * 63 + [1.0]}


class TestItemInput(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		setup_data(cls)
		item_input.ensure_setup()

	def test_words_anywhere(self):
		# "SK Test Pipe 40x40": the words in another order and the size apart still find it
		self.assertIn(RAW, [r["item_code"] for r in run(STORE_U, item_input.search, "pipe 40 test")])
		self.assertIn(RAW, [r["item_code"] for r in run(STORE_U, store.stock_search, "test pipe 40")])

	def test_spoken_list_becomes_rows(self):
		self.assertEqual(item_input.split_line("C channel 100x50 20 nos"), ("C channel 100x50", 20))
		self.assertEqual(item_input.split_line("बोल्ट २० नग"), ("बोल्ट", 20))
		self.assertEqual(item_input.split_line("Hinges ten"), ("Hinges", 10))
		self.assertEqual(item_input.split_line("Door lock"), ("Door lock", 1))
		r = run(STORE_U, item_input.parse_list, "test pipe 40x40 6 nos, unknown thing 3 kg")
		self.assertEqual(len(r["rows"]), 2)
		self.assertEqual((r["rows"][0]["item_code"], r["rows"][0]["qty"]), (RAW, 6))
		self.assertEqual(r["rows"][1]["qty"], 3)
		many = run(STORE_U, item_input.parse_list, "\n".join(f"pipe {i} nos" for i in range(1, 26)))
		self.assertEqual((len(many["rows"]), many["more"]), (20, 5))

	def test_twenty_items_at_most(self):
		rows = [{"item_code": RAW, "qty": 1}] * 21
		self.assertRaises(frappe.ValidationError, run, STORE_U, requisition.raise_request, rows)

	def test_photo_sample_then_match(self):
		frappe.db.set_value("Item", RAW, item_input.FIELD, None)
		first = run(STORE_U, item_input.match, json.dumps(SIG))
		self.assertNotIn(RAW, [r["item_code"] for r in first["rows"]])
		run(STORE_U, item_input.save_sample, RAW, json.dumps(SIG), None)
		near = {"d": "f0f0f0f00f0f0f0e", "h": [0.0] * 62 + [0.1, 0.9]}
		hit = run(STORE_U, item_input.match, json.dumps(near))["rows"][0]
		self.assertEqual(hit["item_code"], RAW)
		self.assertGreater(hit["score"], 90)
		run(STORE_U, item_input.save_sample, RAW, json.dumps(SIG), None)  # the same photo again is not kept twice
		self.assertEqual(len(json.loads(frappe.db.get_value("Item", RAW, item_input.FIELD))), 1)
		self.assertRaises(frappe.ValidationError, run, STORE_U, item_input.match, json.dumps({"d": "zz", "h": []}))
