"""SK 28-Oct review list Rev 1, batch 2 (approved "Approve for modification"): graphs had no data because no order or
customer was in a salesperson's name (point 8), customers had no Cabin / Non-Cabin segment and Rothe Erde showed on the
factory board (point 9), the order board on the graph (point 4), cold-calling data moved to the Marketing list (point 7)."""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, getdate

from sk_app import cold_calls, flows, home_kpi, marketing_list, production, sales_owner, segments
from sk_app.tests.test_change_list_a import _app_user
from sk_app.tests.test_hr import employee

REP, NONCAB = "sk_b2_rep@example.com", "sk_b2_aditya@example.com"
CABIN_CUST, NONCAB_CUST = "SK B2 Cabin Buyer", "SK B2 Ballscrew Buyer"


def _customer(name, group=None):
	if not frappe.db.exists("Customer", name):
		frappe.get_doc({"doctype": "Customer", "customer_name": name, "customer_type": "Company",
			"customer_group": group or frappe.db.get_value("Customer Group", {"is_group": 0})}).insert(ignore_permissions=True)
	return name


def _order(customer, value=100000, day=None):
	from sk_app.store import _company

	item = frappe.db.get_value("Item", {"is_sales_item": 1, "is_stock_item": 0, "disabled": 0})
	if not item:
		item = frappe.get_doc({"doctype": "Item", "item_code": "SK-B2-SERVICE", "item_name": "SK B2 service", "item_group":
			frappe.db.get_value("Item Group", {"is_group": 0}), "stock_uom": "Nos", "is_stock_item": 0}).insert(ignore_permissions=True).name
	day = day or add_days(getdate(), -40)
	so = frappe.get_doc({"doctype": "Sales Order", "customer": customer, "company": _company(), "transaction_date": day,
		"delivery_date": add_days(day, 30), "items": [{"item_code": item, "qty": 1, "rate": value, "delivery_date": add_days(day, 30)}]})
	so.flags.ignore_permissions = True
	so.insert()
	return so


class TestRev1Batch2(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		segments.ensure_customer_groups()
		_app_user(REP, "Sales", ["Sales User", "Employee"])
		_app_user(NONCAB, "Machine Shifting", ["Sales User", "Employee"])
		employee("B2Rep", user=REP)
		employee("B2Aditya", user=NONCAB)
		sales_owner.ensure_sales_persons()
		cls.rep = sales_owner.person_of(REP)
		cls.aditya = sales_owner.person_of(NONCAB)

	def test_non_cabin_customer_goes_to_aditya_and_off_the_factory_board(self):
		self.assertTrue(self.aditya)
		cust = _customer(NONCAB_CUST, "Commercial" if frappe.db.exists("Customer Group", "Commercial") else None)
		frappe.db.delete("Sales Team", {"parenttype": "Customer", "parent": cust})
		so = _order(cust)
		self.assertNotEqual(so.customer_group, "Machine Shifting")
		segments._apply(cust, "Machine Shifting", "test")
		# the open order follows the customer's new segment, and the customer goes to Aditya
		self.assertEqual(frappe.db.get_value("Sales Order", so.name, "customer_group"), "Machine Shifting")
		self.assertEqual(sales_owner._team_of("Customer", cust), [self.aditya])
		self.assertIn(so.name, production.non_cabin_orders())
		frappe.set_user("Administrator")
		board = flows.factory("Administrator")
		self.assertNotIn(so.name, [r["name"] for r in board[0]["rows"]])
		jobs = next(s for s in flows.sales("Administrator", segments.NON_CABIN) if s["key"] == "non_cabin_jobs")
		self.assertIn(so.name, [r["name"] for r in jobs["rows"]])

	def test_order_gets_salesperson_from_customer_and_nightly_fills_old_orders(self):
		self.assertTrue(self.rep)
		cust = _customer(CABIN_CUST, "Standard Cabin (GI / ACP)")
		frappe.db.delete("Sales Team", {"parenttype": "Customer", "parent": cust})
		old = _order(cust, 50000)  # made before anyone sells to the customer: no salesperson
		self.assertEqual(sales_owner._team_of("Sales Order", old.name), [])
		sales_owner._add_team("Customer", cust, self.rep)
		new = _order(cust, 70000)
		self.assertEqual(sales_owner._team_of("Sales Order", new.name), [self.rep])
		sales_owner.auto_link()
		self.assertEqual(sales_owner._team_of("Sales Order", old.name), [self.rep])
		sales_owner.auto_link()  # never twice
		self.assertEqual(sales_owner._team_of("Sales Order", old.name), [self.rep])
		# point 4: both orders are on the order board from before this month
		self.assertGreaterEqual(home_kpi.board_value(getdate(), None, [self.rep]), 120000)
		self.assertEqual(home_kpi.board_value(add_days(getdate(), -60), None, [self.rep]), 0)
		card = home_kpi.sales(REP, only_self=True)
		self.assertGreaterEqual(card["board"]["now"], 120000)

	def test_tagged_by_hand_customer_keeps_its_salesperson(self):
		cust = _customer("SK B2 Hand Tagged", "Machine Shifting")
		frappe.db.delete("Sales Team", {"parenttype": "Customer", "parent": cust})
		sales_owner._add_team("Customer", cust, self.rep)
		self.assertIsNone(sales_owner.link_customer(cust))
		self.assertEqual(sales_owner._team_of("Customer", cust), [self.rep])

	def test_cold_lead_moves_to_marketing_list(self):
		if not cold_calls.has_field():
			cold_calls.ensure_field()
		if not cold_calls.has_field():
			self.skipTest("Frappe CRM not installed")
		marketing_list.ensure_setup()
		lead = frappe.get_doc({"doctype": "CRM Lead", "first_name": "Cold Kumar", "mobile_no": "9811100022", "organization": "Cold Co",
			"lead_owner": REP, "status": frappe.get_all("CRM Lead Status", order_by="position asc", pluck="name", limit=1)[0]})
		lead.flags.ignore_permissions = lead.flags.ignore_mandatory = True
		lead.insert()
		frappe.db.set_value("CRM Lead", lead.name, cold_calls.FIELD, 1)
		self.assertEqual(cold_calls.move_all(), 1)
		self.assertFalse(frappe.db.exists("CRM Lead", lead.name))
		contact = marketing_list._by_mobile("9811100022")
		self.assertTrue(contact)
		self.assertEqual(frappe.db.get_value("Contact", contact, marketing_list.FIELD), 1)
		self.assertEqual(frappe.db.get_value("Contact", contact, "owner"), REP)
		self.assertTrue(frappe.db.exists("Comment", {"reference_doctype": "Contact", "reference_name": contact, "content": ["like", f"%{lead.name}%"]}))

	def test_auto_tag_from_tally_without_a_tap(self):
		cust = _customer("SK B2 Tally Non Cabin", "Commercial" if frappe.db.exists("Customer Group", "Commercial") else None)
		frappe.db.set_value("Customer", cust, "customer_group", "Commercial" if frappe.db.exists("Customer Group", "Commercial") else "All Customer Groups")
		orig = segments.tally_suggestions
		segments.tally_suggestions = lambda: {cust: segments.NON_CABIN}
		try:
			done = segments.auto_tag()
		finally:
			segments.tally_suggestions = orig
		self.assertGreaterEqual(done["non_cabin"], 1)
		self.assertEqual(segments.main_of(frappe.db.get_value("Customer", cust, "customer_group")), segments.NON_CABIN)
