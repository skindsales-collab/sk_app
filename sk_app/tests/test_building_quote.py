"""SK 27-Oct: PUF / EPS building quotation gives the same numbers as SK's Quotation Calculator Excel
(its sample: Legacy Poonawale R04, two G+1 PUF blocks, 240 double bunk beds)."""

import json

import frappe
from frappe.tests import IntegrationTestCase

from sk_app import building_quote, cabin_quote
from sk_app.tests.test_change_list_a import _app_user
from sk_app.tests import test_store_purchase as tsp
from sk_app.tests.test_store_purchase import CUSTOMER

REP = "sk_test_bq_rep@example.com"
BOSS = "sk_test_bq_boss@example.com"
BLK = {"canopy_width": 1.15, "canopy_sides": 1, "stair_width": 1.15, "stairs": 2, "room_width": 12, "floors": "G+1", "height": 6, "nos": 1}
LEGACY = {"panel": "PUF", "electrical": True, "transport": True, "zone": "Pune & PCMC", "special_discount": 0,
	"blocks": [{**BLK, "name": "Bachelors Labour Room", "code": "6K X 24K X 6P", "length": 43.84, "width": 11.16, "stair_length": 13.27, "room_depth": 18, "people": 10},
		{**BLK, "name": "Family Room", "code": "6K X 24K X 6P", "length": 43.84, "width": 7.52, "stair_length": 9.63, "room_depth": 12, "people": 4}],
	"addons": {"Double Bunk Bed (with ply)": 240}}


class TestBuildingQuote(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		tsp.TestStorePurchase.setUpClass.__func__(tsp.TestStorePurchase)
		_app_user(REP, "Sales", ["Sales User"])
		_app_user(BOSS, "Management", ["Sales Manager"])
		cabin_quote.ensure_setup()
		frappe.db.commit()

	def test_same_as_excel(self):
		p = building_quote.price(LEGACY)
		self.assertAlmostEqual(p["total_area"], 20360.033264, places=4)
		self.assertEqual([x["total_rate"] for x in p["blocks"]], [760, 760])  # 750 G+1 PUF - 40 volume slab + 50 electrical
		self.assertAlmostEqual(p["structure"], 15473625.28064, places=3)
		self.assertEqual(p["addon_value"], 1632000)
		self.assertAlmostEqual(p["total"], 17105625.28064, places=3)
		self.assertEqual((p["rooms"], p["people"], p["beds"], p["trips"]), (96, 672, 336, 17))
		self.assertAlmostEqual(p["cost"], 13349816.2982304, places=2)
		self.assertAlmostEqual(p["margin"], 0.219565723017468, places=6)
		self.assertEqual(p["approval"], [])

	def test_rules(self):
		eps = building_quote.price({**LEGACY, "panel": "EPS", "transport": False, "electrical": False, "zone": "Outside Maharashtra", "special_discount": 25})
		self.assertEqual(eps["blocks"][0]["total_rate"], 660 + 40 - 40 - 15 - 25)
		self.assertTrue(any("discount" in w for w in eps["approval"]))  # above Rs 20 / sq ft: SK approves
		# only SK may override the rate
		ov = {**LEGACY, "blocks": [{**LEGACY["blocks"][0], "rate_override": 500}]}
		self.assertEqual(building_quote.price(ov)["blocks"][0]["rate"], 725)  # one block: 11,942 sq ft, slab -25
		self.assertEqual(building_quote.price(ov, may_override=True)["blocks"][0]["rate"], 500)
		self.assertTrue(any("margin" in w for w in building_quote.price(ov, may_override=True)["approval"]))
		with self.assertRaises(frappe.ValidationError):
			building_quote.price({**LEGACY, "blocks": [{"length": 0, "width": 5}]})
		# the salesperson does not see cost and margin
		self.assertNotIn("margin", building_quote.public(building_quote.price(LEGACY), REP))
		self.assertIn("margin", building_quote.public(building_quote.price(LEGACY), BOSS))

	def test_quotation_and_print(self):
		frappe.set_user(REP)
		try:
			r = building_quote.make(REP, LEGACY, customer=CUSTOMER)
			r2 = building_quote.make(REP, {**LEGACY, "special_discount": 30}, customer=CUSTOMER, revise=r["name"])
		finally:
			frappe.set_user("Administrator")
		q = frappe.get_doc("Quotation", r["name"])
		self.assertTrue(q.sk_quote_ref.startswith("SK/BLD/"))
		self.assertEqual(len(q.items), 3)
		self.assertAlmostEqual(r["net_total"], 17105625.28, delta=5)  # sq ft kept to 2 decimals on the quotation
		self.assertEqual((r2["name"], q.sk_rev, q.sk_discount_status), (r["name"], 1, "Requested"))
		html = cabin_quote.quote_html(q)
		for text in ("WAITING FOR SK APPROVAL", "Bachelors Labour Room", "Capacity", "50 mm PUF Panels", "Sq ft calculation details", "General terms"):
			self.assertIn(text, html)
		self.assertTrue(any(x.sk_quote_ref == q.sk_quote_ref for x in cabin_quote.discount_requests(BOSS)))
		cabin_quote.decide_discount(BOSS, q.name, 1)
		q.reload()
		self.assertEqual((q.sk_discount_status, q.additional_discount_percentage), ("Approved", 0))
		self.assertNotIn("WAITING FOR SK", cabin_quote.quote_html(q))
		self.assertEqual(json.loads(q.sk_cabin_request)["kind"], "building")
