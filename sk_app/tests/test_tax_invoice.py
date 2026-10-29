"""SK 29-Oct (Shraddha): invoice print shows Bill to (buyer) and Ship to (consignee); no invoice is submitted without the
buyer's address."""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import nowdate

from sk_app import tax_invoice
from sk_app.tests import test_store_purchase as tsp
from sk_app.tests.test_store_purchase import RAW

NO_ADDRESS = "SK Test Customer No Address"


class TestTaxInvoice(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		tsp.TestStorePurchase.setUpClass.__func__(tsp.TestStorePurchase)
		cls.company = tsp.TestStorePurchase.company
		tax_invoice.ensure_setup()
		if not frappe.db.exists("Customer", NO_ADDRESS):
			frappe.get_doc({"doctype": "Customer", "customer_name": NO_ADDRESS, "customer_type": "Company",
				"customer_group": frappe.db.get_value("Customer Group", {"is_group": 0}, "name")}).insert(ignore_permissions=True)
		frappe.db.commit()

	def _invoice(self, customer):
		si = frappe.get_doc({"doctype": "Sales Invoice", "customer": customer, "company": self.company, "posting_date": nowdate(),
			"due_date": nowdate(), "items": [{"item_code": RAW, "qty": 1, "rate": 1000}]})
		si.flags.ignore_permissions = True
		return si.insert()

	def test_default_print_format(self):
		self.assertTrue(frappe.db.exists("Print Format", tax_invoice.PRINT_FORMAT))
		self.assertEqual(frappe.db.get_value("Property Setter", {"doc_type": "Sales Invoice", "property": "default_print_format"}, "value"),
			tax_invoice.PRINT_FORMAT)

	def test_no_address_cannot_submit_but_prints_the_gap(self):
		si = self._invoice(NO_ADDRESS)
		html = tax_invoice.invoice_html(si)
		self.assertIn("Bill to (Buyer)", html)
		self.assertIn("Ship to (Consignee)", html)
		self.assertIn("Address not in ERPNext", html)
		self.assertRaises(frappe.ValidationError, si.submit)

	def test_customer_address_used_for_bill_and_ship(self):
		si = self._invoice(NO_ADDRESS)
		a = frappe.get_doc({"doctype": "Address", "address_title": NO_ADDRESS, "address_type": "Billing", "address_line1": "Plot 7, MIDC",
			"city": "Pune", "state": "Maharashtra", "pincode": "411026", "country": "India",
			"links": [{"link_doctype": "Customer", "link_name": NO_ADDRESS}]}).insert(ignore_permissions=True)
		try:
			bill, ship, same = tax_invoice.parties(si)
			self.assertEqual((bill.name, ship.name, same), (a.name, a.name, True))
			html = tax_invoice.invoice_html(si)
			self.assertIn("Plot 7, MIDC", html)
			self.assertIn("same as Bill to", html)
		finally:
			frappe.delete_doc("Address", a.name, force=True, ignore_permissions=True)

	def test_rupees_with_paise(self):
		self.assertEqual(tax_invoice.inr2(601800), "₹6,01,800.00")
		self.assertEqual(tax_invoice.inr2(45900.5), "₹45,900.50")
