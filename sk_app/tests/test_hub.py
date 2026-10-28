"""SK Hub (SK 28-Oct): one Claude connector for all Claude Projects, running as the signed-in person."""

import json

import frappe
from frappe.tests import IntegrationTestCase

from sk_app import hub, hub_tools
from sk_app.tests.test_change_list_a import _app_user

SALES = "sk_test_hub_sales@example.com"
STORE = "sk_test_hub_store@example.com"


def rpc(method, params=None, msg_id=1):
	return hub.handle_message({"jsonrpc": "2.0", "id": msg_id, "method": method, "params": params or {}})


def call(name, **arguments):
	answer = rpc("tools/call", {"name": name, "arguments": arguments})["result"]
	text = answer["content"][0]["text"]
	return answer["isError"], (text if answer["isError"] else json.loads(text))


class TestSKHub(IntegrationTestCase):
	def setUp(self):
		_app_user(SALES, "Sales", ["Sales User"])
		_app_user(STORE, "Stores", ["Stock User"])

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_handshake_and_tool_list(self):
		frappe.set_user(SALES)
		init = rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t"}})
		self.assertEqual(init["result"]["protocolVersion"], "2025-06-18")
		self.assertIn("tools", init["result"]["capabilities"])
		self.assertIsNone(hub.handle_message({"jsonrpc": "2.0", "method": "notifications/initialized"}))
		names = {t["name"] for t in rpc("tools/list")["result"]["tools"]}
		self.assertIn("create_draft", names)
		# nothing that submits, cancels or deletes
		self.assertFalse({n for n in names if any(w in n for w in ("submit", "cancel", "delete"))})
		self.assertEqual(rpc("no/such")["error"]["code"], -32601)

	def test_unknown_protocol_version_gets_ours(self):
		init = rpc("initialize", {"protocolVersion": "1999-01-01"})
		self.assertEqual(init["result"]["protocolVersion"], hub.PROTOCOL_VERSIONS[0])

	def test_overview_knows_the_team(self):
		frappe.set_user(STORE)
		err, out = call("hub_overview")
		self.assertFalse(err)
		self.assertEqual(out["user"], STORE)
		self.assertEqual(out["team"], "Stores")

	def test_runs_with_the_persons_own_permissions(self):
		frappe.set_user(STORE)  # a store user cannot read quotations
		err, text = call("search_records", doctype="Quotation", fields=["name"])
		self.assertTrue(err)

	def test_drafts_only_and_protected_fields_ignored(self):
		frappe.set_user(SALES)
		err, out = call("create_draft", doctype="ToDo", data={"description": "SK Hub test", "docstatus": 1, "owner": "x@y.z"}, project="Sales")
		self.assertFalse(err, out)
		todo = frappe.get_doc("ToDo", out["created"])
		self.assertEqual(todo.owner, SALES)
		self.assertTrue(frappe.db.exists("SK Hub Log", {"reference_name": todo.name, "action": "create", "project": "Sales"}))

	def test_system_setup_is_never_changed(self):
		frappe.set_user("Administrator")
		err, text = call("create_draft", doctype="User", data={"email": "hacker@example.com", "first_name": "H"})
		self.assertTrue(err)
		self.assertIn("system set-up", text)
		err, text = call("search_records", doctype="OAuth Bearer Token")
		self.assertTrue(err)

	def test_handoff_between_teams(self):
		frappe.set_user(SALES)
		err, out = call("post_handoff", to_team="Stores", subject="Check stock for cabin 41", project="Sales")
		self.assertFalse(err, out)
		frappe.set_user(STORE)
		err, rows = call("list_handoffs")
		self.assertIn(out["handoff"], [r["name"] for r in rows])
		err, done = call("close_handoff", handoff=out["handoff"], note="Stock OK")
		self.assertFalse(err, done)
		self.assertEqual(frappe.db.get_value("SK Hub Handoff", out["handoff"], "status"), "Done")

	def test_bad_arguments_come_back_as_readable_errors(self):
		frappe.set_user(SALES)
		err, text = call("get_record", doctype="ToDo")
		self.assertTrue(err)
		self.assertIn("Wrong arguments", text)
		err, text = call("search_records", doctype="No Such Doctype")
		self.assertTrue(err)
