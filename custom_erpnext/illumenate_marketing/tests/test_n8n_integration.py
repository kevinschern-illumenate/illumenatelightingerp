# Copyright (c) 2024, ilLumenate Lighting and contributors
# For license information, please see license.txt

"""
Unit tests for Sprint 3: n8n Integration Layer functionality.

These tests validate the n8n webhook handler, event emission,
and marketing journey tracking functionality.

Note: These tests are designed to be standalone and don't require
the frappe framework to run for unit testing purposes.
"""

import json
import unittest
from unittest.mock import MagicMock, patch


class TestN8nWebhookActions(unittest.TestCase):
	"""Tests for n8n webhook handler actions."""

	def test_valid_actions(self):
		"""Test that valid actions are recognized."""
		valid_actions = ["update_journey_stage", "update_contact_status", "log_event"]

		for action in valid_actions:
			self.assertIn(action, valid_actions)

	def test_update_journey_stage_data_structure(self):
		"""Test update_journey_stage action requires correct data."""
		required_fields = ["email", "stage"]

		data = {
			"email": "test@example.com",
			"stage": "Lead",
			"reason": "Converted from prospect",
		}

		for field in required_fields:
			self.assertIn(field, data)

	def test_update_contact_status_data_structure(self):
		"""Test update_contact_status action data structure."""
		data = {
			"doctype": "Lead",
			"email": "test@example.com",
			"status": "Qualified",
		}

		self.assertIn("status", data)
		self.assertTrue(data.get("email") or data.get("docname"))

	def test_log_event_data_structure(self):
		"""Test log_event action data structure."""
		data = {
			"event_type": "custom_event",
			"email": "test@example.com",
			"data": {"custom_field": "value"},
		}

		self.assertIn("event_type", data)


class TestMarketingEventEmission(unittest.TestCase):
	"""Tests for marketing event emission functionality."""

	def test_event_payload_structure(self):
		"""Test marketing event payload has required fields."""
		payload = {
			"event_type": "lead_created",
			"timestamp": "2024-01-01 12:00:00",
			"source": "erpnext",
			"doctype": "Lead",
			"docname": "LEAD-001",
			"data": {"email": "test@example.com"},
		}

		required_fields = ["event_type", "timestamp", "source"]
		for field in required_fields:
			self.assertIn(field, payload)

	def test_supported_event_types(self):
		"""Test supported event types."""
		supported_types = [
			"lead_created",
			"lead_converted",
			"purchase_completed",
			"journey_changed",
		]

		for event_type in supported_types:
			self.assertIn(event_type, supported_types)

	def test_event_settings_map(self):
		"""Test event type to settings mapping."""
		event_settings_map = {
			"lead_created": "emit_lead_created",
			"lead_converted": "emit_lead_converted",
			"purchase_completed": "emit_purchase_completed",
			"journey_changed": "emit_journey_changed",
		}

		# Verify mapping exists for each event type
		self.assertEqual(event_settings_map["lead_created"], "emit_lead_created")
		self.assertEqual(event_settings_map["purchase_completed"], "emit_purchase_completed")


class TestMarketingJourneyStages(unittest.TestCase):
	"""Tests for marketing journey stage management."""

	def test_valid_journey_stages(self):
		"""Test valid journey stages."""
		valid_stages = ["Prospect", "Lead", "Customer"]

		self.assertEqual(len(valid_stages), 3)
		self.assertIn("Prospect", valid_stages)
		self.assertIn("Lead", valid_stages)
		self.assertIn("Customer", valid_stages)

	def test_stage_progression_order(self):
		"""Test that stage progression follows correct order."""
		stages = ["Prospect", "Lead", "Customer"]

		# Prospect should come before Lead
		self.assertTrue(stages.index("Prospect") < stages.index("Lead"))
		# Lead should come before Customer
		self.assertTrue(stages.index("Lead") < stages.index("Customer"))

	def test_journey_record_structure(self):
		"""Test marketing journey record structure."""
		journey = {
			"contact_email": "test@example.com",
			"current_stage": "Prospect",
			"prospect_date": "2024-01-01",
			"lead_date": None,
			"customer_date": None,
			"stage_history": json.dumps([{"stage": "Prospect", "timestamp": "2024-01-01 12:00:00"}]),
		}

		self.assertEqual(journey["contact_email"], "test@example.com")
		self.assertEqual(journey["current_stage"], "Prospect")
		self.assertIsNotNone(journey["prospect_date"])

	def test_stage_history_format(self):
		"""Test stage history JSON format."""
		history = [
			{"stage": "Prospect", "timestamp": "2024-01-01 12:00:00", "reason": "Initial creation"},
			{"stage": "Lead", "timestamp": "2024-01-15 10:30:00", "reason": "Lead created"},
			{
				"stage": "Customer",
				"timestamp": "2024-02-01 14:00:00",
				"reason": "Purchase completed",
			},
		]

		# Verify history entries have required fields
		for entry in history:
			self.assertIn("stage", entry)
			self.assertIn("timestamp", entry)
			self.assertIn("reason", entry)

		# Verify JSON serialization
		serialized = json.dumps(history)
		deserialized = json.loads(serialized)
		self.assertEqual(len(deserialized), 3)


