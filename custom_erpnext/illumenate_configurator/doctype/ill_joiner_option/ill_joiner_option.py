# Copyright (c) 2024, ilLumenate Lighting and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class ILLJoinerOption(Document):
	def validate(self):
		self._validate_uniqueness()

	def _validate_uniqueness(self):
		"""Ensure uniqueness of fixture_template + mounting_method + joiner_angle combination."""
		existing = frappe.db.get_value(
			"ILL Joiner Option",
			{
				"fixture_template": self.fixture_template,
				"mounting_method": self.mounting_method,
				"joiner_angle": self.joiner_angle,
				"name": ("!=", self.name),
			},
			"name",
		)
		if existing:
			frappe.throw(
				_(
					"A joiner option for this combination of Template, Mounting Method, and Angle already exists: {0}"
				).format(existing)
			)
