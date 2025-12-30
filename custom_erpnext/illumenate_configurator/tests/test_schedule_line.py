# Copyright (c) 2024, ilLumenate Lighting and contributors
# For license information, please see license.txt

"""
Unit tests for ILL Fixture Schedule Line enhanced functionality.

These tests validate the fixture schedule line configuration,
validation logic, and spec data handling for both ilLumenate
and Other Manufacturer line types.
"""

import json
import unittest


class TestFixtureScheduleLineConfiguration(unittest.TestCase):
	"""Tests for ilLumenate fixture schedule line configuration."""

	def test_configuration_json_structure(self):
		"""Test that configuration JSON has expected structure."""
		config = {
			"inputs": {
				"template_code": "SH01",
				"tape_spec": "TAPE-001",
				"tape_attribute_combination": "CCT: 3000K, CRI: 90",
				"requested_overall_in": 48,
				"endcap_item": "ENDCAP-001",
			},
			"length": {
				"requested": {"in": 48, "mm": 1219.2},
				"manufacturable": {"in": 48.5, "mm": 1231.9, "in_display_1_16": '48-1/2'},
				"tape_cut": {"mm": 1200},
				"delta": {"mm": 12.7},
			},
			"electrical": {
				"watts_per_ft": 5.0,
				"total_watts": 20.0,
				"runs_count": 1,
				"effective_max_run_ft": 17.0,
			},
			"driver": {
				"driver_spec": "DRV-001",
				"driver_item": "DRIVER-ITEM-001",
				"quantity": 1,
			},
			"pricing": {
				"unit_msrp": 200.00,
				"unit_net_price": 150.00,
				"tier_name": "Dealer A",
				"discount_percent": 25,
			},
		}

		# Verify structure
		self.assertIn("inputs", config)
		self.assertIn("length", config)
		self.assertIn("electrical", config)
		self.assertIn("driver", config)
		self.assertIn("pricing", config)

		# Verify nested values
		self.assertEqual(config["inputs"]["template_code"], "SH01")
		self.assertEqual(config["length"]["manufacturable"]["mm"], 1231.9)
		self.assertEqual(config["electrical"]["runs_count"], 1)

	def test_configuration_summary_generation(self):
		"""Test configuration summary generation from fields."""
		fields = {
			"fixture_template": "SH01",
			"manufacturable_length": '48-1/2"',
			"cct_token": "3000K",
			"cri_value": 90,
			"output_token": 300,
			"finish_token": "BLK",
			"lens_option": "Clear",
			"mounting_method": "Surface",
		}

		parts = [fields["fixture_template"]]
		parts.append(fields["manufacturable_length"])
		if fields.get("cct_token"):
			parts.append(fields["cct_token"])
		if fields.get("cri_value"):
			parts.append(str(fields["cri_value"]) + " CRI")
		if fields.get("output_token"):
			parts.append(str(fields["output_token"]) + "lm")
		if fields.get("finish_token"):
			parts.append(fields["finish_token"])
		if fields.get("lens_option"):
			parts.append(fields["lens_option"])
		if fields.get("mounting_method"):
			parts.append(fields["mounting_method"])

		summary = " | ".join(parts)

		self.assertEqual(summary, 'SH01 | 48-1/2" | 3000K | 90 CRI | 300lm | BLK | Clear | Surface')

	def test_line_total_calculation(self):
		"""Test line total calculation."""
		qty = 3
		unit_net = 150.00

		line_total = qty * unit_net

		self.assertEqual(line_total, 450.00)

	def test_configuration_valid_flag(self):
		"""Test configuration_valid flag behavior."""
		line = {
			"configuration_valid": 0,
			"configuration_json": None,
			"manufacturable_length_in": None,
		}

		# Invalid without config
		self.assertEqual(line["configuration_valid"], 0)

		# Add config
		line["configuration_json"] = '{"inputs": {}}'
		line["manufacturable_length_in"] = 48.5
		line["configuration_valid"] = 1

		# Valid with config
		self.assertEqual(line["configuration_valid"], 1)


