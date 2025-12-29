# Copyright (c) 2024, ilLumenate Lighting and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class ILLDriverSpec(Document):
	def validate(self):
		self.validate_max_wattage()
		self.validate_outputs_count()
		self.validate_uniqueness()

	def validate_max_wattage(self):
		if self.max_wattage is not None and self.max_wattage <= 0:
			frappe.throw(_("Max Wattage must be greater than 0"))

	def validate_outputs_count(self):
		if self.outputs_count is not None and self.outputs_count < 1:
			frappe.throw(_("Number of Outputs must be at least 1"))

	def validate_uniqueness(self):
		if self.is_active:
			existing = frappe.db.exists(
				"ILL Driver Spec",
				{
					"driver_item": self.driver_item,
					"voltage_out": self.voltage_out,
					"dimming_protocol": self.dimming_protocol,
					"is_active": 1,
					"name": ("!=", self.name),
				},
			)
			if existing:
				frappe.throw(
					_(
						"Only one active driver spec per combination of (driver_item, voltage_out, dimming_protocol) is allowed. Existing active spec: {0}"
					).format(existing)
				)

	@property
	def usable_wattage(self):
		"""Derived property: max_wattage * 0.8 (80% derating)"""
		if self.max_wattage:
			return self.max_wattage * 0.8
		return 0
