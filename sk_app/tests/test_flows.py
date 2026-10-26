"""Change list point 17: interactive work flow boxes for every function."""

import frappe
from frappe.tests import IntegrationTestCase

from sk_app import flows
from sk_app.tests.test_sk_app_api import make_user
from sk_app.tests.test_store_purchase import run

REP = "sk_test_flow_rep@example.com"


class TestFlows(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_user(REP, ["Sales User", "Employee"])

	def test_flows_per_function(self):
		r = run(REP, flows.for_user, ["Sales", "Marketing"])
		self.assertEqual([f["function"] for f in r["flows"]], ["Sales"])  # Marketing shares the CRM flow
		for st in r["flows"][0]["stages"]:
			self.assertTrue({"key", "label", "count", "late", "rows"} <= set(st))
		ceo = run("Administrator", flows.for_user, ["Management"])
		self.assertTrue(all(f["function"] == "Management" for f in ceo["flows"]))
		self.assertGreaterEqual(len(ceo["flows"]), 2)
		self.assertEqual(run(REP, flows.for_user, ["Nothing"])["flows"], [])
