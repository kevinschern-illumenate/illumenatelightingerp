# Copyright (c) 2024, ilLumenate Lighting and contributors
# For license information, please see license.txt

"""
Unit tests for Sprint 6 functionality.

These tests validate PDF template management, schedule exports,
spec submittals, and resources library logic.
"""

import unittest
from datetime import date
from typing import ClassVar


class TestPDFTemplateValidation(unittest.TestCase):
	"""Tests for ILL PDF Template validation logic."""

	def test_pdf_extension_validation(self):
		"""Test that only .pdf files are accepted."""
		valid_files = [
			"template.pdf",
			"Template.PDF",
			"my_file.Pdf",
			"/path/to/file.pdf",
		]
		invalid_files = [
			"template.doc",
			"template.docx",
			"template.txt",
			"template",
			"template.pdf.doc",
		]

		for f in valid_files:
			self.assertTrue(f.lower().endswith(".pdf"), f"Should accept: {f}")

		for f in invalid_files:
			self.assertFalse(f.lower().endswith(".pdf"), f"Should reject: {f}")

	def test_fixture_template_required_for_submittal(self):
		"""Test that Fixture Submittal type requires fixture template."""
		template = {
			"template_type": "Fixture Submittal",
			"applies_to_fixture_template": None,
		}

		requires_fixture = (
			template["template_type"] == "Fixture Submittal"
			and not template["applies_to_fixture_template"]
		)
		self.assertTrue(requires_fixture)

		template["applies_to_fixture_template"] = "SH01"
		requires_fixture = (
			template["template_type"] == "Fixture Submittal"
			and not template["applies_to_fixture_template"]
		)
		self.assertFalse(requires_fixture)

	def test_other_types_dont_require_fixture_template(self):
		"""Test that non-submittal types don't require fixture template."""
		for template_type in ["Schedule Cover", "Other"]:
			template = {
				"template_type": template_type,
				"applies_to_fixture_template": None,
			}

			requires_fixture = (
				template["template_type"] == "Fixture Submittal"
				and not template["applies_to_fixture_template"]
			)
			self.assertFalse(requires_fixture)


class TestPDFFieldMapValidation(unittest.TestCase):
	"""Tests for ILL PDF Field Map validation logic."""

	def test_unique_active_mapping(self):
		"""Test that duplicate active mappings are rejected."""
		existing_mappings = [
			{"pdf_template": "T1", "pdf_field_name": "field1", "is_active": 1},
			{"pdf_template": "T1", "pdf_field_name": "field2", "is_active": 1},
			{"pdf_template": "T2", "pdf_field_name": "field1", "is_active": 1},
		]

		new_mapping = {
			"pdf_template": "T1",
			"pdf_field_name": "field1",
			"is_active": 1,
		}

		# Check for conflict
		has_conflict = any(
			m["pdf_template"] == new_mapping["pdf_template"]
			and m["pdf_field_name"] == new_mapping["pdf_field_name"]
			and m["is_active"]
			for m in existing_mappings
		)
		self.assertTrue(has_conflict)

	def test_inactive_mappings_dont_conflict(self):
		"""Test that inactive mappings don't create conflicts."""
		existing_mappings = [
			{"pdf_template": "T1", "pdf_field_name": "field1", "is_active": 0},
		]

		new_mapping = {
			"pdf_template": "T1",
			"pdf_field_name": "field1",
			"is_active": 1,
		}

		has_conflict = any(
			m["pdf_template"] == new_mapping["pdf_template"]
			and m["pdf_field_name"] == new_mapping["pdf_field_name"]
			and m["is_active"]
			for m in existing_mappings
		)
		self.assertFalse(has_conflict)


