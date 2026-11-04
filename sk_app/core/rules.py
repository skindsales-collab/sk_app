"""One way for every module to report a broken rule (rebuild plan, Phase 0).

problems = [(rule key, plain words), ...] as the pure rule files return them (gate_rules, double_rules ...).
"Warn only" (the start for every module): each problem is written to SK Rule Log and the save goes on, so a week of real
work shows what the new rule would stop before anyone is stopped. "Enforce": the save is stopped with all the reasons.
"""

import frappe
from frappe import _

from sk_app.core.switch import rules_for
from sk_app.core.switch_rules import ENFORCE

LOG = "SK Rule Log"


def report(module: str, doc, problems: list, title: str | None = None) -> list:
	if not problems:
		return []
	mode = rules_for(module)
	if frappe.db.table_exists(LOG):
		for key, words in problems:
			frappe.get_doc({"doctype": LOG, "module": module, "rule": str(key)[:140], "mode": mode,
				"reference_doctype": doc.doctype if doc else None, "reference_name": doc.name if doc and not doc.is_new() else None,
				"user": frappe.session.user, "detail": str(words)[:1000]}).insert(ignore_permissions=True)
	if mode == ENFORCE:
		frappe.throw("<br>".join(_(w) for _k, w in problems), title=title or _("Data missing"))
	return problems
