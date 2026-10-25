import frappe
from frappe.desk.form.assign_to import add as assign
from frappe.tests import IntegrationTestCase
from frappe.tests.classes.context_managers import set_user

from sk_app import api, setup

SALES = "sk_test_sales@example.com"
OTHER = "sk_test_other@example.com"


def make_user(email, roles):
	if not frappe.db.exists("User", email):
		frappe.get_doc({"doctype": "User", "email": email, "first_name": email.split("@")[0], "send_welcome_email": 0,
			"roles": [{"role": r} for r in roles]}).insert(ignore_permissions=True)
	return email


class TestSKAppAPI(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		from sk_app.install import after_install

		after_install()
		for email in (SALES, OTHER):
			make_user(email, ["Sales User", "Employee"])
		if not frappe.db.exists("SK App User", SALES):
			frappe.get_doc({"doctype": "SK App User", "user": SALES, "home": "Sales"}).insert()
		frappe.db.delete("SK KPI Target", {"user": SALES})
		for label, code, target, weight, manual in (("DSI", "dsi_count", 26, 50, 0), ("Price", "manual", 100, 50, 50)):
			frappe.get_doc({"doctype": "SK KPI Target", "user": SALES, "kra": label, "kpi_label": label, "kpi_code": code,
				"monthly_target": target, "unit": "Count", "weight": weight, "manual_actual": manual}).insert()
		task = frappe.get_doc({"doctype": "Task", "subject": "SK test: send quote to ABC", "status": "Open", "priority": "High"}).insert()
		assign({"assign_to": [SALES], "doctype": "Task", "name": task.name, "description": task.subject})
		cls.task = task.name

	def test_home_has_sales_tiles(self):
		with set_user(SALES):
			h = api.home()
		self.assertEqual(h["home"]["function"], "Sales")
		self.assertIn("my_leads", h["home"]["tiles"])

	def test_my_day_lists_assigned_task_and_dsi(self):
		frappe.db.delete("SK DSI Entry", {"user": SALES})
		with set_user(SALES):
			items = api.my_day()["items"]
		kinds = {(i["kind"], i["name"]) for i in items}
		self.assertIn(("task", self.task), kinds)
		self.assertTrue(any(i["kind"] == "dsi" for i in items))

	def test_dsi_counts_in_kpi(self):
		frappe.db.delete("SK DSI Entry", {"user": SALES})
		with set_user(SALES):
			api.add_dsi("Labelled the paint shelves so tins are found faster")
			card = api.my_kpi()
			items = api.my_day()["items"]
		dsi = next(k for k in card["kpis"] if k["kpi_code"] == "dsi_count")
		self.assertEqual(dsi["actual"], 1)
		self.assertFalse(any(i["kind"] == "dsi" for i in items))
		# manual KPI 50/100 at weight 50 gives 25 points, DSI 1/26 at weight 50 gives 1.92
		self.assertAlmostEqual(card["total_score"], 26.9, places=1)

	def test_guide_card_rules_and_replan(self):
		with set_user(SALES):
			card = api.next_card(force=1)
			self.assertEqual(card["source"], "Rules")  # no API key in tests
			self.assertTrue(card["card_text"].startswith("Now:"))
			again = api.next_card()
			self.assertEqual(again["name"], card["name"])  # reused within 10 minutes
			new = api.respond_card(card["name"], "Done")
			self.assertNotEqual(new["name"], card["name"])
		self.assertEqual(frappe.db.get_value("SK Guide Card", card["name"], "response"), "Done")

	def test_cannot_answer_someone_elses_card(self):
		with set_user(SALES):
			card = api.next_card(force=1)
		frappe.get_doc({"doctype": "SK App User", "user": OTHER, "home": "Production"}).insert(ignore_if_duplicate=True)
		with set_user(OTHER), self.assertRaises(frappe.PermissionError):
			api.respond_card(card["name"], "Done")

	def test_not_set_up_user_is_refused(self):
		make_user("sk_test_nobody@example.com", ["Employee"])
		with set_user("sk_test_nobody@example.com"), self.assertRaises(frappe.PermissionError):
			api.home()

	def test_problem_report_saved_for_self(self):
		with set_user(SALES):
			name = api.add_work("Grinder stopped", entry_type="Problem", problem_type="Machine breakdown")
		doc = frappe.get_doc("SK Work Log", name)
		self.assertEqual((doc.user, doc.entry_type), (SALES, "Problem"))

	def test_other_function_gets_common_screens(self):
		frappe.get_doc({"doctype": "SK App User", "user": OTHER, "home": "Production"}).insert(ignore_if_duplicate=True)
		with set_user(OTHER):
			h = api.home()
		self.assertIn("my_day", h["home"]["tiles"])
		self.assertIn("job_cards", h["home"]["tiles"])

	def test_order_and_lead_kpis_do_not_break(self):
		from sk_app import kpi

		for code in ("orders_value", "cabins_qty", "quotes_sent", "leads_worked"):
			frappe.get_doc({"doctype": "SK KPI Target", "user": OTHER, "kra": code, "kpi_label": code, "kpi_code": code,
				"monthly_target": 10, "unit": "Count", "weight": 25}).insert()
		card = kpi.scorecard(OTHER)
		by_code = {k["kpi_code"]: k for k in card["kpis"]}
		self.assertEqual(by_code["orders_value"]["actual"], 0)
		self.assertTrue(by_code["orders_value"]["live"])
		# CRM KPIs show 'not live yet' when Frappe CRM is not installed
		self.assertEqual(by_code["leads_worked"]["live"], frappe.db.exists("DocType", "CRM Lead") is not None)

	def test_load_sales_pilot_reports_missing_people(self):
		result = setup.load_sales_pilot()
		self.assertEqual(len(result["set_up"]) + len(result["user_not_found"]), len(setup.SALES_PILOT))

	def test_system_manager_is_set_up_automatically(self):
		admin = make_user("sk_test_admin@example.com", ["System Manager"])
		frappe.db.delete("SK App User", {"user": admin})
		with set_user(admin):
			self.assertEqual(api.home()["home"]["function"], "Sales")
		self.assertTrue(frappe.db.exists("SK App User", {"user": admin}))
		frappe.db.set_value("SK App User", {"user": admin}, "enabled", 0)
		with set_user(admin):
			self.assertRaises(frappe.PermissionError, api.home)  # a record switched off stays off

	def test_load_sales_button_is_for_system_manager_only(self):
		with set_user(SALES), self.assertRaises(frappe.PermissionError):
			setup.load_sales_pilot_now()
		result = setup.load_sales_pilot_now()
		self.assertEqual(len(result["set_up"]) + len(result["user_not_found"]), len(setup.SALES_PILOT))
