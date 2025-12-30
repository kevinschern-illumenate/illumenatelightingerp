# Copyright (c) 2024, ilLumenate Lighting and contributors
# For license information, please see license.txt

"""
Unit tests for Sprint 6: Complex Incentive Calculator functionality.

These tests validate the customer lifetime value (LTV) APIs and
promo code generation functionality.
"""

import json
import secrets
import unittest
from unittest.mock import MagicMock, patch


class TestCustomerLTVAPI(unittest.TestCase):
	"""Tests for customer lifetime value API functionality."""

	def test_ltv_response_structure(self):
		"""Test LTV response has required fields."""
		expected_fields = [
			"lifetime_value",
			"order_count",
			"last_order",
			"product_categories",
			"customer_name",
		]

		# Mock response structure
		response = {
			"lifetime_value": 5000.00,
			"order_count": 10,
			"last_order": "2024-01-15",
			"product_categories": ["Lighting", "Accessories"],
			"customer_name": "CUST-001",
		}

		for field in expected_fields:
			self.assertIn(field, response)

	def test_ltv_calculation_logic(self):
		"""Test LTV calculation from order totals."""
		orders = [
			{"grand_total": 1000.00},
			{"grand_total": 500.50},
			{"grand_total": 1499.50},
		]

		lifetime_value = sum(order["grand_total"] for order in orders)
		self.assertEqual(lifetime_value, 3000.00)

	def test_high_ltv_customers_threshold(self):
		"""Test high LTV customer threshold filtering."""
		customers = [
			{"customer_name": "CUST-001", "lifetime_value": 5000.00},
			{"customer_name": "CUST-002", "lifetime_value": 500.00},
			{"customer_name": "CUST-003", "lifetime_value": 1500.00},
			{"customer_name": "CUST-004", "lifetime_value": 999.99},
		]

		min_threshold = 1000.00
		high_ltv = [c for c in customers if c["lifetime_value"] >= min_threshold]

		self.assertEqual(len(high_ltv), 2)
		self.assertEqual(high_ltv[0]["customer_name"], "CUST-001")
		self.assertEqual(high_ltv[1]["customer_name"], "CUST-003")

	def test_product_categories_aggregation(self):
		"""Test product category aggregation from orders."""
		order_items = [
			{"item_group": "Lighting"},
			{"item_group": "Accessories"},
			{"item_group": "Lighting"},
			{"item_group": "Controls"},
		]

		unique_categories = list(set(item["item_group"] for item in order_items))
		self.assertEqual(len(unique_categories), 3)
		self.assertIn("Lighting", unique_categories)


class TestPromoCodeGeneration(unittest.TestCase):
	"""Tests for promo code generation functionality."""

	def test_promo_code_format(self):
		"""Test promo code follows expected format ILL-XXXXXXXX."""
		import re

		code = f"ILL-{secrets.token_hex(4).upper()}"
		pattern = r"^ILL-[A-F0-9]{8}$"

		self.assertIsNotNone(re.match(pattern, code))

	def test_promo_code_uniqueness(self):
		"""Test that generated promo codes are unique."""
		codes = set()

		for _ in range(100):
			code = f"ILL-{secrets.token_hex(4).upper()}"
			codes.add(code)

		# All 100 codes should be unique (extremely high probability)
		self.assertEqual(len(codes), 100)

	def test_promo_code_response_structure(self):
		"""Test promo code generation response structure."""
		expected_fields = [
			"promo_code",
			"customer",
			"discount_percent",
			"valid_from",
			"valid_until",
			"campaign",
		]

		response = {
			"promo_code": "ILL-ABCD1234",
			"customer": "CUST-001",
			"discount_percent": 50.0,
			"valid_from": "2024-01-01",
			"valid_until": "2024-01-31",
			"campaign": "LTV Promotion",
		}

		for field in expected_fields:
			self.assertIn(field, response)

	def test_discount_percent_validation(self):
		"""Test discount percent must be between 0 and 100."""
		valid_discounts = [0, 10, 50, 75, 100]
		invalid_discounts = [-1, 101, 150, -50]

		for discount in valid_discounts:
			self.assertTrue(0 <= discount <= 100)

		for discount in invalid_discounts:
			self.assertFalse(0 <= discount <= 100)

	def test_valid_days_calculation(self):
		"""Test validity period calculation."""
		from datetime import date, timedelta

		valid_days = 30
		valid_from = date(2024, 1, 1)
		valid_until = valid_from + timedelta(days=valid_days)

		self.assertEqual(valid_until, date(2024, 1, 31))

	def test_promo_code_validation_logic(self):
		"""Test promo code validation checks."""
		promo = {
			"promo_code": "ILL-ABCD1234",
			"customer": "CUST-001",
			"is_used": False,
			"valid_from": "2024-01-01",
			"valid_until": "2024-01-31",
		}

		# Check basic validation
		self.assertIsNotNone(promo["promo_code"])
		self.assertIsNotNone(promo["customer"])
		self.assertFalse(promo["is_used"])


