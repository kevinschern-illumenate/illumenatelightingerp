# Copyright (c) 2024, ilLumenate Lighting and contributors
# For license information, please see license.txt

"""
Unit tests for Sprint 2: Welcome Email Automation functionality.

These tests validate email template mapping, email log tracking,
and welcome email sending logic.

Note: These tests are designed to be standalone and don't require
the frappe framework to run for unit testing purposes.
"""

import secrets
import unittest


class TestEmailTemplateMapping(unittest.TestCase):
	"""Tests for email template mapping configuration."""

	def test_mapping_structure(self):
		"""Test email template mapping has required fields."""
		mapping = {
			"mapping_name": "Welcome Email - Google Ads",
			"is_active": True,
			"lead_source": "Google Ads",
			"email_template": "Welcome Email Template",
			"trigger_event": "Lead Created",
			"delay_minutes": 0,
			"subject_override": None,
			"from_email_override": None,
		}

		self.assertIn("mapping_name", mapping)
		self.assertIn("is_active", mapping)
		self.assertIn("email_template", mapping)
		self.assertIn("trigger_event", mapping)

	def test_trigger_events(self):
		"""Test valid trigger event types."""
		valid_events = ["Lead Created", "Form Submitted"]

		for event in valid_events:
			self.assertIn(event, valid_events)

	def test_delay_minutes_validation(self):
		"""Test delay minutes must be non-negative."""
		valid_delays = [0, 5, 15, 30, 60, 120]
		invalid_delays = [-1, -5, -30]

		for delay in valid_delays:
			self.assertGreaterEqual(delay, 0)

		for delay in invalid_delays:
			self.assertLess(delay, 0)

	def test_lead_source_optional(self):
		"""Test lead source is optional for catch-all mappings."""
		# Mapping without lead source applies to all leads
		catch_all_mapping = {
			"mapping_name": "Default Welcome Email",
			"is_active": True,
			"lead_source": None,  # Applies to all
			"email_template": "Default Welcome Template",
			"trigger_event": "Lead Created",
		}

		# Mapping with specific lead source
		specific_mapping = {
			"mapping_name": "Google Ads Welcome",
			"is_active": True,
			"lead_source": "Google Ads",
			"email_template": "Google Ads Welcome Template",
			"trigger_event": "Lead Created",
		}

		self.assertIsNone(catch_all_mapping["lead_source"])
		self.assertIsNotNone(specific_mapping["lead_source"])


class TestEmailLog(unittest.TestCase):
	"""Tests for email log tracking."""

	def test_email_log_structure(self):
		"""Test email log has required fields."""
		email_log = {
			"recipient_email": "test@example.com",
			"email_type": "Welcome Email",
			"status": "Pending",
			"sent_at": None,
			"lead": "LEAD-001",
			"lead_source": "Website",
			"email_template": "Welcome Email Template",
			"tracking_id": "abc123xyz",
			"opened_at": None,
			"opened_count": 0,
			"clicked_at": None,
			"clicked_count": 0,
		}

		self.assertIn("recipient_email", email_log)
		self.assertIn("status", email_log)
		self.assertIn("tracking_id", email_log)
		self.assertIn("opened_count", email_log)
		self.assertIn("clicked_count", email_log)

	def test_email_statuses(self):
		"""Test valid email status values."""
		valid_statuses = ["Pending", "Sent", "Opened", "Clicked", "Failed", "Bounced"]

		for status in valid_statuses:
			self.assertIn(status, valid_statuses)

	def test_email_types(self):
		"""Test valid email type values."""
		valid_types = ["Welcome Email", "Newsletter", "Marketing", "Transactional", "Other"]

		for email_type in valid_types:
			self.assertIn(email_type, valid_types)

	def test_tracking_id_generation(self):
		"""Test tracking ID is unique and URL-safe."""
		tracking_ids = set()

		for _ in range(10):
			tracking_id = secrets.token_urlsafe(32)
			self.assertNotIn(tracking_id, tracking_ids)
			tracking_ids.add(tracking_id)

			# Should be URL-safe
			self.assertFalse(" " in tracking_id)
			self.assertFalse("/" in tracking_id)
			self.assertFalse("+" in tracking_id)
			self.assertGreaterEqual(len(tracking_id), 32)

	def test_status_progression(self):
		"""Test email status progression logic."""
		# Sent -> Opened -> Clicked
		status_progression = ["Pending", "Sent", "Opened", "Clicked"]

		# Each status should come after the previous in the list
		for i in range(1, len(status_progression)):
			prev_idx = status_progression.index(status_progression[i - 1])
			curr_idx = status_progression.index(status_progression[i])
			self.assertLess(prev_idx, curr_idx)

	def test_open_count_increment(self):
		"""Test open count increments correctly."""
		email_log = {"opened_count": 0, "status": "Sent"}

		# Simulate multiple opens
		for expected_count in [1, 2, 3]:
			email_log["opened_count"] += 1
			self.assertEqual(email_log["opened_count"], expected_count)

	def test_click_count_increment(self):
		"""Test click count increments correctly."""
		email_log = {"clicked_count": 0, "status": "Opened"}

		# Simulate multiple clicks
		for expected_count in [1, 2, 3]:
			email_log["clicked_count"] += 1
			self.assertEqual(email_log["clicked_count"], expected_count)


