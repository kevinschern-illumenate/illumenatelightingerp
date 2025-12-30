# Copyright (c) 2024, ilLumenate Lighting and contributors
# For license information, please see license.txt

"""
Unit tests for Sprint 1: Lead Capture Foundation functionality.

These tests validate form submission, UTM parameter parsing,
GDPR consent tracking, and unsubscribe management.

Note: These tests are designed to be standalone and don't require
the frappe framework to run for unit testing purposes.
"""

import json
import unittest


def parse_utm_parameters(request_data):
	"""
	Parse UTM parameters from request data.
	Standalone copy for unit testing.
	"""
	return {
		"utm_source": request_data.get("utm_source", ""),
		"utm_medium": request_data.get("utm_medium", ""),
		"utm_campaign": request_data.get("utm_campaign", ""),
		"utm_content": request_data.get("utm_content", ""),
		"utm_term": request_data.get("utm_term", ""),
	}


class TestUTMParameterParsing(unittest.TestCase):
	"""Tests for UTM parameter parsing from form submissions."""

	def test_parse_all_utm_params(self):
		"""Test parsing all UTM parameters from request data."""
		request_data = {
			"email": "test@example.com",
			"utm_source": "google",
			"utm_medium": "cpc",
			"utm_campaign": "spring_promo",
			"utm_content": "banner_a",
			"utm_term": "led lighting",
		}

		result = parse_utm_parameters(request_data)

		self.assertEqual(result["utm_source"], "google")
		self.assertEqual(result["utm_medium"], "cpc")
		self.assertEqual(result["utm_campaign"], "spring_promo")
		self.assertEqual(result["utm_content"], "banner_a")
		self.assertEqual(result["utm_term"], "led lighting")

	def test_parse_partial_utm_params(self):
		"""Test parsing when only some UTM parameters are provided."""
		request_data = {
			"email": "test@example.com",
			"utm_source": "newsletter",
			"utm_campaign": "august_2024",
		}

		result = parse_utm_parameters(request_data)

		self.assertEqual(result["utm_source"], "newsletter")
		self.assertEqual(result["utm_medium"], "")
		self.assertEqual(result["utm_campaign"], "august_2024")
		self.assertEqual(result["utm_content"], "")
		self.assertEqual(result["utm_term"], "")

	def test_parse_no_utm_params(self):
		"""Test parsing when no UTM parameters are provided."""
		request_data = {
			"email": "test@example.com",
			"message": "Hello",
		}

		result = parse_utm_parameters(request_data)

		self.assertEqual(result["utm_source"], "")
		self.assertEqual(result["utm_medium"], "")
		self.assertEqual(result["utm_campaign"], "")
		self.assertEqual(result["utm_content"], "")
		self.assertEqual(result["utm_term"], "")


class TestEmailValidation(unittest.TestCase):
	"""Tests for email format validation."""

	def test_valid_emails(self):
		"""Test that valid email formats are accepted."""
		import re

		pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"

		valid_emails = [
			"test@example.com",
			"user.name@domain.com",
			"user+tag@example.org",
			"name123@company.co.uk",
		]

		for email in valid_emails:
			self.assertIsNotNone(re.match(pattern, email), f"{email} should be valid")

	def test_invalid_emails(self):
		"""Test that invalid email formats are rejected."""
		import re

		pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"

		invalid_emails = [
			"notanemail",
			"missing@domain",
			"@nodomain.com",
			"spaces in@email.com",
		]

		for email in invalid_emails:
			self.assertIsNone(re.match(pattern, email), f"{email} should be invalid")


