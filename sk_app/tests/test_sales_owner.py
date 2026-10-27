"""SK 27-Oct point 5: Tally sale on each salesperson's graph, by who sells to each customer."""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import get_first_day, getdate, nowdate

from sk_app import dashboards, sales_owner
from sk_app.tests.test_change_list_a import _app_user
from sk_app.tests.test_hr import employee
from sk_app.tests.test_store_purchase import run

REP = "sk_test_so_rep@example.com"
CUSTOMER = "SK Test Tally Buyer"


class TestSalesOwner(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		_app_user(REP, "Sales", ["Sales User", "Employee"])
		employee("SoRep", user=REP)
		if not frappe.db.exists("Customer", {"customer_name": CUSTOMER}):
			frappe.get_doc({"doctype": "Customer", "customer_name": CUSTOMER, "customer_type": "Company"}).insert(ignore_permissions=True)

	def test_tally_sale_counts_for_the_customers_salesperson(self):
		sales_owner.ensure_sales_persons()
		person = frappe.db.get_value("Sales Person", {"employee": frappe.db.get_value("Employee", {"user_id": REP})})
		self.assertTrue(person)
		sales_owner.ensure_sales_persons()  # once only
		self.assertEqual(frappe.db.count("Sales Person", {"employee": frappe.db.get_value("Employee", {"user_id": REP})}), 1)
		fake = [frappe._dict(name="JV-1", posting_date=getdate(), customer_name=CUSTOMER, amount=250000, voucher="S/1")]
		orig = dashboards._tally_sales
		dashboards._tally_sales = lambda s, e, seg=None: fake
		try:
			start, end = get_first_day(getdate()), getdate(nowdate())
			self.assertEqual(sales_owner.invoiced_for([person], start, end), 0)
			lst = run("Administrator", sales_owner.assign_list)
			row = next(r for r in lst["rows"] if r["title"] == CUSTOMER)
			self.assertEqual((row["sale"], row["persons"]), (250000, []))
			self.assertIn(person, lst["persons"])
			with self.assertRaises(frappe.PermissionError):
				run(REP, sales_owner.assign, row["customer"], person)  # only the CEO / sales manager
			run("Administrator", sales_owner.assign, row["customer"], person)
			self.assertEqual(sales_owner.invoiced_for([person], start, end), 250000)
			from sk_app import home_kpi

			card = run(REP, home_kpi.for_user, ["Sales"])["chart"]
			self.assertEqual([l["label"] for l in card["month"]["lines"]], ["Orders", "Invoices"])
			self.assertEqual(card["month"]["lines"][1]["points"][-1], 250000)
			run("Administrator", sales_owner.assign, row["customer"], None)
			self.assertEqual(sales_owner.invoiced_for([person], start, end), 0)
		finally:
			dashboards._tally_sales = orig
