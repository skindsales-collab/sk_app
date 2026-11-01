"""SK 1-Nov minimum input → quote: the app fills the boxes the quote / design AIs read (sk_app.quote_pickup)."""

from unittest import TestCase
from unittest.mock import patch

from sk_app import quote_pickup as qp


class _Field:
	def __init__(self, options):
		self.options = options


class _Meta:
	FIELDS = {"custom_segment": "Cabin\nMachine Shifting\nJob Work", "ms_quote_status": "", "custom_design_status": "",
		"sk_segment": "", "ms_quote_no": "", "lead": ""}

	def has_field(self, f):
		return f in self.FIELDS

	def get_field(self, f):
		return _Field(self.FIELDS[f])


class _Deal(dict):
	"""Enough of a CRM Deal for the hook."""
	meta = _Meta()
	name = "CRM-DEAL-TEST"
	creation = None

	def __getattr__(self, k):
		return self.get(k)

	def __setattr__(self, k, v):
		self[k] = v

	def is_new(self):
		return True


def _run(deal, closed=False, quoted=False, has_input=True):
	with patch.object(qp, "_closed", return_value=closed), patch.object(qp, "_has_quotation", return_value=quoted), \
			patch.object(qp, "_has_input", return_value=has_input), patch.object(qp.frappe, "flags", type("F", (), {"sk_quote_in_hand": False})()):
		qp.on_deal_validate(deal)
	return deal


class TestQuotePickup(TestCase):
	def test_size_and_type_from_free_text(self):
		self.assertEqual(qp.guess_size("need security cabin 10x8 at Chakan"), (10.0, 8.0))
		self.assertEqual(qp.guess_size("cabin 8 ft x 20 ft"), (20.0, 8.0))
		self.assertEqual(qp.guess_size("20' by 10'"), (20.0, 10.0))
		self.assertIsNone(qp.guess_size("office cabin with AC"))
		self.assertEqual(qp.guess_type("Security Cabin"), "security")
		self.assertEqual(qp.guess_type("FRP security cabin"), "frp_security")
		self.assertEqual(qp.guess_type("site office"), "office")
		self.assertTrue(qp.needs_design("ACP premium office 20x10"))
		self.assertFalse(qp.needs_design("GI office 20x10"))

	def test_aditya_deal_goes_for_quote(self):
		d = _run(_Deal(sk_segment="Machine Shifting", custom_segment="Cabin", ms_quote_status="Not Requested"))
		self.assertEqual(d.custom_segment, "Machine Shifting")
		self.assertEqual(d.ms_quote_status, "Sent to Quote")
		d = _run(_Deal(sk_segment="Maintenance", custom_segment="Cabin", ms_quote_status="Not Requested"))
		self.assertEqual(d.custom_segment, "Machine Shifting")

	def test_no_second_quote(self):
		d = _run(_Deal(sk_segment="Job Work", ms_quote_status="Not Requested"), quoted=True)
		self.assertEqual(d.custom_segment, "Job Work")
		self.assertEqual(d.ms_quote_status, "Not Requested")
		d = _run(_Deal(sk_segment="Machine Shifting", ms_quote_status="Info Required"))
		self.assertEqual(d.ms_quote_status, "Info Required")
		d = _run(_Deal(sk_segment="Machine Shifting", ms_quote_status="Not Requested"), closed=True)
		self.assertEqual(d.ms_quote_status, "Not Requested")

	def test_cabin_deal_goes_to_design(self):
		d = _run(_Deal(sk_segment="Standard Cabin (GI / ACP)", custom_design_status="Not Required"))
		self.assertEqual(d.custom_segment, "Cabin")
		self.assertEqual(d.custom_design_status, "Sent to Design")
		d = _run(_Deal(sk_segment="LGSF", custom_design_status="Not Required"), has_input=False)
		self.assertEqual(d.custom_design_status, "Not Required")
		# Rushi 30-Oct: the stage "Sent to Design" picked by hand now really sends it
		d = _run(_Deal(sk_segment="Standard Cabin (GI / ACP)", status="Sent to Design", custom_design_status="Not Required"), has_input=False)
		self.assertEqual(d.custom_design_status, "Sent to Design")
		d = _run(_Deal(sk_segment="Standard Cabin (GI / ACP)", custom_design_status="Drawing Sent"))
		self.assertEqual(d.custom_design_status, "Drawing Sent")
