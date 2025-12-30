# Copyright (c) 2024, ilLumenate Lighting and contributors
# For license information, please see license.txt

import json

from frappe.model.document import Document


class ILLFixtureScheduleLine(Document):
	def validate(self):
		"""Validate the schedule line."""
		if self.line_type == "ilLumenate":
			self.validate_illumenate_line()
		else:
			self.validate_other_manufacturer_line()

	def validate_illumenate_line(self):
		"""Validate ilLumenate line configuration."""
		# If configuration_valid is set, ensure we have required computed fields
		if self.configuration_valid:
			if not self.configuration_json:
				self.configuration_valid = 0
			elif self.manufacturable_length_in is None or self.manufacturable_length_mm is None:
				self.configuration_valid = 0

		# Generate configuration summary if missing but we have config
		if self.configuration_json and not self.configuration_summary:
			self.generate_summary_from_json()

	def validate_other_manufacturer_line(self):
		"""Validate Other Manufacturer line."""
		# Clear ilLumenate-specific fields
		self.fixture_template = None
		self.configuration_json = None
		self.configuration_valid = 0
		self.unit_msrp = None
		self.unit_net = None
		self.tier_name = None
		self.discount_percent = None
		self.line_total = None

	def generate_summary_from_json(self):
		"""Generate a summary string from the stored configuration JSON."""
		try:
			config = json.loads(self.configuration_json)
			parts = []

			if self.fixture_template:
				parts.append(self.fixture_template)

			length_info = config.get("length", {}).get("manufacturable", {})
			if length_info.get("in_display_1_16"):
				parts.append(length_info.get("in_display_1_16") + '"')

			inputs = config.get("inputs", {})
			if inputs.get("cct_token"):
				parts.append(inputs.get("cct_token"))
			if inputs.get("cri_value"):
				parts.append(str(inputs.get("cri_value")) + " CRI")
			if inputs.get("output_token"):
				parts.append(str(inputs.get("output_token")) + "lm")
			if inputs.get("finish_token"):
				parts.append(inputs.get("finish_token"))
			if inputs.get("lens_option"):
				parts.append(inputs.get("lens_option"))
			if inputs.get("mounting_method"):
				parts.append(inputs.get("mounting_method"))

			self.configuration_summary = " | ".join(parts) if parts else ""
		except (json.JSONDecodeError, TypeError):
			pass

	def get_spec_data_dict(self):
		"""Get specification data as a dictionary (for Other Manufacturer lines)."""
		if self.line_type != "Other Manufacturer":
			return {}

		result = {}
		for row in self.spec_data or []:
			result[row.spec_name] = row.spec_value
		return result

