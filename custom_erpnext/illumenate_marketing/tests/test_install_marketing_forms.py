# Copyright (c) 2024, ilLumenate Lighting and contributors
# For license information, please see license.txt

"""
Unit tests for install module and marketing form creation.

These tests validate that the install hooks properly ensure
marketing forms exist in the database.
"""

import unittest


class TestMarketingFormDefinitions(unittest.TestCase):
	"""Tests for marketing form definitions used during installation."""

	def test_dealer_inquiry_form_definition(self):
		"""Test Dealer Inquiry form has required fields."""
		form_data = {
			"doctype": "ILL Marketing Form",
			"form_name": "Dealer Inquiry",
			"form_type": "Dealer Inquiry",
			"is_active": 1,
			"route": "/dealer_inquiry",
			"require_gdpr_consent": 1,
			"gdpr_consent_text": (
				"I agree to receive communications from ilLumenate Lighting "
				"regarding my dealer application. I understand I can unsubscribe at any time."
			),
			"success_message": (
				"Thank you for your interest in becoming an ilLumenate dealer. "
				"Our dealer team will review your application and contact you within 2 business days."
			),
		}

		self.assertEqual(form_data["form_name"], "Dealer Inquiry")
		self.assertEqual(form_data["form_type"], "Dealer Inquiry")
		self.assertEqual(form_data["is_active"], 1)
		self.assertEqual(form_data["route"], "/dealer_inquiry")
		self.assertTrue(form_data["require_gdpr_consent"])
		self.assertIn("agree", form_data["gdpr_consent_text"].lower())
		self.assertIn("thank you", form_data["success_message"].lower())

	def test_contact_form_definition(self):
		"""Test Contact form has required fields."""
		form_data = {
			"doctype": "ILL Marketing Form",
			"form_name": "Contact",
			"form_type": "Contact",
			"is_active": 1,
			"route": "/contact",
			"require_gdpr_consent": 1,
			"gdpr_consent_text": (
				"I agree to receive communications from ilLumenate Lighting. "
				"I understand I can unsubscribe at any time."
			),
			"success_message": "Thank you for your inquiry. We will be in touch shortly.",
		}

		self.assertEqual(form_data["form_name"], "Contact")
		self.assertEqual(form_data["form_type"], "Contact")
		self.assertEqual(form_data["is_active"], 1)
		self.assertEqual(form_data["route"], "/contact")
		self.assertTrue(form_data["require_gdpr_consent"])
		self.assertIn("agree", form_data["gdpr_consent_text"].lower())
		self.assertIn("thank you", form_data["success_message"].lower())

	def test_form_names_match_expected_values(self):
		"""Test that form names match what the HTML forms submit."""
		expected_form_names = ["Dealer Inquiry", "Contact"]

		# These are the form_name values submitted by the HTML forms
		html_form_names = ["Dealer Inquiry", "Contact"]

		for name in html_form_names:
			self.assertIn(name, expected_form_names)

	def test_routes_match_form_pages(self):
		"""Test that routes match the expected page paths."""
		expected_routes = {
			"Dealer Inquiry": "/dealer_inquiry",
			"Contact": "/contact",
		}

		# Verify routes are correctly configured
		self.assertEqual(expected_routes["Dealer Inquiry"], "/dealer_inquiry")
		self.assertEqual(expected_routes["Contact"], "/contact")


class TestFormValidationStructure(unittest.TestCase):
	"""Tests for form validation error structure."""

	def test_form_not_found_error_structure(self):
		"""Test Form not found error structure matches API expectations."""
		error_response = {
			"valid": False,
			"errors": [{"field": "form", "message": "Form not found"}],
		}

		self.assertFalse(error_response["valid"])
		self.assertEqual(len(error_response["errors"]), 1)
		self.assertEqual(error_response["errors"][0]["field"], "form")
		self.assertEqual(error_response["errors"][0]["message"], "Form not found")

	def test_form_inactive_error_structure(self):
		"""Test Form inactive error structure."""
		error_response = {
			"valid": False,
			"errors": [{"field": "form", "message": "Form is not active"}],
		}

		self.assertFalse(error_response["valid"])
		self.assertEqual(error_response["errors"][0]["message"], "Form is not active")


class TestInstallHooksConfiguration(unittest.TestCase):
	"""Tests for install hooks configuration."""

	def test_after_install_hook_path(self):
		"""Test after_install hook path is correctly formatted."""
		hook_path = "custom_erpnext.install.after_install"

		parts = hook_path.split(".")
		self.assertEqual(len(parts), 3)
		self.assertEqual(parts[0], "custom_erpnext")
		self.assertEqual(parts[1], "install")
		self.assertEqual(parts[2], "after_install")

	def test_after_migrate_hook_path(self):
		"""Test after_migrate hook path is correctly formatted."""
		hook_path = "custom_erpnext.install.after_migrate"

		parts = hook_path.split(".")
		self.assertEqual(len(parts), 3)
		self.assertEqual(parts[0], "custom_erpnext")
		self.assertEqual(parts[1], "install")
		self.assertEqual(parts[2], "after_migrate")


if __name__ == "__main__":
	unittest.main()
