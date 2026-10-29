"""SK 29-Oct: one Project + cost centre per cabin; rows of the cabin go to its cost centre."""

import frappe
from frappe.tests import IntegrationTestCase

from sk_app import cabin_projects


class TestCabinProjects(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.company = frappe.db.get_value("Company", {}, "name")
		abbr = frappe.db.get_value("Company", cls.company, "abbr")
		root = frappe.db.get_value("Cost Center", {"company": cls.company, "is_group": 1, "parent_cost_center": ["in", ["", None]]})
		cls.cc = f"SK Test Cabin 999 - {abbr}"
		if not frappe.db.exists("Cost Center", cls.cc):
			frappe.get_doc({"doctype": "Cost Center", "cost_center_name": "SK Test Cabin 999", "parent_cost_center": root,
				"company": cls.company, "is_group": 0}).insert()
		cls.project = frappe.db.get_value("Project", {"project_name": "Cabin 999 · SK Test · Office 20ft x 10ft"}) or frappe.get_doc({
			"doctype": "Project", "project_name": "Cabin 999 · SK Test · Office 20ft x 10ft", "company": cls.company,
			"cost_center": cls.cc}).insert().name

	def test_done_stages(self):
		self.assertEqual(cabin_projects.done_stages("Fabrication, Painting\nElectrical Work,"), ["Fabrication", "Painting", "Electrical Work"])
		self.assertEqual(cabin_projects.done_stages(None), [])

	def test_cabin_no(self):
		self.assertEqual(cabin_projects.cabin_no(self.project), "Cabin 999")
		self.assertIsNone(cabin_projects.cabin_no(None))

	def test_row_gets_cabin_cost_centre(self):
		item = frappe.db.get_value("Item", {"is_stock_item": 1, "disabled": 0}, "name")
		mr = frappe.get_doc({"doctype": "Material Request", "company": self.company, "material_request_type": "Purchase",
			"items": [{"item_code": item, "qty": 1, "project": self.project}]})
		cabin_projects.set_cost_centre(mr)
		self.assertEqual(mr.items[0].cost_center, self.cc)

	def test_days_per_100_sqft(self):
		from sk_app import lead_time

		self.assertEqual(lead_time.area("Cabin 314 · HD Hyundai · Electric Control Room 8ft x 6ft x 8.6ft"), 48)
		self.assertEqual(lead_time.area("25ft x 22ft x 8.6ft"), 550)
		self.assertEqual(lead_time.per_100(30, 300), 10)
		self.assertEqual(lead_time.per_100(30, 0), 0)
