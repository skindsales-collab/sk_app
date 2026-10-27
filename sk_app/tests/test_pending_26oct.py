"""SK 26-Oct pending items: short Home in levels, Target Action Plan, TLC SAS, photo checks, automatic Day Report."""

import frappe
from frappe.tests import IntegrationTestCase

from sk_app import functions, photocheck, plan, sas


class TestPending26Oct(IntegrationTestCase):
	def test_home_levels_short(self):
		s = functions.sections_for(["Sales"])
		x = s["sections"][0]
		self.assertEqual(x["main"], ["new_lead", "my_leads", "cold_leads", "follow_up"])
		self.assertEqual(set(x["main"]) | set(x["more"]), set(x["tiles"]))
		# main screen Rev 2 (SK 26-Oct): My Day + DSI at the bottom, a common row and Call / WhatsApp / Mail
		self.assertEqual(s["main_shared"], ["my_day", "dsi"])
		self.assertEqual(s["main_contact"], ["calls", "whatsapp", "mail"])
		self.assertEqual(s["main_common"], ["day_report", "my_kpi", "reminders", "problem"])
		inside = [t for g in s["more_groups"] for t in g["tiles"]]
		self.assertNotIn("calendar", inside)  # inside My Day now
		on_main = set(s["main_shared"] + s["main_common"] + s["main_contact"])
		self.assertTrue(set(s["shared"]) - on_main <= set(inside))
		for k in ("training", "library"):  # SK 26-Oct: not on the main screen
			self.assertIn(k, inside)
		ceo = functions.sections_for(["Management"])["sections"][0]
		self.assertEqual(ceo["main"], ["dash_overview", "po_approvals", "pay_approvals", "view_member"])
		for k in ("leave_expense", "my_kpi", "attendance", "dash_cr100", "leadership"):
			self.assertNotIn(k, ceo["main"])
		self.assertIn("leadership", ceo["tiles"])
		self.assertNotIn("attendance", functions.sections_for(["HR"])["sections"][0]["main"])
		self.assertIn("el_points", functions.sections_for(["Quality"])["sections"][0]["main"])

	def test_funnel(self):
		f = plan.funnel(1500000, 200000, 0.25, 26)
		self.assertEqual(f["month"], {"orders": 8, "quotes": 32, "leads": 80, "calls": 240})
		self.assertEqual(f["day"], {"quotes": 2, "leads": 4, "calls": 10})
		self.assertEqual(plan.funnel(0, 200000, 0.25, 26), {})

	def test_sas(self):
		subjects = sas.for_functions(["Management"])
		self.assertEqual([s["key"] for s in subjects], ["strategy", "sales_marketing", "hr", "finance", "wcp"])
		hr = next(s for s in subjects if s["key"] == "hr")
		self.assertEqual(hr["self_score"], 82)
		self.assertIsNone(hr["assessor_pct"])  # no assessor score yet (the 8% was a mistake)
		staff_hr = sas.for_functions(["HR"])[0]
		self.assertNotIn("salary", str(staff_hr).lower())  # salary is confidential: CEO only
		self.assertEqual(sas.weakest(hr)[0]["score"], 0)
		d = sas.leadership("Administrator")
		self.assertEqual(len(d["subjects"]), 5)
		self.assertTrue(all(s["evidence"] for s in d["subjects"]))

	def test_photo_checks(self):
		rows = photocheck.check("Administrator", "expense", {"amount": "0", "expense_date": "2099-01-01"})["rows"]
		self.assertEqual([r["state"] for r in rows], ["red", "red", "red"])
		v = photocheck.check("Administrator", "voucher", {"spent_on": "Tea for site team", "amount": 120, "account": "x"})
		self.assertEqual(v["red"], 0)
		self.assertEqual(photocheck.check("Administrator", "receipt", {"po": "NOPE"})["rows"], [])
		self.assertEqual(photocheck._numbers("GI sheet 0.5mm  12 Nos  1,250.00"), [0.5, 12.0, 1250.0])
		line, score = photocheck._best_line("GI Sheet 0.5 mm", ["Invoice No 55", "GI sheet 0.5mm 12 Nos"])
		self.assertEqual(line, "GI sheet 0.5mm 12 Nos")
		self.assertGreaterEqual(score, 0.5)

	def test_auto_day_report_text(self):
		from sk_app.day_report import auto_text

		self.assertIn("3 calls", auto_text({"calls_made": 3, "talk_minutes": 9, "leads_created": 1}))
		self.assertEqual(auto_text({}), "Auto: No activity recorded in the app")

	def test_problem_goes_to_function_owner(self):
		from sk_app.api import PROBLEM_OWNER

		self.assertEqual(PROBLEM_OWNER["IT / app"], "AI")
		self.assertEqual(PROBLEM_OWNER["Material shortage"], "Stores")
