"""SK Hub (SK 28-Oct): one Claude connector for every Claude Project, inside ERPNext.

Claude connects to   https://<erpnext-site>/api/method/sk_app.hub.mcp
and every person signs in with their OWN ERPNext login (Frappe's built-in OAuth:
dynamic client registration + PKCE, switched on in OAuth Settings). Each tool then runs
as that person, so their ERPNext roles, the CRM own-leads rule and every other permission
apply exactly as on the desk and in the SK App.

This file is the MCP "Streamable HTTP" transport, written for Frappe's normal request
cycle: one JSON-RPC message (or a batch) in, one JSON answer out, no server-side session.
The tools themselves are in sk_app/hub_tools.py.
"""

import json
import traceback

import frappe
from werkzeug.wrappers import Response

SERVER_NAME = "SK Hub"
SERVER_VERSION = "1.0.0"
# newest first; we answer with the client's version when we know it, else our newest
PROTOCOL_VERSIONS = ("2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05")

INSTRUCTIONS = (
	"SK Hub is the shared ERPNext connector of SK IND Tech Solutions Pvt Ltd. Every Claude Project "
	"(Sales, Design, Store, Purchase, Production, Quality, Finance, HR, Machine Shifting ...) uses it, so "
	"ERPNext is the single source of truth for all departments. You act as the signed-in person, with "
	"exactly their ERPNext permissions.\n"
	"- Start with hub_overview: it says who you are, your team, and any open handoffs for your team.\n"
	"- Read numbers from ERPNext (search_records, get_record, count_records, item_stock); never guess.\n"
	"- Before creating a record you have not made before, call describe_doctype to get the exact fields.\n"
	"- You can create and change DRAFTS only. Submitting, cancelling and deleting stay with the responsible "
	"person in ERPNext / SK App, so the ERPNext flow is never bypassed. Say which draft you made and who "
	"must submit it.\n"
	"- When work must move to another team (sales -> design -> store ...), use post_handoff; the other "
	"team's Project sees it in list_handoffs. Close a handoff with close_handoff when it is done.\n"
	"- Two Projects must never bulk-change the same records at the same time: check list_handoffs and "
	"recent_activity before any bulk change."
)


# ---- HTTP entry point ---------------------------------------------------------------------------
@frappe.whitelist(allow_guest=True, methods=["GET", "POST", "DELETE"])
def mcp(**_ignored):
	"""The MCP endpoint. Guests get 401 + where to sign in; signed-in users get JSON-RPC answers."""
	request = frappe.request
	if request.method != "POST":
		# no server-sent event stream and no sessions to end: POST only
		return _http(405, {"error": "Use POST for MCP requests."}, headers={"Allow": "POST"})

	if frappe.session.user in ("Guest", "", None):
		base = frappe.utils.get_url()
		return _http(
			401,
			{"error": "Sign in to ERPNext to use SK Hub."},
			headers={"WWW-Authenticate": f'Bearer resource_metadata="{base}/.well-known/oauth-protected-resource"'},
		)

	if frappe.get_cached_value("User", frappe.session.user, "user_type") != "System User":
		# customers / suppliers with a portal login never get the hub
		return _http(403, {"error": "SK Hub is only for SK staff with an ERPNext desk login."})

	raw = request.get_data(as_text=True)
	try:
		message = json.loads(raw) if raw else None
	except ValueError:
		return _http(400, _error(None, -32700, "Parse error: body is not JSON"))

	if isinstance(message, list):  # JSON-RPC batch (2025-03-26 clients)
		answers = [a for a in (handle_message(m) for m in message) if a is not None]
		return _http(200, answers) if answers else _http(202, None)

	answer = handle_message(message)
	if answer is None:  # a notification or a response from the client: nothing to send back
		return _http(202, None)
	return _http(200, answer)


def _http(status: int, body, headers: dict | None = None) -> Response:
	response = Response(status=status, headers=headers or {})
	if body is not None:
		response.mimetype = "application/json"
		response.set_data(json.dumps(body, default=str, ensure_ascii=False))
	return response