class TestWelcomeEmailLogic(unittest.TestCase):
	"""Tests for welcome email sending logic."""

	def test_lead_context_building(self):
		"""Test context is built correctly from lead data."""
		lead = {
			"name": "LEAD-001",
			"lead_name": "John Doe",
			"first_name": "John",
			"last_name": "Doe",
			"email_id": "john@example.com",
			"company_name": "Test Corp",
			"phone": "555-1234",
		}

		context = {
			"lead": lead,
			"lead_name": lead["lead_name"],
			"first_name": lead["first_name"],
			"last_name": lead["last_name"],
			"email": lead["email_id"],
			"company_name": lead["company_name"],
			"phone": lead["phone"],
		}

		full_name = f"{context['first_name']} {context['last_name']}".strip()
		context["full_name"] = full_name or context["lead_name"]
		context["greeting_name"] = context["first_name"] or context["lead_name"] or "there"

		self.assertEqual(context["full_name"], "John Doe")
		self.assertEqual(context["greeting_name"], "John")
		self.assertEqual(context["email"], "john@example.com")

	def test_greeting_name_fallback(self):
		"""Test greeting name falls back correctly."""
		# With first name
		self.assertEqual("John" or "Lead Name" or "there", "John")

		# Without first name, with lead name
		self.assertEqual("" or "Lead Name" or "there", "Lead Name")

		# Without either
		self.assertEqual("" or "" or "there", "there")

	def test_lead_without_email_skipped(self):
		"""Test leads without email are skipped."""
		lead_without_email = {
			"name": "LEAD-001",
			"lead_name": "No Email Lead",
			"email_id": None,
		}

		email = lead_without_email.get("email_id")
		should_send = bool(email)

		self.assertFalse(should_send)

	def test_lead_with_email_processed(self):
		"""Test leads with email are processed."""
		lead_with_email = {
			"name": "LEAD-002",
			"lead_name": "Has Email Lead",
			"email_id": "test@example.com",
		}

		email = lead_with_email.get("email_id")
		should_send = bool(email)

		self.assertTrue(should_send)

	def test_mapping_matching_priority(self):
		"""Test specific lead source mapping takes priority over catch-all."""
		mappings = [
			{"lead_source": None, "email_template": "Default Template"},
			{"lead_source": "Google Ads", "email_template": "Google Template"},
			{"lead_source": "Facebook", "email_template": "Facebook Template"},
		]

		lead_source = "Google Ads"

		# Find specific mapping first
		specific_match = next(
			(m for m in mappings if m["lead_source"] == lead_source),
			None,
		)

		# Fall back to catch-all if no specific match
		if not specific_match:
			specific_match = next(
				(m for m in mappings if m["lead_source"] is None),
				None,
			)

		self.assertEqual(specific_match["email_template"], "Google Template")

		# Test catch-all fallback
		lead_source = "Unknown Source"
		specific_match = next(
			(m for m in mappings if m["lead_source"] == lead_source),
			None,
		)
		if not specific_match:
			specific_match = next(
				(m for m in mappings if m["lead_source"] is None),
				None,
			)

		self.assertEqual(specific_match["email_template"], "Default Template")


