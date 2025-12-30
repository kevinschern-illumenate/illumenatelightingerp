# Copyright (c) 2024, ilLumenate Lighting and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ILLProject(Document):
	def validate(self):
		"""Validate project document."""
		self.validate_dates()

	def validate_dates(self):
		"""Validate start and end dates."""
		if self.expected_start_date and self.expected_end_date:
			if self.expected_start_date > self.expected_end_date:
				frappe.throw("Expected End Date cannot be before Expected Start Date")
