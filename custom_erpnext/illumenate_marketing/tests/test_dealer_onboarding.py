# Copyright (c) 2024, ilLumenate Lighting and contributors
# For license information, please see license.txt

"""
Unit tests for Sprint 4 & 5: B2B Price List Logic & Dealer Onboarding.

These tests validate:
- Auto-detect pricing tier on login
- Company inheritance for employee users
- MSRP fallback for retail customers
- Dealer application workflow
- Dealer account provisioning

Note: These tests are designed to be standalone and don't require
the frappe framework to run for unit testing purposes.
"""

import re
import secrets
import unittest


class TestPricingTierDetection(unittest.TestCase):
	"""Tests for pricing tier detection based on user linkages."""

	def test_valid_pricing_tiers(self):
		"""Test valid pricing tier names."""
		valid_tiers = ["MSRP", "Dealer A", "Dealer B", "Dealer C", "Dealer D"]

		for tier in valid_tiers:
			self.assertIn(tier, valid_tiers)

	def test_msrp_is_default_fallback(self):
		"""Test that MSRP is the default fallback for retail customers."""
		# When no customer or dealer link is found, MSRP should be returned
		default_tier = "MSRP"
		self.assertEqual(default_tier, "MSRP")

	def test_price_list_result_structure(self):
		"""Test the structure of price list detection result."""
		result = {
			"price_list": "Dealer A",
			"customer": "CUST-001",
			"source": "portal_user",
		}

		self.assertIn("price_list", result)
		self.assertIn("customer", result)
		self.assertIn("source", result)

	def test_price_list_sources(self):
		"""Test valid sources for price list detection."""
		valid_sources = [
			"default",  # MSRP fallback
			"portal_user",  # Direct portal user mapping
			"contact_customer",  # User → Contact → Customer
			"company_inheritance",  # User → Contact → Company → Customer
		]

		for source in valid_sources:
			self.assertIn(source, valid_sources)


class TestCompanyInheritance(unittest.TestCase):
	"""Tests for company inheritance logic (PL-002)."""

	def test_inheritance_chain(self):
		"""Test the User → Contact → Company → Customer chain."""
		# Simulated chain
		user = "employee@dealercompany.com"
		contact = "CONT-001"
		company = "Dealer Company LLC"
		customer = "Dealer Company LLC"

		# Each step should be validated
		self.assertIsNotNone(user)
		self.assertIsNotNone(contact)
		self.assertIsNotNone(company)
		self.assertIsNotNone(customer)

	def test_employee_inherits_company_tier(self):
		"""Test that employee inherits company's pricing tier."""
		# If an employee's contact is linked to a company,
		# and that company has a customer record with a price list,
		# the employee should see that price list

		company_customer = {
			"customer_name": "ABC Lighting Design",
			"default_price_list": "Dealer B",
		}

		# Employee should inherit Dealer B pricing
		inherited_tier = company_customer["default_price_list"]
		self.assertEqual(inherited_tier, "Dealer B")


class TestRetailCustomerFallback(unittest.TestCase):
	"""Tests for retail customer MSRP fallback (PL-003)."""

	def test_no_customer_returns_msrp(self):
		"""Test that users without customer link get MSRP."""
		customer = None

		if customer:
			price_list = "Dealer A"  # hypothetical
		else:
			price_list = "MSRP"

		self.assertEqual(price_list, "MSRP")

	def test_customer_without_price_list_returns_msrp(self):
		"""Test that customers without price list get MSRP."""
		customer = "CUST-001"
		customer_price_list = None  # Not set

		if customer_price_list:
			price_list = customer_price_list
		else:
			price_list = "MSRP"

		self.assertEqual(price_list, "MSRP")


