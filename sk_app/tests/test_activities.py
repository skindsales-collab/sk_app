"""SK 27-Oct points 4 and 11: sales activity counters and the phone call list."""

import frappe
from frappe.tests import IntegrationTestCase

from sk_app import activities
from sk_app.tests.test_change_list_a import _app_user

REP = "sk_test_act_rep@example.com"


class TestActivities(IntegrationTestCase):
	def test_counters_with_targets(self):
		_app_user(REP, "Sales", ["Sales User"])
		frappe.db.delete("SK Activity Count", {"user": REP})
		a = activities.today(REP)
		self.assertEqual(a["total"], 11)
		visits = next(r for r in a["rows"] if r["key"] == "visits")
		self.assertEqual((visits["done"], visits["target"], visits["c"]), (0, 1, "red"))
		activities.tap(REP, "visits")
		a = activities.tap(REP, "cold_calls", 3)
		self.assertEqual(next(r for r in a["rows"] if r["key"] == "visits")["c"], "green")
		self.assertEqual(next(r for r in a["rows"] if r["key"] == "cold_calls")["done"], 3)
		a = activities.tap(REP, "cold_calls", -5)
		self.assertEqual(next(r for r in a["rows"] if r["key"] == "cold_calls")["done"], 0)  # never below 0
		with self.assertRaises(frappe.ValidationError):
			activities.tap(REP, "salary")

	def test_call_list_file(self):
		rows = activities._rows(b"Number,Date,Duration,Type\n+91 98765 43210,2026-10-27 10:05:00,2:30,Outgoing\n9876500000,2026-10-27 11:00,0,Missed\n", "calls.csv")
		self.assertEqual([r["number"] for r in rows], ["9876543210", "9876500000"])
		self.assertEqual([activities._seconds(x) for x in ("2:30", "1h 2m 5s", "95", "", "0:01:10")], [150, 3725, 95, 0, 70])
		with self.assertRaises(frappe.ValidationError):
			activities._rows(b"Name,Notes\nx,y\n", "x.csv")