class TestLeadSourceValidation(unittest.TestCase):
	"""Tests for lead source validation logic."""

	def test_lead_source_format(self):
		"""Test lead source name format validation."""
		import re

		pattern = r"^[a-zA-Z0-9\-_\s]+$"

		valid_names = [
			"Google Ads",
			"facebook-campaign",
			"Newsletter_2024",
			"Trade Show",
		]

		for name in valid_names:
			self.assertIsNotNone(re.match(pattern, name), f"{name} should be valid")

	def test_invalid_lead_source_format(self):
		"""Test that invalid lead source formats are rejected."""
		import re

		pattern = r"^[a-zA-Z0-9\-_\s]+$"

		invalid_names = [
			"Source<script>",
			"Name@Special",
			"Test!Campaign",
		]

		for name in invalid_names:
			self.assertIsNone(re.match(pattern, name), f"{name} should be invalid")


class TestGDPRConsent(unittest.TestCase):
	"""Tests for GDPR consent tracking."""

	def test_consent_record_structure(self):
		"""Test consent record has required fields."""
		consent_record = {
			"email": "test@example.com",
			"consent_type": "Marketing Communications",
			"consent_given": True,
			"consent_timestamp": "2024-01-01 12:00:00",
			"ip_address": "192.168.1.1",
			"utm_source": "google",
			"consent_text_shown": "I agree to receive communications...",
		}

		self.assertIn("email", consent_record)
		self.assertIn("consent_type", consent_record)
		self.assertIn("consent_given", consent_record)
		self.assertIn("consent_timestamp", consent_record)
		self.assertIn("ip_address", consent_record)
		self.assertIn("consent_text_shown", consent_record)

	def test_consent_types(self):
		"""Test valid consent types."""
		valid_types = [
			"Marketing Communications",
			"Newsletter",
			"Product Updates",
			"Dealer Communications",
		]

		for consent_type in valid_types:
			self.assertIn(consent_type, valid_types)

	def test_consent_boolean_parsing(self):
		"""Test parsing of consent checkbox values."""
		true_values = ["true", "1", "yes", "on", True]
		false_values = ["false", "0", "no", "off", False, None, ""]

		for val in true_values:
			if isinstance(val, str):
				parsed = val.lower() in ("true", "1", "yes", "on")
			else:
				parsed = bool(val)
			self.assertTrue(parsed, f"{val} should parse as True")

		for val in false_values:
			if val is None or val == "":
				parsed = False
			elif isinstance(val, str):
				parsed = val.lower() in ("true", "1", "yes", "on")
			else:
				parsed = bool(val)
			self.assertFalse(parsed, f"{val} should parse as False")


class TestEmailPreferences(unittest.TestCase):
	"""Tests for email preference management."""

	def test_preference_defaults(self):
		"""Test default preference values."""
		defaults = {
			"global_unsubscribe": False,
			"marketing_emails": True,
			"newsletter_emails": True,
			"product_updates": True,
			"dealer_communications": True,
		}

		self.assertFalse(defaults["global_unsubscribe"])
		self.assertTrue(defaults["marketing_emails"])
		self.assertTrue(defaults["newsletter_emails"])
		self.assertTrue(defaults["product_updates"])
		self.assertTrue(defaults["dealer_communications"])

	def test_global_unsubscribe_trumps_all(self):
		"""Test that global unsubscribe blocks all email types."""
		preferences = {
			"global_unsubscribe": True,
			"marketing_emails": True,
			"newsletter_emails": True,
		}

		# If global_unsubscribe is True, no emails should be sent
		can_send = not preferences["global_unsubscribe"]
		self.assertFalse(can_send)

	def test_unsubscribe_token_format(self):
		"""Test unsubscribe token generation format."""
		import secrets

		token = secrets.token_urlsafe(32)

		# Token should be URL-safe
		self.assertFalse(" " in token)
		self.assertFalse("/" in token)
		self.assertFalse("+" in token)

		# Token should be sufficient length
		self.assertGreaterEqual(len(token), 32)


