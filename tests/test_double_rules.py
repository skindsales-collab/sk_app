"""SK 4-Nov-2026: double entry rules, checked on the doubles actually found in ERPNext that day."""

from sk_app.double_rules import bank_mode_to_cash, different_refs, find_pairs, looks_bank_ref, mobile_key, near, norm_ref, same_amount


def test_reference_numbers():
	assert norm_ref("IMPS 628918804996") == norm_ref("imps-628918804996") == "IMPS628918804996"
	for blank in [None, "", "NA", "n/a", "-", "0", "000", "Cash", "SK App 2026-10-28", "Cash 2026-11-04", "12"]:
		assert norm_ref(blank) is None, blank
	assert looks_bank_ref("IMPS628918804996") and looks_bank_ref("NEFT-CITI0000005") and looks_bank_ref("UTR 1234")
	assert not looks_bank_ref("Bill 45") and not looks_bank_ref(None)
	assert different_refs("INV/001", "INV/002") and not different_refs("INV/001", "inv 001") and not different_refs("INV/001", None)


def test_amounts_dates_mobiles():
	assert same_amount(1746400, 1746400.3) and not same_amount(1746400, 1746401)
	assert near("2026-10-27", "2026-11-03") and not near("2026-10-26", "2026-11-03")
	assert mobile_key("+91 98220 12345") == mobile_key("9822012345") == "9822012345"
	assert mobile_key("12345") is None


def test_net_banking_booked_in_cash_is_caught():
	# Shraddha 4-Nov: Neo Curtains 15,600 and 3,900 were Net Banking (mode type was Cash) booked from Cash - SITSPL
	assert bank_mode_to_cash("Bank", "Cash")
	assert bank_mode_to_cash("Cash", "Cash", "IMPS628918804996")
	assert not bank_mode_to_cash("Cash", "Cash", None)  # a real cash payment (some cabins) is fine
	assert not bank_mode_to_cash("Bank", "Bank", "IMPS1")


def _pe(name, party, amount, d, ref=None, ok=0, kind="Pay"):
	return {"doctype": "Payment Entry", "kind": kind, "name": name, "party": party, "amount": amount, "date": d, "ref": ref, "ok": ok}


def test_morning_list_finds_the_4nov_doubles():
	rows = [
		_pe("ACC-PAY-2026-00198", "Ai Portable Cabin", 332500, "2026-10-27"),
		_pe("ACC-PAY-2026-00204", "Ai Portable Cabin", 332500, "2026-10-30", "IMPS777"),
		_pe("ACC-PAY-2026-00205", "Swaraj", 50000, "2026-10-30", "IMPS 777"),  # same IMPS ref, other party
		_pe("ACC-PAY-2026-00197", "Ms. Technomech Solutions", 10000, "2026-10-26"),
		_pe("ACC-PAY-2026-00203", "Ms. Technomech Solutions", 10000, "2026-11-03"),  # 8 days apart: not listed
		_pe("ACC-PAY-2026-00300", "Oxford Realty Llp", 45900, "2026-10-28", kind="Receive"),
		_pe("ACC-PAY-2026-00301", "Oxford Realty Llp", 45900, "2026-10-29"),  # a payment, not a receipt: not listed
		{"doctype": "Purchase Invoice", "kind": "Purchase Invoice 0", "name": "PINV-26-00369", "party": "Plylam", "amount": 88500,
			"date": "2026-09-10", "ref": "Plylam 1234"},
		{"doctype": "Purchase Invoice", "kind": "Purchase Invoice 0", "name": "PINV-26-00371", "party": "Plylam", "amount": 88500,
			"date": "2026-09-10", "ref": "Plylam 1234"},
	]
	pairs = find_pairs(rows)
	got = {(p["first"]["name"], p["second"]["name"]) for p in pairs}
	assert ("ACC-PAY-2026-00198", "ACC-PAY-2026-00204") in got
	assert ("ACC-PAY-2026-00204", "ACC-PAY-2026-00205") in got
	assert ("PINV-26-00369", "PINV-26-00371") in got
	assert len(got) == 3, got  # each pair once, even when found by amount and by bill number


def test_ticked_not_a_double_is_not_listed_again():
	rows = [_pe("A", "X", 100, "2026-11-01"), _pe("B", "X", 100, "2026-11-02", ok=1)]
	assert find_pairs(rows) == []


def test_journal_and_payment_of_same_party_amount():
	# a Tally journal and a payment entry for the same payment
	rows = [_pe("ACC-PAY-2026-00012", "Oxford", 1746400, "2026-10-01"),
		{"doctype": "Journal Entry", "kind": "Pay", "name": "ACC-JV-2026-00500", "party": "Oxford", "amount": 1746400, "date": "2026-10-03"}]
	assert len(find_pairs(rows)) == 1
