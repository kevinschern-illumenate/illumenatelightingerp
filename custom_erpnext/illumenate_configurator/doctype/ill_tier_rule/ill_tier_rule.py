# Copyright (c) 2024, ilLumenate Lighting and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class ILLTierRule(Document):
	def validate(self):
		self.validate_discount()

	def validate_discount(self):
		"""Validate that discount percentage is within valid range."""
		if self.discount_percent_off_msrp is not None:
			if self.discount_percent_off_msrp < 0 or self.discount_percent_off_msrp > 100:
				frappe.throw(_("Discount percentage must be between 0 and 100"))
