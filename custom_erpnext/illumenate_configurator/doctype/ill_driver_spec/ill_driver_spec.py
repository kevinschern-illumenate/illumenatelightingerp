# Copyright (c) 2024, ilLumenate Lighting and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class ILLDriverSpec(Document):
	def validate(self):
		self.validate_driver_item()
		self.validate_variant_specs()
		self.validate_uniqueness()
		self.set_help_html()

	def validate_driver_item(self):
		"""Validate that the driver item is active and preferably a template."""
		if self.driver_item:
			item = frappe.get_doc("Item", self.driver_item)
			if item.disabled:
				frappe.throw(_("The selected Driver Item is disabled. Please select an active item."))

	def validate_variant_specs(self):
		"""Validate each variant spec row."""
		if not self.variant_specs:
			return

		seen_combinations = set()
		for row in self.variant_specs:
			# Validate max wattage
			if row.max_wattage is not None and row.max_wattage <= 0:
				frappe.throw(_("Row {0}: Max Wattage must be greater than 0").format(row.idx))

			# Validate outputs count
			if row.outputs_count is not None and row.outputs_count < 1:
				frappe.throw(_("Row {0}: Number of Outputs must be at least 1").format(row.idx))

			# Validate unique attribute combinations within this spec
			combination = row.attribute_combination.strip() if row.attribute_combination else ""
			if combination in seen_combinations:
				frappe.throw(
					_("Row {0}: Duplicate attribute combination '{1}'. Each combination must be unique.").format(
						row.idx, combination
					)
				)
			seen_combinations.add(combination)

	def validate_uniqueness(self):
		"""Ensure only one active driver spec per driver item template."""
		if self.is_active:
			existing = frappe.db.exists(
				"ILL Driver Spec",
				{
					"driver_item": self.driver_item,
					"is_active": 1,
					"name": ("!=", self.name),
				},
			)
			if existing:
				frappe.throw(
					_("Only one active driver spec per Driver Item Template is allowed. Existing active spec: {0}").format(
						existing
					)
				)

	def set_help_html(self):
		"""Set the help HTML field with usage instructions."""
		self.help_html = """
		<div class="alert alert-info">
			<h5>How to Configure Variant Specifications</h5>
			<p>Each row in the <strong>Variant Specs</strong> table defines the electrical specifications for a specific attribute combination.</p>
			<ol>
				<li><strong>Attribute Combination:</strong> Enter the combination of variant attributes as a comma-separated string (e.g., "Input Voltage: 120V, Dimming: 0-10V")</li>
				<li><strong>Output Voltage:</strong> Select the DC output voltage for this combination</li>
				<li><strong>Dimming Protocol:</strong> Select the dimming protocol for this combination</li>
				<li><strong>Max Wattage:</strong> Enter the maximum power capacity for this combination</li>
				<li><strong>Number of Outputs:</strong> Enter the number of output channels for this combination</li>
			</ol>
			<p><strong>Note:</strong> The Attribute Combination string will be matched against the fixture configuration during BOM generation.</p>
		</div>
		"""

	def get_spec_for_attributes(self, attribute_combination: str) -> dict:
		"""
		Get the specification for a given attribute combination.

		Args:
			attribute_combination: A string like "Input Voltage: 120V, Dimming: 0-10V"

		Returns:
			Dict with voltage_out, dimming_protocol, max_wattage, outputs_count, usable_wattage or None if not found
		"""
		if not self.variant_specs:
			return None

		# Normalize the input combination
		normalized_input = self._normalize_combination(attribute_combination)

		for row in self.variant_specs:
			normalized_row = self._normalize_combination(row.attribute_combination)
			if normalized_row == normalized_input:
				return {
					"voltage_out": row.voltage_out,
					"dimming_protocol": row.dimming_protocol,
					"max_wattage": row.max_wattage,
					"outputs_count": row.outputs_count,
					"usable_wattage": row.max_wattage * 0.8 if row.max_wattage else 0,
				}

		return None

	def _normalize_combination(self, combination: str) -> str:
		"""Normalize an attribute combination string for comparison."""
		if not combination:
			return ""
		# Split by comma, strip whitespace, sort, and rejoin
		parts = [p.strip().lower() for p in combination.split(",")]
		return ", ".join(sorted(parts))

	def get_all_attribute_combinations(self) -> list:
		"""Get a list of all defined attribute combinations."""
		if not self.variant_specs:
			return []
		return [row.attribute_combination for row in self.variant_specs]

	def get_usable_wattage_for_attributes(self, attribute_combination: str) -> float:
		"""Get the usable wattage (80% derating) for a given attribute combination."""
		spec = self.get_spec_for_attributes(attribute_combination)
		if spec:
			return spec.get("usable_wattage", 0)
		return 0
