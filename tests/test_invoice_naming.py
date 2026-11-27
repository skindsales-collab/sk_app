# SK 21-Nov: SK/IND/MMYY/### with one running number across months
import sys, types

sys.modules.setdefault("frappe", types.ModuleType("frappe"))
fu = types.ModuleType("frappe.utils")
import datetime
fu.cint = lambda v: int(v or 0)
fu.getdate = lambda v: v if isinstance(v, datetime.date) else datetime.date.fromisoformat(str(v))
sys.modules.setdefault("frappe.utils", fu)
from sk_app.invoice_naming import name_for, number_of  # noqa: E402


def test_name_for():
	assert name_for("2026-11-21", 849) == "SK/IND/1126/849"
	assert name_for("2026-12-01", 850) == "SK/IND/1226/850"  # new month, number runs on
	assert name_for("2027-01-05", 7) == "SK/IND/0127/007"
	assert len(name_for("2026-11-21", 1234)) <= 16  # GST invoice number limit


def test_number_of():
	assert number_of("SK/IND/1126/008") == 8
	assert number_of("SK/IND/1126/849") == 849
	assert number_of("SINV-26-00159") == 0
	assert number_of(None) == 0


def test_amendment_keeps_the_number_with_a_letter():
	from sk_app.invoice_naming import amended_name

	taken = {"SK/IND/1126/850A"}.__contains__
	assert amended_name("SK/IND/1126/850", lambda n: False) == "SK/IND/1126/850A"
	assert amended_name("SK/IND/1126/850A", taken) == "SK/IND/1126/850B"
	assert len("SK/IND/1126/850A") == 16  # GST limit
	assert amended_name("SINV-26-00151", lambda n: False) is None
	assert number_of("SK/IND/1126/850A") == 850


def test_cancelled_copy_name():
	from sk_app.invoice_naming import cxl_name

	assert cxl_name("SK/IND/1126/850", lambda n: False) == "SK/IND/1126/850-CXL"
	assert cxl_name("SK/IND/1126/850", {"SK/IND/1126/850-CXL"}.__contains__) == "SK/IND/1126/850-CXL2"