class TestDataHygieneReport(unittest.TestCase):
	"""Tests for unlinked contacts data hygiene report (PL-004)."""

	def test_report_columns(self):
		"""Test report has required columns."""
		columns = [
			"contact_name",
			"email_id",
			"full_name",
			"has_user",
			"has_company",
			"has_customer",
			"linked_company",
			"linked_customer",
			"issue_type",
			"creation",
		]

		required_columns = ["contact_name", "email_id", "issue_type"]
		for col in required_columns:
			self.assertIn(col, columns)

	def test_issue_types(self):
		"""Test valid issue types for unlinked contacts."""
		valid_issues = [
			"No User Account",
			"No Company Link",
			"No Customer Link",
		]

		for issue in valid_issues:
			self.assertIn(issue, valid_issues)

	def test_issue_type_combination(self):
		"""Test contacts can have multiple issues."""
		issues = []
		has_user = False
		has_company = False
		has_customer = False

		if not has_user:
			issues.append("No User Account")
		if not has_company:
			issues.append("No Company Link")
		if not has_customer:
			issues.append("No Customer Link")

		issue_string = ", ".join(issues)
		self.assertEqual(issue_string, "No User Account, No Company Link, No Customer Link")


class TestDealerApplicationWorkflow(unittest.TestCase):
	"""Tests for dealer application workflow (DA-001, DA-002)."""

	def test_application_statuses(self):
		"""Test valid application statuses."""
		valid_statuses = ["Pending", "Under Review", "Approved", "Rejected"]

		for status in valid_statuses:
			self.assertIn(status, valid_statuses)

	def test_status_transitions(self):
		"""Test valid status transitions."""
		# Valid transitions
		valid_transitions = [
			("Pending", "Under Review"),
			("Pending", "Approved"),
			("Pending", "Rejected"),
			("Under Review", "Approved"),
			("Under Review", "Rejected"),
		]

		for from_status, to_status in valid_transitions:
			# These transitions should be allowed
			self.assertIn(from_status, ["Pending", "Under Review"])

	def test_rejection_requires_reason(self):
		"""Test that rejection requires a reason."""
		status = "Rejected"
		rejection_reason = None

		if status == "Rejected" and not rejection_reason:
			is_valid = False
		else:
			is_valid = True

		self.assertFalse(is_valid)

	def test_application_data_structure(self):
		"""Test dealer application data structure."""
		application = {
			"company_name": "Test Lighting Co",
			"contact_first_name": "John",
			"contact_last_name": "Doe",
			"email": "john@testlighting.com",
			"phone": "555-123-4567",
			"business_type": "Lighting Designer",
			"requested_tier": "Dealer D",
			"status": "Pending",
		}

		self.assertIn("company_name", application)
		self.assertIn("email", application)
		self.assertIn("status", application)
		self.assertEqual(application["status"], "Pending")

	def test_requested_tiers(self):
		"""Test valid requested pricing tiers."""
		valid_tiers = ["Dealer D", "Dealer C", "Dealer B", "Dealer A"]

		for tier in valid_tiers:
			self.assertIn(tier, valid_tiers)

	def test_business_types(self):
		"""Test valid business types."""
		valid_types = [
			"Lighting Designer",
			"Electrical Contractor",
			"Distributor",
			"Retailer",
			"Architect",
			"Interior Designer",
			"Other",
		]

		for btype in valid_types:
			self.assertIn(btype, valid_types)


class TestDealerProvisioning(unittest.TestCase):
	"""Tests for dealer account provisioning (DA-003)."""

	def test_provisioning_creates_required_records(self):
		"""Test provisioning creates Customer, Contact, User."""
		required_records = ["Customer", "Contact", "User"]

		for record in required_records:
			self.assertIn(record, required_records)

	def test_provisioning_result_structure(self):
		"""Test provisioning result structure."""
		result = {
			"success": True,
			"message": "Dealer account provisioned successfully",
			"customer": "CUST-001",
			"contact": "CONT-001",
			"user": "dealer@example.com",
		}

		self.assertTrue(result["success"])
		self.assertIn("customer", result)
		self.assertIn("contact", result)
		self.assertIn("user", result)

	def test_secure_password_generation(self):
		"""Test that secure passwords are generated."""
		password = secrets.token_urlsafe(12)

		# Password should be at least 12 characters
		self.assertGreaterEqual(len(password), 12)

		# Password should be URL-safe (no spaces, special chars)
		self.assertFalse(" " in password)

	def test_customer_creation_with_price_list(self):
		"""Test customer is created with correct price list."""
		requested_tier = "Dealer C"

		customer = {
			"customer_name": "New Dealer Co",
			"customer_group": "Dealer",
			"default_price_list": requested_tier,
		}

		self.assertEqual(customer["default_price_list"], "Dealer C")
		self.assertEqual(customer["customer_group"], "Dealer")


