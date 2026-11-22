from sk_app.print_rules import clean_description


def test_internal_notes_never_print_sk_22_nov():
	d = ("SK 18-Nov: Divgi 2 separate SOs of Rs 1,80,000 each, 14-May-2026 (do not mix). This is SO 2; SO-00037 to be amended "
		"from Rs 3,60,000 to Rs 1,80,000. Shraddha: check amount/GST and PO no., then submit.")
	assert clean_description(d) == ""
	t = ("FROM TALLY SK/SO/059 dated 15-Oct-2026 (6-Nov audit, SK approved 'all missing need to enter'): Rs 2,00,000 before GST. "
		"Already invoiced: SINV-26-00148 Rs 2,36,000 dated 21-Oct. Submit, then link to the invoice.")
	assert clean_description(t) == ""
	keep = "GI portable cabin as per Drawing\nSize 30ft x 10ft x 8.6ft\n1) Conference Table - qty 1"
	assert clean_description(keep) == keep
	assert clean_description("Office cabin 20x10. Shraddha: check GST.") == "Office cabin 20x10."