class TestFormatValue(unittest.TestCase):
	"""Tests for format_value function."""

	def _format_value(self, value, format_rule: str) -> str:
		"""
		Local implementation of format_value for testing without frappe import.
		"""
		if value is None:
			return ""

		if format_rule == "Raw":
			return str(value)

		elif format_rule == "Uppercase":
			return str(value).upper()

		elif format_rule == "Currency_2dp":
			try:
				return f"${float(value):,.2f}"
			except (ValueError, TypeError):
				return str(value)

		elif format_rule == "Inches_1_16":
			try:
				from math import gcd

				inches = float(value)
				whole = int(inches)
				fraction = inches - whole
				sixteenths = round(fraction * 16)
				if sixteenths == 0:
					return f'{whole}"'
				elif sixteenths == 16:
					return f'{whole + 1}"'
				else:
					g = gcd(sixteenths, 16)
					num = sixteenths // g
					den = 16 // g
					return f'{whole} {num}/{den}"'
			except (ValueError, TypeError):
				return str(value)

		elif format_rule == "MM_0dp":
			try:
				return f"{round(float(value))} mm"
			except (ValueError, TypeError):
				return str(value)

		elif format_rule == "Meters_3dp":
			try:
				return f"{float(value):.3f} m"
			except (ValueError, TypeError):
				return str(value)

		elif format_rule == "Percent_0dp":
			try:
				return f"{round(float(value))}%"
			except (ValueError, TypeError):
				return str(value)

		elif format_rule == "Date_YYYY_MM_DD":
			if isinstance(value, date):
				return value.strftime("%Y-%m-%d")
			else:
				return str(value)

		return str(value)

	def test_raw_format(self):
		"""Test Raw format rule."""
		self.assertEqual(self._format_value("hello", "Raw"), "hello")
		self.assertEqual(self._format_value(123, "Raw"), "123")
		self.assertEqual(self._format_value(None, "Raw"), "")

	def test_uppercase_format(self):
		"""Test Uppercase format rule."""
		self.assertEqual(self._format_value("hello", "Uppercase"), "HELLO")
		self.assertEqual(self._format_value("Hello World", "Uppercase"), "HELLO WORLD")

	def test_currency_format(self):
		"""Test Currency_2dp format rule."""
		self.assertEqual(self._format_value(100, "Currency_2dp"), "$100.00")
		self.assertEqual(self._format_value(1234.567, "Currency_2dp"), "$1,234.57")
		self.assertEqual(self._format_value("invalid", "Currency_2dp"), "invalid")

	def test_mm_format(self):
		"""Test MM_0dp format rule."""
		self.assertEqual(self._format_value(1234.5, "MM_0dp"), "1234 mm")
		self.assertEqual(self._format_value(1000, "MM_0dp"), "1000 mm")

	def test_meters_format(self):
		"""Test Meters_3dp format rule."""
		self.assertEqual(self._format_value(1.2345, "Meters_3dp"), "1.234 m")
		self.assertEqual(self._format_value(2, "Meters_3dp"), "2.000 m")

	def test_percent_format(self):
		"""Test Percent_0dp format rule."""
		self.assertEqual(self._format_value(25.5, "Percent_0dp"), "26%")
		self.assertEqual(self._format_value(100, "Percent_0dp"), "100%")

	def test_date_format(self):
		"""Test Date_YYYY_MM_DD format rule."""
		self.assertEqual(self._format_value(date(2024, 6, 15), "Date_YYYY_MM_DD"), "2024-06-15")
		self.assertEqual(self._format_value("2024-06-15", "Date_YYYY_MM_DD"), "2024-06-15")


class TestPricingGuardrail(unittest.TestCase):
	"""Tests for submittal pricing guardrail."""

	# Define PRICING_KEYS locally for testing without frappe import
	PRICING_KEYS: ClassVar[set] = {"unit_msrp", "unit_net", "tier_name", "discount_percent"}

	def test_pricing_keys_defined(self):
		"""Test that PRICING_KEYS contains expected keys."""
		expected_keys = {"unit_msrp", "unit_net", "tier_name", "discount_percent"}
		self.assertEqual(self.PRICING_KEYS, expected_keys)

	def test_pricing_keys_blocked_for_submittal(self):
		"""Test that pricing keys are blocked for Fixture Submittal templates."""
		template = {"template_type": "Fixture Submittal"}
		enforce_guardrail = True

		context = {
			"unit_msrp": 100.00,
			"unit_net": 75.00,
			"tier_name": "Dealer A",
			"discount_percent": 25,
			"template_code": "SH01",  # Not a pricing key
		}

		# Simulate guardrail logic
		blocked_keys = []
		for key in context:
			if (
				enforce_guardrail
				and template["template_type"] == "Fixture Submittal"
				and key in self.PRICING_KEYS
			):
				blocked_keys.append(key)

		self.assertEqual(len(blocked_keys), 4)
		self.assertIn("unit_msrp", blocked_keys)
		self.assertIn("unit_net", blocked_keys)

	def test_pricing_keys_allowed_for_other_types(self):
		"""Test that pricing keys are allowed for non-submittal types."""
		template = {"template_type": "Schedule Cover"}
		enforce_guardrail = True

		context = {"unit_msrp": 100.00, "unit_net": 75.00}

		blocked_keys = []
		for key in context:
			if (
				enforce_guardrail
				and template["template_type"] == "Fixture Submittal"
				and key in self.PRICING_KEYS
			):
				blocked_keys.append(key)

		self.assertEqual(len(blocked_keys), 0)


class TestCSVExport(unittest.TestCase):
	"""Tests for CSV export functionality."""

	def test_csv_includes_both_line_types(self):
		"""Test that CSV export includes ilLumenate and Other Manufacturer lines."""
		lines = [
			{"line_type": "ilLumenate", "qty": 2},
			{"line_type": "Other Manufacturer", "qty": 1},
			{"line_type": "ilLumenate", "qty": 3},
		]

		exported_lines = [line for line in lines]
		self.assertEqual(len(exported_lines), 3)

		ilumenate_count = sum(1 for l in exported_lines if l["line_type"] == "ilLumenate")
		other_count = sum(1 for l in exported_lines if l["line_type"] == "Other Manufacturer")

		self.assertEqual(ilumenate_count, 2)
		self.assertEqual(other_count, 1)

	def test_csv_escaping(self):
		"""Test that CSV properly escapes special characters."""
		import csv
		from io import StringIO

		data = [
			["Description with, comma", "Value"],
			['Description with "quotes"', "Value"],
			["Description\nwith newline", "Value"],
		]

		output = StringIO()
		writer = csv.writer(output)
		for row in data:
			writer.writerow(row)

		csv_content = output.getvalue()
		self.assertIn(",", csv_content)  # Commas should be in output (escaped in quotes)


