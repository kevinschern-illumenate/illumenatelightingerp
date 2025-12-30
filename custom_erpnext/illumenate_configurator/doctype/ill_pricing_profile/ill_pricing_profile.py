# Copyright (c) 2024, ilLumenate Lighting and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class ILLPricingProfile(Document):
	def validate(self):
		self.validate_monetary_fields()
		self.validate_uniqueness()

	def validate_monetary_fields(self):
		"""Validate that all monetary fields are >= 0."""
		monetary_fields = [
			"base_fee",
			"profile_rate_per_m",
			"lens_rate_per_m",
			"tape_rate_per_m",
			"labor_fee",
			"labor_rate_per_m",
		]
		for field in monetary_fields:
			value = getattr(self, field, None)
			if value is not None and value < 0:
				frappe.throw(_("{0} must be greater than or equal to 0").format(self.meta.get_label(field)))

		if self.driver_markup_percent is not None and self.driver_markup_percent < 0:
			frappe.throw(_("Driver Markup % must be greater than or equal to 0"))

	def validate_uniqueness(self):
		"""Ensure only one active pricing profile per fixture template."""
		if self.is_active:
			existing = frappe.db.exists(
				"ILL Pricing Profile",
				{
					"fixture_template": self.fixture_template,
					"is_active": 1,
					"name": ("!=", self.name),
				},
			)
			if existing:
				frappe.throw(
					_(
						"Only one active pricing profile per Fixture Template is allowed. Existing active profile: {0}"
					).format(existing)
				)