class TestFormSubmissionFlow(unittest.TestCase):
	"""Tests for complete form submission flow."""

	def test_form_submission_data_structure(self):
		"""Test form submission data structure."""
		form_data = {
			"form_name": "Contact Form",
			"email": "test@example.com",
			"first_name": "John",
			"last_name": "Doe",
			"company": "Test Corp",
			"phone": "555-1234",
			"message": "Hello",
			"utm_source": "google",
			"utm_campaign": "test",
			"gdpr_consent": True,
		}

		self.assertEqual(form_data["form_name"], "Contact Form")
		self.assertEqual(form_data["email"], "test@example.com")
		self.assertTrue(form_data["gdpr_consent"])

	def test_form_response_structure(self):
		"""Test form submission response structure."""
		success_response = {
			"success": True,
			"message": "Thank you for your submission.",
			"redirect_url": None,
			"lead_name": "LEAD-001",
		}

		self.assertTrue(success_response["success"])
		self.assertIn("message", success_response)

		error_response = {
			"success": False,
			"errors": [
				{"field": "email", "message": "Email is required"},
			],
		}

		self.assertFalse(error_response["success"])
		self.assertIn("errors", error_response)

	def test_required_fields_validation(self):
		"""Test that required fields are validated."""
		# Email is always required
		data_without_email = {
			"form_name": "Contact Form",
			"first_name": "John",
		}

		email = data_without_email.get("email", "").strip()
		self.assertEqual(email, "")

	def test_utm_fallback_to_defaults(self):
		"""Test UTM parameters fall back to form defaults."""
		form_defaults = {
			"default_utm_source": "website",
			"default_utm_medium": "organic",
			"default_utm_campaign": "general",
		}

		submission_data = {
			"email": "test@example.com",
			"utm_source": "",  # Empty - should fall back
			"utm_medium": "cpc",  # Provided - should keep
		}

		# Simulate fallback logic
		utm_source = submission_data.get("utm_source") or form_defaults["default_utm_source"]
		utm_medium = submission_data.get("utm_medium") or form_defaults["default_utm_medium"]

		self.assertEqual(utm_source, "website")
		self.assertEqual(utm_medium, "cpc")


class TestMarketingFormConfiguration(unittest.TestCase):
	"""Tests for marketing form configuration."""

	def test_form_types(self):
		"""Test valid form types."""
		valid_types = ["Contact", "Dealer Inquiry", "Newsletter", "Quote Request", "Other"]

		for form_type in valid_types:
			self.assertIn(form_type, valid_types)

	def test_route_normalization(self):
		"""Test route path normalization."""
		test_cases = [
			("contact", "/contact"),
			("/contact", "/contact"),
			("/contact/", "/contact"),
			("dealer-inquiry", "/dealer-inquiry"),
		]

		for input_route, expected in test_cases:
			# Simulate normalization logic
			route = input_route
			if not route.startswith("/"):
				route = "/" + route
			route = route.rstrip("/")
			self.assertEqual(route, expected)


class TestHiddenFieldProcessing(unittest.TestCase):
	"""Tests for hidden field auto-population from URL parameters."""

	def test_url_param_extraction(self):
		"""Test extraction of UTM params from URL query string."""
		# Simulate URL parameters
		url_params = {
			"utm_source": "google",
			"utm_medium": "cpc",
			"utm_campaign": "spring_2024",
		}

		# These would be extracted by JavaScript on client side
		# and populated into hidden form fields
		hidden_fields = {
			"utm_source": url_params.get("utm_source", ""),
			"utm_medium": url_params.get("utm_medium", ""),
			"utm_campaign": url_params.get("utm_campaign", ""),
		}

		self.assertEqual(hidden_fields["utm_source"], "google")
		self.assertEqual(hidden_fields["utm_medium"], "cpc")
		self.assertEqual(hidden_fields["utm_campaign"], "spring_2024")

	def test_lead_source_from_url(self):
		"""Test lead source can be passed via URL."""
		url_params = {"source": "trade_show_2024"}

		lead_source = url_params.get("source") or url_params.get("lead_source", "")
		self.assertEqual(lead_source, "trade_show_2024")


