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

	def test_function_manuals_seeded(self):
		from sk_app.manuals import FUNCTION_LESSONS
		from sk_app.training import seed_lessons

		seed_lessons()
		have = set(frappe.get_all("SK Training Lesson", filters={"published": 1}, pluck="function"))
		for fn in ("Production", "Subcontractor", "Stores", "Purchase", "Quality", "Accounts", "HR", "AI", "Management"):
			self.assertIn(fn, have)
		self.assertEqual(len({x[0] for x in FUNCTION_LESSONS}), len(FUNCTION_LESSONS))

	def test_manual_lessons_with_quiz(self):
		from sk_app.manual_lessons import MANUAL_LESSONS
		from sk_app.training import mark_done, seed_lessons

		seed_lessons()
		titles = [x[0] for x in MANUAL_LESSONS]
		self.assertEqual(len(set(titles)), len(titles))
		for fn in ("Sales", "Marketing", "Accounts", "Management", "All", "Production", "Stores", "Purchase", "Quality", "HR", "AI"):
			self.assertIn(fn, {x[2] for x in MANUAL_LESSONS})
		for row in MANUAL_LESSONS:
			self.assertNotIn("salary", (row[4] + row[5] + str(row[6])).lower())  # SK 26-Oct: salary is confidential
			for _q, choices, ok in row[6]:
				self.assertEqual(len(choices), 3)
				self.assertIn(ok, (1, 2, 3))
		name = frappe.db.get_value("SK Training Lesson", {"title": titles[0]})
		doc = frappe.get_doc("SK Training Lesson", name)
		self.assertEqual(len(doc.questions), len(MANUAL_LESSONS[0][6]))
		right = [int(q.correct) for q in doc.questions]
		wrong = [1 + (r % 3) for r in right]
		self.assertFalse(mark_done(REP, name, wrong)["passed"])
		self.assertTrue(mark_done(REP, name, right)["passed"])
		seed_lessons()  # seeding again keeps one set of questions
		self.assertEqual(len(frappe.get_doc("SK Training Lesson", name).questions), len(right))

	def test_routine_on_my_day(self):
		from datetime import datetime

		from sk_app.calendar_view import routine_today

		with self.subTest("Production 5S at 3 pm is on a weekday's My Day"):
			import sk_app.calendar_view as cv
			orig = cv._routine
			cv._routine = lambda u: [("daily", "15:00", 15, "5S (15 minutes)"), ("Sun", "10:00", 10, "x"), ("daily", None, 5, "y")]
			try:
				day = datetime(2026, 10, 26, 9, 0)  # a Monday
				out = routine_today(REP, day.date(), day)
				self.assertEqual([t for _s, _e, t in out], ["🔁 5S (15 minutes)"])
				self.assertEqual(routine_today(REP, day.date(), datetime(2026, 10, 26, 16, 0)), [])
			finally:
				cv._routine = orig
