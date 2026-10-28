"""Change list point 7: lessons of every function a person has, FAQ per function, Ask a question."""

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from sk_app import training
from sk_app.tests.test_change_list_a import _app_user

BOSS = "sk_test_t_boss@example.com"
CEO = "sk_test_t_ceo@example.com"
WORKER = "sk_test_t_worker@example.com"


class TestTrainingFaq(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		_app_user(BOSS, "Production", ["Manufacturing User"])
		_app_user(WORKER, "Subcontractor", ["SK Subcontractor"])
		_app_user(CEO, "Management", ["System Manager"])
		frappe.db.set_value("SK App User", {"user": WORKER}, "manager", BOSS)
		for fn, title in (("Subcontractor", "SK Test sub lesson"), ("Production", "SK Test prod lesson")):
			if not frappe.db.exists("SK Training Lesson", {"title": title}):
				frappe.get_doc({"doctype": "SK Training Lesson", "title": title, "function": fn, "published": 1,
					"lesson_type": "My function", "content": "x"}).insert(ignore_permissions=True)

	def test_ask_answer_goes_into_the_faq(self):
		titles = [r["title"] for r in training.lessons(WORKER, "Subcontractor")]
		self.assertIn("SK Test sub lesson", titles)
		self.assertNotIn("SK Test prod lesson", titles)
		with patch.object(training, "_ceos", return_value=[]):  # no CEO login: the person's manager answers
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

	def test_question_to_ceo_grouped_answered_or_sent_for_development(self):
		"""SK 28-Oct (Rev 1 point 6): My question → CEO grouped with a summary → answer → FAQ, or → development → deployed."""
		with patch.object(training, "_ceos", return_value=[CEO]):
			a = training.ask(WORKER, "How to attach the job card photo?")
			b = training.ask(BOSS, "Job card photo upload fails on my phone")
			self.assertEqual(a["owner"], frappe.utils.get_fullname(CEO))
			self.assertRaises(frappe.PermissionError, training.questions, WORKER)
			d = training.questions(CEO)
			mine = [g for g in d["groups"] if a["todo"] in [r["todo"] for r in g["rows"]]][0]
			self.assertIn("question", mine["summary"])
			training.answer(CEO, a["todo"], "Tap Done, then Camera")
			self.assertTrue(frappe.db.exists("ToDo", {"allocated_to": WORKER, "description": ["like", "Answer to your question%"]}))
			w = training.send_for_development(CEO, b["todo"], "check the upload size")["work_log"]
			self.assertEqual(frappe.db.get_value("ToDo", b["todo"], "status"), "Closed")
			self.assertIn(w, [x.name for x in training.questions(CEO)["dev"]])
			from sk_app import ai_desk

			self.assertIn(w, [i["name"] for i in ai_desk.inbox("Administrator")["new"]])  # in the AI & ERP inbox
			training.mark_deployed(CEO, w, "App")
			self.assertEqual(frappe.db.get_value("SK Work Log", w, "status"), "Done")
			self.assertNotIn(w, [x.name for x in training.questions(CEO)["dev"]])
			self.assertTrue(frappe.db.exists("ToDo", {"allocated_to": BOSS, "description": ["like", "Done:%SK App%"]}))