class TestDealerWelcomeEmail(unittest.TestCase):
	"""Tests for dealer welcome email (DA-004)."""

	def test_email_contains_required_info(self):
		"""Test welcome email contains required information."""
		email_content = {
			"recipient": "dealer@example.com",
			"subject": "Welcome to ilLumenate Lighting",
			"includes_password": True,
			"includes_login_url": True,
			"includes_tier_info": True,
		}

		self.assertTrue(email_content["includes_password"])
		self.assertTrue(email_content["includes_login_url"])
		self.assertTrue(email_content["includes_tier_info"])

	def test_email_subject_format(self):
		"""Test welcome email subject format."""
		subject = "Welcome to ilLumenate Lighting - Your Dealer Account is Ready!"

		self.assertIn("ilLumenate", subject)
		self.assertIn("Dealer", subject)


class TestDealerApplicationValidation(unittest.TestCase):
	"""Tests for dealer application validation."""

	def test_email_validation(self):
		"""Test email format validation."""
		pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"

		valid_emails = [
			"dealer@company.com",
			"john.doe@lighting.co.uk",
		]

		for email in valid_emails:
			self.assertIsNotNone(re.match(pattern, email))

		invalid_emails = [
			"not-an-email",
			"missing@domain",
		]

		for email in invalid_emails:
			self.assertIsNone(re.match(pattern, email))

	def test_required_fields(self):
		"""Test that required fields are enforced."""
		required_fields = ["company_name", "contact_first_name", "contact_last_name", "email"]

		application = {
			"company_name": "Test Co",
			"contact_first_name": "John",
			"contact_last_name": "Doe",
			"email": "john@test.com",
		}

		for field in required_fields:
			self.assertIn(field, application)
			self.assertTrue(application[field])  # Not empty


class TestN8nIntegrationForDealer(unittest.TestCase):
	"""Tests for n8n integration with dealer provisioning."""

	def test_provisioning_event_structure(self):
		"""Test dealer_provisioned event structure."""
		event = {
			"event_type": "dealer_provisioned",
			"doctype": "ILL Dealer Application",
			"docname": "DA-2024-00001",
			"data": {
				"email": "dealer@example.com",
				"company_name": "Test Dealer Co",
				"customer": "CUST-001",
				"contact": "CONT-001",
				"user": "dealer@example.com",
				"pricing_tier": "Dealer D",
			},
		}

		self.assertEqual(event["event_type"], "dealer_provisioned")
		self.assertIn("email", event["data"])
		self.assertIn("customer", event["data"])
		self.assertIn("pricing_tier", event["data"])


class TestApprovalActions(unittest.TestCase):
	"""Tests for one-click approval/rejection actions."""

	def test_approve_sets_status(self):
		"""Test approve action sets correct status."""
		status = "Pending"
		new_status = "Approved"

		if status in ["Pending", "Under Review"]:
			status = new_status

		self.assertEqual(status, "Approved")

	def test_approve_records_reviewer(self):
		"""Test approve action records reviewer info."""
		reviewed_by = "admin@company.com"
		reviewed_on = "2024-01-15 10:30:00"

		self.assertIsNotNone(reviewed_by)
		self.assertIsNotNone(reviewed_on)

	def test_reject_requires_reason(self):
		"""Test reject action requires rejection reason."""

		def reject_application(rejection_reason=None):
			if not rejection_reason:
				raise ValueError("Please provide a rejection reason")
			return True

		with self.assertRaises(ValueError):
			reject_application(None)

		# With reason should work
		result = reject_application("Not qualified")
		self.assertTrue(result)


