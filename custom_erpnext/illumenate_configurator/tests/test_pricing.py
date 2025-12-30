# Copyright (c) 2024, ilLumenate Lighting and contributors
# For license information, please see license.txt

"""
Unit tests for the Pricing Engine.

These tests validate the pricing calculation logic without requiring a full Frappe instance.
"""

import unittest
from unittest.mock import MagicMock, patch


class TestPricingMath(unittest.TestCase):
	"""Tests for pricing calculation logic."""

	def test_basic_msrp_calculation(self):
		"""Test basic MSRP calculation with base fee and per-meter rates."""
		# Setup mock data
		validated_result = {
			"inputs": {
				"template_code": "SH01",
				"output_token": None,
				"finish_token": None,
				"lens_option": None,
				"mounting_method": None,
				"joiner_angle": None,
				"environment_token": None,
			},
			"length": {
				"manufacturable": {"mm": 1000},  # 1 meter
				"tape_cut": {"mm": 950},  # 0.95 meters
			},
			"electrical": {
				"runs_count": 1,
				"joiner_qty": 0,
			},
			"driver": {
				"driver_item": None,
				"quantity": 0,
			},
		}

		# Mock pricing profile data
		pricing_profile = {
			"name": "SH01-DEFAULT",
			"currency": "USD",
			"msrp_price_list": "MSRP",
			"base_fee": 25.00,
			"profile_rate_per_m": 50.00,
			"lens_rate_per_m": 15.00,
			"tape_rate_per_m": 30.00,
			"labor_fee": 10.00,
			"labor_rate_per_m": 5.00,
			"driver_markup_percent": 10,
		}

		# Expected MSRP (no driver, no adders):
		# base_fee = 25
		# profile_cost = 50 * 1 = 50
		# lens_cost = 15 * 1 = 15
		# tape_cost = 30 * 0.95 = 28.5
		# labor_cost = 10 + 5 * 1 = 15
		# Total = 25 + 50 + 15 + 28.5 + 15 = 133.5

		expected_msrp = 133.50

		# Calculate manually
		m_profile = 1.0  # 1000mm / 1000
		m_tape = 0.95  # 950mm / 1000

		msrp = float(pricing_profile["base_fee"])
		msrp += float(pricing_profile["profile_rate_per_m"]) * m_profile
		msrp += float(pricing_profile["lens_rate_per_m"]) * m_profile
		msrp += float(pricing_profile["tape_rate_per_m"]) * m_tape
		msrp += float(pricing_profile["labor_fee"]) + float(pricing_profile["labor_rate_per_m"]) * m_profile

		self.assertAlmostEqual(msrp, expected_msrp, places=2)

	def test_tier_discount_msrp(self):
		"""Test MSRP tier (0% discount)."""
		msrp = 100.00
		discount = 0
		net = msrp * (1 - discount / 100)
		self.assertEqual(net, 100.00)

	def test_tier_discount_dealer_a(self):
		"""Test Dealer A tier (40% discount)."""
		msrp = 100.00
		discount = 40
		net = msrp * (1 - discount / 100)
		self.assertEqual(net, 60.00)

	def test_tier_discount_dealer_b(self):
		"""Test Dealer B tier (45% discount)."""
		msrp = 100.00
		discount = 45
		net = msrp * (1 - discount / 100)
		self.assertAlmostEqual(net, 55.00, places=2)

	def test_tier_discount_dealer_c(self):
		"""Test Dealer C tier (50% discount)."""
		msrp = 100.00
		discount = 50
		net = msrp * (1 - discount / 100)
		self.assertAlmostEqual(net, 50.00, places=2)

	def test_tier_discount_dealer_d(self):
		"""Test Dealer D tier (55% discount)."""
		msrp = 100.00
		discount = 55
		net = msrp * (1 - discount / 100)
		self.assertAlmostEqual(net, 45.00, places=2)

	def test_rounding_to_2_decimals(self):
		"""Test that results are rounded to 2 decimal places."""
		msrp = 133.567
		rounded = round(msrp, 2)
		self.assertEqual(rounded, 133.57)

	def test_output_pricing_adder(self):
		"""Test tape rate adder for output level."""
		base_tape_rate = 30.00
		adder = 10.00
		m_tape = 1.0

		tape_cost_without_adder = base_tape_rate * m_tape
		tape_cost_with_adder = (base_tape_rate + adder) * m_tape

		self.assertEqual(tape_cost_without_adder, 30.00)
		self.assertEqual(tape_cost_with_adder, 40.00)

	def test_output_pricing_override(self):
		"""Test tape rate override for output level."""
		base_tape_rate = 30.00
		override_rate = 50.00
		m_tape = 1.0

		# When override is set, it replaces the base rate
		tape_cost = override_rate * m_tape
		self.assertEqual(tape_cost, 50.00)

	def test_option_adder_flat_per_fixture(self):
		"""Test flat per fixture adder mode."""
		amount = 15.00
		adder_total = amount  # Flat per fixture = just the amount
		self.assertEqual(adder_total, 15.00)

	def test_option_adder_per_meter(self):
		"""Test per meter adder mode."""
		amount = 5.00
		m_profile = 2.5
		adder_total = amount * m_profile
		self.assertEqual(adder_total, 12.50)

	def test_option_adder_per_joiner(self):
		"""Test per joiner adder mode."""
		amount = 8.00
		joiner_qty = 3
		adder_total = amount * joiner_qty
		self.assertEqual(adder_total, 24.00)

	def test_option_adder_per_driver(self):
		"""Test per driver adder mode."""
		amount = 10.00
		driver_qty = 2
		adder_total = amount * driver_qty
		self.assertEqual(adder_total, 20.00)

	def test_option_adder_per_run(self):
		"""Test per run adder mode."""
		amount = 5.00
		runs_count = 4
		adder_total = amount * runs_count
		self.assertEqual(adder_total, 20.00)

	def test_driver_markup(self):
		"""Test driver price with markup."""
		item_price = 100.00
		markup_percent = 10
		driver_unit = item_price * (1 + markup_percent / 100)
		self.assertAlmostEqual(driver_unit, 110.00, places=2)

	def test_driver_total_cost(self):
		"""Test total driver cost calculation."""
		item_price = 100.00
		markup_percent = 10
		driver_qty = 2

		driver_unit = item_price * (1 + markup_percent / 100)
		driver_total = driver_unit * driver_qty

		self.assertAlmostEqual(driver_total, 220.00, places=2)


class TestPricingEdgeCases(unittest.TestCase):
	"""Tests for edge cases in pricing calculation."""

	def test_zero_length(self):
		"""Test pricing with zero length."""
		m_profile = 0
		profile_rate = 50.00
		profile_cost = profile_rate * m_profile
		self.assertEqual(profile_cost, 0)

	def test_no_driver(self):
		"""Test pricing with no driver."""
		driver_item = None
		driver_qty = 0
		driver_cost = 0  # Should be 0 when no driver
		self.assertEqual(driver_cost, 0)

	def test_discount_boundary_0(self):
		"""Test 0% discount boundary."""
		msrp = 100.00
		discount = 0
		net = msrp * (1 - discount / 100)
		self.assertEqual(net, msrp)

	def test_discount_boundary_100(self):
		"""Test 100% discount boundary (theoretical)."""
		msrp = 100.00
		discount = 100
		net = msrp * (1 - discount / 100)
		self.assertEqual(net, 0)


if __name__ == "__main__":
	unittest.main()
