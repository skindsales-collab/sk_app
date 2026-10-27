"""SK 27-Oct: cold-calling leads on their own Cold Calling list, not in My Leads, the New arrow or Follow-up."""

import frappe
from frappe.tests import IntegrationTestCase

from sk_app import activities, cold_leads, crm, flows, functions, work
from sk_app.tests.test_change_list_a import _app_user

REP = "sk_test_cold_rep@example.com"


class TestColdLeads(IntegrationTestCase):
	def test_sources_match_loosely_and_only_new(self):
		s = {cold_leads._norm(x) for x in cold_leads.DEFAULT_SOURCES}
		self.assertTrue(cold_leads.is_cold("Marketing call", "New", s))
		self.assertTrue(cold_leads.is_cold("Marketingg Call", "New", s))  # the typo in the live data
		self.assertTrue(cold_leads.is_cold("cold calling", "Contacted", s))  # old status, still the New step
		self.assertFalse(cold_leads.is_cold("Marketing call", "Qualified", s))  # moved on: a current lead
		self.assertFalse(cold_leads.is_cold("JustDial", "New", s))
		self.assertFalse(cold_leads.is_cold(None, "New", s))

	def test_main_screen_has_cold_calling(self):
		self.assertIn("cold_leads", functions.sections_for(["Sales"])["sections"][0]["main"])
		self.assertIn("cold_leads", functions.sections_for(["Marketing"])["sections"][0]["main"])
		self.assertIn("team_leads", functions.sections_for(["Sales"], has_team=True)["sections"][0]["main"])

	def test_cold_lead_kept_apart_until_qualified(self):
		if not frappe.db.exists("DocType", "CRM Lead"):
			self.skipTest("Frappe CRM not installed")
		_app_user(REP, "Sales", ["Sales User"])
		for src in ("Marketing call", "JustDial"):
			if not frappe.db.exists("CRM Lead Source", src):
				frappe.get_doc({"doctype": "CRM Lead Source", "source_name": src}).insert(ignore_permissions=True)

		def lead(first, source):
			return frappe.get_doc({"doctype": "CRM Lead", "first_name": first, "organization": f"SK Cold Test {first}",
				"source": source, "lead_owner": REP, "status": "New"}).insert(ignore_permissions=True).name

		cold, hot = lead("Cold", "Marketing call"), lead("Hot", "JustDial")
		cold_names = [i.name for i in work.open_leads(REP, cold=True)]
		hot_names = [i.name for i in work.open_leads(REP)]
		self.assertIn(cold, cold_names)
		self.assertNotIn(hot, cold_names)
		self.assertIn(hot, hot_names)
		self.assertNotIn(cold, hot_names)
		self.assertNotIn(cold, [r["name"] for r in crm.follow_up(REP, for_manager=True)])
		stages = {s["key"]: s for s in flows.sales(REP, only_self=True)}
		self.assertEqual(stages["cold"]["late"], 0)  # never red
		self.assertIn(cold, [r["name"] for r in stages["cold"]["rows"]])
		self.assertNotIn(cold, [r["name"] for r in stages["new"]["rows"]])
		self.assertEqual(cold_leads.badge(REP, ["Sales"])["cold_leads"]["c"], "blue")
		# a call on it counts as a cold call, not a raw lead call
		frappe.get_doc({"doctype": "CRM Call Log", "id": frappe.generate_hash(length=16), "type": "Outgoing", "status": "Completed",
			"from": "0", "to": "0", "telephony_medium": "Manual", "caller": REP,
			"reference_doctype": "CRM Lead", "reference_docname": cold}).insert(ignore_permissions=True)
		self.assertGreaterEqual(activities._calls_by_step(REP, frappe.utils.nowdate())["cold_calls"], 1)
		# marked Qualified in the CRM: it becomes a current lead
		frappe.db.set_value("CRM Lead", cold, "status", "Qualified")
		self.assertIn(cold, [i.name for i in work.open_leads(REP)])
		self.assertNotIn(cold, [i.name for i in work.open_leads(REP, cold=True)])
