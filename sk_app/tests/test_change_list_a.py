"""Change list Rev 13, part A: admin icons by function, roles follow functions, week plan, AI & ERP desk, colours."""

from datetime import date, datetime, timedelta

import frappe
from frappe.tests import IntegrationTestCase
from frappe.tests.classes.context_managers import set_user
from frappe.utils import add_days, getdate

from sk_app import ai_desk, api, colours, logins
from sk_app.logic import WorkItem, plan_week
from sk_app.tests.test_sk_app_api import make_user

REP = "sk_test_a_rep@example.com"  # salesperson with an HR Manager role left from before the app
HRP = "sk_test_a_hr@example.com"
CEO = "sk_test_a_ceo@example.com"
AI = "sk_test_a_ai@example.com"
MOBILE = "9876500031"


def _app_user(email, home, roles):
	make_user(email, roles)
	frappe.db.delete("SK App User", {"user": email})
	frappe.get_doc({"doctype": "SK App User", "user": email, "home": home, "enabled": 1}).insert(ignore_permissions=True)


class TestPlanWeek(IntegrationTestCase):
	def test_overdue_spills_over_days_and_later_work_sits_on_its_due_day(self):
		monday = date(2026, 10, 26)
		days = [monday + timedelta(days=n) for n in range(7)]
		now = datetime(2026, 10, 26, 9, 0)
		items = [WorkItem("lead_followup", f"Old {n}", "CRM Lead", f"L{n}", due=now - timedelta(days=2), minutes=60) for n in range(10)]
		items.append(WorkItem("task", "Thursday job", "Task", "T1", due=datetime(2026, 10, 29, 12, 0), minutes=60))
		items.append(WorkItem("task", "Any day", "Task", "T2", minutes=30))
		plan = plan_week(items, days, now, "09:00", "18:00", "13:00", "14:00", ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
			routine=[("Mon", "10:00", 60, "Team meeting")])
		mon = plan[monday]
		self.assertEqual(mon["capacity"], 8 * 60)
		self.assertEqual(mon["routine"][0]["title"], "Team meeting")
		self.assertLessEqual(mon["load"], mon["capacity"])
		self.assertEqual(len(mon["items"]), 7)  # 8 h minus the 1 h meeting
		self.assertEqual(len(plan[days[1]]["items"]), 3 + 1)  # the rest of the overdue work, then the job with no date
		self.assertTrue(all(flag == "overdue" for _i, flag in mon["items"]))
		self.assertEqual([i.title for i, _f in plan[days[3]]["items"]], ["Thursday job"])
		self.assertEqual(plan[days[6]]["capacity"], 0)  # Sunday off

	def test_a_moved_item_goes_where_the_person_put_it(self):
		monday = date(2026, 10, 26)
		days = [monday + timedelta(days=n) for n in range(7)]
		item = WorkItem("task", "Call supplier", "Task", "T9", minutes=30)
		plan = plan_week([item], days, datetime(2026, 10, 26, 9, 0), "09:00", "18:00", "13:00", "14:00",
			["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"], moves={"Task:T9": "2026-10-30"})
		self.assertEqual(plan[days[4]]["items"][0][1], "moved")


