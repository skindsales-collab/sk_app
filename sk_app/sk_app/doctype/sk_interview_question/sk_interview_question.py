import frappe
from frappe.model.document import Document


class SKInterviewQuestion(Document):
	def validate(self):
		from sk_app.hiring_rules import forbidden_words

		bad = forbidden_words(" ".join(x for x in (self.en, self.mr, self.hi) if x))
		if bad:
			frappe.throw(frappe._("A question may not touch {0} (SK hiring rule)").format(", ".join(bad)))
