import json

import frappe
from frappe.tests import IntegrationTestCase
from frappe.tests.classes.context_managers import set_user
from frappe.utils import add_to_date, now_datetime

from sk_app import api, comms, day_report, library, training
from sk_app.tests.test_crm_day_report import app_user, make_user

REP = "sk_test_rep2@example.com"
BOSS = "sk_test_boss2@example.com"
OTHER = "sk_test_other2@example.com"
CEO = "sk_test_ceo2@example.com"


class TestCommsAndLibrary(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		from sk_app.install import after_install

		after_install()
		for u in (REP, BOSS, OTHER, CEO):
			make_user(u, ["Sales User", "Employee"])
		app_user(CEO, "Sales")
		app_user(BOSS, "Sales", CEO)
		app_user(REP, "Sales", BOSS)
		app_user(OTHER, "Sales")
		cls.crm = bool(frappe.db.exists("DocType", "CRM Lead"))

	def _lead(self, org):
		return api.new_lead("Suresh", mobile_no="9822011111", organization=f"{org} {frappe.generate_hash(length=5)}", segment="LGSF")

	def test_call_talk_time_summary_and_team_view(self):
		if not self.crm:
			self.skipTest("Frappe CRM not installed")
		with set_user(REP):
			before = comms.call_totals(REP, frappe.utils.getdate())
			name = self._lead("Talk Time Pvt Ltd")
			api.log_contact("CRM Lead", name, "Call", "Talked", "Wants 3 cabins", duration=185)
			api.log_contact("CRM Lead", name, "Call", "No answer", duration=40)  # no answer: no talk time
			api.add_call("CRM Lead", name, direction="Incoming", outcome="Talked", minutes=2, text="Customer called back")
			api.add_call("CRM Lead", name, direction="Incoming", outcome="Missed", minutes=1)  # missed: no talk time
			today = api.my_calls()["today"]
			self.assertEqual(today["calls"], before["calls"] + 4)
			self.assertEqual(today["missed"], before["missed"] + 2)  # no answer + missed
			self.assertEqual(day_report.captured(REP)["missed_calls"], today["missed"])
			self.assertEqual(today["talk_seconds"], before["talk_seconds"] + 185 + 120)
			self.assertEqual(day_report.captured(REP)["talk_minutes"], round(today["talk_seconds"] / 60))
			log = frappe.get_all("CRM Call Log", filters={"reference_docname": name, "type": "Incoming", "status": "Completed"}, fields=["receiver", "duration"])
			self.assertEqual((log[0].receiver, log[0].duration), (REP, 120))
		with set_user(BOSS):
			mine = [p for p in api.team_calls()["people"] if p["user"] == REP]
			self.assertEqual(mine[0]["day"]["talk_seconds"], today["talk_seconds"])
		with set_user(CEO):  # the whole chain: CEO -> manager -> salesperson
			self.assertTrue([p for p in api.team_calls()["people"] if p["user"] == REP])
		with set_user(OTHER):
			self.assertFalse([p for p in api.team_calls()["people"] if p["user"] == REP])

	def test_reminders_event_task_repeat_and_due(self):
		with set_user(REP):
			soon = add_to_date(now_datetime(), minutes=-1)
			r = api.add_reminder("Call Mr Patil about cabin", str(soon))
			self.assertEqual(r["doctype"], "Event")
			daily = api.add_reminder("Check IndiaMART buy leads", str(add_to_date(now_datetime(), days=-3, minutes=-2)), "Daily")
			due = {x["name"] for x in api.home()["due_reminders"]}
			self.assertIn(r["name"], due)
			self.assertIn(daily["name"], due)  # repeats every day
			self.assertTrue([i for i in api.my_day()["items"] if i["kind"] == "reminder" and i["name"] == r["name"]])
			week = api.cal_week()
			self.assertTrue(any(e["title"] == "Check IndiaMART buy leads" for d in week["days"] for e in d["events"]))
			api.done_reminder("Event", r["name"])
			self.assertEqual(frappe.db.get_value("Event", r["name"], "status"), "Completed")
			self.assertRaises(frappe.ValidationError, api.add_reminder, "", str(soon))
			if self.crm:
				lead = self._lead("Reminder Lead Ltd")
				t = api.add_reminder("Send revised quote", str(add_to_date(now_datetime(), hours=2)), doctype="CRM Lead", name=lead)
				self.assertEqual(t["doctype"], "CRM Task")
				self.assertEqual(frappe.db.get_value("CRM Task", t["name"], "assigned_to"), REP)
		with set_user(BOSS):
			given = api.add_reminder("Visit Chakan site", str(add_to_date(now_datetime(), hours=3)), for_user=REP)
			self.assertEqual(frappe.db.get_value("Event", given["name"], "owner"), REP)
		with set_user(OTHER):
			self.assertRaises(frappe.PermissionError, api.add_reminder, "x", str(soon), for_user=REP)

	def test_mail_needs_email_account(self):
		if not self.crm:
			self.skipTest("Frappe CRM not installed")
		with set_user(REP):
			name = self._lead("Mail Test Ltd")
			box = api.my_mail()
			self.assertIn("ready", box)
			if not box["ready"]:
				self.assertRaises(frappe.ValidationError, api.send_mail, "CRM Lead", name, "a@b.com", "Quote", "Please see")
			self.assertEqual(api.mail_thread("CRM Lead", name), [])
		if not frappe.db.exists("Email Account", "SK Test Outgoing"):
			frappe.get_doc({"doctype": "Email Account", "email_account_name": "SK Test Outgoing", "email_id": "sales@sk-test.example",
				"enable_outgoing": 1, "smtp_server": "smtp.sk-test.example", "smtp_port": 587, "password": "x",
				"default_outgoing": 1}).insert(ignore_permissions=True)
		from unittest.mock import patch

		# the local test bench has no built website assets for the mail stylesheet; the real site has them
		with set_user(REP), patch("frappe.email.email_body.inline_style_in_html", lambda html, **kw: html):
			self.assertTrue(api.my_mail()["ready"])
			photo = frappe.get_doc({"doctype": "File", "file_name": "sk_drawing.pdf", "content": _pdf(1), "is_private": 1,
				"attached_to_doctype": "CRM Lead", "attached_to_name": name}).insert(ignore_permissions=True)
			api.send_mail("CRM Lead", name, "buyer@customer.example", "Cabin quotation", "Dear sir,\nPlease find the drawing.",
				[photo.name])
			thread = api.mail_thread("CRM Lead", name)
			self.assertEqual(thread[0]["subject"], "Cabin quotation")
			self.assertIn("drawing", thread[0]["text"])
			self.assertTrue([m for m in api.my_mail()["mails"] if m["reference_name"] == name])
		with set_user(OTHER):
			self.assertRaises(frappe.PermissionError, api.mail_thread, "CRM Lead", name)

	def test_library_pack_sections_and_training_check(self):
		manual = frappe.get_doc({"doctype": "File", "file_name": "sk_test_manual.pdf", "content": _pdf(5), "is_private": 1}).insert(
			ignore_permissions=True)
		old = frappe.db.get_single_value("SK App Settings", "sales_manual")
		self.addCleanup(frappe.db.set_single_value, "SK App Settings", "sales_manual", old)
		frappe.db.set_single_value("SK App Settings", "sales_manual", manual.file_url)
		pack = {
			"library": [
				{"key": "faq", "title": "SK test: Why is your price higher?", "category": "Customer FAQ", "audience": "Customer",
					"text": "Heavy-duty chassis, no repair cost.", "sequence": 1},
				{"key": "pitch", "title": "SK test: Manual - first call", "category": "Sales Manual", "audience": "Internal",
					"function": "Sales", "page_from": 2, "page_to": 3},
			],
			"lessons": [
				{"title": "SK test: First call pitch", "lesson_type": "My function", "function": "Sales", "published": 1,
					"minutes": 5, "content": "<p>Ask site and duration.</p>", "library_key": "pitch",
					"questions": [
						{"question": "First call within?", "choice_1": "5 min", "choice_2": "1 day", "correct": "1"},
						{"question": "Send designs on?", "choice_1": "Post", "choice_2": "WhatsApp", "correct": "2"},
						{"question": "Ask about?", "choice_1": "Site and duration", "choice_2": "Cricket", "correct": "1"},
					]},
			],
		}
		self.assertEqual(library.load_pack(json.dumps(pack)), {"lessons": 1, "library": 2})
		self.assertEqual(library.load_pack(json.dumps(pack)), {"lessons": 1, "library": 2})  # again: updates only
		self.assertEqual(frappe.db.count("SK Library Item", {"title": "SK test: Why is your price higher?"}), 1)
		with set_user(REP):
			items = {i["title"]: i for i in api.library()}
			section = items["SK test: Manual - first call"]
			self.assertEqual(section["kind"], "pages")
			self.assertFalse(section["sendable"])
			self.assertTrue(items["SK test: Why is your price higher?"]["sendable"])
			data, _title = library.section_pdf(section["name"])
			import io

			from pypdf import PdfReader

			self.assertEqual(len(PdfReader(io.BytesIO(data)).pages), 2)
			lesson = [r for r in api.training_lessons() if r["title"] == "SK test: First call pitch"][0]
			self.assertEqual(lesson["lesson_type"], "My function")
			full = api.training_lesson(lesson["name"])
			self.assertEqual(len(full["questions"]), 3)
			self.assertNotIn("correct", json.dumps(full["questions"]))
			self.assertTrue(full["pages_url"])
			self.assertFalse(api.training_done(lesson["name"], ["2", "1", "2"])["passed"])
			res = api.training_done(lesson["name"], ["1", "2", "2"])
			self.assertEqual((res["passed"], res["score"]), (True, 2))
			self.assertEqual([r for r in api.training_lessons() if r["name"] == lesson["name"]][0]["score"], "2/3")
		with set_user(BOSS):
			mine = [p for p in api.team_training()["people"] if p["user"] == REP]
			self.assertGreaterEqual(mine[0]["done"], 1)
		self.assertEqual(training.pass_mark(3), 2)
		self.assertEqual(training.pass_mark(4), 3)


def _pdf(pages):
	import io

	from pypdf import PdfWriter

	w = PdfWriter()
	for _ in range(pages):
		w.add_blank_page(width=200, height=200)
	buf = io.BytesIO()
	w.write(buf)
	return buf.getvalue()