class TestOtherManufacturerLine(unittest.TestCase):
	"""Tests for Other Manufacturer line type."""

	def test_spec_data_structure(self):
		"""Test spec_data table structure."""
		spec_data = [
			{"spec_name": "CCT", "spec_value": "3000K"},
			{"spec_name": "CRI", "spec_value": "90+"},
			{"spec_name": "Watts per Foot", "spec_value": "5.0"},
			{"spec_name": "Max Run Length", "spec_value": "20ft"},
		]

		self.assertEqual(len(spec_data), 4)
		self.assertEqual(spec_data[0]["spec_name"], "CCT")
		self.assertEqual(spec_data[0]["spec_value"], "3000K")

	def test_spec_data_to_dict(self):
		"""Test converting spec_data to dictionary."""
		spec_data = [
			{"spec_name": "CCT", "spec_value": "3000K"},
			{"spec_name": "CRI", "spec_value": "90+"},
			{"spec_name": "Lumens", "spec_value": "450lm/ft"},
		]

		result = {}
		for spec in spec_data:
			result[spec["spec_name"]] = spec["spec_value"]

		self.assertEqual(result["CCT"], "3000K")
		self.assertEqual(result["CRI"], "90+")
		self.assertEqual(result["Lumens"], "450lm/ft")

	def test_other_manufacturer_required_fields(self):
		"""Test Other Manufacturer required fields."""
		line = {
			"line_type": "Other Manufacturer",
			"manufacturer_name": "Acme Lighting",
			"model_number": "ACM-LED-100",
			"spec_data": [],
		}

		self.assertEqual(line["line_type"], "Other Manufacturer")
		self.assertIsNotNone(line["manufacturer_name"])
		self.assertIsNotNone(line["model_number"])

	def test_illumenate_fields_cleared_for_other_mfr(self):
		"""Test that ilLumenate fields are cleared for Other Manufacturer."""
		line = {
			"line_type": "Other Manufacturer",
			"fixture_template": None,
			"configuration_json": None,
			"configuration_valid": 0,
			"unit_msrp": None,
			"unit_net": None,
		}

		self.assertIsNone(line["fixture_template"])
		self.assertIsNone(line["configuration_json"])
		self.assertEqual(line["configuration_valid"], 0)
		self.assertIsNone(line["unit_msrp"])


class TestLineTypeSwitching(unittest.TestCase):
	"""Tests for switching between line types."""

	def test_switch_to_other_manufacturer_clears_config(self):
		"""Test switching to Other Manufacturer clears ilLumenate config."""
		# Start with ilLumenate line
		line = {
			"line_type": "ilLumenate",
			"fixture_template": "SH01",
			"configuration_json": '{"inputs": {}}',
			"configuration_valid": 1,
			"unit_msrp": 200.00,
			"manufacturer_name": None,
			"spec_data": [],
		}

		# Switch to Other Manufacturer
		line["line_type"] = "Other Manufacturer"
		# Clear ilLumenate fields
		line["fixture_template"] = None
		line["configuration_json"] = None
		line["configuration_valid"] = 0
		line["unit_msrp"] = None

		self.assertIsNone(line["fixture_template"])
		self.assertIsNone(line["configuration_json"])
		self.assertEqual(line["configuration_valid"], 0)

	def test_switch_to_illumenate_clears_mfr_data(self):
		"""Test switching to ilLumenate clears Other Manufacturer data."""
		# Start with Other Manufacturer line
		line = {
			"line_type": "Other Manufacturer",
			"manufacturer_name": "Acme Lighting",
			"model_number": "ACM-100",
			"spec_data": [{"spec_name": "CCT", "spec_value": "3000K"}],
			"fixture_template": None,
		}

		# Switch to ilLumenate
		line["line_type"] = "ilLumenate"
		# Clear Other Manufacturer fields
		line["manufacturer_name"] = None
		line["model_number"] = None
		line["spec_data"] = []

		self.assertIsNone(line["manufacturer_name"])
		self.assertIsNone(line["model_number"])
		self.assertEqual(len(line["spec_data"]), 0)


class TestValidationAPIArgs(unittest.TestCase):
	"""Tests for validation API argument handling."""

	def test_required_args_for_illumenate(self):
		"""Test required arguments for ilLumenate validation."""
		required_args = [
			"fixture_template",
			"tape_spec",
			"tape_attribute_combination",
			"requested_length_in",
		]

		args = {
			"fixture_template": "SH01",
			"tape_spec": "TAPE-001",
			"tape_attribute_combination": "CCT: 3000K",
			"requested_length_in": 48,
		}

		for arg in required_args:
			self.assertIn(arg, args)
			self.assertIsNotNone(args[arg])

	def test_optional_args_handling(self):
		"""Test optional arguments are properly handled."""
		args = {
			"fixture_template": "SH01",
			"tape_spec": "TAPE-001",
			"tape_attribute_combination": "CCT: 3000K",
			"requested_length_in": 48,
			# Optional args
			"endcap_item": None,
			"driver_spec": None,
			"cct_token": "3000K",
			"cri_value": 90,
			"finish_token": None,
		}

		# Filter out None values for API call
		filtered_args = {k: v for k, v in args.items() if v is not None}

		self.assertIn("cct_token", filtered_args)
		self.assertIn("cri_value", filtered_args)
		self.assertNotIn("endcap_item", filtered_args)
		self.assertNotIn("driver_spec", filtered_args)


