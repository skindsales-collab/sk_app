"""SK 27-Oct: Tally-style Accounts: Gateway sections, Tally voucher names, Day Book, Alter Ledger search, Narration."""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, nowdate

from sk_app import finance, tally
from sk_app.store import need
from sk_app.tests import test_finance as tf
from sk_app.tests.test_finance import ACC, SALES
from sk_app.tests.test_store_purchase import CUSTOMER, run


class TestTally(IntegrationTestCase):
	# same accounts set-up and invoice helper as the Finance tests, without running those tests again
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		tf.TestFinance.setUpClass()
		cls.company = tf.TestFinance.company

	_invoice = tf.TestFinance._invoice

	def test_gateway_sections_like_tally(self):
		g = tally.gateway()
		self.assertEqual([s["section"] for s in g["sections"]], ["Masters", "Transactions", "Utilities", "Reports"])
		keys = {i["key"]: i for s in g["sections"] for i in s["items"]}
		self.assertEqual((keys["payment"]["keys"], keys["receipt"]["keys"], keys["contra"]["keys"]), ("F5", "F6", "F4"))
		self.assertIn("payment_type=Internal%20Transfer", keys["contra"]["url"])
		self.assertTrue(g["fy"].startswith("FY "))
		self.assertTrue(all(frappe.db.exists("Report", m["url"].split("/")[-1]) for m in g["more"]))
		self.assertTrue(frappe.db.exists("Report", "Day Book"))
		self.assertTrue(frappe.db.exists("Page", "accounts-gateway"))

	def test_vch_type_names(self):
		self.assertEqual(tally.vch_type("Payment Entry", payment_type="Receive"), "Receipt")
		self.assertEqual(tally.vch_type("Payment Entry", payment_type="Internal Transfer"), "Contra")
		self.assertEqual(tally.vch_type("Sales Invoice", is_return=1), "Credit Note")
		self.assertEqual(tally.vch_type("Purchase Invoice"), "Purchase")
		self.assertEqual(tally.vch_type("Journal Entry", je_type="Contra Entry"), "Contra")
		self.assertEqual(tally.vch_type("Purchase Receipt"), "Receipt Note")

	def test_day_book_and_app_gateway(self):
		day = add_days(nowdate(), -3)
		si = self._invoice(2500, day)
		r = run(ACC, finance.receive_payment, "Sales Invoice", si.name, 1000, None, "UTR9")
		rows = tally.day_book(day, day)
		sale = next(x for x in rows if x["vch_no"] == si.name)
		self.assertEqual((sale["vch_type"], sale["particulars"]), ("Sales", CUSTOMER))
		self.assertGreater(sale["debit"], 0)
		self.assertEqual(sale["credit"], 0)
		if r["posted"]:
			rec = next(x for x in tally.day_book(nowdate(), nowdate()) if x["vch_no"] == r["name"])
			self.assertEqual((rec["vch_type"], rec["credit"] > 0, rec["debit"]), ("Receipt", True, 0))

	def test_sales_cannot_open_gateway(self):
		with self.assertRaises(frappe.PermissionError):
			need(SALES, "Accounts", "Management")  # the app's Gateway and Day Book check this
		need(ACC, "Accounts", "Management")

	def test_find_ledger_and_narration(self):
		found = tally.find_ledger(CUSTOMER[:5])
		self.assertTrue(any(x["doctype"] == "Customer" and x["group"] == "Sundry Debtors" for x in found))
		self.assertEqual(tally.find_ledger("a"), [])
		tally.ensure()
		self.assertEqual(frappe.get_meta("Payment Entry").get_field("remarks").label, "Narration")
		self.assertEqual(frappe.get_meta("Journal Entry").get_field("user_remark").label, "Narration")
