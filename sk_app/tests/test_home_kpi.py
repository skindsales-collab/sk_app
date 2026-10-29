"""Main screen Rev 2 (SK 26-Oct): one KPI chart against target per person, money charts week / month."""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import get_first_day, getdate

from sk_app import home_kpi
from sk_app.tests.test_sk_app_api import make_user
from sk_app.tests.test_store_purchase import run

REP = "sk_test_kpi_rep@example.com"
MGR = "sk_test_kpi_mgr@example.com"


def _target(user, amount):
	if not frappe.db.exists("SK KPI Target", {"user": user, "kpi_code": "orders_value"}):
		frappe.get_doc({"doctype": "SK KPI Target", "user": user, "kpi_code": "orders_value", "kra": "Sales", "kpi_label": "Orders",
			"monthly_target": amount, "unit": "Rs", "weight": 50, "active": 1}).insert(ignore_permissions=True)


class TestHomeKpi(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		for u, mgr in ((MGR, None), (REP, MGR)):
			make_user(u, ["Sales User", "Employee"])
			if not frappe.db.exists("SK App User", {"user": u}):
				frappe.get_doc({"doctype": "SK App User", "user": u, "home": "Sales", "enabled": 1, "manager": mgr}).insert(ignore_permissions=True)
		_target(REP, 1500000)
		_target(MGR, 4500000)

	def test_cabin_size_from_item_name(self):
		self.assertEqual(home_kpi.sq_ft("Office Cabin 12x10"), 120)
		self.assertEqual(home_kpi.sq_ft("Security cabin 8' X 6'"), 48)
		self.assertEqual(home_kpi.sq_ft("Guard room 10 ft x 10 ft"), 100)
		self.assertAlmostEqual(home_kpi.sq_ft("Kiosk 3048 x 3048"), 100, 0)
		self.assertEqual(home_kpi.sq_ft("Paint 20 L"), 0)

	def test_weeks_of_month(self):
		start = getdate("2026-10-01")
		weeks = home_kpi._weeks(start, getdate("2026-10-26"))
		self.assertEqual([w[0] for w in weeks], ["W1", "W2", "W3", "W4"])
		self.assertEqual(str(weeks[-1][1]), "2026-10-22")
		self.assertEqual(len(home_kpi._weeks(start, getdate("2026-10-31"))), 5)

	def test_sales_money_card(self):
		c = run(REP, home_kpi.for_user, ["Sales"])["chart"]
		self.assertEqual(c["kind"], "money")
		self.assertEqual(c["target"], 1500000)
		self.assertEqual(len(c["month"]["labels"]), home_kpi.MONTHS)
		self.assertEqual(len(c["week"]["labels"]), len(c["week"]["target"]))
		self.assertEqual([l["label"] for l in c["week"]["lines"]], ["Orders", "Invoices"])  # SK 27-Oct: own customers' Tally sale too
		pts = c["week"]["lines"][0]["points"]
		self.assertEqual(pts, sorted(pts))  # running total never goes down
		self.assertLessEqual(c["week"]["target"][-1], 1500000)

	def test_sales_manager_sees_team_total(self):
		"""SK 26-Oct: for Rushi the team's total sale against the team's targets together."""
		c = run(MGR, home_kpi.for_user, ["Sales"])["chart"]
		self.assertEqual(c["target"], 6000000)
		self.assertEqual(c["title"], "Team PO booking")

	def test_ceo_two_lines_and_trends(self):
		c = run("Administrator", home_kpi.for_user, ["Management", "Sales"])["chart"]
		self.assertEqual([l["label"] for l in c["month"]["lines"]], ["Orders", "Invoices"])  # SK 26-Oct
		self.assertGreater(c["target"], 0)
		for fn in ("Production", "HR", "Stores", "Quality", "Purchase", "AI"):
			t = run("Administrator", home_kpi.for_user, [fn])["chart"]
			self.assertEqual(t["kind"], "trend", fn)
			self.assertEqual(len(t["points"]), home_kpi.MONTHS)
			self.assertEqual(t["points"][-1]["m"], get_first_day(getdate()).strftime("%b"))
			if all(p["v"] is None for p in t["points"]):
				self.assertTrue(t["need"])  # says what to enter in ERPNext
		self.assertIsNone(run("Administrator", home_kpi.for_user, ["Nothing"])["chart"])
		# SK 27-Oct: Sales as an extra function never hides the person's own graph
		self.assertEqual(run("Administrator", home_kpi.for_user, ["Sales", "Machine Shifting"])["chart"]["title"], "Non-Cabin sale")
		self.assertEqual(run("Administrator", home_kpi.for_user, ["Sales", "Production"])["chart"]["function"], "Production")

	def test_accounts_project_pnl(self):
		"""SK 29-Oct: Shraddha's graph shows the number of projects and each project's own profit & loss, read from the
		ledger rows posted to the project or to its cost centre; what is not posted yet is listed under the project."""
		company = frappe.db.get_value("Company", {}, "name")
		parent = frappe.db.get_value("Cost Center", {"company": company, "is_group": 1}, "name")
		if not frappe.db.exists("Cost Center", {"cost_center_name": "SK Test PnL Cabin"}):
			frappe.get_doc({"doctype": "Cost Center", "cost_center_name": "SK Test PnL Cabin", "parent_cost_center": parent, "company": company}).insert()
		cc = frappe.db.get_value("Cost Center", {"cost_center_name": "SK Test PnL Cabin"})
		if not frappe.db.exists("Project", {"project_name": "Cabin 999 · SK Test PnL · Office Cabin"}):
			frappe.get_doc({"doctype": "Project", "project_name": "Cabin 999 · SK Test PnL · Office Cabin", "cost_center": cc, "company": company}).insert()
		pid = frappe.db.get_value("Project", {"project_name": "Cabin 999 · SK Test PnL · Office Cabin"})
		before = {r["name"]: r for r in home_kpi.accounts("Administrator")["projects"]}
		self.assertIn(pid, before)
		self.assertEqual(before[pid]["label"], "999 SK Test PnL")
		self.assertIn("sale", before[pid]["missing"])
		income = frappe.db.get_value("Account", {"company": company, "root_type": "Income", "is_group": 0})
		expense = frappe.db.get_value("Account", {"company": company, "root_type": "Expense", "is_group": 0})
		other = frappe.db.get_value("Account", {"company": company, "root_type": "Asset", "is_group": 0, "account_type": ["in", ["Cash", "Bank", ""]]})
		for account, dr, cr, project in ((income, 0, 100000, pid), (other, 100000, 0, None), (expense, 30000, 0, None), (other, 0, 30000, None)):
			frappe.get_doc({"doctype": "GL Entry", "company": company, "posting_date": getdate(), "account": account, "debit": dr, "credit": cr,
				"debit_in_account_currency": dr, "credit_in_account_currency": cr, "cost_center": cc, "project": project,
				"voucher_type": "Journal Entry", "voucher_no": "SK-TEST-PNL", "is_cancelled": 0}).db_insert()
		c = home_kpi.accounts("Administrator")
		self.assertEqual((c["kind"], c["title"], c["target"]), ("projects", "Project profit & loss", 100))
		self.assertEqual(c["count"], len(c["projects"]))
		r = next(r for r in c["projects"] if r["name"] == pid)
		self.assertEqual((r["sale"] - before[pid]["sale"], r["cost"] - before[pid]["cost"]), (100000, 30000))
		self.assertNotIn("sale", r["missing"])
		self.assertIn("material", r["missing"])  # no material issue posted yet
		self.assertNotIn("ERPNext Implementation", [x["label"] for x in c["projects"]])  # internal projects stay off

	def test_actions_to_improve_graph(self):
		"""SK 26-Oct: actions that lift the graph, added by AI / manager / CEO, shown first by priority, closed by the owner."""
		run(MGR, home_kpi.add_action, REP, "Call 10 old customers for repeat orders", "High")
		run("Administrator", home_kpi.add_action, REP, "Send cabin catalogue on WhatsApp", "Low")
		with self.assertRaises(frappe.PermissionError):
			run(REP, home_kpi.add_action, MGR, "Not my team", "High")  # a salesperson cannot give the manager actions
		r = run(REP, home_kpi.actions)
		texts = [a["text"] for a in r["actions"] if not a["done"]]
		self.assertLess(texts.index("Call 10 old customers for repeat orders"), texts.index("Send cabin catalogue on WhatsApp"))
		self.assertGreaterEqual(run(REP, home_kpi.for_user, ["Sales"])["actions"], 2)
		self.assertIn(REP, [p["user"] for p in run(MGR, home_kpi.actions, REP)["team"]])
		first = next(a for a in r["actions"] if a["text"].startswith("Call 10"))
		with self.assertRaises(frappe.PermissionError):
			run(MGR, home_kpi.finish_action, first["name"])  # only the person who has it closes it
		run(REP, home_kpi.finish_action, first["name"], "Called 10, 2 quotes asked")
		self.assertTrue(next(a for a in run(REP, home_kpi.actions)["actions"] if a["name"] == first["name"])["done"])


class TestDayWeekMonth(IntegrationTestCase):
	def test_target_split_by_working_days(self):
		"""SK 27-Oct: Day / Week / Month on every graph; the month target split over Mon-Sat working days."""
		from frappe.utils import getdate

		frappe.local.sk_festivals = set()
		try:
			self.assertEqual(home_kpi.working_days("2026-10-26", "2026-11-01"), 6)  # Mon-Sat, Sunday off
			self.assertEqual(home_kpi.working_days("2026-10-01", "2026-10-31"), 27)
			self.assertAlmostEqual(home_kpi.split_target(2700000, "2026-10-26", "2026-10-26"), 100000)
			self.assertAlmostEqual(home_kpi.split_target(2700000, "2026-10-26", "2026-10-31"), 600000)
			frappe.local.sk_festivals = {getdate("2026-10-27")}
			self.assertEqual(home_kpi.working_days("2026-10-26", "2026-11-01"), 5)
			days = home_kpi._days_back("2026-10-27")
			self.assertEqual(len(days), home_kpi.DAYS_SHOWN)
			self.assertTrue(all(d.weekday() < 6 and str(d) != "2026-10-27" for _l, d, _e in days))
			self.assertEqual(len(home_kpi._weeks_back("2026-10-27")), home_kpi.WEEKS_SHOWN)
		finally:
			del frappe.local.sk_festivals

	def test_every_chart_has_day_and_week(self):
		for fn in ("Sales", "Management", "Production", "AI"):
			c = run("Administrator", home_kpi.for_user, [fn])["chart"]
			self.assertEqual(len(c["day"]["labels"] if c["kind"] == "money" else c["day"]), home_kpi.DAYS_SHOWN, fn)
		ai = run("Administrator", home_kpi.for_user, ["AI"])["chart"]
		self.assertLess(ai["day"][-1]["t"], ai["target"])  # a count: the day's share of the month target
		prod = run("Administrator", home_kpi.for_user, ["Production"])["chart"]
		self.assertEqual(prod["day"][-1]["t"], prod["target"])  # a rate: same target every day
