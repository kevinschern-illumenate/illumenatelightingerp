# Copyright (c) 2024, ilLumenate Lighting and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class ILLLEDTapeSpec(Document):
	def validate(self):
		self.validate_tape_item()
		self.validate_variant_specs()
		self.validate_uniqueness()
		self.compute_cut_increment_mm_for_variants()
		self.set_help_html()

	def validate_tape_item(self):
		"""Validate that the tape item is active and preferably a template."""
		if self.tape_item:
			item = frappe.get_doc("Item", self.tape_item)
			if item.disabled:
				frappe.throw(_("The selected Tape Item is disabled. Please select an active item."))

	def validate_variant_specs(self):
		"""Validate each variant spec row."""
		if not self.variant_specs:
			return

		seen_combinations = set()
		for row in self.variant_specs:
			# Validate watts per foot
			if row.watts_per_ft is not None and row.watts_per_ft <= 0:
				frappe.throw(_("Row {0}: Watts per Foot must be greater than 0").format(row.idx))

			# Validate cut increment
			if row.cut_increment_in is not None and row.cut_increment_in <= 0:
				frappe.throw(_("Row {0}: Cut Increment (inches) must be greater than 0").format(row.idx))

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
		"""Ensure only one active tape spec per tape item template."""
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
					_("Only one active tape spec per Tape Item Template is allowed. Existing active spec: {0}").format(
						existing
					)
				)

	def compute_cut_increment_mm_for_variants(self):
		"""Compute mm values for each variant's cut increment."""
		if self.variant_specs:
			for row in self.variant_specs:
				if row.cut_increment_in:
					row.cut_increment_mm = row.cut_increment_in * 25.4
				else:
					row.cut_increment_mm = 0

	def set_help_html(self):
		"""Set the help HTML field with usage instructions."""
		self.help_html = """
		<div class="alert alert-info">
			<h5>How to Configure Variant Specifications</h5>
			<p>Each row in the <strong>Variant Specs</strong> table defines the electrical specifications for a specific attribute combination.</p>
			<ol>
				<li><strong>Attribute Combination:</strong> Enter the combination of variant attributes as a comma-separated string (e.g., "Color Temperature: 2700K, CRI: 90")</li>
				<li><strong>Voltage:</strong> Select the operating voltage for this combination</li>
				<li><strong>Watts per Foot:</strong> Enter the power consumption per foot for this combination</li>
				<li><strong>Cut Increment:</strong> Enter the minimum cut length in inches for this combination</li>
			</ol>
			<p><strong>Note:</strong> The Attribute Combination string will be matched against the fixture configuration during BOM generation.</p>
		</div>
		"""

	def get_spec_for_attributes(self, attribute_combination: str) -> dict:
		"""
		Get the specification for a given attribute combination.

		Args:
			attribute_combination: A string like "Color Temperature: 2700K, CRI: 90"

		Returns:
			Dict with voltage, watts_per_ft, cut_increment_in, cut_increment_mm, voltage_drop_max_run_ft or None if not found
		"""
		if not self.variant_specs:
			return None

		# Normalize the input combination
		normalized_input = self._normalize_combination(attribute_combination)

		for row in self.variant_specs:
			normalized_row = self._normalize_combination(row.attribute_combination)
			if normalized_row == normalized_input:
				return {
					"voltage": row.voltage,
					"watts_per_ft": row.watts_per_ft,
					"cut_increment_in": row.cut_increment_in,
					"cut_increment_mm": row.cut_increment_mm,
					"voltage_drop_max_run_ft": row.voltage_drop_max_run_ft,
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
