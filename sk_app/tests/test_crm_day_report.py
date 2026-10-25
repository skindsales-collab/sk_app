import frappe
from frappe.tests import IntegrationTestCase
from frappe.tests.classes.context_managers import set_user
from frappe.utils import add_to_date, now_datetime

from sk_app import api, day_report

REP = "sk_test_rep@example.com"
BOSS = "sk_test_boss@example.com"
STRANGER = "sk_test_stranger@example.com"


def pdf_bytes():
	import io

	from pypdf import PdfWriter

	w = PdfWriter()
	w.add_blank_page(width=200, height=200)
	buf = io.BytesIO()
	w.write(buf)
	return buf.getvalue()


def make_user(email, roles):
	if not frappe.db.exists("User", email):
		frappe.get_doc({"doctype": "User", "email": email, "first_name": email.split("@")[0], "send_welcome_email": 0,
			"roles": [{"role": r} for r in roles]}).insert(ignore_permissions=True)
	return email


def app_user(email, home, manager=None):
	if not frappe.db.exists("SK App User", email):
		frappe.get_doc({"doctype": "SK App User", "user": email, "home": home, "manager": manager}).insert()


class TestCrmAndDayReport(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		from sk_app.install import after_install

		after_install()
		make_user(REP, ["Sales User", "Employee"])
		make_user(BOSS, ["Sales User", "Employee"])
		make_user(STRANGER, ["Sales User", "Employee"])
		app_user(BOSS, "Sales")
		app_user(REP, "Sales", BOSS)
		app_user(STRANGER, "Sales")
		cls.crm = bool(frappe.db.exists("DocType", "CRM Lead"))

	def test_training_lessons_seeded_and_done(self):
		with set_user(REP):
			rows = api.training_lessons()
			self.assertGreaterEqual(len(rows), 7)
			api.training_done(rows[0].name)
			self.assertTrue(api.training_lessons()[0]["done"])

	def test_day_report_one_per_day_and_manager_review(self):
		with set_user(REP):
			api.add_work("Visited site at Taloja")
			name = api.send_day_report("Two site visits, one quote", problems="Need drawing", plan_tomorrow="Call ABC")
			again = api.send_day_report("Two site visits, one quote, updated")
			self.assertEqual(name, again)
			doc = frappe.get_doc("SK Day Report", name)
			self.assertEqual(doc.manager, BOSS)
			self.assertGreaterEqual(doc.work_entries, 1)
			self.assertIn("Taloja", doc.auto_summary)
			self.assertTrue(api.home()["day_report_sent"])
		with set_user(BOSS):
			team = api.team_day_reports()
			self.assertEqual(team["sent"], 1)
			self.assertIn("team_reports", api.home()["home"]["tiles"])
			api.review_day_report(name, "Good", "Well done")
		self.assertEqual(frappe.db.get_value("SK Day Report", name, "manager_rating"), "Good")
		with set_user(STRANGER):
			self.assertRaises(frappe.PermissionError, api.review_day_report, name, "OK")
			self.assertEqual(api.team_day_reports()["total"], 0)

	def test_day_report_needs_text(self):
		with set_user(REP):
			self.assertRaises(frappe.ValidationError, api.send_day_report, "  ")

	def test_reminder_only_near_work_end_and_until_sent(self):
		due = day_report.due_at()
		self.assertEqual(day_report.reminder(STRANGER, add_to_date(due, hours=-3)), [])
		self.assertEqual(len(day_report.reminder(STRANGER, add_to_date(due, minutes=-30))), 1)

	def test_crm_new_lead_follow_up_and_call_log(self):
		if not self.crm:
			self.skipTest("Frappe CRM not installed")
		with set_user(REP):
			name = api.new_lead("Ramesh", mobile_no="9876543210", organization="SK Test Cabins Ltd", segment="Cabin",
				requirement="2 site cabins 20x10")
			rows = [r for r in api.follow_up() if r["name"] == name]
			self.assertTrue(rows and rows[0]["new"])
			api.log_contact("CRM Lead", name, "Call", "Talked", "Wants quote by Monday")
			d = api.crm_detail("CRM Lead", name)
			self.assertEqual(d["doc"]["sk_segment"], "Cabin")
			self.assertEqual(len(d["calls"]), 1)
			self.assertTrue(any("Requirement" in n["title"] for n in d["notes"]))
			self.assertTrue(frappe.db.get_value("CRM Lead", name, "first_responded_on"))
			self.assertEqual(day_report.captured(REP)["calls_made"], 1)
			# the CRM's own assignment ToDo must not show the lead a second time
			self.assertFalse([i for i in api.my_day()["items"] if i["kind"] == "task" and i["name"] == name])
		with set_user(STRANGER):
			self.assertRaises(frappe.PermissionError, api.crm_detail, "CRM Lead", name)

	def test_ai_drawing_alerts_owner_until_sent(self):
		if not self.crm:
			self.skipTest("Frappe CRM not installed")
		with set_user(REP):
			lead = api.new_lead("Suresh", mobile_no="9876500000", organization="SK Test Drawing Co")
		with set_user(BOSS):  # stands in for the AI design user
			def attach(fname):
				return frappe.get_doc({"doctype": "File", "file_name": fname, "content": pdf_bytes() if fname.endswith(".pdf") else b"x", "is_private": 1,
					"attached_to_doctype": "CRM Lead", "attached_to_name": lead}).insert(ignore_permissions=True)
			pdf = attach("Cabin99_Test_Customer_Drawing_GA-01C_Rev0.pdf")
			attach("Cabin99_Test_BOM_Costing_Quote_Rev0.xlsx")
			attach("Cabin99_Test_BOM_Costing_Rev0.pdf")
		from sk_app import crm

		crm.alert_owner(REP)
		self.assertEqual(frappe.session.user, "Administrator")
		with set_user(REP):
			self.assertEqual([f.name for f in api.home()["new_files"]], [pdf.name])
			card = frappe.get_all("SK Guide Card", filters={"user": REP}, fields=["card_text", "reference_name"],
				order_by="creation desc", limit=1)[0]
			self.assertIn("Cabin99", card.card_text)
			self.assertEqual(card.reference_name, pdf.name)
			api.mark_file_sent(pdf.name)
			self.assertEqual(api.home()["new_files"], [])
			self.assertFalse([i for i in api.my_day()["items"] if i["kind"] == "send_file"])
			self.assertTrue(any("Sent Cabin99" in n["title"] for n in api.crm_detail("CRM Lead", lead)["notes"]))

	def test_drawing_correction_goes_back_to_design(self):
		if not self.crm:
			self.skipTest("Frappe CRM not installed")
		from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

		# sk-dev has a Design Status select used by the AI design flow; make a stand-in here
		create_custom_fields({"CRM Lead": [{"fieldname": "sk_test_design_status", "label": "Design Status", "fieldtype": "Select",
			"options": "\nSent to Design\nDrawing Sent\nRevision Requested\nDrawing Approved", "insert_after": "status"}]})
		with set_user(REP):
			lead = api.new_lead("Mahesh", mobile_no="9876511111", organization="SK Test Correction Co")
			self.assertRaises(frappe.ValidationError, api.request_correction, "CRM Lead", lead, "  ")
			r = api.request_correction("CRM Lead", lead, "Door on the 10 ft side, add one window")
			self.assertTrue(r["status_set"])
			d = api.crm_detail("CRM Lead", lead)
			self.assertEqual(d["doc"]["design_status"], "Revision Requested")
			self.assertTrue(any("add one window" in n["content"] for n in d["notes"]))
		with set_user(STRANGER):
			self.assertRaises(frappe.PermissionError, api.request_correction, "CRM Lead", lead, "change")

	def test_share_link_only_for_quotation_and_sales_order(self):
		with set_user(REP):
			self.assertRaises(frappe.ValidationError, api.share_link, "User", REP)