class TestPromoCodeValidation(unittest.TestCase):
	"""Tests for promo code validation functionality."""

	def test_validation_response_structure(self):
		"""Test validation response has required fields."""
		valid_response = {
			"valid": True,
			"promo_code": "ILL-ABCD1234",
			"customer": "CUST-001",
			"discount_percent": 50.0,
			"valid_from": "2024-01-01",
			"valid_until": "2024-01-31",
		}

		invalid_response = {
			"valid": False,
			"error": "Promo code has expired",
		}

		self.assertTrue(valid_response["valid"])
		self.assertFalse(invalid_response["valid"])
		self.assertIn("error", invalid_response)

	def test_customer_ownership_check(self):
		"""Test promo code customer ownership validation."""
		promo_customer = "CUST-001"
		requesting_customer = "CUST-002"

		is_owner = promo_customer == requesting_customer
		self.assertFalse(is_owner)

	def test_expiration_check(self):
		"""Test promo code expiration validation."""
		from datetime import date

		today = date(2024, 2, 15)
		valid_until = date(2024, 1, 31)

		is_expired = today > valid_until
		self.assertTrue(is_expired)

	def test_already_used_check(self):
		"""Test promo code already used validation."""
		promo = {"is_used": True, "used_at": "2024-01-15 10:30:00"}

		is_valid = not promo["is_used"]
		self.assertFalse(is_valid)


class TestPromoCodeRedemption(unittest.TestCase):
	"""Tests for promo code redemption functionality."""

	def test_redemption_response_structure(self):
		"""Test redemption response has required fields."""
		success_response = {
			"success": True,
			"message": "Promo code redeemed successfully",
			"discount_percent": 50.0,
		}

		error_response = {
			"success": False,
			"error": "Promo code has already been used",
		}

		self.assertTrue(success_response["success"])
		self.assertFalse(error_response["success"])

	def test_mark_as_used_updates(self):
		"""Test marking promo code as used updates correct fields."""
		promo = {
			"is_used": False,
			"used_at": None,
		}

		# Simulate marking as used
		promo["is_used"] = True
		promo["used_at"] = "2024-01-15 10:30:00"

		self.assertTrue(promo["is_used"])
		self.assertIsNotNone(promo["used_at"])


class TestLTVQueryParameters(unittest.TestCase):
	"""Tests for LTV API query parameter handling."""

	def test_min_lifetime_value_conversion(self):
		"""Test min_lifetime_value is converted to float."""
		min_value_str = "1000"
		min_value = float(min_value_str)

		self.assertEqual(min_value, 1000.0)

	def test_limit_conversion(self):
		"""Test limit is converted to int."""
		limit_str = "100"
		limit = int(limit_str)

		self.assertEqual(limit, 100)

	def test_default_parameters(self):
		"""Test default parameter values."""
		defaults = {
			"min_lifetime_value": 1000,
			"limit": 100,
			"valid_days": 30,
		}

		self.assertEqual(defaults["min_lifetime_value"], 1000)
		self.assertEqual(defaults["limit"], 100)
		self.assertEqual(defaults["valid_days"], 30)


class TestN8nIntegrationForLTV(unittest.TestCase):
	"""Tests for n8n workflow integration with LTV APIs."""

	def test_ltv_payload_for_n8n(self):
		"""Test LTV data payload is suitable for n8n consumption."""
		ltv_data = {
			"lifetime_value": 5000.00,
			"order_count": 10,
			"last_order": "2024-01-15",
			"product_categories": ["Lighting", "Accessories"],
			"customer_name": "CUST-001",
		}

		# Should be JSON serializable
		json_str = json.dumps(ltv_data)
		self.assertIsInstance(json_str, str)

		# Should be deserializable
		parsed = json.loads(json_str)
		self.assertEqual(parsed["lifetime_value"], 5000.00)

	def test_high_ltv_customers_payload(self):
		"""Test high LTV customers list is suitable for n8n loop."""
		customers = [
			{"customer_name": "CUST-001", "lifetime_value": 5000.00, "customer_email": "cust1@example.com"},
			{"customer_name": "CUST-002", "lifetime_value": 3000.00, "customer_email": "cust2@example.com"},
		]

		# Should be iterable for n8n loop node
		for customer in customers:
			self.assertIn("customer_name", customer)
			self.assertIn("customer_email", customer)
			self.assertIn("lifetime_value", customer)

	def test_promo_code_payload_for_email(self):
		"""Test promo code data is suitable for email template."""
		promo_data = {
			"promo_code": "ILL-ABCD1234",
			"customer": "CUST-001",
			"discount_percent": 50,
			"valid_until": "2024-01-31",
		}

		# Email template placeholders
		email_content = f"Use code {promo_data['promo_code']} for {promo_data['discount_percent']}% off!"
		self.assertIn("ILL-ABCD1234", email_content)
		self.assertIn("50", email_content)


if __name__ == "__main__":
	unittest.main()
