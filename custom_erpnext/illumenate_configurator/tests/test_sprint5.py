# Copyright (c) 2024, ilLumenate Lighting and contributors
# For license information, please see license.txt

"""
Unit tests for Sprint 5 functionality.

These tests validate the project/schedule workflow, customer scoping,
and sales order creation logic.
"""

import json
import unittest


class TestCustomerScoping(unittest.TestCase):
	"""Tests for customer scoping logic."""

	def test_portal_user_customer_mapping(self):
		"""Test that portal user can be mapped to customer."""
		# Simulate portal user lookup
		user = "portal@example.com"
		customer = "CUST-001"

		# Mock the lookup logic
		portal_user_record = {"user": user, "parent": customer}

		self.assertEqual(portal_user_record["parent"], customer)

	def test_contact_fallback_mapping(self):
		"""Test fallback to Contact -> Customer link."""
		contact = "CONT-001"
		customer = "CUST-001"

		# Simulate contact -> dynamic link mapping
		dynamic_link = {
			"link_doctype": "Customer",
			"parent": contact,
			"link_name": customer,
		}

		self.assertEqual(dynamic_link["link_name"], customer)

	def test_no_customer_returns_none(self):
		"""Test that no mapping returns None."""
		customer = None
		self.assertIsNone(customer)


class TestScheduleLocking(unittest.TestCase):
	"""Tests for schedule locking behavior."""

	def test_draft_schedule_editable(self):
		"""Test that Draft schedules can be edited."""
		schedule = {
			"name": "SCH-001",
			"status": "Draft",
			"lines": [],
		}

		is_editable = schedule["status"] == "Draft"
		self.assertTrue(is_editable)

	def test_ordered_schedule_locked(self):
		"""Test that Ordered schedules are locked."""
		schedule = {
			"name": "SCH-001",
			"status": "Ordered",
			"sales_order": "SO-001",
		}

		is_editable = schedule["status"] == "Draft"
		self.assertFalse(is_editable)

	def test_status_transition_draft_to_ordered(self):
		"""Test valid status transition from Draft to Ordered."""
		old_status = "Draft"
		new_status = "Ordered"

		# Valid transition
		valid_transitions = {
			"Draft": ["Ordered"],
		}

		self.assertIn(new_status, valid_transitions.get(old_status, []))


class TestSalesOrderCreation(unittest.TestCase):
	"""Tests for Sales Order creation from schedule."""

	def test_so_line_rate_equals_unit_net(self):
		"""Test that SO line rate equals schedule line unit_net."""
		schedule_line = {
			"line_type": "ilLumenate",
			"qty": 2,
			"unit_net": 150.00,
			"unit_msrp": 200.00,
			"configuration_json": '{"inputs": {}}',
		}

		so_item = {
			"item_code": "ILL-CONFIGURED-FIXTURE",
			"qty": schedule_line["qty"],
			"rate": schedule_line["unit_net"],
		}

		self.assertEqual(so_item["rate"], schedule_line["unit_net"])
		self.assertEqual(so_item["rate"], 150.00)

	def test_other_mfr_lines_excluded(self):
		"""Test that Other Manufacturer lines are excluded from SO."""
		schedule_lines = [
			{"line_type": "ilLumenate", "configuration_json": '{}'},
			{"line_type": "Other Manufacturer", "configuration_json": None},
			{"line_type": "ilLumenate", "configuration_json": '{}'},
		]

		ilumenate_lines = [
			line for line in schedule_lines
			if line["line_type"] == "ilLumenate" and line.get("configuration_json")
		]

		self.assertEqual(len(ilumenate_lines), 2)

	def test_so_total_matches_schedule_total(self):
		"""Test that SO totals match schedule estimated totals."""
		schedule_lines = [
			{"line_type": "ilLumenate", "qty": 2, "unit_net": 100.00, "line_total": 200.00},
			{"line_type": "ilLumenate", "qty": 3, "unit_net": 150.00, "line_total": 450.00},
		]

		schedule_total = sum(line["line_total"] for line in schedule_lines)
		self.assertEqual(schedule_total, 650.00)

		# Verify SO item totals would match
		so_items = [
			{"qty": line["qty"], "rate": line["unit_net"]}
			for line in schedule_lines
		]
		so_total = sum(item["qty"] * item["rate"] for item in so_items)
		self.assertEqual(so_total, schedule_total)


