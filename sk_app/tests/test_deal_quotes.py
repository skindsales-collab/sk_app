"""SK 28-Oct: every quote (cabin, machine shifting, job work, any other) goes through ERPNext as a Quotation."""

import frappe
from frappe.tests import IntegrationTestCase

from sk_app import deal_quotes


class TestDealQuotes(IntegrationTestCase):
	def test_quote_files_are_recognised(self):
		for name in ("Cabin41_Kusum_Office_20x8_WC_BOM_Costing_Quote_Rev0.xlsx", "SK_Quotation_CRM-DEAL-2026-00052_Hyundai_Store.pdf",
				"SK Quote - D14 Z Axis Ground Ball Screw.pdf", "Cabin37_Godrej_Kharadi_Quotation_R2.pdf"):
			self.assertTrue(deal_quotes.is_quote_file(name), name)
		for name in ("Office Layout 20X10.pdf", "Cabin41_Kusum_Office_20x8_WC_Customer_Drawing_GA-01C_Rev0.pdf", None):
			self.assertFalse(deal_quotes.is_quote_file(name), name)

	def test_safe_without_crm(self):
		if frappe.db.exists("DocType", "CRM Deal"):
			self.skipTest("CRM installed")
		self.assertEqual(deal_quotes.sync(), 0)
		self.assertIsNone(deal_quotes.make_for_deal("CRM-DEAL-X"))

	def test_job_item_for_non_cabin_quotes(self):
		deal_quotes.ensure_setup()
		self.assertTrue(frappe.db.exists("Item", deal_quotes.SERVICE_ITEM))

	def test_won_deal_hook_is_safe_without_crm(self):
		if frappe.db.exists("DocType", "CRM Deal"):
			self.skipTest("CRM installed")
		doc = frappe._dict(name="CRM-DEAL-X", status="Open", meta=frappe._dict(has_field=lambda f: False), get_doc_before_save=lambda: None)
		deal_quotes.on_deal_update(doc)  # not won, no value: nothing happens, no error
