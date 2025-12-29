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
		self.validate_variant_attributes()
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

	def validate_variant_attributes(self):
		"""Validate that variant attributes are specified if tape_item is a template."""
		if not self.tape_item:
			return

		item = frappe.get_doc("Item", self.tape_item)

		if item.has_variants and self.variant_attributes:
			# Validate that specified attributes match the template's attributes
			template_attrs = {attr.attribute for attr in item.attributes}
			for row in self.variant_attributes:
				if row.attribute not in template_attrs:
					frappe.throw(
						_("Attribute '{0}' is not defined for Item Template '{1}'").format(
							row.attribute, self.tape_item
						)
					)

			# Validate attribute values
			for row in self.variant_attributes:
				attr_doc = frappe.get_doc("Item Attribute", row.attribute)
				if attr_doc.numeric_values:
					try:
						val = float(row.attribute_value)
						if val < attr_doc.from_range or val > attr_doc.to_range:
							frappe.throw(
								_("Value '{0}' for attribute '{1}' must be between {2} and {3}").format(
									row.attribute_value, row.attribute, attr_doc.from_range, attr_doc.to_range
								)
							)
					except ValueError:
						frappe.throw(
							_("Value '{0}' for attribute '{1}' must be a number").format(
								row.attribute_value, row.attribute
							)
						)
				else:
					valid_values = [v.attribute_value for v in attr_doc.item_attribute_values]
					if row.attribute_value not in valid_values:
						frappe.throw(
							_("Value '{0}' is not valid for attribute '{1}'. Valid values: {2}").format(
								row.attribute_value, row.attribute, ", ".join(valid_values)
							)
						)

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

	def get_resolved_item(self, create_if_missing=False):
		"""
		Get the resolved Item for BOM generation.

		If tape_item is a template and variant_attributes are specified,
		resolves to the matching variant. Otherwise returns tape_item.

		Args:
			create_if_missing: If True, creates the variant if it doesn't exist

		Returns:
			Item name (variant or original tape_item)
		"""
		if not self.tape_item:
			return None

		item = frappe.get_doc("Item", self.tape_item)

		# If not a template, return as-is
		if not item.has_variants:
			return self.tape_item

		# If template but no attributes specified, return template (will error at BOM creation)
		if not self.variant_attributes:
			return self.tape_item

		# Resolve variant
		from custom_erpnext.illumenate_configurator.api import (
			get_or_create_variant,
			resolve_variant_item,
		)

		variant_attrs = [
			{"attribute": row.attribute, "attribute_value": row.attribute_value}
			for row in self.variant_attributes
		]

		if create_if_missing:
			return get_or_create_variant(self.tape_item, variant_attrs)
		else:
			return resolve_variant_item(self.tape_item, variant_attrs)
