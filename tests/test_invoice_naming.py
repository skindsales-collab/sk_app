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
