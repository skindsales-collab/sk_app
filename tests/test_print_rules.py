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


def test_tally_and_cabin_numbers_never_print():
	from sk_app.print_rules import clean_description as c

	assert c("As per Tally invoice SK/IND/1026/821") == ""
	po = ("PO DATA FROM SK PO SHEET (negotiated price): Rs 205,000 before GST, PO date 2026-09-03, cabin no 293, Tally invoice 818. "
		"Sales: enter PO no., then submit. SK Portable Kiosk Shop: Requirement is kiosk cafe 15ft x 10ft. Old quote no 428. "
		"Source: CRM-LEAD-2026-00630 (Deal Won)")
	assert c(po) == "SK Portable Kiosk Shop: Requirement is kiosk cafe 15ft x 10ft."
	assert c("Office cabin 20x10 with toilet (cabins 294, 295)") == "Office cabin 20x10 with toilet"
	assert c("Cabin 226 security cabin 8x6") == "security cabin 8x6"
	assert c("Cabin 120 sq ft office") == "Cabin 120 sq ft office" and c("Cabin 20 x 10") == "Cabin 20 x 10"


def test_header_from_items_when_group_says_nothing():
	from sk_app.print_rules import items_noncabin as n

	assert n([{"item_code": "SK-JOB", "item_name": "Job / service (as per quotation)", "hsn": "998519"}]) is True
	assert n([{"item_code": "X1", "item_name": "Service Charges for Skilled Manpower", "hsn": "998519"}]) is True
	assert n([{"item_code": "SK-CABIN", "item_name": "Standard cabin (as per quotation)", "hsn": "94069090"}]) is False
	assert n([{"item_code": "Prod-0012-20ft x 10ft", "item_name": "Office", "hsn": ""}, {"item_code": "SK-TRANSPORT", "item_name": "Installation", "hsn": "9965"}]) is False
	assert n([{"item_code": "Ele-0063", "item_name": "MCB", "hsn": "8536"}]) is None
	assert n([{"item_code": "SK-JOB", "item_name": "Job / service (as per quotation)", "hsn": "94069090"}]) is True  # Tally HSN on a job
