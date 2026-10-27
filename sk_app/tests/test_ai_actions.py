"""SK 27-Oct points 3 / 6: AI actions every morning from ERPNext data, with the reason; Start here on empty graphs."""

import frappe
from frappe.tests import IntegrationTestCase

from sk_app import ai_actions, home_kpi
from sk_app.tests.test_change_list_a import _app_user
from sk_app.tests.test_store_purchase import run

BOSS = "sk_test_ai_prod@example.com"


class TestAiActions(IntegrationTestCase):
	def test_morning_actions_kept_and_cancelled(self):
		_app_user(BOSS, "Production", ["Manufacturing User"])
		frappe.db.delete("ToDo", {"allocated_to": BOSS})
		orig = ai_actions.rules
		ai_actions.rules = lambda u, f: [
			{"key": "late:Production:fabrication", "term": "short", "days": 0, "priority": "High", "text": "Clear the 2 late in Fabrication", "why": "2 of 3 waiting, oldest 9 days"},
			{"key": "start", "term": "long", "days": 7, "priority": "Medium", "text": "Start here: finish Work Orders", "why": "Your graph has no data in ERPNext yet"}]
		try:
			self.assertEqual(ai_actions.refresh(BOSS), 2)
			self.assertEqual(ai_actions.refresh(BOSS), 2)
			self.assertEqual(home_kpi.open_actions(BOSS), 2)  # not made twice
			a = run(BOSS, home_kpi.actions, BOSS)["actions"]
			first = next(x for x in a if "Fabrication" in x["text"])
			self.assertTrue(first["ai"])
			self.assertEqual((first["term"], first["why"], first["priority"]), ("Short term", "2 of 3 waiting, oldest 9 days", "High"))
			self.assertNotIn("[ai:", first["text"])
			ai_actions.rules = lambda u, f: [{"key": "start", "term": "long", "days": 7, "priority": "Medium", "text": "Start here: finish Work Orders", "why": "x"}]
			ai_actions.refresh(BOSS)
			self.assertEqual(home_kpi.open_actions(BOSS), 1)  # the fixed one is cancelled
		finally:
			ai_actions.rules = orig

	def test_real_rules_run(self):
		_app_user(BOSS, "Production", ["Manufacturing User"])
		out = ai_actions.rules(BOSS, ["Production"])
		self.assertTrue(all({"key", "text", "why", "term", "priority"} <= set(r) for r in out))
		self.assertTrue(any(r["key"] == "start" or r["key"].startswith("late:") or r["key"] == "trend" for r in out))