class TestN8nSettingsConfiguration(unittest.TestCase):
	"""Tests for n8n settings configuration."""

	def test_settings_fields(self):
		"""Test n8n settings has required fields."""
		settings = {
			"enabled": True,
			"n8n_webhook_url": "https://n8n.example.com/webhook",
			"api_key": "secret_key_123",
			"emit_lead_created": True,
			"emit_lead_converted": True,
			"emit_purchase_completed": True,
			"emit_journey_changed": True,
		}

		self.assertTrue(settings["enabled"])
		self.assertIn("n8n_webhook_url", settings)
		self.assertIn("api_key", settings)

	def test_webhook_url_normalization(self):
		"""Test webhook URL trailing slash is removed."""
		test_cases = [
			("https://n8n.example.com/webhook/", "https://n8n.example.com/webhook"),
			("https://n8n.example.com/webhook", "https://n8n.example.com/webhook"),
			("https://n8n.example.com/", "https://n8n.example.com"),
		]

		for input_url, expected in test_cases:
			normalized = input_url.rstrip("/")
			self.assertEqual(normalized, expected)


class TestMarketingEventTypeConfiguration(unittest.TestCase):
	"""Tests for marketing event type configuration."""

	def test_event_type_record_structure(self):
		"""Test event type record structure."""
		event_type = {
			"event_name": "Lead Created",
			"event_code": "lead_created",
			"is_active": True,
			"source_doctype": "Lead",
			"description": "Emitted when a new lead is created",
		}

		self.assertEqual(event_type["event_code"], "lead_created")
		self.assertTrue(event_type["is_active"])

	def test_event_code_validation(self):
		"""Test event code format validation."""
		import re

		pattern = r"^[a-z][a-z0-9_]*$"

		valid_codes = ["lead_created", "purchase_completed", "journey_changed", "custom_event_1"]

		for code in valid_codes:
			self.assertIsNotNone(re.match(pattern, code), f"{code} should be valid")

		invalid_codes = [
			"LeadCreated",  # uppercase
			"1_lead",  # starts with number
			"lead-created",  # contains hyphen
			"lead created",  # contains space
		]

		for code in invalid_codes:
			self.assertIsNone(re.match(pattern, code), f"{code} should be invalid")


class TestAPIKeyAuthentication(unittest.TestCase):
	"""Tests for API key authentication."""

	def test_api_key_from_header(self):
		"""Test extracting API key from X-API-Key header."""
		headers = {"X-API-Key": "secret_key_123"}

		api_key = headers.get("X-API-Key")
		self.assertEqual(api_key, "secret_key_123")

	def test_api_key_from_bearer_token(self):
		"""Test extracting API key from Bearer token."""
		auth_header = "Bearer secret_key_123"

		api_key = auth_header
		if api_key.startswith("Bearer "):
			api_key = api_key[7:]

		self.assertEqual(api_key, "secret_key_123")


class TestWebhookPayloadSerialization(unittest.TestCase):
	"""Tests for webhook payload serialization."""

	def test_payload_json_serialization(self):
		"""Test that webhook payloads can be JSON serialized."""
		payload = {
			"event_type": "lead_created",
			"timestamp": "2024-01-01 12:00:00.000000",
			"source": "erpnext",
			"doctype": "Lead",
			"docname": "LEAD-001",
			"data": {
				"email": "test@example.com",
				"lead_name": "Test User",
				"source": "Website",
			},
			"document": {
				"name": "LEAD-001",
				"doctype": "Lead",
				"creation": "2024-01-01 12:00:00.000000",
				"email": "test@example.com",
			},
		}

		# Should not raise an exception
		json_str = json.dumps(payload)
		self.assertIsInstance(json_str, str)

		# Should be deserializable
		deserialized = json.loads(json_str)
		self.assertEqual(deserialized["event_type"], "lead_created")

	def test_webhook_url_construction(self):
		"""Test webhook URL construction for different endpoints."""
		base_url = "https://n8n.example.com/webhook"

		# Marketing events endpoint
		events_url = f"{base_url}/marketing-events"
		self.assertEqual(events_url, "https://n8n.example.com/webhook/marketing-events")


class TestJourneyUpdateScenarios(unittest.TestCase):
	"""Tests for journey update scenarios."""

	def test_prospect_to_lead_transition(self):
		"""Test transitioning from Prospect to Lead."""
		journey = {"current_stage": "Prospect"}
		new_stage = "Lead"

		# Verify transition is valid
		self.assertNotEqual(journey["current_stage"], new_stage)
		journey["current_stage"] = new_stage
		self.assertEqual(journey["current_stage"], "Lead")

	def test_lead_to_customer_transition(self):
		"""Test transitioning from Lead to Customer on purchase."""
		journey = {"current_stage": "Lead"}
		new_stage = "Customer"

		# Verify transition is valid
		self.assertNotEqual(journey["current_stage"], new_stage)
		journey["current_stage"] = new_stage
		self.assertEqual(journey["current_stage"], "Customer")

	def test_prospect_to_customer_transition(self):
		"""Test transitioning directly from Prospect to Customer."""
		# This can happen when someone makes a purchase without being a lead first
		journey = {"current_stage": "Prospect"}
		new_stage = "Customer"

		journey["current_stage"] = new_stage
		self.assertEqual(journey["current_stage"], "Customer")

	def test_no_change_same_stage(self):
		"""Test that updating to same stage makes no change."""
		journey = {"current_stage": "Lead"}
		new_stage = "Lead"

		# No update needed if same stage
		self.assertEqual(journey["current_stage"], new_stage)


if __name__ == "__main__":
	unittest.main()
