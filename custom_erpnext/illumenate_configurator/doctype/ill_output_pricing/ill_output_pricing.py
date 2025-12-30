# Copyright (c) 2024, ilLumenate Lighting and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class ILLOutputPricing(Document):
	def validate(self):
		self.validate_override_or_adder()
		self.validate_uniqueness()

	def validate_override_or_adder(self):
		"""Validate that at least one of override or adder is set."""
		if not self.tape_rate_per_m_override and not self.tape_adder_per_m:
			frappe.throw(_("At least one of Tape Rate Override or Tape Adder must be set"))

	def validate_uniqueness(self):
		"""Ensure unique active record per (template, output_token)."""
		if self.is_active:
			existing = frappe.db.exists(
				"ILL Output Pricing",
				{
					"fixture_template": self.fixture_template,
					"output_token": self.output_token,
					"is_active": 1,
					"name": ("!=", self.name),
				},
			)
			if existing:
				frappe.throw(
					_(
						"Only one active output pricing per (Template, Output Token) is allowed. Existing: {0}"
					).format(existing)
				)
