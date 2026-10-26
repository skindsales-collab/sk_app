"""Change list point 14: team mailboxes and free auto leads from IndiaMART / JustDial / GeM mails."""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import now_datetime

from sk_app import install, lead_sources, mailbox
from sk_app.tests.test_change_list_a import _app_user

SALES1 = "sk_test_m_sales1@example.com"
SALES2 = "sk_test_m_sales2@example.com"
ACC = "sk_test_m_acc@example.com"

INDIAMART = """Dear Seller,
You have received a new enquiry on IndiaMART.
Buyer Name: Ramesh Patil
Mobile: +91-98220 41234
Email: ramesh.patil@example.com
Company: Patil Agro Industries
City: Ahmednagar
Requirement: Portable office cabin 20x10 ft with AC
"""
JUSTDIAL = """Caller Name : Suresh
Caller Phone : 9822012345
Area : MIDC Chakan
City : Pune
Category : Machine Shifting Services
"""
GEM = """Bid Number: GEM/2026/B/5551234
Item Category: Prefabricated Portable Cabin (Q3)
Ministry: Ministry of Defence
Bid End Date/Time: 05-11-2026 15:00:00
"""


class TestMailLeads(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		install.ensure_mail_fields()
		_app_user(SALES1, "Sales", ["Sales User"])
		_app_user(SALES2, "Sales", ["Sales User"])
		_app_user(ACC, "Accounts", ["Accounts User"])

	def test_portal_mails_are_read_into_lead_fields(self):
		d = lead_sources.parse_mail("Enquiry for Portable Cabin", INDIAMART, "IndiaMART")
		self.assertEqual(d["first_name"], "Ramesh Patil")
		self.assertEqual(d["mobile_no"], "9822041234")
		self.assertEqual(d["email"], "ramesh.patil@example.com")
		self.assertEqual(d["organization"], "Patil Agro Industries")
		self.assertIn("cabin", d["requirement"].lower())
		self.assertEqual(lead_sources.segment_of(d["requirement"]), "Standard Cabin (GI / ACP)")
		j = lead_sources.parse_mail("JD lead", JUSTDIAL, "JustDial")
		self.assertEqual((j["first_name"], j["mobile_no"]), ("Suresh", "9822012345"))
		self.assertEqual(lead_sources.segment_of(j["requirement"]), "Machine Shifting")
		g = lead_sources.parse_mail("GeM bid alert", GEM, "GeM")
		self.assertEqual(g["first_name"], "GeM bid GEM/2026/B/5551234")
		self.assertEqual(g["organization"], "Ministry of Defence")
		self.assertIn("bid ends", g["requirement"])
		self.assertEqual(lead_sources.source_of("buyleads@indiamart.com"), "IndiaMART")
		self.assertEqual(lead_sources.source_of("x@gem.gov.in"), "GeM")
		self.assertIsNone(lead_sources.source_of("friend@gmail.com", "Hello"))

	def _mail(self, subject="Need a cabin"):
		return frappe.get_doc({"doctype": "Communication", "communication_medium": "Email", "sent_or_received": "Received",
			"subject": subject, "sender": "buyer@example.com", "recipients": "cabin@skind.tech", "content": "Please quote",
			"communication_date": now_datetime()}).insert(ignore_permissions=True).name

	def test_team_mailbox_take_once_and_only_its_people(self):
		self.assertIn("cabin@skind.tech", mailbox.boxes_for(SALES1))
		self.assertEqual(mailbox.boxes_for(ACC), ["acc@skind.tech"])
		comm = self._mail()
		box = mailbox.inbox(SALES1)
		row = next(m for m in box["mails"] if m["name"] == comm)
		self.assertEqual(row["status"], "New")
		mailbox.take(SALES1, comm)
		self.assertRaises(frappe.ValidationError, mailbox.take, SALES2, comm)
		row = next(m for m in mailbox.inbox(SALES2)["mails"] if m["name"] == comm)
		self.assertEqual((row["status"], row["sk_taken_by"]), ("Taken", SALES1))
		self.assertRaises(frappe.PermissionError, mailbox.read, ACC, comm)
		mailbox.not_a_lead(SALES1, comm)
		self.assertEqual(frappe.db.get_value("Communication", comm, "sk_mail_status"), "Not a lead")
		# reply needs the mailbox to be able to send
		if not frappe.db.exists("Email Account", {"email_id": "cabin@skind.tech", "enable_outgoing": 1}):
			self.assertRaises(frappe.ValidationError, mailbox.reply, SALES1, comm, "Thank you, we will call you")

	def test_upload_needs_sales_rights(self):
		self.assertRaises(frappe.PermissionError, lead_sources.upload, ACC, "/files/x.xlsx")
		cols = lead_sources._map_header(["Sender Name", "Sender Mobile", "Sender Email", "Company Name", "City", "Query Message"])
		self.assertEqual(cols, {"first_name": 0, "mobile_no": 1, "email": 2, "organization": 3, "city": 4, "requirement": 5})
