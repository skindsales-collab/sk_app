from sk_app.photo_entry_rules import gstins, iso_date, parse, problems, utr

OWN = ("27ABBCS4285J1ZZ",)

BILL = """JAY MATADI ELECTRICALS
GSTIN: 27AAPFJ1234K1Z5
Tax Invoice
Invoice No: JME/266 Date: 14/11/2026
Buyer: SK Ind Tech Solutions Pvt Ltd GSTIN 27ABBCS4285J1ZZ
Cable 4 sq mm 100 m 4,600.00
Taxable Value 4,600.00
CGST @ 9% 414.00
SGST @ 9% 414.00
Grand Total 5,428.00
"""


def test_bill_facts():
	p = parse(BILL, OWN)
	assert p["gstin"] == "27AAPFJ1234K1Z5"  # never our own GSTIN
	assert (p["bill_no"], p["bill_date"]) == ("JME/266", "2026-11-14")
	assert (p["taxable"], p["cgst"], p["sgst"], p["igst"], p["total"]) == (4600.0, 414.0, 414.0, 0.0, 5428.0)


def test_taxable_worked_out_when_missing():
	p = parse("GSTIN 24AAACG1234A1Z9\nBill No 77\nIGST 18% 1,800.00\nTotal Amount 11,800.00", OWN)
	assert (p["igst"], p["total"], p["taxable"]) == (1800.0, 11800.0, 10000.0)


def test_payment_slip():
	p = parse("NEFT Transaction successful\nUTR No: SBINR52026112112345\nAmount Rs 2,36,000.00\nDate 21-Nov-2026", OWN)
	assert (p["utr"], p["amount"], p["bill_date"]) == ("SBINR52026112112345", 236000.0, "2026-11-21")
	assert utr("IMPS ref 632514789012 done") == "632514789012"


def test_ocr_zero_letter_in_gstin_and_dates():
	assert gstins("GSTIN O7AAPFJ1234K1Z5", OWN) == ["07AAPFJ1234K1Z5"]
	assert iso_date("dt 5.1.26") == "2026-01-05" and iso_date("21 Nov 2026") == "2026-11-21" and iso_date("99/99/2026") is None


def test_what_is_missing():
	assert problems("supplier_bill", {"supplier": "X", "bill_no": "1"}) == ["Bill without PO: pick the expense head", "Give the taxable value"]
	assert problems("supplier_bill", {"supplier": "X", "bill_no": "1", "purchase_order": "PO-1"}) == []
	assert problems("money_in", {"customer": "C", "amount": 0}) == ["Give the amount"]
	assert problems("sales_invoice", {"customer": "C"}) == ["Pick the Sales Order or Delivery Note"]
	assert problems("nonsense", {}) == ["Pick what the photo is"]
