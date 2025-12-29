# Copyright (c) 2024, ilLumenate Lighting and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class ILLLEDTapeSpec(Document):
	def validate(self):
		self.validate_watts_per_ft()
		self.validate_cut_increment()
		self.validate_tape_item()
		self.validate_uniqueness()
		self.compute_cut_increment_mm()

	def validate_watts_per_ft(self):
		if self.watts_per_ft is not None and self.watts_per_ft <= 0:
			frappe.throw(_("Watts per Foot must be greater than 0"))

	def validate_cut_increment(self):
		if self.cut_increment_in is not None and self.cut_increment_in <= 0:
			frappe.throw(_("Cut Increment (inches) must be greater than 0"))

	def validate_tape_item(self):
		if self.tape_item:
			item = frappe.get_doc("Item", self.tape_item)
			if item.disabled:
				frappe.throw(_("The selected Tape Item is disabled. Please select an active item."))

	def validate_uniqueness(self):
		if self.is_active:
			existing = frappe.db.exists(
				"ILL LED Tape Spec",
				{
					"tape_item": self.tape_item,
					"is_active": 1,
					"name": ("!=", self.name),
				},
			)
			if existing:
				frappe.throw(
					_("Only one active tape spec per tape Item is allowed. Existing active spec: {0}").format(
						existing
					)
				)

	def compute_cut_increment_mm(self):
		if self.cut_increment_in:
			self.cut_increment_mm = self.cut_increment_in * 25.4
		else:
			self.cut_increment_mm = 0
