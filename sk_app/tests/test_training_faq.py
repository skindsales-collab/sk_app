"""Change list point 7: lessons of every function a person has, FAQ per function, Ask a question."""

import frappe
from frappe.tests import IntegrationTestCase

from sk_app import training
from sk_app.tests.test_change_list_a import _app_user

BOSS = "sk_test_t_boss@example.com"
WORKER = "sk_test_t_worker@example.com"


class TestTrainingFaq(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		_app_user(BOSS, "Production", ["Manufacturing User"])
		_app_user(WORKER, "Subcontractor", ["SK Subcontractor"])
		frappe.db.set_value("SK App User", {"user": WORKER}, "manager", BOSS)
		for fn, title in (("Subcontractor", "SK Test sub lesson"), ("Production", "SK Test prod lesson")):
			if not frappe.db.exists("SK Training Lesson", {"title": title}):
				frappe.get_doc({"doctype": "SK Training Lesson", "title": title, "function": fn, "published": 1,
					"lesson_type": "My function", "content": "x"}).insert(ignore_permissions=True)

	def test_ask_answer_goes_into_the_faq(self):
		titles = [r["title"] for r in training.lessons(WORKER, "Subcontractor")]
		self.assertIn("SK Test sub lesson", titles)
		self.assertNotIn("SK Test prod lesson", titles)
		r = training.ask(WORKER, "Paint colour not written on the job: what to do?")
		self.assertEqual(r["owner"], frappe.utils.get_fullname(BOSS))
		todo = training.faq(BOSS)["to_answer"][-1]
		self.assertIn("Paint colour", todo["question"])
		self.assertRaises(frappe.PermissionError, training.answer, WORKER, todo["name"], "x")
		item = training.answer(BOSS, todo["name"], "Ask the supervisor for the RAL number before painting")["faq"]
		self.assertEqual(frappe.db.get_value("SK Library Item", item, "function"), "Subcontractor")
		self.assertIn(item, [x["name"] for x in training.faq(WORKER, "Paint")["rows"]])
		self.assertFalse(training.faq(BOSS)["to_answer"] and training.faq(BOSS)["to_answer"][-1]["name"] == todo["name"])

	def test_hr_production_accounts_faq_seeded(self):
		from sk_app.function_faq import FUNCTION_FAQ, seed_faq

		seed_faq()
		seed_faq()  # twice: no duplicates
		titles = [r["title"] for r in training.faq(BOSS)["rows"]]
		prod = [x[2] for x in FUNCTION_FAQ if x[0] == "Production"]
		self.assertTrue(set(prod) <= set(titles))
		self.assertFalse({x[2] for x in FUNCTION_FAQ if x[0] == "HR"} & set(titles))  # only own function
		self.assertEqual(frappe.db.count("SK Library Item", {"title": prod[0], "category": "FAQ"}), 1)
		for fn in ("HR", "Accounts"):
			self.assertGreaterEqual(sum(1 for x in FUNCTION_FAQ if x[0] == fn), 8)
