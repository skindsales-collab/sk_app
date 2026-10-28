"""SK 28-Oct: a submitted Sales Order turns its CRM lead / deal Won at once."""

import frappe
from frappe.tests import IntegrationTestCase

from sk_app import won_deals


class TestWonDeals(IntegrationTestCase):
	def test_order_finds_its_lead_or_deal(self):
		so = frappe._dict(po_no="From CRM-LEAD-2026-00660", items=[frappe._dict(description="Cabin 20x10<br>Source: CRM-LEAD-2026-00660"),
			frappe._dict(description="Extra for CRM-DEAL-2026-00052")])
		self.assertEqual(won_deals.refs(so), ["CRM-LEAD-2026-00660", "CRM-DEAL-2026-00052"])

	def test_order_without_crm_link(self):
		self.assertEqual(won_deals.refs(frappe._dict(po_no="PO/123", items=[frappe._dict(description="Cabin")])), [])
