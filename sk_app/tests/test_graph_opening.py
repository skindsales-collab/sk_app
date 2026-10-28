"""SK 28-Oct "need correct data on graph": the 1-Apr opening invoices (last year's dues, is_opening = Yes) are not sales."""

from unittest.mock import patch

from frappe.tests import IntegrationTestCase

from sk_app import dashboards


class TestGraphOpening(IntegrationTestCase):
	def test_opening_invoices_are_not_sales(self):
		seen = []
		with patch.object(dashboards, "_sum", side_effect=lambda dt, f, filters: seen.append(filters) or 0), \
				patch.object(dashboards, "_tally_sales", return_value=[]):
			dashboards._invoiced("2026-04-01", "2026-04-30")
		self.assertEqual(seen[0]["is_opening"], ["!=", "Yes"])

	def test_won_crm_deals_count_as_orders(self):
		"""SK 28-Oct "why no order is seen Apr to Jul ... it was available in CRM": won deals fill the Orders line."""
		import frappe

		from sk_app import home_kpi

		deal = frappe._dict(name="CRM-DEAL-T1", doctype="CRM Deal", customer_name="SK Test Org", transaction_date=frappe.utils.getdate("2026-05-10"),
			base_net_total=500000, customer_group=None, delivery_date=None, docstatus=0, deal_owner="sk_test_deal_owner@example.com")
		with patch.object(dashboards, "won_deals", return_value=[deal]):
			rows = dashboards._orders("2026-05-01", "2026-05-31")
			self.assertIn("CRM-DEAL-T1", [r.name for r in rows])
			self.assertEqual(home_kpi._orders_value(None)("2026-05-01", "2026-05-31") - sum(
				frappe.utils.flt(r.base_net_total) for r in rows if r.doctype == "Sales Order"), 500000)
			self.assertEqual(home_kpi._orders_value(["sk_test_deal_owner@example.com"])("2026-05-01", "2026-05-31"), 500000)
			self.assertEqual(home_kpi._orders_value(["sk_test_other@example.com"])("2026-05-01", "2026-05-31"), 0)