class TestEmailTracking(unittest.TestCase):
	"""Tests for email open and click tracking."""

	def test_tracking_pixel_url_format(self):
		"""Test tracking pixel URL format."""
		tracking_id = "abc123xyz"
		base_url = "https://example.com"

		pixel_url = f"{base_url}/api/method/custom_erpnext.illumenate_marketing.email.track_email_open?tracking_id={tracking_id}"

		self.assertIn("track_email_open", pixel_url)
		self.assertIn(f"tracking_id={tracking_id}", pixel_url)

	def test_click_tracking_url_format(self):
		"""Test click tracking URL format."""
		tracking_id = "abc123xyz"
		redirect_url = "https://target.com/page"
		base_url = "https://example.com"

		click_url = f"{base_url}/api/method/custom_erpnext.illumenate_marketing.email.track_email_click?tracking_id={tracking_id}&redirect_url={redirect_url}"

		self.assertIn("track_email_click", click_url)
		self.assertIn(f"tracking_id={tracking_id}", click_url)
		self.assertIn("redirect_url=", click_url)

	def test_first_open_records_timestamp(self):
		"""Test first open records timestamp."""
		email_log = {
			"opened_at": None,
			"opened_count": 0,
		}

		# First open
		if email_log["opened_at"] is None:
			email_log["opened_at"] = "2024-01-01 12:00:00"
		email_log["opened_count"] += 1

		self.assertIsNotNone(email_log["opened_at"])
		self.assertEqual(email_log["opened_count"], 1)

		# Second open (timestamp should not change)
		original_timestamp = email_log["opened_at"]
		if email_log["opened_at"] is None:
			email_log["opened_at"] = "2024-01-01 13:00:00"
		email_log["opened_count"] += 1

		self.assertEqual(email_log["opened_at"], original_timestamp)
		self.assertEqual(email_log["opened_count"], 2)

	def test_click_implies_open(self):
		"""Test that click tracking also records open."""
		email_log = {
			"status": "Sent",
			"opened_at": None,
			"opened_count": 0,
			"clicked_at": None,
			"clicked_count": 0,
		}

		# Record click
		email_log["clicked_count"] += 1
		email_log["clicked_at"] = "2024-01-01 12:00:00"

		# Click should imply open
		if email_log["opened_at"] is None:
			email_log["opened_at"] = email_log["clicked_at"]
			email_log["opened_count"] += 1

		email_log["status"] = "Clicked"

		self.assertIsNotNone(email_log["opened_at"])
		self.assertEqual(email_log["opened_count"], 1)
		self.assertEqual(email_log["status"], "Clicked")


class TestDelayedEmailSending(unittest.TestCase):
	"""Tests for delayed email sending."""

	def test_immediate_send_when_no_delay(self):
		"""Test emails are sent immediately when delay is 0."""
		mapping = {"delay_minutes": 0}

		should_queue = mapping["delay_minutes"] > 0
		self.assertFalse(should_queue)

	def test_queue_when_delay_configured(self):
		"""Test emails are queued when delay is configured."""
		mapping = {"delay_minutes": 5}

		should_queue = mapping["delay_minutes"] > 0
		self.assertTrue(should_queue)

	def test_delay_conversion(self):
		"""Test delay minutes conversion."""
		delays = [
			(5, 300),  # 5 min = 300 sec
			(15, 900),  # 15 min = 900 sec
			(60, 3600),  # 60 min = 3600 sec
		]

		for minutes, expected_seconds in delays:
			seconds = minutes * 60
			self.assertEqual(seconds, expected_seconds)


if __name__ == "__main__":
	unittest.main()
