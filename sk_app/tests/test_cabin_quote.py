"""SK 27-Oct: standard cabin quotation: same requirement = same price, price only from the rate card, discount limits,
SK's quote number and revision, print in SK's template."""

import json

import frappe
from frappe.tests import IntegrationTestCase

from sk_app import cabin_quote
from sk_app.tests.test_change_list_a import _app_user
from sk_app.tests import test_store_purchase as tsp
from sk_app.tests.test_store_purchase import CUSTOMER

REP = "sk_test_cq_rep@example.com"
BOSS = "sk_test_cq_boss@example.com"
REQ = {"type": "office", "length": 20, "width": 10, "height": 8.5, "qty": 1, "options": {"window": 1, "ac_point": 1}, "km": 45}


class TestCabinQuote(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		tsp.TestStorePurchase.setUpClass.__func__(tsp.TestStorePurchase)
		_app_user(REP, "Sales", ["Sales User"])
		_app_user(BOSS, "Management", ["Sales Manager"])
		cabin_quote.ensure_setup()
		frappe.db.commit()

	def test_same_price_as_sample(self):
		p = cabin_quote.price(REQ)
		self.assertEqual(p["total"], 283000)  # SK_Standard_Cabin_Quote_Sample_R0: 20x10 office, Rs 2,83,000 ex-GST
		self.assertEqual(p["lines"][0]["rate"], 260000)
		self.assertEqual(cabin_quote.price(dict(REQ))["total"], p["total"])
		taller = cabin_quote.price({**REQ, "height": 9.5, "options": {}})
		self.assertEqual(taller["lines"][0]["rate"], 276000)  # +1 ft x Rs 80 / sq ft
		self.assertEqual(cabin_quote.price({"type": "security", "length": 6, "width": 5})["lines"][0]["rate"], 60000)  # minimum
		self.assertEqual(cabin_quote.price({"type": "frp_security", "length": 6, "width": 4, "transport": False})["total"], 34000)  # rounded up to Rs 1,000 like every price

	def test_outside_rate_card_goes_to_design(self):
		for bad in ({"type": "lgsf", "length": 20, "width": 10}, {"type": "office", "length": 45, "width": 10},
				{"type": "frp_security", "length": 8, "width": 6}):
			with self.assertRaises(frappe.ValidationError):
				cabin_quote.price(bad)

	def test_quote_number_revision_discount(self):
		frappe.set_user(REP)
		try:
			r = cabin_quote.make(REP, REQ, customer=CUSTOMER)
			q = frappe.get_doc("Quotation", r["name"])
			self.assertTrue(q.sk_quote_ref.startswith("SK/CAB/"))
			self.assertEqual((q.sk_rev, q.net_total, q.sk_rate_card), (0, 283000, cabin_quote.rate_card()["version"]))
			self.assertEqual(json.loads(q.sk_cabin_request)["type"], "office")
			self.assertEqual(len(q.items), 4)
			self.assertIn("format=SK%20Cabin%20Quotation", r["pdf"])
			# a salesperson cannot give a discount: it waits for SK
			r2 = cabin_quote.make(REP, {**REQ, "options": {}}, customer=CUSTOMER, discount_pct=3, revise=r["name"])
		finally:
			frappe.set_user("Administrator")
		q = frappe.get_doc("Quotation", r2["name"])
		self.assertEqual((q.name, q.sk_rev, q.sk_discount_status, q.discount_amount), (r["name"], 1, "Requested", 0))
		self.assertTrue(r2["discount_waiting"])
		self.assertTrue(frappe.db.exists("ToDo", {"reference_name": q.name, "allocated_to": BOSS, "status": "Open"}))
		self.assertIn(q.name, [x["name"] for x in cabin_quote.discount_requests(BOSS)])
		with self.assertRaises(frappe.PermissionError):
			cabin_quote.discount_requests(REP)
		out = cabin_quote.decide_discount(BOSS, q.name, 1)
		q.reload()
		self.assertEqual((out["status"], q.total, round(q.discount_amount), q.net_total), ("Approved", 275000, 8250, 266750))
		self.assertIn(q.name, [x["name"] for x in cabin_quote.open_quotes(CUSTOMER)])

	def test_print_format(self):
		r = cabin_quote.make("Administrator", REQ, customer=CUSTOMER)
		html = cabin_quote.quote_html(frappe.get_doc("Quotation", r["name"]))
		for part in ("QUOTATION", r["ref"], "Rev: R0", "Two Lakh Eighty-Three Thousand", "Technical specification", "₹2,83,000", "sk-quote-header.png"):
			self.assertIn(part, html)
		self.assertTrue(frappe.db.exists("Print Format", cabin_quote.PRINT_FORMAT))
		self.assertEqual(frappe.db.get_value("Property Setter", {"doc_type": "Quotation", "property": "default_print_format"}, "value"), cabin_quote.PRINT_FORMAT)
		self.assertEqual(cabin_quote.max_discount(REP), 0)
		self.assertEqual(cabin_quote.max_discount(BOSS), 100)
