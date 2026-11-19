"""SK 4-Nov-2026: double entry rules, checked on the doubles actually found in ERPNext that day."""

from sk_app.double_rules import bank_mode_to_cash, day_window, different_refs, find_pairs, looks_bank_ref, mobile_key, near, norm_ref, same_amount, tally_ref


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


def test_plain_tally_serials_are_two_vouchers():
	# checker 9-Nov: 8 of 9 pairs left were Tally receipts numbered 329 and 330 (314 / 320, 206 / 207 ...): two entries
	assert find_pairs([_pe("A", "Anand", 16000, "2026-10-05", "329"), _pe("B", "Anand", 16000, "2026-10-05", "330")]) == []
	# the same plain number twice is still a double; a plain number against no number too
	assert len(find_pairs([_pe("A", "Anand", 16000, "2026-10-05", "329"), _pe("B", "Anand", 16000, "2026-10-05", "329")])) == 1
	assert len(find_pairs([_pe("A", "Anand", 16000, "2026-10-05", "329"), _pe("B", "Anand", 16000, "2026-10-06")])) == 1


def test_bank_side_pairs_a_payment_entry_with_a_journal_without_party():
	# checker 9-Nov: PE-00202 (Babasaheb advance, bank date 26-Oct, IMPS) = JE-01769 (Tally PAY/586, no party, 26-Oct)
	bank = "STATE BANK OF INDIA - SITSPL"
	rows = [{"doctype": "Payment Entry", "kind": "bank out", "name": "ACC-PAY-2026-00202", "party": bank, "payee": "Babasaheb Sir [Advance]",
			"amount": 5000, "date": "2026-10-26", "ref": "IMPS62991715402"},
		{"doctype": "Journal Entry", "kind": "bank out", "name": "ACC-JV-2026-01769", "party": bank, "payee": None,
			"hint": "Tally Payment PAY/586/25-26 | BABASAHEB SIR (ADVANCE)", "amount": 5000, "date": "2026-10-26", "ref": "PAY/586/25-26"}]
	assert [(p["first"]["name"], p["second"]["name"]) for p in find_pairs(rows)] == [("ACC-JV-2026-01769", "ACC-PAY-2026-00202")]
	# another person's advance of the same amount on the same bank (JE-01734 Shraddha, 24-Oct) is not the pair
	other = {**rows[1], "name": "ACC-JV-2026-01734", "hint": "Tally Payment PAY/581/25-26 | Shraddha Mam [Advance]", "date": "2026-10-24", "ref": "PAY/581/25-26"}
	assert find_pairs([rows[0], other]) == []
	# two payees named and different: two payments of the same amount on one day are not a pair
	rows[1]["payee"] = "Someone Else"
	assert find_pairs(rows) == []
	# money in against money out is never a pair
	rows[1]["payee"] = None; rows[1]["kind"] = "bank in"
	assert find_pairs(rows) == []


def test_two_entries_with_their_own_voucher_numbers_are_not_a_pair():
	# SK 7-Nov: all 9 pairs of the morning mail were Tally entries with their own numbers; the bank showed both payments
	assert find_pairs([_pe("A", "Vascon", 50000, "2026-11-01", "PAY/526"), _pe("B", "Vascon", 50000, "2026-11-02", "PAY/527")]) == []
	assert find_pairs([_pe("A", "Vascon", 50000, "2026-11-01", "J329"), _pe("B", "Vascon", 50000, "2026-11-02", "J330")]) == []
	# one of them without a number: still a possible double
	assert len(find_pairs([_pe("A", "Vascon", 50000, "2026-11-01", "PAY/526"), _pe("B", "Vascon", 50000, "2026-11-02")])) == 1


def test_tally_invoice_number_in_remarks_is_the_reference():
	assert tally_ref("Tally invoice SK/IND/0926/812 (was journal entry ACC-JV-2026-01542, total Rs 106,200). Accounts: cancel first") == "SK/IND/0926/812"
	assert tally_ref("Tally voucher no PUR/NC/066/25-26 | Ms. Technomech") == "PUR/NC/066/25-26"
	assert tally_ref("Tally Purchase [Non Cabin] PUR/NC/066/25-26") is None  # the bracket breaks the pattern: such bills carry bill_no anyway
	assert tally_ref("Issued from SK App") is None
	# checker 7-Nov: SINV-26-00101 / 00102, same customer, same amount, same day, own Tally numbers → not a pair
	si = lambda n, ref: {"doctype": "Sales Invoice", "kind": "Sales Invoice 0", "name": n, "party": "Sj Contracts Private Limited", "amount": 106200,
		"date": "2026-09-29", "ref": f"Sj Contracts Private Limited {ref}"}
	assert find_pairs([si("SINV-26-00101", tally_ref("Tally invoice SK/IND/0926/812 (was journal entry ACC-JV-2026-01542)")),
		si("SINV-26-00102", tally_ref("Tally invoice SK/IND/0926/813 (was journal entry ACC-JV-2026-01543)"))]) == []
	assert len(find_pairs([si("SINV-26-00101", "SK/IND/0926/812"), si("SINV-26-00103", "SK/IND/0926/812")])) == 1  # same number twice: a double