class TestChangeListA(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		logins.setup_site()
		_app_user(REP, "Sales", ["Sales User", "HR Manager", "Employee"])
		_app_user(HRP, "HR", ["HR Manager", "Employee"])
		_app_user(CEO, "Management", ["System Manager"])
		_app_user(AI, "AI", ["Projects User"])

	def test_admin_icons_follow_the_function_not_an_old_role(self):
		with set_user(REP):
			h = api.home()
		self.assertNotIn("logins", h["home"]["tiles"])
		self.assertNotIn("team_reports", h["home"]["tiles"])
		self.assertNotIn("work_book", h["home"]["tiles"])  # point 10: inside My Day now
		with set_user(HRP):  # point 20 (SK 26-Oct): Logins / Reset PIN removed from HR, CEO only
			self.assertNotIn("logins", api.home()["home"]["tiles"])
		with set_user(CEO):
			tiles = api.home()["home"]["tiles"]
		self.assertIn("logins", tiles)
		self.assertIn("team_reports", tiles)

	def test_ai_desk_has_its_own_icons(self):
		with set_user(AI):
			h = api.home()
		self.assertEqual(h["home"]["label"]["English"], "AI & ERP")
		for k in ("improvement_inbox", "dept_visits", "erp_gaps", "app_users", "change_list", "projects", "training_progress"):
			self.assertIn(k, h["home"]["tiles"])
		self.assertNotIn("logins", h["home"]["tiles"])

	def test_editing_a_login_takes_off_roles_of_old_functions(self):
		for u in frappe.get_all("User", filters={"mobile_no": MOBILE}, pluck="name") + [f"{MOBILE}@{logins.HIDDEN_DOMAIN}"]:
			if frappe.db.exists("User", u):
				frappe.db.delete("SK App User", {"user": u})
				frappe.delete_doc("User", u, force=True, ignore_permissions=True)
		r = logins.make_login(CEO, MOBILE, ["Sales", "HR"], full_name="Role Test")
		self.assertIn("HR Manager", frappe.get_roles(r["user"]))
		logins.make_login(CEO, MOBILE, ["Sales"], full_name="Role Test")
		roles = set(frappe.get_roles(r["user"]))
		self.assertIn("Sales User", roles)
		self.assertFalse({"HR Manager", "HR User", "Sales Manager"} & roles)
		with set_user(CEO):
			row = next(p for p in logins.people(CEO) if p["user"] == r["user"])
		self.assertIn("Sales User", row["roles"])

	def test_inbox_sort_and_close_posts_a_dsi(self):
		with set_user(REP):
			name = api.add_work("Stock count screen hangs", entry_type="Problem", problem_type="IT / app")
		self.assertRaises(frappe.PermissionError, ai_desk.inbox, REP)
		box = ai_desk.inbox(AI)
		self.assertIn(name, [x["name"] for x in box["new"]])
		todo = ai_desk.sort_item(AI, "SK Work Log", name, "App bug")["todo"]
		box = ai_desk.inbox(AI)
		self.assertNotIn(name, [x["name"] for x in box["new"]])
		self.assertEqual(next(x for x in box["working"] if x["name"] == name)["category"], "App bug")
		dsi = ai_desk.close_item(AI, todo, "Fixed slow count list")["dsi"]
		self.assertEqual(frappe.db.get_value("SK Work Log", name, "status"), "Done")
		self.assertEqual(frappe.db.get_value("SK DSI Entry", dsi, "user"), AI)
		ai_desk.set_change(AI, 9, "Testing")
		self.assertEqual(next(r for r in ai_desk.change_list(AI) if r["no"] == 9)["status"], "Testing")
		self.assertTrue(ai_desk.app_users(AI)["total"] >= 1)
		self.assertIsInstance(ai_desk.erp_gaps(AI), list)
		ai_desk.visit_note(AI, "Sales & Marketing", "Rahul needs training on quotes")
		self.assertTrue(ai_desk.visit(AI, "2026-10-26")["notes"])

	def test_dsi_icon_is_red_until_posted_then_green(self):
		monday = datetime(2026, 10, 26, 16, 45)
		late = WorkItem("task", "Late job", "Task", "T1", due=monday - timedelta(hours=3))
		out = colours.for_user(REP, [late], False, False, {"receive": 2}, now=monday)
		self.assertEqual(out["dsi"]["c"], "red")
		self.assertTrue(out["dsi"].get("blink"))
		self.assertEqual(out["my_day"], {"n": 1, "c": "red"})
		self.assertEqual(out["receive"]["c"], "amber")
		self.assertNotIn("day_report", out)
		out = colours.for_user(REP, [], True, True, {}, now=monday.replace(hour=17, minute=30))
		self.assertEqual(out["dsi"]["c"], "green")
		self.assertEqual(out["day_report"]["c"], "green")
		sunday = datetime(2026, 10, 25, 18, 0)
		self.assertNotIn("dsi", colours.for_user(REP, [], False, False, {}, now=sunday))

	def test_week_view_and_move(self):
		with set_user(REP):
			w = api.cal_week(str(getdate()))
			self.assertEqual(len(w["days"]), 7)
			self.assertTrue(any(d["routine"] for d in w["days"] if d["working"] and d["date"] >= str(getdate())) or
				all(not d["capacity"] for d in w["days"]))
			api.cal_move("Task:XYZ", str(add_days(getdate(), 1)))
			from sk_app.calendar_view import _moves

			self.assertIn("Task:XYZ", _moves(REP))


class TestLedgerScreens(IntegrationTestCase):
	def test_every_ledger_list_and_the_pnl_reports_run(self):
		from sk_app import ledger

		acc = "sk_test_a_acc@example.com"
		_app_user(acc, "Accounts", ["Accounts User", "Accounts Manager"])
		for kind in ledger.KINDS:
			d = ledger.ledgers(acc, kind)
			self.assertIn("rows", d)
			if d["rows"]:
				e = ledger.entries(acc, kind, d["rows"][0]["ledger"])
				self.assertIn("rows", e)
		seg = ledger.segment_wise(acc)
		self.assertEqual([r["segment"] for r in seg["rows"]], ["Cabin", "Non-Cabin", "Common"])
		self.assertAlmostEqual(seg["total"]["net"], seg["total"]["income"] - seg["total"]["direct"] - seg["total"]["indirect"], 2)
		mw = ledger.month_wise(acc)
		self.assertTrue(mw["rows"])
		self.assertEqual(mw["rows"][0]["month"][5:], "04")
		# SK 28-Oct: each month split Cabin / Non-Cabin / Common, adding up to the month
		self.assertIsNone(mw["only"])
		for r in mw["rows"]:
			self.assertAlmostEqual(sum(r["segments"][s]["net"] for s in ("Cabin", "Non-Cabin", "Common")), r["net"], 2)
			# Non-Cabin split into Machine Shifting / Job Work / Maintenance, older entries combined
			self.assertAlmostEqual(sum(r["subs"][s]["net"] for s in ledger.NON_CABIN_SUBS), r["segments"]["Non-Cabin"]["net"], 2)
		self.assertEqual(ledger._non_cabin_sub(None, {}), ledger.COMBINED)
		self.assertEqual(ledger._non_cabin_sub("Site Expenses - X", {"Site Expenses - X": "Machine Shifting - X"}), "Machine Shifting")
		self.assertEqual(ledger._segment_of(None, None, {}, "Cabin"), "Cabin")
		# Aditya (Machine Shifting) sees the Non-Cabin P&L only
		ms = "sk_test_a_ms@example.com"
		_app_user(ms, "Machine Shifting", ["Sales User"])
		nc = ledger.month_wise(ms)
		self.assertEqual(nc["only"], "Non-Cabin")
		self.assertEqual([r["net"] for r in nc["rows"]], [r["segments"]["Non-Cabin"]["net"] for r in mw["rows"]])
		self.assertRaises(frappe.PermissionError, ledger.ledgers, REP, "bank")
		self.assertEqual(ledger._segment_of_names(["Direct Expenses Non Cabin - X"]), "Non-Cabin")
		self.assertEqual(ledger._segment_of_names(["Cabin Sales - X"]), "Cabin")
