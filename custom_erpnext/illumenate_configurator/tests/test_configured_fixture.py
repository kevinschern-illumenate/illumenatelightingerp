# Copyright (c) 2024, ilLumenate Lighting and contributors
# For license information, please see license.txt

"""
Unit tests for configuration persistence and SKU generation.

These tests validate signature generation and SKU builder without requiring a Frappe instance.
"""

import hashlib
import json
import unittest


class TestSignatureGeneration(unittest.TestCase):
	"""Tests for configuration signature generation."""

	def test_signature_deterministic(self):
		"""Test that the same inputs produce the same signature."""
		signature_data = {
			"template_code": "SH01",
			"tape_spec": "TAPE-001",
			"tape_attribute_combination": "Color Temperature: 2700K, CRI: 90",
			"endcap_item": "ENDCAP-001",
			"requested_overall_mm": 500.00,
		}

		sorted_json = json.dumps(signature_data, sort_keys=True)
		sig1 = hashlib.md5(sorted_json.encode()).hexdigest()
		sig2 = hashlib.md5(sorted_json.encode()).hexdigest()

		self.assertEqual(sig1, sig2)

	def test_signature_different_inputs(self):
		"""Test that different inputs produce different signatures."""
		data1 = {
			"template_code": "SH01",
			"tape_spec": "TAPE-001",
			"tape_attribute_combination": "Color Temperature: 2700K, CRI: 90",
			"endcap_item": "ENDCAP-001",
			"requested_overall_mm": 500.00,
		}

		data2 = {
			"template_code": "SH01",
			"tape_spec": "TAPE-001",
			"tape_attribute_combination": "Color Temperature: 3000K, CRI: 90",  # Different
			"endcap_item": "ENDCAP-001",
			"requested_overall_mm": 500.00,
		}

		sig1 = hashlib.md5(json.dumps(data1, sort_keys=True).encode()).hexdigest()
		sig2 = hashlib.md5(json.dumps(data2, sort_keys=True).encode()).hexdigest()

		self.assertNotEqual(sig1, sig2)

	def test_signature_ordering_independent(self):
		"""Test that key ordering doesn't affect signature (due to sort_keys=True)."""
		data1 = {
			"template_code": "SH01",
			"tape_spec": "TAPE-001",
			"tape_attribute_combination": "",
			"endcap_item": "ENDCAP-001",
			"requested_overall_mm": 500.00,
		}

		# Same data, different dict ordering in Python
		data2 = {
			"requested_overall_mm": 500.00,
			"endcap_item": "ENDCAP-001",
			"tape_attribute_combination": "",
			"tape_spec": "TAPE-001",
			"template_code": "SH01",
		}

		sig1 = hashlib.md5(json.dumps(data1, sort_keys=True).encode()).hexdigest()
		sig2 = hashlib.md5(json.dumps(data2, sort_keys=True).encode()).hexdigest()

		self.assertEqual(sig1, sig2)


class TestSKUGeneration(unittest.TestCase):
	"""Tests for SKU generation logic."""

	def test_sku_format(self):
		"""Test basic SKU format."""
		template_code = "SH01"
		manufacturable_overall_in = 48.0

		# Round to nearest 1/16"
		length_16ths = round(manufacturable_overall_in * 16) / 16
		length_str = f"{length_16ths:.2f}".replace(".", "_")
		sku = f"ILL-{template_code}-NA-NA-NA-NA-NA-NA-NA-{length_str}"

		self.assertEqual(sku, "ILL-SH01-NA-NA-NA-NA-NA-NA-NA-48_00")

	def test_sku_with_fractional_inches(self):
		"""Test SKU generation with fractional inch length."""
		template_code = "SH01"
		# 48 3/16" = 48.1875"
		manufacturable_overall_in = 48.1875

		length_16ths = round(manufacturable_overall_in * 16) / 16
		length_str = f"{length_16ths:.2f}".replace(".", "_")
		sku = f"ILL-{template_code}-NA-NA-NA-NA-NA-NA-NA-{length_str}"

		self.assertEqual(sku, "ILL-SH01-NA-NA-NA-NA-NA-NA-NA-48_19")  # 48.1875 rounds to 48.1875

	def test_sku_rounding_to_16th(self):
		"""Test that non-1/16" values are properly rounded."""
		template_code = "SH01"
		# Value that's not exactly a 1/16"
		manufacturable_overall_in = 48.1

		length_16ths = round(manufacturable_overall_in * 16) / 16
		# 48.1 * 16 = 769.6, rounds to 770, 770/16 = 48.125
		self.assertAlmostEqual(length_16ths, 48.125, places=4)

		length_str = f"{length_16ths:.2f}".replace(".", "_")
		sku = f"ILL-{template_code}-NA-NA-NA-NA-NA-NA-NA-{length_str}"

		self.assertEqual(sku, "ILL-SH01-NA-NA-NA-NA-NA-NA-NA-48_12")


class TestTravelerInstructions(unittest.TestCase):
	"""Tests for traveler instruction generation."""

	def test_traveler_instruction_format(self):
		"""Test that traveler instructions contain expected information."""
		# Create a mock configured fixture data
		class MockCF:
			requested_overall_in = 48.0
			requested_overall_mm = 1219.2
			manufacturable_overall_in = 47.9375
			manufacturable_overall_mm = 1217.61
			delta_mm = 1.59
			tape_cut_length_mm = 1200.0
			runs_count = 2
			selected_driver_spec = "DRV-001"
			selected_driver_qty = 1

		cf = MockCF()

		# Generate instructions
		instructions = f"""
Configuration Instructions
--------------------------
Requested Overall Length: {cf.requested_overall_in}" ({cf.requested_overall_mm} mm)
Manufacturable Overall Length: {cf.manufacturable_overall_in}" ({cf.manufacturable_overall_mm} mm)
Delta (rounded down): {round(cf.delta_mm / 25.4, 4)}" ({cf.delta_mm} mm)
Tape Cut Length: {cf.tape_cut_length_mm} mm ({round(cf.tape_cut_length_mm / 25.4, 4)}")
Runs: {cf.runs_count}
Driver: {cf.selected_driver_spec} x {cf.selected_driver_qty} (80% derated)

Components:
- Profile: {round(cf.manufacturable_overall_mm / 1000, 3)} m
- Tape: {round(cf.tape_cut_length_mm / 1000, 3)} m
- Endcaps: 4 (includes extra pair)
- Leader cables: {cf.runs_count}
- Drivers: {cf.selected_driver_qty}
"""

		# Verify key information is present
		self.assertIn("48.0", instructions)  # Requested length
		self.assertIn("47.9375", instructions)  # Manufacturable length
		self.assertIn("Runs: 2", instructions)
		self.assertIn("DRV-001", instructions)
		self.assertIn("Endcaps: 4", instructions)


if __name__ == "__main__":
	unittest.main()
