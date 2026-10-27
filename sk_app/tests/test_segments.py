"""Change list point 2: Cabin / Non-Cabin, two levels; each team sees only its customers."""

import frappe
from frappe.tests import IntegrationTestCase

from sk_app import lead_sources, segments
from sk_app.tests.test_change_list_a import _app_user

CABIN_REP = "sk_test_s_cabin@example.com"
NONCABIN = "sk_test_s_noncabin@example.com"
CEO = "sk_test_s_ceo@example.com"


def _customer(name, group):
	if frappe.db.exists("Customer", name):
		frappe.db.set_value("Customer", name, "customer_group", group)
		return name
	return frappe.get_doc({"doctype": "Customer", "customer_name": name, "customer_group": group,
		"customer_type": "Company"}).insert(ignore_permissions=True).name


class TestSegments(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		segments.ensure_customer_groups()
		_app_user(CABIN_REP, "Sales", ["Sales User"])
		_app_user(NONCABIN, "Machine Shifting", ["Sales User", "Projects User"])
		_app_user(CEO, "Management", ["System Manager"])
		frappe.db.set_value("SK App User", {"user": NONCABIN}, "sk_main_segment", "Non-Cabin")

	def test_two_levels(self):
		self.assertEqual(segments.main_of("LGSF"), "Cabin")
		self.assertEqual(segments.main_of("Cabin"), "Cabin")  # old flat value
		self.assertEqual(segments.sub_of("Cabin"), "Standard Cabin (GI / ACP)")
		self.assertEqual(segments.main_of("Job Work"), "Non-Cabin")
		self.assertEqual(segments.main_of("Other Non-Cabin"), "Non-Cabin")
		for g in segments.all_groups():
			self.assertTrue(frappe.db.exists("Customer Group", g), g)
		self.assertEqual(frappe.db.get_value("Customer Group", "LGSF", "parent_customer_group"), "Cabin")
		self.assertEqual(lead_sources.segment_of("Need LGSF site office"), "LGSF")
		self.assertEqual(lead_sources.segment_of("labour camp G+1 for 200 workers"), "Modular / Labour Camp")

	def test_who_sees_what(self):
		self.assertEqual(segments.user_main(CABIN_REP), "Cabin")
		self.assertEqual(segments.user_main(NONCABIN), "Non-Cabin")
		self.assertEqual(segments.user_main(CEO), "Both")
		cab = _customer("SK Test Seg Cabin Co", "LGSF")
		non = _customer("SK Test Seg Shifting Co", "Machine Shifting")
		old = _customer("SK Test Seg Old Co", "Commercial") if frappe.db.exists("Customer Group", "Commercial") else \
			_customer("SK Test Seg Old Co", frappe.db.get_value("Customer Group", {"is_group": 0, "name": ["not in", segments.all_groups()]}))
		names = lambda user, **kw: {r["name"] for r in segments.customers(user, q="SK Test Seg", **kw)["rows"]}  # noqa: E731
		self.assertEqual(names(CABIN_REP), {cab})
		self.assertEqual(names(NONCABIN), {non})
		self.assertEqual(names(CEO), {cab, non})
		self.assertEqual(names(CEO, segment="Non-Cabin"), {non})
		# a form's customer search (complaints): own segment plus untagged old customers, never the other team's
		self.assertEqual(names(CABIN_REP, tab="pick"), {cab, old})
		# not tagged: only on the "Segment not set" tab, and only for Management / Aditya / the sales manager
		self.assertIn(old, names(CEO, tab="not_set"))
		self.assertRaises(frappe.PermissionError, segments.customers, CABIN_REP, "not_set")
		self.assertRaises(frappe.PermissionError, segments.tag, CABIN_REP, old, "LGSF")
		res = segments.tag(NONCABIN, old, "Job Work")
		self.assertEqual(res["main"], "Non-Cabin")
		self.assertEqual(frappe.db.get_value("Customer", old, "customer_group"), "Job Work")
		self.assertIn(old, names(NONCABIN))
		self.assertTrue(frappe.db.exists("Comment", {"reference_doctype": "Customer", "reference_name": old}))


class TestViewMemberApp(IntegrationTestCase):
	"""Point 3: the CEO opens a member's app as the member sees it, view only."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		_app_user(CABIN_REP, "Sales", ["Sales User"])
		_app_user(CEO, "Management", ["System Manager"])

	def test_ceo_sees_the_member_screens_and_cannot_save(self):
		from frappe.tests.classes.context_managers import set_user

		from sk_app import api, view_member

		with set_user(CEO):
			groups = {g["function"]: g for g in api.view_members()["groups"]}
			self.assertIn(CABIN_REP, [p["user"] for p in groups["Sales"]["people"]])
			h = api.view_as(CABIN_REP, "home", "{}", "home")
			self.assertEqual(h["user"], CABIN_REP)
			self.assertEqual(frappe.session.user, CEO)  # straight back to the CEO
			self.assertRaises(frappe.PermissionError, api.view_as, CABIN_REP, "add_work", '{"text": "x"}')  # POST only
			self.assertRaises(frappe.PermissionError, api.view_as, CABIN_REP, "view_as", "{}")
			name = api.view_suggest(CABIN_REP, "Show the deal value bigger", "my_deals")
		self.assertIn("Show the deal value bigger", frappe.db.get_value("SK Work Log", name, "description"))
		self.assertTrue(frappe.db.exists("Activity Log", {"reference_doctype": "User", "reference_name": CABIN_REP, "user": CEO}))
		with set_user(CABIN_REP):
			self.assertRaises(frappe.PermissionError, api.view_as, CEO, "home", "{}")
		self.assertFalse(view_member.can_view(CABIN_REP))

	def test_manager_sees_only_his_team(self):
		from frappe.tests.classes.context_managers import set_user

		from sk_app import api, view_member

		_app_user(NONCABIN, "Sales", ["Sales User"])
		frappe.db.set_value("SK App User", {"user": CABIN_REP}, "manager", NONCABIN)
		frappe.db.set_value("SK App User", {"user": CEO}, "manager", None)
		try:
			self.assertTrue(view_member.can_view(NONCABIN))
			with set_user(NONCABIN):
				people = [p["user"] for g in api.view_members()["groups"] for p in g["people"]]
				self.assertEqual(people, [CABIN_REP])
				self.assertEqual(api.view_as(CABIN_REP, "home", "{}", "home")["user"], CABIN_REP)
				self.assertRaises(frappe.PermissionError, api.view_as, CEO, "home", "{}")
				self.assertIn("view_member", api.home()["sections"]["sections"][0]["tiles"])
		finally:
			frappe.db.set_value("SK App User", {"user": CABIN_REP}, "manager", None)


class TestCeoDashboards(IntegrationTestCase):
	"""Point 13: every live dashboard page opens for the CEO, with lists behind its numbers; nobody else opens them."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		_app_user(CABIN_REP, "Sales", ["Sales User"])
		_app_user(CEO, "Management", ["System Manager"])

	def test_every_page_opens_for_the_ceo_only(self):
		from sk_app import dashboards

		for key in dashboards.PAGE_KEYS:
			for seg in (None, "Cabin"):
				d = dashboards.page(CEO, key, segment=seg)
				self.assertEqual(d["key"], key)
				for c in d["cards"]:
					self.assertIn("label", c)
					self.assertIsInstance(c["rows"] or [], list)
		self.assertTrue(dashboards.page(CEO, "overview")["cards"])
		self.assertRaises(frappe.PermissionError, dashboards.page, CABIN_REP, "overview")
		self.assertIsInstance(dashboards.badges(CEO), dict)
		from sk_app.functions import DASH_TILES

		self.assertEqual([f"dash_{k}" for k in dashboards.PAGE_KEYS], DASH_TILES)

	def test_tally_sales_and_draft_orders_count(self):
		"""Live sk-dev: the year's sales are Tally Journal Entries and the orders are drafts (SK 26-Oct: "not getting live data")."""
		from frappe.utils import nowdate

		from sk_app import dashboards

		company = frappe.db.get_value("Company", {}, "name")
		if not company:
			self.skipTest("needs an ERPNext company")
		income = frappe.db.get_value("Account", {"company": company, "root_type": "Income", "is_group": 0}, "name")
		debtor = frappe.db.get_value("Account", {"company": company, "account_type": "Cash", "is_group": 0}, "name")
		start, end, _ps, _pe = dashboards._period(None)
		before = dashboards._invoiced(start, end)
		je = frappe.get_doc({"doctype": "Journal Entry", "company": company, "posting_date": nowdate(),
			"user_remark": "Tally Non Cabin Sales 9001 | SK Test Party", "accounts": [
				{"account": debtor, "debit_in_account_currency": 11800},
				{"account": income, "credit_in_account_currency": 11800}]}).insert(ignore_permissions=True)
		je.submit()
		self.assertEqual(dashboards._invoiced(start, end) - before, 11800)
		self.assertTrue(any(r.name == je.name for r in dashboards._tally_sales(start, end, "Non-Cabin")))
		self.assertFalse(any(r.name == je.name for r in dashboards._tally_sales(start, end, "Cabin")))

	def test_dues_from_ledger_and_tag_from_tally(self):
		"""Trial on live sk-dev data (26-Oct): Tally bills are Journal Entries against the party, so the CEO's receivables
		come from the ledger; customers get their Cabin / Non-Cabin from their Tally sales vouchers."""
		from frappe.utils import add_days, nowdate

		from sk_app import dashboards

		company = frappe.db.get_value("Company", {}, "name")
		if not company:
			self.skipTest("needs an ERPNext company")
		debtors = frappe.db.get_value("Account", {"company": company, "account_type": "Receivable", "is_group": 0}, "name")
		income = frappe.db.get_value("Account", {"company": company, "root_type": "Income", "is_group": 0}, "name")
		cash = frappe.db.get_value("Account", {"company": company, "account_type": "Cash", "is_group": 0}, "name")
		if not (debtors and income and cash):
			self.skipTest("needs debtors, income and cash accounts")
		old_group = frappe.db.get_value("Customer Group", {"is_group": 0, "name": ["not in", segments.all_groups()]}) or "All Customer Groups"
		party = _customer("SK Test Tally Party", old_group)
		frappe.db.set_value("Customer", party, "customer_group", old_group)

		def je(remark, days_ago, dr, cr, amount, party_side):
			rows = [{"account": dr, "debit_in_account_currency": amount}, {"account": cr, "credit_in_account_currency": amount}]
			rows[0 if party_side == "dr" else 1].update({"party_type": "Customer", "party": party})
			d = frappe.get_doc({"doctype": "Journal Entry", "company": company, "posting_date": add_days(nowdate(), -days_ago),
				"user_remark": remark, "accounts": rows}).insert(ignore_permissions=True)
			d.submit()

		je("Tally Non Cabin Sales 9101 | SK Test Tally Party", 90, debtors, income, 50000, "dr")
		je("Tally Non Cabin Sales 9102 | SK Test Tally Party", 10, debtors, income, 20000, "dr")
		je("Tally Receipt 9103 | SK Test Tally Party", 5, cash, debtors, 30000, "cr")
		due = next(r for r in dashboards._receivables() if r.name == party)
		self.assertEqual(due.outstanding_amount, 40000)  # 70,000 billed - 30,000 paid
		self.assertEqual(due.ages["Over 60 days"], 20000)  # the payment went to the oldest bill first
		self.assertEqual(due.ages["0-30 days"], 20000)
		self.assertGreaterEqual(due.late, 89)

		self.assertEqual(segments.tally_suggestions().get(party), "Non-Cabin")
		with self.assertRaises(frappe.PermissionError):
			segments.tag_from_tally(CABIN_REP)
		r = segments.tag_from_tally(CEO)
		self.assertGreaterEqual(r["non_cabin"], 1)
		self.assertEqual(frappe.db.get_value("Customer", party, "customer_group"), "Other Non-Cabin")
		self.assertNotIn(party, segments.tally_suggestions())
