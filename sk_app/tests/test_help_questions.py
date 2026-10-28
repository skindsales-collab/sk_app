"""SK 28-Oct: ❓ on every screen. The screen name travels with the question, Claude's draft is kept for the CEO, the FAQ
gets the clean question, and "send for development" also lands on the IT / ERP desk (SK Hub handoff)."""

import json
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from sk_app import training
from sk_app.tests.test_change_list_a import _app_user

STORE = "sk_test_help_store@example.com"
CEO = "sk_test_help_ceo@example.com"


class TestHelpQuestions(IntegrationTestCase):
	def setUp(self):
		_app_user(STORE, "Stores", ["Stock User"])
		_app_user(CEO, "Management", ["System Manager"])

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_screen_kept_apart_from_question(self):
		q = "Receipt not saving" + training.SCREEN_TAG + "Receive · receive⟧"
		self.assertEqual(training.split_screen(q), ("Receipt not saving", "Receive · receive"))
		self.assertEqual(training.split_screen("No screen here"), ("No screen here", ""))

	def test_question_with_screen_and_ai_draft_reach_the_ceo(self):
		draft = {"answer": "Tap Receive, pick the PO.", "answer_marathi": "...", "action": "how_to", "action_note": "", "faq_title": "How to receive"}
		with patch("sk_app.training._ceos", return_value=[CEO]), patch("frappe.enqueue"):
			r = training.ask(STORE, "How do I receive without a PO?", "Stores", None, "Receive · receive")
		with patch("sk_app.claude.available", return_value=True), patch("sk_app.claude.help_draft", return_value=draft):
			training.ai_draft(r["todo"])
		with patch("sk_app.training._ceos", return_value=[CEO]):
			rows = [x for g in training.questions(CEO)["groups"] for x in g["rows"]]
		row = next(x for x in rows if x["todo"] == r["todo"])
		self.assertEqual(row["question"], "How do I receive without a PO?")
		self.assertEqual(row["screen"], "Receive · receive")
		self.assertEqual(row["ai"]["action"], "how_to")

	def test_faq_gets_clean_question(self):
		with patch("sk_app.training._ceos", return_value=[CEO]), patch("frappe.enqueue"):
			r = training.ask(STORE, "Where is low stock?", "Stores", None, "Home · home")
		with patch("sk_app.training._ceos", return_value=[CEO]):
			out = training.answer(CEO, r["todo"], "Store → Low Stock tile.", 1)
		self.assertEqual(frappe.db.get_value("SK Library Item", out["faq"], "title"), "Where is low stock?")

	def test_send_for_development_goes_to_it_desk(self):
		with patch("sk_app.training._ceos", return_value=[CEO]), patch("frappe.enqueue"):
			r = training.ask(STORE, "Issue button gives error", "Stores", None, "Issue · issue")
		with patch("sk_app.training._ceos", return_value=[CEO]):
			out = training.send_for_development(CEO, r["todo"], "Check job card mapping")
		if frappe.db.exists("DocType", "SK Hub Handoff"):
			h = frappe.get_doc("SK Hub Handoff", out["handoff"])
			self.assertEqual(h.to_team, "IT / ERP")
			self.assertIn("Screen: Issue · issue", h.details)
