# Copyright (c) 2024, ilLumenate Lighting and contributors
# For license information, please see license.txt

"""
ILL PDF Template DocType.

Manages PDF templates for fixture submittals, schedule covers, and other documents.
"""

import frappe
from frappe import _
from frappe.model.document import Document


class ILLPDFTemplate(Document):
	def validate(self):
		self.validate_pdf_extension()
		self.validate_fixture_template_for_submittal()
		self.validate_single_active_template()

	def validate_pdf_extension(self):
		"""Ensure the attached file has a .pdf extension."""
		if self.pdf_file:
			if not self.pdf_file.lower().endswith(".pdf"):
				frappe.throw(_("PDF File must have a .pdf extension"))

	def validate_fixture_template_for_submittal(self):
		"""Ensure fixture template is set for Fixture Submittal type."""
		if self.template_type == "Fixture Submittal" and not self.applies_to_fixture_template:
			frappe.throw(
				_("Fixture Template is required for Fixture Submittal type templates")
			)

	def validate_single_active_template(self):
		"""Enforce single active template per type/fixture combo."""
		if not self.is_active:
			return

		filters = {
			"template_type": self.template_type,
			"is_active": 1,
			"name": ("!=", self.name),
		}

		if self.template_type == "Fixture Submittal":
			filters["applies_to_fixture_template"] = self.applies_to_fixture_template

		existing = frappe.db.exists("ILL PDF Template", filters)
		if existing:
			if self.template_type == "Fixture Submittal":
				frappe.throw(
					_(
						"An active template already exists for fixture template '{0}'. "
						"Please deactivate it first."
					).format(self.applies_to_fixture_template)
				)
			else:
				frappe.throw(
					_(
						"An active template already exists for type '{0}'. "
						"Please deactivate it first."
					).format(self.template_type)
				)
