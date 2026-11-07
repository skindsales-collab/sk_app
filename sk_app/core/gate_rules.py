"""Pure rule of the switch gate (SK 6-Nov, KF-04334 "no missing after rebuild"): before a module goes Old → New, and
before old code is removed, the record counts per doctype and per person must still all be there. New records made
after the switch are fine; a record that was there before and is not now is a difference, and a difference blocks."""


def compare(before: dict, now: dict, new_since: dict) -> dict:
	"""before / now = {doctype: {"total": n, "by_owner": {owner: n}}}; new_since = {doctype: {"total": n, "by_owner": {...}}}
	made after the switch. Returns {"ok": bool, "missing": {doctype: {"total": n, "by_owner": {owner: n}}}, "rows": [...]}."""
	missing, rows = {}, []
	for dt, b in (before or {}).items():
		n = (now or {}).get(dt) or {"total": 0, "by_owner": {}}
		added = (new_since or {}).get(dt) or {"total": 0, "by_owner": {}}
		gone = int(b.get("total") or 0) - (int(n.get("total") or 0) - int(added.get("total") or 0))
		by_owner = {}
		for owner, cnt in (b.get("by_owner") or {}).items():
			left = int(cnt) - (int((n.get("by_owner") or {}).get(owner, 0)) - int((added.get("by_owner") or {}).get(owner, 0)))
			if left > 0:
				by_owner[owner] = left
		rows.append({"doctype": dt, "before": int(b.get("total") or 0), "now": int(n.get("total") or 0), "new": int(added.get("total") or 0),
			"missing": max(gone, 0)})
		if gone > 0 or by_owner:
			missing[dt] = {"total": max(gone, 0), "by_owner": by_owner}
	return {"ok": not missing, "missing": missing, "rows": rows}