# ---- JSON-RPC ---------------------------------------------------------------------------------
def _error(msg_id, code: int, text: str) -> dict:
	return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": text}}


def _result(msg_id, result: dict) -> dict:
	return {"jsonrpc": "2.0", "id": msg_id, "result": result}


def handle_message(message) -> dict | None:
	"""Answer one JSON-RPC message. Returns None for notifications and client responses."""
	if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
		return _error(None, -32600, "Invalid request: expected a JSON-RPC 2.0 object")

	if "method" not in message:  # a response to something we asked (we never ask): ignore
		return None

	method = message.get("method")
	params = message.get("params") or {}
	is_notification = "id" not in message
	msg_id = message.get("id")

	if is_notification:
		return None  # notifications/initialized, notifications/cancelled ... need no answer

	if not isinstance(params, dict):
		return _error(msg_id, -32602, "params must be an object")

	if method == "initialize":
		asked = params.get("protocolVersion")
		version = asked if asked in PROTOCOL_VERSIONS else PROTOCOL_VERSIONS[0]
		return _result(
			msg_id,
			{
				"protocolVersion": version,
				"capabilities": {"tools": {"listChanged": False}},
				"serverInfo": {"name": SERVER_NAME, "title": "SK Hub (ERPNext)", "version": SERVER_VERSION},
				"instructions": INSTRUCTIONS,
			},
		)

	if method == "ping":
		return _result(msg_id, {})

	if method == "tools/list":
		from sk_app import hub_tools

		return _result(msg_id, {"tools": hub_tools.tool_list()})

	if method == "tools/call":
		return _result(msg_id, call_tool(params.get("name"), params.get("arguments") or {}))

	if method in ("resources/list", "resources/templates/list"):
		return _result(msg_id, {"resources": []} if method == "resources/list" else {"resourceTemplates": []})

	if method == "prompts/list":
		return _result(msg_id, {"prompts": []})

	return _error(msg_id, -32601, f"Method not found: {method}")


def call_tool(name: str, arguments: dict) -> dict:
	"""Run one tool as the signed-in user. Errors come back as a tool result Claude can read."""
	from sk_app import hub_tools

	tool = hub_tools.TOOLS.get(name or "")
	if tool is None:
		return _tool_error(f"Unknown tool '{name}'. Call tools/list to see the SK Hub tools.")
	if not isinstance(arguments, dict):
		return _tool_error("arguments must be an object")

	try:
		output = tool["fn"](**arguments)
	except TypeError as e:
		frappe.db.rollback()
		return _tool_error(f"Wrong arguments for {name}: {e}")
	except (frappe.PermissionError, frappe.ValidationError, frappe.DoesNotExistError) as e:
		frappe.db.rollback()
		frappe.clear_messages()
		return _tool_error(_clean(e) or type(e).__name__)
	except Exception as e:
		frappe.db.rollback()
		frappe.clear_messages()
		frappe.log_error(title=f"SK Hub tool {name} failed", message=traceback.format_exc())
		return _tool_error(f"{type(e).__name__}: {_clean(e)}")

	frappe.clear_messages()  # msgprints from ERPNext validations are not for the JSON answer
	text = json.dumps(output, default=str, ensure_ascii=False, indent=1)
	if len(text) > hub_tools.MAX_ANSWER_CHARS:
		text = (
			text[: hub_tools.MAX_ANSWER_CHARS]
			+ "\n... [answer cut: ask for fewer rows or fields, or use start/limit to page]"
		)
	return {"content": [{"type": "text", "text": text}], "isError": False}


def _tool_error(text: str) -> dict:
	return {"content": [{"type": "text", "text": text}], "isError": True}


def _clean(e: Exception) -> str:
	"""Plain message from a Frappe exception (they often carry HTML)."""
	text = str(e) or ""
	return frappe.utils.strip_html(text).strip()[:1500]
