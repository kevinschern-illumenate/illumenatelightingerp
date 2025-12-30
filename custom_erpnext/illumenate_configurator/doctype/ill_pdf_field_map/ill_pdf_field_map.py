# Copyright (c) 2024, ilLumenate Lighting and contributors
# For license information, please see license.txt

"""
ILL PDF Field Map DocType.

Maps PDF AcroForm field names to data keys for automatic filling.
"""

import frappe
from frappe import _
from frappe.model.document import Document


class ILLPDFFieldMap(Document):
	def validate(self):
		self.validate_unique_active_mapping()

	def validate_unique_active_mapping(self):
		"""Ensure unique active mapping per (pdf_template, pdf_field_name)."""
		if not self.is_active:
			return

		existing = frappe.db.exists(
			"ILL PDF Field Map",
			{
				"pdf_template": self.pdf_template,
				"pdf_field_name": self.pdf_field_name,
				"is_active": 1,
				"name": ("!=", self.name),
			},
		)
		if existing:
			frappe.throw(
				_(
					"An active mapping already exists for field '{0}' in template '{1}'"
				).format(self.pdf_field_name, self.pdf_template)
			)
