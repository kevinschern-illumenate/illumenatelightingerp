# Copyright (c) 2024, ilLumenate Lighting and contributors
# For license information, please see license.txt

"""
Unit tests for the Configurator Rules Engine.

These tests validate the core math module without requiring a Frappe instance.
"""

import unittest

from custom_erpnext.illumenate_configurator.engine import (
	compute_length,
	compute_runs,
	format_to_16th,
	inches_to_mm,
	mm_to_inches,
	select_driver,
)


class TestUnitConversions(unittest.TestCase):
	"""Tests for unit conversion functions."""

	def test_inches_to_mm(self):
		self.assertAlmostEqual(inches_to_mm(1), 25.4, places=4)
		self.assertAlmostEqual(inches_to_mm(10), 254.0, places=4)
		self.assertAlmostEqual(inches_to_mm(0), 0, places=4)

	def test_mm_to_inches(self):
		self.assertAlmostEqual(mm_to_inches(25.4), 1, places=4)
		self.assertAlmostEqual(mm_to_inches(254.0), 10, places=4)
		self.assertAlmostEqual(mm_to_inches(0), 0, places=4)

	def test_format_to_16th(self):
		# Test exact 1/16" increments
		self.assertEqual(format_to_16th(1.0), 1.0)
		self.assertEqual(format_to_16th(1.0625), 1.0625)  # 1/16
		self.assertEqual(format_to_16th(1.125), 1.125)  # 2/16 = 1/8
		self.assertEqual(format_to_16th(1.5), 1.5)  # 8/16 = 1/2

		# Test rounding to nearest 1/16"
		# 1.03 * 16 = 16.48, rounds to 16, so 16/16 = 1.0
		self.assertEqual(format_to_16th(1.03), 1.0)
		self.assertEqual(format_to_16th(1.01), 1.0)  # rounds to 0
		# 10.1 * 16 = 161.6, rounds to 162, so 162/16 = 10.125
		self.assertEqual(format_to_16th(10.1), 10.125)


class TestLengthComputation(unittest.TestCase):
	"""Tests for length computation function."""

	def test_basic_length_computation(self):
		"""
		Test case: cut_increment_in = 1", requested_overall_in = 10.10"
		Verify manufacturable_overall_in_display is <= requested and snapped to 1/16"
		"""
		result = compute_length(
			requested_overall_in=10.10,
			endcap_allowance_mm_per_side=2.0,
			leader_allowance_mm=15.0,
			cut_increment_mm=25.4,  # 1" = 25.4mm
		)

		self.assertFalse(result.get("error"))
		# Manufacturable should be <= requested
		self.assertLessEqual(
			result["manufacturable"]["in_display_1_16"], result["requested"]["in_display_1_16"]
		)
		# Display should be a multiple of 1/16
		display_value = result["manufacturable"]["in_display_1_16"]
		self.assertEqual(display_value, format_to_16th(display_value))

	def test_length_too_short(self):
		"""Test that very short length returns an error."""
		result = compute_length(
			requested_overall_in=0.5,  # Very short
			endcap_allowance_mm_per_side=2.0,
			leader_allowance_mm=15.0,
			cut_increment_mm=25.4,
		)

		self.assertTrue(result.get("error"))
		self.assertEqual(result["code"], "LENGTH_TOO_SHORT")
		self.assertIn("too short", result["message"].lower())

	def test_length_rounding_down(self):
		"""Ensure length is always rounded down to cut increment."""
		# Request 50" with 0.5" cut increment
		result = compute_length(
			requested_overall_in=50.0,
			endcap_allowance_mm_per_side=2.0,
			leader_allowance_mm=15.0,
			cut_increment_mm=12.7,  # 0.5" = 12.7mm
		)

		self.assertFalse(result.get("error"))
		# Tape cut should be an exact multiple of cut increment
		# Due to floating point, we check if remainder is very small or very close to increment
		tape_cut_mm = result["tape_cut"]["mm"]
		remainder = tape_cut_mm % 12.7
		self.assertTrue(remainder < 0.01 or abs(remainder - 12.7) < 0.01)

	def test_warning_is_present(self):
		"""Ensure a warning about rounding is included."""
		result = compute_length(
			requested_overall_in=10.10,
			endcap_allowance_mm_per_side=2.0,
			leader_allowance_mm=15.0,
			cut_increment_mm=25.4,
		)

		self.assertFalse(result.get("error"))
		self.assertIn("rounded down", result.get("warning", "").lower())


