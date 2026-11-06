"""Pure rule: who must have an SK App login (SK 6-Nov, Santosh case: "such gaps are not acceptable after the rebuild").
Every active Employee, and every supplier we buy services from (a submitted service PO or labour bill this year).
No name in code: people come from ERPNext masters; the login is made from the mobile number."""

EMPLOYEE, SUPPLIER = "Employee", "Supplier"


def missing_logins(employees: list[dict], suppliers: list[dict], logins: set, supplier_logins: set) -> list[dict]:
	"""employees = [{name, employee_name, user_id, cell_number, status}], suppliers = [{name, supplier_name, mobile}] (service
	suppliers only), logins = user ids with an enabled app login, supplier_logins = supplier names already linked to a login.
	Returns [{kind, name, full_name, mobile, can_make}]."""
	out = []
	for e in employees:
		if (e.get("status") or "Active") != "Active":
			continue
		if e.get("user_id") and e["user_id"] in logins:
			continue
		mobile = _digits(e.get("cell_number"))
		out.append({"kind": EMPLOYEE, "name": e["name"], "full_name": e.get("employee_name") or e["name"], "mobile": mobile,
			"can_make": len(mobile) == 10})
	for s in suppliers:
		if s["name"] in supplier_logins:
			continue
		mobile = _digits(s.get("mobile"))
		out.append({"kind": SUPPLIER, "name": s["name"], "full_name": s.get("supplier_name") or s["name"], "mobile": mobile,
			"can_make": len(mobile) == 10})
	return out


def _digits(text) -> str:
	d = "".join(ch for ch in str(text or "") if ch.isdigit())
	if len(d) == 12 and d.startswith("91"):
		d = d[2:]
	if len(d) == 11 and d.startswith("0"):
		d = d[1:]
	return d
