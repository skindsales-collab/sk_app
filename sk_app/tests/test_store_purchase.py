import frappe
from frappe.tests import IntegrationTestCase
from frappe.tests.classes.context_managers import set_user
from frappe.utils import add_days, flt, nowdate

from sk_app import purchase, store
from sk_app.tests.test_sk_app_api import make_user

STORE_U = "sk_test_store@example.com"
BUY_U = "sk_test_buyer@example.com"
BOSS = "sk_test_boss@example.com"
RAW = "SK Test Pipe 40x40"
FG = "SK Test Cabin 10x8"
SUPPLIER = "SK Test Steel Traders"
CUSTOMER = "SK Test Customer"


def app_user(email, home, roles):
	from sk_app.functions import FUNCTIONS

	make_user(email, roles)
	frappe.get_doc("User", email).add_roles(*[r for r in FUNCTIONS[home]["erpnext_roles"] if frappe.db.exists("Role", r)])
	if not frappe.db.exists("SK App User", {"user": email}):
		frappe.get_doc({"doctype": "SK App User", "user": email, "home": home}).insert(ignore_permissions=True)


def run(user, fn, *args, **kw):
	"""Call a screen function the way the phone does: logged in as that person."""
	with set_user(user):
		return fn(user, *args, **kw)


class TestStorePurchase(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.company = frappe.db.get_value("Company", {}, "name")
		if not cls.company:
			raise cls.skipTest(cls, "needs an ERPNext company (setup wizard done)")
		abbr = frappe.db.get_value("Company", cls.company, "abbr")
		cls.stores = f"Stores - {abbr}"
		cls.wip = f"Work In Progress - {abbr}"
		cls.fgw = f"Finished Goods - {abbr}"
		frappe.db.set_single_value("Stock Settings", "default_warehouse", cls.stores)
		app_user(STORE_U, "Stores", ["Stock User"])
		app_user(BUY_U, "Purchase", ["Purchase User"])
		app_user(BOSS, "Management", ["System Manager"])
		for code, stock in ((RAW, 1), (FG, 1)):
			if not frappe.db.exists("Item", code):
				frappe.get_doc({"doctype": "Item", "item_code": code, "item_name": code, "item_group": frappe.db.get_value("Item Group", {"is_group": 0}, "name"), "stock_uom": "Nos", "is_stock_item": stock,
					"valuation_rate": 100, "item_defaults": [{"company": cls.company, "default_warehouse": cls.stores}]}).insert()
		if not frappe.db.exists("Supplier", SUPPLIER):
			frappe.get_doc({"doctype": "Supplier", "supplier_name": SUPPLIER, "supplier_group": frappe.db.get_value("Supplier Group", {"is_group": 0}, "name")}).insert()
		if not frappe.db.exists("Customer", CUSTOMER):
			frappe.get_doc({"doctype": "Customer", "customer_name": CUSTOMER, "customer_group": frappe.db.get_value("Customer Group", {"is_group": 0}, "name"),
				"territory": frappe.db.get_value("Territory", {"is_group": 0}, "name")}).insert()
		have = flt(frappe.db.get_value("Bin", {"item_code": RAW, "warehouse": cls.stores}, "actual_qty"))
		if have < 50:
			se = frappe.get_doc({"doctype": "Stock Entry", "stock_entry_type": "Material Receipt", "company": cls.company,
				"items": [{"item_code": RAW, "qty": 50 - have, "t_warehouse": cls.stores, "basic_rate": 100}]})
			se.insert()
			se.submit()
		if not frappe.db.exists("BOM", {"item": FG, "docstatus": 1}):
			bom = frappe.get_doc({"doctype": "BOM", "item": FG, "company": cls.company, "quantity": 1,
				"items": [{"item_code": RAW, "qty": 10, "rate": 100}]})
			bom.insert()
			bom.submit()
		frappe.db.commit()

	def test_stock_check_shows_live_qty(self):
		rows = run(STORE_U, store.stock_search, "Test Pipe")
		row = next(r for r in rows if r["item_code"] == RAW)
		self.assertGreaterEqual(row["qty"], 1)
		self.assertTrue(any(w["warehouse"] == self.stores for w in row["warehouses"]))
		self.assertEqual(run(STORE_U, store.item_detail, RAW)["item_code"], RAW)

	def test_only_function_members_use_screens(self):
		self.assertRaises(frappe.PermissionError, run, BUY_U, store.issue, "x", [{"item_code": RAW, "qty": 1}])
		self.assertRaises(frappe.PermissionError, run, STORE_U, purchase.make_po, "x")
		self.assertRaises(frappe.PermissionError, run, BUY_U, purchase.approvals)

	def test_low_stock_goes_to_purchase_requests(self):
		item = frappe.get_doc("Item", RAW)
		item.set("reorder_levels", [{"warehouse": self.stores, "warehouse_reorder_level": 100000, "warehouse_reorder_qty": 20,
			"material_request_type": "Purchase"}])
		item.save()
		try:
			low = run(STORE_U, store.low_stock)
			self.assertTrue(any(r["item_code"] == RAW for r in low))
			r = run(STORE_U, store.order_low, [RAW])
			self.assertEqual(frappe.db.get_value("Material Request", r["name"], "docstatus"), 1)
			reqs = run(BUY_U, purchase.requests)
			self.assertTrue(any(x["request"] == r["name"] and x["item_code"] == RAW for x in reqs))
		finally:
			item.reload()
			item.set("reorder_levels", [])
			item.save()

	def test_rates_quote_po_receive(self):
		rfq = run(BUY_U, purchase.make_rfq, [{"item_code": RAW, "qty": 10}], [SUPPLIER], add_days(nowdate(), 3))
		self.assertIn(RAW, rfq["text"])
		self.assertEqual(frappe.db.get_value("Request for Quotation", rfq["name"], "docstatus"), 0)
		q = run(BUY_U, purchase.add_quote, SUPPLIER, RAW, 10, 90, 2, rfq=rfq["name"])
		cmp = run(BUY_U, purchase.compare, RAW)
		self.assertTrue(any(x["name"] == q["name"] for x in cmp["quotes"]))
		po = run(BUY_U, purchase.make_po, q["name"])
		self.assertFalse(po["needs_approval"])
		self.assertTrue(po["posted"], frappe.get_all("Comment", filters={"reference_name": po["name"]}, pluck="content"))
		pos = run(STORE_U, store.open_purchase_orders)
		mine = next(p for p in pos if p["name"] == po["name"])
		pr = run(STORE_U, store.receive, po["name"], [{"po_detail": mine["items"][0]["name"], "qty": 4}], note="challan 418")
		doc = frappe.get_doc("Purchase Receipt", pr["name"])
		self.assertEqual(doc.docstatus, 0)
		self.assertEqual(doc.items[0].qty, 4)

	def test_big_po_waits_for_sk(self):
		q = run(BUY_U, purchase.add_quote, SUPPLIER, RAW, 10, 100000)
		po = run(BUY_U, purchase.make_po, q["name"])
		self.assertTrue(po["needs_approval"])
		self.assertTrue(any(p.name == po["name"] for p in run(BOSS, purchase.approvals)))
		self.assertTrue(frappe.db.exists("ToDo", {"allocated_to": BOSS, "reference_name": po["name"]}))
		r = run(BOSS, purchase.decide, po["name"], True)
		self.assertTrue(r["posted"], frappe.get_all("Comment", filters={"reference_name": po["name"]}, pluck="content"))
		self.assertEqual(frappe.db.get_value("Purchase Order", po["name"], "docstatus"), 1)

	def test_issue_to_job(self):
		wo = frappe.get_doc({"doctype": "Work Order", "production_item": FG, "qty": 1, "company": self.company,
			"bom_no": frappe.db.get_value("BOM", {"item": FG, "docstatus": 1, "is_default": 1}),
			"wip_warehouse": self.wip, "fg_warehouse": self.fgw, "source_warehouse": self.stores, "skip_transfer": 0})
		wo.insert()
		wo.submit()
		self.assertTrue(any(w.name == wo.name for w in run(STORE_U, store.open_work_orders)))
		before = flt(frappe.db.get_value("Bin", {"item_code": RAW, "warehouse": self.stores}, "actual_qty"))
		r = run(STORE_U, store.issue, wo.name, [{"item_code": RAW, "qty": 5}], taken_by="Ranjit")
		self.assertTrue(r["posted"], frappe.get_all("Comment", filters={"reference_name": r["name"]}, pluck="content"))
		after = flt(frappe.db.get_value("Bin", {"item_code": RAW, "warehouse": self.stores}, "actual_qty"))
		self.assertEqual(before - after, 5)

	def test_dispatch_makes_draft_delivery_note(self):
		so = frappe.get_doc({"doctype": "Sales Order", "customer": CUSTOMER, "company": self.company, "delivery_date": add_days(nowdate(), 1),
			"items": [{"item_code": FG, "qty": 1, "rate": 900000, "warehouse": self.fgw, "delivery_date": add_days(nowdate(), 1)}]})
		so.insert()
		so.submit()
		self.assertTrue(any(o.name == so.name for o in run(STORE_U, store.orders_to_dispatch)))
		r = run(STORE_U, store.dispatch, so.name, vehicle_no="mh 46 ab 1234", driver_mobile="9876500001")
		dn = frappe.get_doc("Delivery Note", r["name"])
		self.assertEqual(dn.docstatus, 0)
		self.assertEqual(dn.vehicle_no, "MH 46 AB 1234")

	def test_erp_flow_order_to_work_order(self):
		"""SK 26-Oct: Production makes the Work Order of a confirmed order in the app (BOM needed, Design makes it)."""
		from sk_app import erp_flow

		so = frappe.get_doc({"doctype": "Sales Order", "customer": CUSTOMER, "company": self.company, "delivery_date": add_days(nowdate(), 5),
			"items": [{"item_code": FG, "qty": 2, "rate": 500000, "warehouse": self.fgw, "delivery_date": add_days(nowdate(), 5)}]})
		so.insert()
		so.submit()
		rows = [r for r in run(BOSS, erp_flow.orders_to_plan) if r["sales_order"] == so.name]
		self.assertEqual(len(rows), 1)
		self.assertTrue(rows[0]["bom"])
		wo = run(BOSS, erp_flow.make_work_order, so.name, rows[0]["so_item"])
		self.assertEqual(frappe.db.get_value("Work Order", wo["name"], "sales_order"), so.name)
		self.assertFalse([r for r in run(BOSS, erp_flow.orders_to_plan) if r["sales_order"] == so.name])
		self.assertRaises(frappe.PermissionError, run, STORE_U, erp_flow.orders_to_plan)

	def test_stock_count_sends_only_differences(self):
		rows = run(STORE_U, store.count_list, self.stores)
		book = next(r["qty"] for r in rows if r["item_code"] == RAW)
		r = run(STORE_U, store.stock_count, self.stores, [{"item_code": RAW, "qty": book - 2}])
		self.assertEqual(r["differences"], 1)
		self.assertEqual(frappe.db.get_value("Stock Reconciliation", r["name"], "docstatus"), 0)
		self.assertIsNone(run(STORE_U, store.stock_count, self.stores, [{"item_code": RAW, "qty": book}])["name"])

	def test_new_item_and_supplier_without_duplicates(self):
		self.assertTrue(any(r.item_code == RAW for r in run(STORE_U, store.similar_items, "pipe 40x40")))
		name = "SK Test Apex Paint 20 L"
		if frappe.db.exists("Item", name):
			frappe.delete_doc("Item", name, force=True)
		r = run(STORE_U, store.new_item, name, frappe.db.get_value("Item Group", {"is_group": 0}, "name"), "Nos")
		self.assertEqual(frappe.db.get_value("Item", r["name"], "disabled"), 1)
		self.assertRaises(frappe.ValidationError, run, STORE_U, store.new_item, name, "x", "Nos")
		self.assertRaises(frappe.ValidationError, run, BUY_U, purchase.new_supplier, SUPPLIER)
