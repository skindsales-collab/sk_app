import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, flt, nowdate

from sk_app import finance
from sk_app.tests.test_store_purchase import BOSS, CUSTOMER, RAW, SUPPLIER, TestStorePurchase, app_user, run

ACC = "sk_test_shraddha@example.com"
SALES = "sk_test_fin_rep@example.com"


class TestFinance(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		TestStorePurchase.setUpClass.__func__(TestStorePurchase)
		cls.company = TestStorePurchase.company
		app_user(ACC, "Accounts", ["Employee"])
		app_user(SALES, "Sales", ["Employee"])
		frappe.db.commit()

	def _invoice(self, rate=1000, due=None):
		si = frappe.get_doc({"doctype": "Sales Invoice", "customer": CUSTOMER, "company": self.company, "posting_date": due or nowdate(),
			"set_posting_time": 1, "due_date": due or nowdate(), "items": [{"item_code": RAW, "qty": 1, "rate": rate}]})
		si.flags.ignore_permissions = True
		si.insert()
		si.submit()
		return si

	def _bill(self, rate):
		pi = frappe.get_doc({"doctype": "Purchase Invoice", "supplier": SUPPLIER, "company": self.company, "posting_date": nowdate(),
			"bill_no": f"T-{frappe.generate_hash(length=5)}", "items": [{"item_code": RAW, "qty": 1, "rate": rate}]})
		pi.insert()
		pi.submit()
		return pi

	def test_collect_promise_and_receive(self):
		si = self._invoice(1200, add_days(nowdate(), -40))
		row = next(r for r in run(ACC, finance.to_collect) if r["name"] == si.name)
		self.assertEqual(row["bucket"], "d31_60")
		run(ACC, finance.promise, si.name, "Friday la payment", add_days(nowdate(), 3))
		self.assertTrue(frappe.db.exists("ToDo", {"reference_name": si.name, "allocated_to": ACC, "date": add_days(nowdate(), 3)}))
		self.assertIn("Friday", next(r for r in run(ACC, finance.to_collect) if r["name"] == si.name)["promise"])
		r = run(ACC, finance.receive_payment, "Sales Invoice", si.name, 500, None, "UTR123")
		pe = frappe.get_doc("Payment Entry", r["name"])
		self.assertEqual(pe.references[0].reference_name, si.name)
		self.assertEqual(flt(pe.paid_amount), 500)
		self.assertEqual(pe.reference_no, "UTR123")
		if r["posted"]:
			self.assertEqual(flt(frappe.db.get_value("Sales Invoice", si.name, "outstanding_amount")), 700)
		self.assertRaises(frappe.PermissionError, run, SALES, finance.receive_payment, "Sales Invoice", si.name, 1)

	def test_big_payment_needs_sk_ok(self):
		small, big = self._bill(100), self._bill(finance.po_limit() + 1000)
		rows = {r["name"]: r for r in run(ACC, finance.to_pay)}
		self.assertFalse(rows[small.name]["needs_ok"])
		self.assertTrue(rows[big.name]["needs_ok"])
		self.assertTrue(run(ACC, finance.pay, small.name)["name"])
		self.assertRaises(frappe.ValidationError, run, ACC, finance.pay, big.name)
		self.assertIn(big.name, [r["name"] for r in run(BOSS, finance.pay_approvals)])
		run(BOSS, finance.approve_payment, big.name)
		self.assertTrue(frappe.db.exists("ToDo", {"reference_name": big.name, "allocated_to": ACC, "status": "Open"}))
		self.assertNotIn(big.name, [r["name"] for r in run(BOSS, finance.pay_approvals)])
		r = run(ACC, finance.pay, big.name, None, None, "NEFT9")
		self.assertTrue(r["name"])
		self.assertFalse(frappe.db.exists("ToDo", {"reference_name": big.name, "allocated_to": ACC, "status": "Open"}))

	def test_invoice_from_dispatch_and_post(self):
		dn = frappe.get_doc({"doctype": "Delivery Note", "customer": CUSTOMER, "company": self.company, "posting_date": nowdate(),
			"items": [{"item_code": RAW, "qty": 1, "rate": 900, "warehouse": TestStorePurchase.stores}]})
		dn.insert()
		dn.submit()
		self.assertIn(dn.name, [d["name"] for d in run(ACC, finance.invoices)["to_bill"]])
		r = run(ACC, finance.make_invoice, dn.name)
		si = frappe.get_doc("Sales Invoice", r["name"])
		self.assertEqual(si.items[0].delivery_note, dn.name)
		self.assertIn(si.name, [d["name"] for d in run(ACC, finance.invoices)["drafts"]])
		p = run(ACC, finance.post, "Sales Invoice", si.name)
		self.assertTrue(p["posted"], p.get("reason"))
		self.assertNotIn(dn.name, [d["name"] for d in run(ACC, finance.invoices)["to_bill"]])

	def test_bill_photo_to_purchase_invoice(self):
		from sk_app import purchase

		q = purchase.add_quote("Administrator", SUPPLIER, RAW, 2, 150, 2)
		po = purchase.make_po("Administrator", q["name"])["name"]
		frappe.get_doc({"doctype": "ToDo", "allocated_to": ACC, "reference_type": "Supplier", "reference_name": SUPPLIER,
			"description": "Supplier bill from test"}).insert(ignore_permissions=True)
		b = run(ACC, finance.bills_to_post)
		photo = next(p for p in b["photos"] if p["reference_name"] == SUPPLIER)
		self.assertIn(po, [o["name"] for o in photo["orders"]])
		r = run(ACC, finance.make_bill, po, "INV-77", nowdate(), photo["name"])
		self.assertEqual(frappe.db.get_value("Purchase Invoice", r["name"], "bill_no"), "INV-77")
		self.assertEqual(frappe.db.get_value("ToDo", photo["name"], "status"), "Closed")
		self.assertTrue(run(ACC, finance.post, "Purchase Invoice", r["name"])["posted"])

	def test_petty_cash_pnl_and_month_close(self):
		o = run(ACC, finance.voucher_options)
		self.assertTrue(o["expense_accounts"] and o["cash_accounts"])
		self.assertRaises(frappe.ValidationError, run, ACC, finance.petty_cash, o["expense_accounts"][0], 250, o["cash_accounts"][0])
		before = run(ACC, finance.segment_pnl)["total"]
		r = run(ACC, finance.petty_cash, o["expense_accounts"][0], 250, o["cash_accounts"][0], o["cost_centers"][0], "Tea for site team")
		self.assertTrue(r["posted"])
		self._invoice(5000)
		p = run(ACC, finance.segment_pnl)
		self.assertAlmostEqual(p["total"]["income"] - before["income"], 5000)
		self.assertAlmostEqual(p["total"]["cost"] - before["cost"], 250)
		cash = run(ACC, finance.cash_today)
		self.assertTrue(cash["accounts"])
		run(ACC, finance.tick_close, "stock_close")
		self.assertTrue(next(r for r in run(ACC, finance.month_close) if r["key"] == "stock_close")["done"])
		self.assertRaises(frappe.PermissionError, run, SALES, finance.month_close)
