# Copyright (c) 2024, ilLumenate Lighting and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class ILLOptionPriceAdder(Document):
	def validate(self):
		self.validate_amount()
		self.validate_uniqueness()

	def validate_amount(self):
		"""Validate that amount is >= 0."""
		if self.amount is not None and self.amount < 0:
			frappe.throw(_("Amount must be greater than or equal to 0"))

	def validate_uniqueness(self):
		"""Ensure unique active record per (template, type, key, mode)."""
		if self.is_active:
			existing = frappe.db.exists(
				"ILL Option Price Adder",
				{
					"fixture_template": self.fixture_template,
					"adder_type": self.adder_type,
					"adder_key": self.adder_key,
					"adder_mode": self.adder_mode,
					"is_active": 1,
					"name": ("!=", self.name),
				},
			)
			if existing:
				frappe.throw(
					_(
						"Only one active adder per (Template, Type, Key, Mode) is allowed. Existing: {0}"
					).format(existing)
				)