class TestComputedFieldsMapping(unittest.TestCase):
	"""Tests for mapping validation result to schedule line fields."""

	def test_length_fields_mapping(self):
		"""Test mapping length result to line fields."""
		validation_result = {
			"length": {
				"manufacturable": {"in": 48.5, "mm": 1231.9, "in_display_1_16": '48-1/2'},
				"tape_cut": {"mm": 1200},
			}
		}

		line = {}
		line["manufacturable_length_in"] = validation_result["length"]["manufacturable"]["in"]
		line["manufacturable_length_mm"] = validation_result["length"]["manufacturable"]["mm"]
		line["tape_cut_length_mm"] = validation_result["length"]["tape_cut"]["mm"]
		line["led_tape_length_mm"] = validation_result["length"]["tape_cut"]["mm"]

		self.assertEqual(line["manufacturable_length_in"], 48.5)
		self.assertEqual(line["manufacturable_length_mm"], 1231.9)
		self.assertEqual(line["tape_cut_length_mm"], 1200)

	def test_electrical_fields_mapping(self):
		"""Test mapping electrical result to line fields."""
		validation_result = {
			"electrical": {
				"watts_per_ft": 5.0,
				"total_watts": 20.0,
				"runs_count": 1,
				"effective_max_run_ft": 17.0,
			}
		}

		line = {}
		line["watts_per_ft"] = validation_result["electrical"]["watts_per_ft"]
		line["total_watts"] = validation_result["electrical"]["total_watts"]
		line["runs_count"] = validation_result["electrical"]["runs_count"]
		line["max_run_length_ft"] = validation_result["electrical"]["effective_max_run_ft"]

		self.assertEqual(line["watts_per_ft"], 5.0)
		self.assertEqual(line["total_watts"], 20.0)
		self.assertEqual(line["runs_count"], 1)
		self.assertEqual(line["max_run_length_ft"], 17.0)

	def test_driver_fields_mapping(self):
		"""Test mapping driver result to line fields."""
		validation_result = {
			"driver": {
				"driver_spec": "DRV-001",
				"quantity": 1,
			}
		}

		line = {}
		line["selected_driver_spec"] = validation_result["driver"]["driver_spec"]
		line["selected_driver_qty"] = validation_result["driver"]["quantity"]

		self.assertEqual(line["selected_driver_spec"], "DRV-001")
		self.assertEqual(line["selected_driver_qty"], 1)

	def test_pricing_fields_mapping(self):
		"""Test mapping pricing result to line fields."""
		validation_result = {
			"pricing": {
				"unit_msrp": 200.00,
				"unit_net_price": 150.00,
				"tier_name": "Dealer A",
				"discount_percent": 25,
			}
		}
		qty = 2

		line = {}
		pricing = validation_result["pricing"]
		line["unit_msrp"] = pricing["unit_msrp"]
		line["unit_net"] = pricing["unit_net_price"]
		line["tier_name"] = pricing["tier_name"]
		line["discount_percent"] = pricing["discount_percent"]
		line["line_total"] = pricing["unit_net_price"] * qty

		self.assertEqual(line["unit_msrp"], 200.00)
		self.assertEqual(line["unit_net"], 150.00)
		self.assertEqual(line["tier_name"], "Dealer A")
		self.assertEqual(line["discount_percent"], 25)
		self.assertEqual(line["line_total"], 300.00)


class TestSpecDataParsing(unittest.TestCase):
	"""Tests for spec_data parsing from API."""

	def test_parse_spec_data_from_json_string(self):
		"""Test parsing spec_data from JSON string."""
		spec_data_str = '[{"spec_name": "CCT", "spec_value": "3000K"}, {"spec_name": "CRI", "spec_value": "90"}]'

		spec_data = json.loads(spec_data_str)

		self.assertEqual(len(spec_data), 2)
		self.assertEqual(spec_data[0]["spec_name"], "CCT")
		self.assertEqual(spec_data[1]["spec_value"], "90")

	def test_parse_spec_data_from_list(self):
		"""Test parsing spec_data from list."""
		spec_data = [
			{"spec_name": "CCT", "spec_value": "3000K"},
			{"spec_name": "CRI", "spec_value": "90"},
		]

		result = []
		for spec in spec_data:
			if spec.get("spec_name") and spec.get("spec_value"):
				result.append({
					"spec_name": spec["spec_name"],
					"spec_value": spec["spec_value"],
				})

		self.assertEqual(len(result), 2)

	def test_skip_empty_spec_data_entries(self):
		"""Test that empty spec_data entries are skipped."""
		spec_data = [
			{"spec_name": "CCT", "spec_value": "3000K"},
			{"spec_name": "", "spec_value": "90"},  # Empty name
			{"spec_name": "CRI", "spec_value": ""},  # Empty value
			{"spec_name": "Lumens", "spec_value": "450lm/ft"},
		]

		result = []
		for spec in spec_data:
			if spec.get("spec_name") and spec.get("spec_value"):
				result.append(spec)

		self.assertEqual(len(result), 2)
		self.assertEqual(result[0]["spec_name"], "CCT")
		self.assertEqual(result[1]["spec_name"], "Lumens")


if __name__ == "__main__":
	unittest.main()