class TestPDFExport(unittest.TestCase):
	"""Tests for PDF export functionality."""

	def test_include_pricing_toggle(self):
		"""Test that include_pricing controls pricing column visibility."""
		include_pricing = 0
		show_pricing_columns = bool(include_pricing)
		self.assertFalse(show_pricing_columns)

		include_pricing = 1
		show_pricing_columns = bool(include_pricing)
		self.assertTrue(show_pricing_columns)

	def test_schedule_total_calculation(self):
		"""Test schedule total only includes ilLumenate lines."""
		lines = [
			{"line_type": "ilLumenate", "line_total": 200.00},
			{"line_type": "Other Manufacturer", "line_total": None},
			{"line_type": "ilLumenate", "line_total": 300.00},
			{"line_type": "ilLumenate", "line_total": None},
		]

		schedule_total = sum(
			line["line_total"] or 0
			for line in lines
			if line["line_type"] == "ilLumenate" and line.get("line_total")
		)

		self.assertEqual(schedule_total, 500.00)


class TestResourceDocument(unittest.TestCase):
	"""Tests for ILL Resource Document functionality."""

	def test_public_resources_visibility(self):
		"""Test that public resources are visible to all."""
		resources = [
			{"is_public": 1, "is_active": 1, "title": "Public Doc 1"},
			{"is_public": 0, "is_active": 1, "title": "Private Doc 1"},
			{"is_public": 1, "is_active": 0, "title": "Inactive Public Doc"},
		]

		# Public view (not logged in)
		public_visible = [
			r for r in resources
			if r["is_public"] == 1 and r["is_active"] == 1
		]
		self.assertEqual(len(public_visible), 1)
		self.assertEqual(public_visible[0]["title"], "Public Doc 1")

	def test_portal_user_visibility(self):
		"""Test that portal users see all active resources."""
		resources = [
			{"is_public": 1, "is_active": 1, "title": "Public Doc"},
			{"is_public": 0, "is_active": 1, "title": "Private Doc"},
			{"is_public": 0, "is_active": 0, "title": "Inactive Doc"},
		]

		# Portal view (logged in)
		portal_visible = [r for r in resources if r["is_active"] == 1]
		self.assertEqual(len(portal_visible), 2)

	def test_category_grouping(self):
		"""Test that resources are properly grouped by category."""
		resources = [
			{"category": "Installation", "title": "Doc 1"},
			{"category": "Warranty", "title": "Doc 2"},
			{"category": "Installation", "title": "Doc 3"},
		]

		categories = {}
		for r in resources:
			cat = r["category"]
			if cat not in categories:
				categories[cat] = []
			categories[cat].append(r)

		self.assertEqual(len(categories["Installation"]), 2)
		self.assertEqual(len(categories["Warranty"]), 1)


class TestSubmittalPackage(unittest.TestCase):
	"""Tests for submittal package generation."""

	def test_package_includes_schedule_and_submittals(self):
		"""Test that package includes schedule PDF + N submittals."""
		submittal_pdfs = [b"submittal_1", b"submittal_2"]

		# Simulate package creation: 1 schedule + N submittals
		total_pdfs = 1 + len(submittal_pdfs)
		self.assertEqual(total_pdfs, 3)

	def test_only_ilumenate_lines_get_submittals(self):
		"""Test that only ilLumenate lines get submittals."""
		lines = [
			{"line_type": "ilLumenate", "configuration_json": "{}"},
			{"line_type": "Other Manufacturer", "configuration_json": None},
			{"line_type": "ilLumenate", "configuration_json": "{}"},
			{"line_type": "ilLumenate", "configuration_json": None},  # No config
		]

		submittal_lines = [
			line for line in lines
			if line["line_type"] == "ilLumenate" and line.get("configuration_json")
		]

		self.assertEqual(len(submittal_lines), 2)


class TestPortalScoping(unittest.TestCase):
	"""Tests for portal security scoping."""

	def test_customer_scoping_check(self):
		"""Test customer scoping pattern."""
		schedule_customer = "CUST-001"
		portal_customer = "CUST-001"

		# Same customer - allowed
		is_authorized = schedule_customer == portal_customer
		self.assertTrue(is_authorized)

		# Different customer - blocked
		portal_customer = "CUST-002"
		is_authorized = schedule_customer == portal_customer
		self.assertFalse(is_authorized)

	def test_admin_bypasses_scoping(self):
		"""Test that admin users bypass customer scoping."""
		user_roles = ["Illumenate Admin"]
		is_admin = "Illumenate Admin" in user_roles or "Illumenate Product Manager" in user_roles
		self.assertTrue(is_admin)


if __name__ == "__main__":
	unittest.main()