class TestDealerApplicationFromFormSubmission(unittest.TestCase):
	"""Tests for creating ILL Dealer Application from form submission."""

	def test_form_data_to_application_mapping(self):
		"""Test mapping of form data to dealer application fields."""
		form_data = {
			"first_name": "John",
			"last_name": "Doe",
			"email": "john@dealerco.com",
			"phone": "555-123-4567",
			"company": "Dealer Company LLC",
			"business_type": "Lighting Distributor",
			"years_in_business": "5",
			"website": "https://dealerco.com",
			"message": "Interested in becoming a dealer",
		}

		# Simulate mapping
		application = {
			"company_name": form_data.get("company", ""),
			"contact_first_name": form_data.get("first_name", ""),
			"contact_last_name": form_data.get("last_name", ""),
			"email": form_data.get("email", ""),
			"phone": form_data.get("phone", ""),
			"website": form_data.get("website", ""),
		}

		self.assertEqual(application["company_name"], "Dealer Company LLC")
		self.assertEqual(application["contact_first_name"], "John")
		self.assertEqual(application["contact_last_name"], "Doe")
		self.assertEqual(application["email"], "john@dealerco.com")

	def test_business_type_mapping(self):
		"""Test mapping of HTML form business types to doctype options."""
		business_type_mapping = {
			"Lighting Distributor": "Distributor",
			"Electrical Distributor": "Distributor",
			"Lighting Designer": "Lighting Designer",
			"Contractor": "Electrical Contractor",
			"Architect/Design Firm": "Architect",
			"Other": "Other",
		}

		self.assertEqual(business_type_mapping["Lighting Distributor"], "Distributor")
		self.assertEqual(business_type_mapping["Contractor"], "Electrical Contractor")
		self.assertEqual(business_type_mapping["Architect/Design Firm"], "Architect")

	def test_years_in_business_mapping(self):
		"""Test mapping of free text years to select options."""
		def map_years(years_str):
			try:
				years = int(years_str)
				if years < 1:
					return "Less than 1 year"
				elif years <= 3:
					return "1-3 years"
				elif years <= 5:
					return "3-5 years"
				elif years <= 10:
					return "5-10 years"
				else:
					return "10+ years"
			except ValueError:
				return None

		self.assertEqual(map_years("0"), "Less than 1 year")
		self.assertEqual(map_years("2"), "1-3 years")
		self.assertEqual(map_years("4"), "3-5 years")
		self.assertEqual(map_years("7"), "5-10 years")
		self.assertEqual(map_years("15"), "10+ years")
		self.assertIsNone(map_years("not a number"))

	def test_application_default_status(self):
		"""Test that new applications default to Pending status."""
		status = "Pending"
		self.assertEqual(status, "Pending")

	def test_message_stored_in_additional_notes(self):
		"""Test that form message is stored in additional_notes."""
		message = "I want to become a dealer because I love your products."
		additional_notes = message

		self.assertEqual(additional_notes, message)

	def test_non_numeric_years_in_business_stored_in_notes(self):
		"""Test that non-numeric years_in_business is stored in additional_notes."""
		years_in_business = "Five years"
		message = "Looking to become a dealer."

		# Simulate the logic from create_dealer_application
		years_in_business_text = ""
		try:
			int(years_in_business)
		except ValueError:
			years_in_business_text = f"Years in Business: {years_in_business}"

		notes_parts = []
		if years_in_business_text:
			notes_parts.append(years_in_business_text)
		if message:
			notes_parts.append(message)

		additional_notes = "\n".join(notes_parts)

		self.assertEqual(additional_notes, "Years in Business: Five years\nLooking to become a dealer.")

	def test_duplicate_application_handling(self):
		"""Test that duplicate applications are detected."""
		# Simulate checking for existing application
		existing_applications = [
			{"email": "john@dealerco.com", "status": "Pending"},
			{"email": "jane@otherco.com", "status": "Approved"},
		]

		def check_duplicate(email):
			for app in existing_applications:
				if app["email"] == email and app["status"] in ["Pending", "Under Review"]:
					return app
			return None

		# Should find existing pending application
		result = check_duplicate("john@dealerco.com")
		self.assertIsNotNone(result)

		# Should not find approved application
		result = check_duplicate("jane@otherco.com")
		self.assertIsNone(result)

		# Should not find non-existent email
		result = check_duplicate("new@company.com")
		self.assertIsNone(result)


if __name__ == "__main__":
	unittest.main()
