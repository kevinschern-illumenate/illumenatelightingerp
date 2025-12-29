# Copyright (c) 2024, ilLumenate Lighting and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class ILLDriverSpec(Document):
	def validate(self):
		self.validate_max_wattage()
		self.validate_outputs_count()
		self.validate_variant_attributes()
		self.validate_uniqueness()

	def validate_max_wattage(self):
		if self.max_wattage is not None and self.max_wattage <= 0:
			frappe.throw(_("Max Wattage must be greater than 0"))

	def validate_outputs_count(self):
		if self.outputs_count is not None and self.outputs_count < 1:
			frappe.throw(_("Number of Outputs must be at least 1"))

	def validate_variant_attributes(self):
		"""Validate that variant attributes are specified if driver_item is a template."""
		if not self.driver_item:
			return

		item = frappe.get_doc("Item", self.driver_item)

		if item.has_variants and self.variant_attributes:
			# Validate that specified attributes match the template's attributes
			template_attrs = {attr.attribute for attr in item.attributes}
			for row in self.variant_attributes:
				if row.attribute not in template_attrs:
					frappe.throw(
						_("Attribute '{0}' is not defined for Item Template '{1}'").format(
							row.attribute, self.driver_item
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

	def get_resolved_item(self, create_if_missing=False):
		"""
		Get the resolved Item for BOM generation.

		If driver_item is a template and variant_attributes are specified,
		resolves to the matching variant. Otherwise returns driver_item.

		Args:
			create_if_missing: If True, creates the variant if it doesn't exist

		Returns:
			Item name (variant or original driver_item)
		"""
		if not self.driver_item:
			return None

		item = frappe.get_doc("Item", self.driver_item)

		# If not a template, return as-is
		if not item.has_variants:
			return self.driver_item

		# If template but no attributes specified, return template (will error at BOM creation)
		if not self.variant_attributes:
			return self.driver_item

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
			return get_or_create_variant(self.driver_item, variant_attrs)
		else:
			return resolve_variant_item(self.driver_item, variant_attrs)