class TestRunsComputation(unittest.TestCase):
	"""Tests for run count calculation."""

	def test_single_run_under_85w(self):
		"""If total watts < 85, should have 1 run."""
		# 2ft at 10W/ft = 20W total, well under 85W
		result = compute_runs(
			tape_cut_mm=609.6,  # 2 ft = 609.6mm
			watts_per_ft=10.0,
		)

		self.assertEqual(result["runs_count"], 1)
		self.assertAlmostEqual(result["total_watts"], 20.0, places=2)

	def test_runs_just_over_85w(self):
		"""
		watts_per_ft = 10
		Choose L_tape_cut such that W_total just over 85 → runs_count = 2
		"""
		# 9ft at 10W/ft = 90W, just over 85W threshold
		result = compute_runs(
			tape_cut_mm=2743.2,  # 9 ft = 2743.2mm
			watts_per_ft=10.0,
		)

		self.assertEqual(result["runs_count"], 2)
		self.assertAlmostEqual(result["total_watts"], 90.0, places=2)
		self.assertAlmostEqual(result["max_run_ft_by_85w"], 8.5, places=2)

	def test_high_wattage_tape(self):
		"""Test with high wattage tape requiring multiple runs."""
		# 10ft at 20W/ft = 200W total
		# Max run at 85W = 4.25ft
		# runs_count = ceil(10 / 4.25) = 3
		result = compute_runs(
			tape_cut_mm=3048.0,  # 10 ft
			watts_per_ft=20.0,
		)

		self.assertEqual(result["runs_count"], 3)
		self.assertAlmostEqual(result["total_watts"], 200.0, places=2)

	def test_voltage_drop_limit_used(self):
		"""Test that voltage drop max run is used when it's more restrictive."""
		# 20ft at 5W/ft = 100W total
		# Max run at 85W = 17ft
		# But voltage drop limit = 10ft
		# Effective max run = 10ft (voltage drop is more restrictive)
		# runs_count = ceil(20 / 10) = 2
		result = compute_runs(
			tape_cut_mm=6096.0,  # 20 ft
			watts_per_ft=5.0,
			voltage_drop_max_run_ft=10.0,
		)

		self.assertEqual(result["runs_count"], 2)
		self.assertEqual(result["limiting_factor"], "voltage_drop")
		self.assertAlmostEqual(result["effective_max_run_ft"], 10.0, places=2)
		self.assertAlmostEqual(result["max_run_ft_by_voltage_drop"], 10.0, places=2)

	def test_85w_rule_used_when_more_restrictive(self):
		"""Test that 85W rule is used when it's more restrictive than voltage drop."""
		# 20ft at 20W/ft = 400W total
		# Max run at 85W = 4.25ft
		# Voltage drop limit = 15ft
		# Effective max run = 4.25ft (85W is more restrictive)
		# runs_count = ceil(20 / 4.25) = 5
		result = compute_runs(
			tape_cut_mm=6096.0,  # 20 ft
			watts_per_ft=20.0,
			voltage_drop_max_run_ft=15.0,
		)

		self.assertEqual(result["runs_count"], 5)
		self.assertEqual(result["limiting_factor"], "85w_rule")
		self.assertAlmostEqual(result["effective_max_run_ft"], 4.25, places=2)

	def test_no_voltage_drop_limit(self):
		"""Test that without voltage drop limit, 85W rule is used."""
		result = compute_runs(
			tape_cut_mm=3048.0,  # 10 ft
			watts_per_ft=10.0,
			voltage_drop_max_run_ft=None,
		)

		self.assertEqual(result["limiting_factor"], "85w_rule")
		self.assertIsNone(result["max_run_ft_by_voltage_drop"])