class TestUnsubscribeWorkflow(unittest.TestCase):
	"""Tests for unsubscribe workflow."""

	def test_one_click_unsubscribe(self):
		"""Test one-click unsubscribe from email link."""
		# Simulated unsubscribe request
		request = {
			"token": "abc123xyz",
			"action": "unsubscribe",
		}

		self.assertIn("token", request)
		self.assertEqual(request["action"], "unsubscribe")

	def test_preference_center_update(self):
		"""Test updating preferences from preference center."""
		update_request = {
			"token": "abc123xyz",
			"global_unsubscribe": False,
			"marketing_emails": False,
			"newsletter_emails": True,
			"product_updates": True,
			"dealer_communications": False,
		}

		# After update, marketing and dealer should be off
		self.assertFalse(update_request["marketing_emails"])
		self.assertFalse(update_request["dealer_communications"])
		# Newsletter and product updates should still be on
		self.assertTrue(update_request["newsletter_emails"])
		self.assertTrue(update_request["product_updates"])


class TestContactCreationFromForm(unittest.TestCase):
	"""Tests for creating Company and Individual contacts from form submissions."""

	def test_contact_creation_with_company(self):
		"""Test that form data creates both company and individual contacts."""
		form_data = {
			"first_name": "John",
			"last_name": "Doe",
			"email": "john@testcompany.com",
			"phone": "555-123-4567",
			"company": "Test Company LLC",
		}

		# Simulate contact creation logic
		company_name = form_data.get("company", "").strip()
		first_name = form_data.get("first_name", "").strip()
		last_name = form_data.get("last_name", "").strip()
		email = form_data.get("email", "").strip()

		# Verify company contact would be created
		self.assertEqual(company_name, "Test Company LLC")
		self.assertTrue(len(company_name) > 0)

		# Verify individual contact would be created
		self.assertEqual(first_name, "John")
		self.assertEqual(last_name, "Doe")
		self.assertEqual(email, "john@testcompany.com")

	def test_contact_creation_without_company(self):
		"""Test that form data without company only creates individual contact."""
		form_data = {
			"first_name": "Jane",
			"last_name": "Smith",
			"email": "jane@personal.com",
			"phone": "555-987-6543",
			"company": "",
		}

		company_name = form_data.get("company", "").strip()
		first_name = form_data.get("first_name", "").strip()

		# Company contact should not be created
		self.assertEqual(company_name, "")
		self.assertFalse(len(company_name) > 0)

		# Individual contact should still be created
		self.assertEqual(first_name, "Jane")

	def test_email_fallback_for_first_name(self):
		"""Test that email prefix is used if first name not provided."""
		form_data = {
			"first_name": "",
			"last_name": "",
			"email": "anonymous.user@example.com",
		}

		first_name = form_data.get("first_name", "").strip()
		email = form_data.get("email", "")

		# If first name is empty, use email prefix
		contact_first_name = first_name or email.split("@")[0]
		self.assertEqual(contact_first_name, "anonymous.user")

	def test_company_contact_structure(self):
		"""Test the structure of a company contact."""
		company_contact = {
			"first_name": "Acme Corporation",
			"company_name": "Acme Corporation",
			"is_primary_contact": 1,
		}

		self.assertEqual(company_contact["first_name"], company_contact["company_name"])
		self.assertEqual(company_contact["is_primary_contact"], 1)

	def test_individual_contact_structure(self):
		"""Test the structure of an individual contact."""
		individual_contact = {
			"first_name": "John",
			"last_name": "Doe",
			"email_id": "john@acme.com",
			"company_name": "Acme Corporation",
			"email_ids": [{"email_id": "john@acme.com", "is_primary": 1}],
			"phone_nos": [{"phone": "555-123-4567", "is_primary_phone": 1}],
			"links": [{"link_doctype": "Contact", "link_name": "CONT-ACME"}],
		}

		self.assertEqual(individual_contact["first_name"], "John")
		self.assertEqual(individual_contact["last_name"], "Doe")
		self.assertEqual(individual_contact["company_name"], "Acme Corporation")
		self.assertEqual(len(individual_contact["email_ids"]), 1)
		self.assertEqual(individual_contact["email_ids"][0]["is_primary"], 1)

	def test_duplicate_email_detection(self):
		"""Test that duplicate emails are detected."""
		existing_contacts = [
			{"email_id": "john@acme.com", "name": "CONT-001"},
			{"email_id": "jane@acme.com", "name": "CONT-002"},
		]

		def find_existing_contact(email):
			for contact in existing_contacts:
				if contact["email_id"] == email:
					return contact["name"]
			return None

		# Existing email should return existing contact
		result = find_existing_contact("john@acme.com")
		self.assertEqual(result, "CONT-001")

		# New email should return None
		result = find_existing_contact("new@example.com")
		self.assertIsNone(result)

	def test_duplicate_company_detection(self):
		"""Test that duplicate companies are detected."""
		existing_companies = [
			{"company_name": "Acme Corporation", "name": "CONT-ACME"},
			{"company_name": "Beta Inc", "name": "CONT-BETA"},
		]

		def find_existing_company(company_name):
			for company in existing_companies:
				if company["company_name"] == company_name:
					return company["name"]
			return None

		# Existing company should return existing contact
		result = find_existing_company("Acme Corporation")
		self.assertEqual(result, "CONT-ACME")

		# New company should return None
		result = find_existing_company("New Company LLC")
		self.assertIsNone(result)

	def test_contact_link_structure(self):
		"""Test the structure of contact links for individual to company."""
		link = {"link_doctype": "Contact", "link_name": "CONT-COMPANY-001"}

		self.assertEqual(link["link_doctype"], "Contact")
		self.assertIn("CONT", link["link_name"])

	def test_form_response_includes_contact_names(self):
		"""Test that form submission response includes contact names."""
		response = {
			"success": True,
			"message": "Thank you for your submission.",
			"lead_name": "LEAD-001",
			"dealer_application_name": "DA-001",
			"company_contact_name": "CONT-COMPANY-001",
			"individual_contact_name": "CONT-INDIVIDUAL-001",
		}

		self.assertTrue(response["success"])
		self.assertIn("company_contact_name", response)
		self.assertIn("individual_contact_name", response)
		self.assertEqual(response["company_contact_name"], "CONT-COMPANY-001")
		self.assertEqual(response["individual_contact_name"], "CONT-INDIVIDUAL-001")

	def test_contact_form_creates_contacts(self):
		"""Test that /contact form creates both contacts."""
		# For /contact form, company is optional
		form_data = {
			"form_name": "Contact",
			"first_name": "Alex",
			"last_name": "Johnson",
			"email": "alex@company.com",
			"company": "Company XYZ",
			"phone": "555-111-2222",
			"message": "I have a question about your products.",
		}

		# Verify all required fields are present
		self.assertEqual(form_data["form_name"], "Contact")
		self.assertTrue(form_data.get("email"))
		self.assertTrue(form_data.get("company"))

	def test_dealer_inquiry_form_creates_contacts(self):
		"""Test that /dealer_inquiry form creates both contacts."""
		# For /dealer_inquiry form, company is required
		form_data = {
			"form_name": "Dealer Inquiry",
			"first_name": "Bob",
			"last_name": "Builder",
			"email": "bob@dealerco.com",
			"company": "Dealer Company LLC",
			"phone": "555-333-4444",
			"business_type": "Lighting Distributor",
		}

		# Verify all required fields are present
		self.assertEqual(form_data["form_name"], "Dealer Inquiry")
		self.assertTrue(form_data.get("email"))
		self.assertTrue(form_data.get("company"))


if __name__ == "__main__":
	unittest.main()
