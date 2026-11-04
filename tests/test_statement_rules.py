"""SK 4-Nov-2026: reading an SBI statement (made-up sample lines in SBI's layout; no real statement in this public repo)."""

import pytest

from sk_app.statement_rules import StatementError, parse_text, pick_match

SAMPLE = """Opening Balance as on 1 Oct 2026 :1,00,000.00
Txn Date     Value Date Description                  Ref No./Cheque    Branch   Debit         Credit      Balance
  16/10/2026 16/10/2026     TO TRANSFER-              TRANSFER TO     16209       15,600.00                   84,400.00
                          IMPS/628900000001/UTIB-     4698294162096 /
                          xx644-/Neo curt-
  17/10/2026 17/10/2026    BY TRANSFER-RTGS UTR       TRANSFER FROM   4430                    50,000.00   1,34,400.00
                          NO: ICICR22026101700000001 4698335044308 / -ORLLP
  20/10/2026 20/10/2026     TO TRANSFER--             TRANSFER TO     16209        4,400.00                1,30,000.00
                          4698290162099 /
**This is a computer generated statement and does not require a signature.
"""


def test_reads_lines_sides_and_utr():
	st = parse_text(SAMPLE)
	assert (st["opening"], st["closing"], len(st["rows"])) == (100000.0, 130000.0, 3)
	a, b, c = st["rows"]
	assert (a["date"], a["withdrawal"], a["deposit"], a["reference_number"], a["party_hint"]) == ("2026-10-16", 15600.0, 0.0, "IMPS628900000001", "Neo curt")
	assert (b["withdrawal"], b["deposit"], b["reference_number"]) == (0.0, 50000.0, "ICICR22026101700000001")
	assert c["reference_number"] is None


def test_a_misread_amount_stops():
	with pytest.raises(StatementError):
		parse_text(SAMPLE.replace("84,400.00", "84,000.00"))
	with pytest.raises(StatementError):
		parse_text("no statement here")


def test_matching_payment():
	row = {"reference_number": "IMPS628900000001", "party_hint": "Neo curt"}
	neo = {"name": "PE-1", "party": "Neo Curtains", "reference_no": None}
	other = {"name": "PE-2", "party": "Ms. Technomech Solutions", "reference_no": None}
	assert pick_match(row, [neo])[0] is neo
	assert pick_match(row, [other, neo])[0] is neo  # by the name the bank shows
	assert pick_match(row, [other, {**neo, "reference_no": "IMPS 628900000001"}])[0]["name"] == "PE-1"  # by UTR
	assert pick_match({"reference_number": None, "party_hint": ""}, [neo, other])[0] is None  # two of the same amount: ask
	assert pick_match(row, []) == (None, "not in ERPNext")
