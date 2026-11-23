"""Nightly data check (SK 14-Nov): items, owners, new / fixed between two nights, the Rule Log line, mail subject."""

from sk_app.core.night_rules import (DRAFT_DOCTYPES, KINDS, by_user, dedupe, detail_text, diff, draft_is_stale, item, key, module_lines,
	parse_detail, person_summary, subject)


def test_item_takes_the_kinds_words_and_owner_function():
	it = item("unlinked_payment", "Payment Entry", "ACC-PAY-1", "Hi Box ₹12,000 unallocated", "acc@skind.tech")
	assert it["function"] == "Accounts" and it["action"].startswith("Link the payment")
	late = item("late", "Sales Order", "SO-1", "Orders to start: Godrej · 4 days late", "sales@x", function="Production", days=4)
	assert late["function"] == "Production" and late["days"] == 4 and key(late) == ("late", "Sales Order", "SO-1")


def test_same_record_through_two_people_is_one_item():
	a = item("late", "CRM Lead", "L1", "x", "member@x", function="Sales")
	b = item("late", "CRM Lead", "L1", "x", "manager@x", function="Sales")
	assert dedupe([a, b]) == [a]


def test_new_and_fixed_between_two_nights():
	last = [item("draft", "Quotation", "Q1", "", "u"), item("draft", "Quotation", "Q2", "", "u")]
	now = [item("draft", "Quotation", "Q2", "", "u"), item("draft", "Quotation", "Q3", "", "u")]
	new, fixed = diff(last, now)
	assert new == {("draft", "Quotation", "Q3")} and fixed == {("draft", "Quotation", "Q1")}
	assert person_summary(now, new, len(fixed)) == {"open": 2, "new": 1, "fixed": 1}


def test_by_user_orders_doubles_first_then_oldest():
	items = [item("draft", "Sales Order", "S", "", "u", days=1), item("late", "Sales Order", "A", "", "u", days=9),
		item("late", "Sales Order", "B", "", "u", days=30), item("double", "Journal Entry", "J", "", "u")]
	assert [i["name"] for i in by_user(items)["u"]] == ["J", "B", "A", "S"]


def test_rule_log_detail_round_trip():
	it = item("late", "Purchase Order", "PO-9", "PO sent, to come: Steel supplier", "p@x", function="Purchase", days=6)
	d = parse_detail(detail_text(it))
	assert d == {"function": "Purchase", "what": "PO sent, to come: Steel supplier", "action": KINDS["late"][1], "days": 6}
	assert parse_detail("") == {"function": "", "what": "", "action": "", "days": 0}


def test_module_lines_and_subject():
	items = [item("late", "X", "1", "", "u", function="Sales"), item("late", "X", "2", "", "u", function="Sales"),
		item("draft", "X", "3", "", "u", function="Accounts")]
	assert module_lines(items) == [("Sales", 2, 2), ("Accounts", 1, 0)]
	assert subject(0, 0) == "SK App night check: all clear"
	assert subject(1, 0) == "SK App night check: 1 item to fix" and subject(5, 2) == "SK App night check: 5 items to fix (2 new)"


def test_drafts_never_include_salary_and_a_fresh_draft_waits():
	assert "Salary Slip" not in DRAFT_DOCTYPES and "Payroll Entry" not in DRAFT_DOCTYPES and "Job Card" not in DRAFT_DOCTYPES
	assert not draft_is_stale(0) and not draft_is_stale(1) and draft_is_stale(2)


def test_quote_and_expense_drafts_wait_two_days_then_go_to_sk_after_five():
	from sk_app.core.night_rules import draft_due

	assert draft_due("Quotation", 2) == (False, False)
	assert draft_due("Quotation", 3) == (True, False)
	assert draft_due("Expense Claim", 6) == (True, True)
	assert draft_due("Sales Order", 2) == (True, False)  # other drafts keep the 1-day grace, never to SK
