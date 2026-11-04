from sk_app.core.switch_rules import ENFORCE, WARN, pilot_list, rule_mode, uses_new


def test_no_row_or_old_means_old_path_for_everyone():
	assert not uses_new(None, "a@x")
	assert not uses_new({"path": "Old", "pilot_users": "a@x"}, "a@x")


def test_new_path_only_for_pilots():
	row = {"path": "New", "pilot_users": "Shraddha@skind.tech\n sk@x , other@x"}
	assert uses_new(row, "shraddha@skind.tech")
	assert uses_new(row, "SK@x")
	assert not uses_new(row, "rahul@x")


def test_new_path_with_no_pilots_is_everyone():
	assert uses_new({"path": "New", "pilot_users": ""}, "anyone@x")


def test_rules_warn_until_enforce():
	assert rule_mode(None) == WARN
	assert rule_mode({"rules": "Warn only"}) == WARN
	assert rule_mode({"rules": ENFORCE}) == ENFORCE


def test_pilot_list_dedupes():
	assert pilot_list("a@x\nA@x;b@x") == ["a@x", "b@x"]