class TestDriverSelection(unittest.TestCase):
	"""Tests for driver auto-selection."""

	def test_driver_sizing_by_watts(self):
		"""
		driver max_wattage 100W → usable 80W
		if total_watts=120W => N_w=2
		"""
		drivers = [
			{
				"name": "DRV-001",
				"driver_item": "DRIVER-100W",
				"max_wattage": 100,
				"outputs_count": 4,
			}
		]

		result = select_driver(
			eligible_drivers=drivers,
			runs_count=2,
			total_watts=120.0,  # > 80W usable, so N_w = 2
		)

		self.assertFalse(result.get("error"))
		self.assertEqual(result["quantity"], 2)
		self.assertEqual(result["usable_watts_each"], 80.0)

	def test_driver_sizing_by_outputs(self):
		"""
		runs_count=5, outputs_count=2 => N_out=3
		"""
		drivers = [
			{
				"name": "DRV-002",
				"driver_item": "DRIVER-200W",
				"max_wattage": 200,
				"outputs_count": 2,
			}
		]

		result = select_driver(
			eligible_drivers=drivers,
			runs_count=5,
			total_watts=50.0,  # Low wattage, so N_w = 1
		)

		self.assertFalse(result.get("error"))
		# N_out = ceil(5/2) = 3, N_w = ceil(50/160) = 1
		# N = max(3, 1) = 3
		self.assertEqual(result["quantity"], 3)

	def test_no_matching_driver(self):
		"""Return error when no drivers match."""
		result = select_driver(
			eligible_drivers=[],
			runs_count=2,
			total_watts=100.0,
		)

		self.assertTrue(result.get("error"))
		self.assertEqual(result["code"], "NO_MATCHING_DRIVER")

	def test_driver_ranking(self):
		"""Test that lowest quantity is preferred, then lowest wattage."""
		drivers = [
			{
				"name": "DRV-BIG",
				"driver_item": "DRIVER-200W",
				"max_wattage": 200,
				"outputs_count": 4,
			},
			{
				"name": "DRV-SMALL",
				"driver_item": "DRIVER-100W",
				"max_wattage": 100,
				"outputs_count": 4,
			},
		]

		# For 120W total:
		# DRV-BIG: usable=160W, N_w=1, N_out=1, N=1
		# DRV-SMALL: usable=80W, N_w=2, N_out=1, N=2
		# DRV-BIG should be selected (lower N)
		result = select_driver(
			eligible_drivers=drivers,
			runs_count=2,
			total_watts=120.0,
		)

		self.assertFalse(result.get("error"))
		self.assertEqual(result["driver_spec"], "DRV-BIG")
		self.assertEqual(result["quantity"], 1)

	def test_driver_ranking_tiebreaker(self):
		"""When quantity is the same, prefer lower wattage."""
		drivers = [
			{
				"name": "DRV-BIG",
				"driver_item": "B-DRIVER-200W",
				"max_wattage": 200,
				"outputs_count": 2,
			},
			{
				"name": "DRV-SMALL",
				"driver_item": "A-DRIVER-100W",
				"max_wattage": 100,
				"outputs_count": 2,
			},
		]

		# For 80W total, 2 runs:
		# Both need 1 driver (N=1), so prefer lower wattage (DRV-SMALL)
		result = select_driver(
			eligible_drivers=drivers,
			runs_count=2,
			total_watts=80.0,
		)

		self.assertFalse(result.get("error"))
		self.assertEqual(result["driver_spec"], "DRV-SMALL")


if __name__ == "__main__":
	unittest.main()
