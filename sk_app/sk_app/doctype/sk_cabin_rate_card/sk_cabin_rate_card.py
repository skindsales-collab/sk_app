import json

import frappe
from frappe.model.document import Document


class SKCabinRateCard(Document):
	def validate(self):
		try:
			rc = json.loads(self.rate_card or "{}")
		except ValueError as e:
			frappe.throw(f"Rate card is not valid JSON: {e}")
		for key in ("types", "options", "transport", "terms"):
			if key not in rc:
				frappe.throw(f"Rate card needs '{key}'")
		rc["version"] = self.version
		self.rate_card = json.dumps(rc, indent=1, ensure_ascii=False)
