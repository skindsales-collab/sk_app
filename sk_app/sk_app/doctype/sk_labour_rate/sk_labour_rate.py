# Copyright (c) 2026, SK Ind Tech Solutions Pvt Ltd

from frappe.model.document import Document
from frappe.utils import flt


def _ft(x) -> str:
	x = flt(x)
	return str(int(x)) if x == int(x) else str(x)


class SKLabourRate(Document):
	def validate(self):
		from sk_app.sub_bills import check_rate_edit

		check_rate_edit(self)
		self.cabin_size = " x ".join(_ft(v) for v in (self.length, self.width, self.height or 8.6))
