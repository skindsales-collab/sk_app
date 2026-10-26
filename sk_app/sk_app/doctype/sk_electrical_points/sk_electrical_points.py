# Copyright (c) 2026, SK Ind Tech Solutions Pvt Ltd

from frappe.model.document import Document
from frappe.utils import cint

POINTS = ("light", "fan", "socket_5a", "socket_15a", "ac_point", "mcb_db", "earthing", "other_points")


class SKElectricalPoints(Document):
	def validate(self):
		self.total_points = sum(cint(self.get(f)) for f in POINTS)