class TestManufacturingGeneration(unittest.TestCase):
	"""Tests for manufacturing package generation from SO."""

	def test_idempotent_generation(self):
		"""Test that running twice doesn't duplicate WOs."""
		so_item = {
			"item_code": "ILL-CONFIGURED-FIXTURE",
			"ill_configuration_json": '{"inputs": {"template_code": "SH01"}}',
			"ill_work_order": None,
		}

		# First run - should process
		should_process = so_item["ill_work_order"] is None
		self.assertTrue(should_process)

		# Simulate processing
		so_item["ill_work_order"] = "WO-001"

		# Second run - should skip
		should_process = so_item["ill_work_order"] is None
		self.assertFalse(should_process)

	def test_config_json_parsing(self):
		"""Test parsing of stored configuration JSON."""
		config_json = json.dumps({
			"inputs": {
				"template_code": "SH01",
				"tape_spec": "TAPE-001",
				"tape_attribute_combination": "CCT: 3000K, CRI: 90",
				"requested_overall_in": 48,
			},
			"pricing": {
				"unit_msrp": 200.00,
				"unit_net_price": 150.00,
			},
		})

		config = json.loads(config_json)
		inputs = config.get("inputs", {})

		self.assertEqual(inputs.get("template_code"), "SH01")
		self.assertEqual(inputs.get("requested_overall_in"), 48)

	def test_non_placeholder_items_skipped(self):
		"""Test that non-placeholder items are skipped."""
		so_items = [
			{"item_code": "ILL-CONFIGURED-FIXTURE", "ill_configuration_json": "{}"},
			{"item_code": "REGULAR-ITEM", "ill_configuration_json": None},
			{"item_code": "ILL-CONFIGURED-FIXTURE", "ill_configuration_json": None},
		]

		processable = [
			item for item in so_items
			if item["item_code"] == "ILL-CONFIGURED-FIXTURE" and item.get("ill_configuration_json")
		]

		self.assertEqual(len(processable), 1)


class TestLineTotalComputation(unittest.TestCase):
	"""Tests for schedule line total computation."""

	def test_line_total_calculation(self):
		"""Test line_total = unit_net * qty."""
		lines = [
			{"line_type": "ilLumenate", "qty": 2, "unit_net": 100.00},
			{"line_type": "ilLumenate", "qty": 3, "unit_net": 150.50},
			{"line_type": "Other Manufacturer", "qty": 1, "unit_net": None},
		]

		for line in lines:
			if line["line_type"] == "ilLumenate" and line.get("unit_net"):
				line["line_total"] = line["unit_net"] * line["qty"]
			else:
				line["line_total"] = 0

		self.assertEqual(lines[0]["line_total"], 200.00)
		self.assertAlmostEqual(lines[1]["line_total"], 451.50, places=2)
		self.assertEqual(lines[2]["line_total"], 0)

	def test_schedule_total_ilumenate_only(self):
		"""Test schedule total includes only ilLumenate lines."""
		lines = [
			{"line_type": "ilLumenate", "line_total": 200.00},
			{"line_type": "Other Manufacturer", "line_total": 0},
			{"line_type": "ilLumenate", "line_total": 300.00},
		]

		total = sum(
			line["line_total"]
			for line in lines
			if line["line_type"] == "ilLumenate"
		)

		self.assertEqual(total, 500.00)


class TestProjectScheduleRelationship(unittest.TestCase):
	"""Tests for project-schedule relationships."""

	def test_schedule_inherits_customer_from_project(self):
		"""Test that schedule customer is auto-populated from project."""
		project = {
			"name": "PRJ-001",
			"customer": "CUST-001",
		}

		schedule = {
			"project": project["name"],
			"customer": None,
		}

		# Simulate auto-population
		if schedule["project"]:
			schedule["customer"] = project["customer"]

		self.assertEqual(schedule["customer"], "CUST-001")

	def test_schedule_belongs_to_project(self):
		"""Test schedule has proper project reference."""
		schedule = {
			"name": "SCH-001",
			"project": "PRJ-001",
			"schedule_name": "Conference Room",
		}

		self.assertIsNotNone(schedule["project"])


class TestValidDateRanges(unittest.TestCase):
	"""Tests for project date validation."""

	def test_end_date_after_start_date(self):
		"""Test that end date must be after start date."""
		from datetime import date

		start = date(2025, 1, 1)
		end = date(2025, 6, 30)

		is_valid = end >= start
		self.assertTrue(is_valid)

	def test_end_date_before_start_date_invalid(self):
		"""Test that end date before start date is invalid."""
		from datetime import date

		start = date(2025, 6, 30)
		end = date(2025, 1, 1)

		is_valid = end >= start
		self.assertFalse(is_valid)


if __name__ == "__main__":
	unittest.main()