def test_same_lead_same_date_is_a_duplicate_other_date_is_new():
	# SK 7-Nov (KF-04801): a JustDial lead of 4-Nov evening; the same mobile again that night = duplicate, on 5-Nov = new lead
	start, end = day_window("2026-11-04 10:00:00")
	assert (start, end) == ("2026-11-04 00:00:00", "2026-11-04 23:59:59")
	assert start <= "2026-11-04 19:06:01" <= end
	assert not (start <= "2026-11-05 19:46:02" <= end)
	assert day_window("2026-11-07") == ("2026-11-07 00:00:00", "2026-11-07 23:59:59")


def test_ticked_not_a_double_is_not_listed_again():
	rows = [_pe("A", "X", 100, "2026-11-01"), _pe("B", "X", 100, "2026-11-02", ok=1)]
	assert find_pairs(rows) == []


def test_journal_and_payment_of_same_party_amount():
	# a Tally journal and a payment entry for the same payment
	rows = [_pe("ACC-PAY-2026-00012", "Oxford", 1746400, "2026-10-01"),
		{"doctype": "Journal Entry", "kind": "Pay", "name": "ACC-JV-2026-00500", "party": "Oxford", "amount": 1746400, "date": "2026-10-03"}]
	assert len(find_pairs(rows)) == 1


def test_bank_number_never_clears_a_pair():
	from sk_app.double_rules import different_vouchers, ref_kind, voucher_double

	assert ref_kind("PAY/586/25-26") == ref_kind("J329") == ref_kind("SK/IND/0926/812") == "tally"
	assert ref_kind("IMPS62991715402") == ref_kind("ICICR2202261") == ref_kind("469833504408") == "bank"
	assert ref_kind("INV-305") == "bill" and ref_kind("JE-01769") == "bill" and ref_kind(None) is None
	# same kind, own numbers: two real entries (SK 7-Nov)
	assert different_vouchers("PAY/526", "PAY/527") and different_vouchers("J329", "J330") and different_vouchers("INV-305", "INV-306")
	assert not different_vouchers("ICICR2202261", "469833504408") and not different_vouchers("PAY/586/25-26", "IMPS62991715402")
	assert voucher_double("PAY/586/25-26", "2026-10-14", "IMPS62991715402", "2026-10-22")  # 8 days, Tally vs bank
	assert not voucher_double("PAY/526", "2026-10-14", "PAY/527", "2026-10-14")
	assert not voucher_double(None, "2026-10-01", None, "2026-10-09")  # no numbers: 7 days only


def test_checker_7nov_live_doubles_stay_in_morning_list():
	pe = lambda n, ref, d, party, amount: {"doctype": "Payment Entry", "kind": "Pay", "name": n, "party": party, "amount": amount, "date": d, "ref": ref}
	je = lambda n, ref, d, party, amount: {"doctype": "Journal Entry", "kind": "Pay", "name": n, "party": party, "amount": amount, "date": d, "ref": ref}
	# Oxford Rs 17,46,400 paid twice, two different bank numbers
	oxford = find_pairs([pe("ACC-PAY-2026-00012", "ICICR2202261", "2026-10-27", "Oxford", 1746400),
		pe("ACC-PAY-2026-00206", "469833504408", "2026-11-03", "Oxford", 1746400)])
	assert len(oxford) == 1
	# Babasaheb Rs 5,000: Tally journal PAY/586/25-26 and the app payment by IMPS, 8 days apart
	baba = find_pairs([je("ACC-JV-2026-01769", "PAY/586/25-26", "2026-10-14", "Babasaheb", 5000),
		pe("ACC-PAY-2026-00202", "IMPS62991715402", "2026-10-22", "Babasaheb", 5000)])
	assert len(baba) == 1 and "10 days" in baba[0]["why"]
	# the 7-Nov mail's false pairs stay out: own Tally numbers / bill numbers
	assert find_pairs([je("ACC-JV-1", "PAY/526", "2026-10-14", "X", 5000), je("ACC-JV-2", "PAY/527", "2026-10-14", "X", 5000)]) == []
	assert find_pairs([je("ACC-JV-3", "J329", "2026-10-14", "X", 5000), je("ACC-JV-4", "J330", "2026-10-15", "X", 5000)]) == []
	# no number and 8 days apart: outside the 7-day window as before
	assert find_pairs([je("ACC-JV-5", None, "2026-10-14", "X", 5000), pe("PE-9", None, "2026-10-22", "X", 5000)]) == []
