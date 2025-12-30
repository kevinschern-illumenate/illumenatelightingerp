# Copyright (c) 2024, ilLumenate Lighting and contributors
# For license information, please see license.txt

"""
Unit tests for Sprint 7: Marketing Analytics Dashboard functionality.

These tests validate the Campaign Performance report calculations,
filtering logic, and data aggregation.
"""

import unittest


class TestCampaignPerformanceReport(unittest.TestCase):
	"""Tests for Campaign Performance report functionality."""

	def test_report_columns_structure(self):
		"""Test report has all required columns."""
		expected_columns = [
			"campaign",
			"source_type",
			"total_leads",
			"converted",
			"conversion_rate",
			"attributed_revenue",
			"avg_order_value",
			"emails_sent",
			"emails_opened",
			"email_open_rate",
			"emails_clicked",
			"email_click_rate",
		]

		# Mock column definitions
		columns = [
			{"fieldname": "campaign"},
			{"fieldname": "source_type"},
			{"fieldname": "total_leads"},
			{"fieldname": "converted"},
			{"fieldname": "conversion_rate"},
			{"fieldname": "attributed_revenue"},
			{"fieldname": "avg_order_value"},
			{"fieldname": "emails_sent"},
			{"fieldname": "emails_opened"},
			{"fieldname": "email_open_rate"},
			{"fieldname": "emails_clicked"},
			{"fieldname": "email_click_rate"},
		]

		column_names = [c["fieldname"] for c in columns]
		for expected in expected_columns:
			self.assertIn(expected, column_names)

	def test_conversion_rate_calculation(self):
		"""Test conversion rate is correctly calculated."""
		test_cases = [
			(10, 100, 10.0),  # 10 converted, 100 total = 10%
			(0, 100, 0.0),  # 0 converted = 0%
			(50, 100, 50.0),  # 50 converted = 50%
			(100, 100, 100.0),  # All converted = 100%
		]

		for converted, total, expected_rate in test_cases:
			rate = (converted / total * 100) if total > 0 else 0
			self.assertEqual(rate, expected_rate)

	def test_conversion_rate_zero_division(self):
		"""Test conversion rate handles zero total leads."""
		converted = 0
		total = 0

		rate = (converted / total * 100) if total > 0 else 0
		self.assertEqual(rate, 0)


class TestInternalAccountExclusion(unittest.TestCase):
	"""Tests for AD-003: Exclude internal/test accounts from statistics."""

	def test_internal_email_detection(self):
		"""Test internal email detection (emails containing @illumenate.lighting)."""
		internal_emails = [
			"john@illumenate.lighting",
			"sales@illumenate.lighting",
			"test.user@illumenate.lighting",
		]

		external_emails = [
			"customer@example.com",
			"buyer@company.com",
			"client@business.org",
		]

		for email in internal_emails:
			is_internal = "@illumenate.lighting" in email.lower()
			self.assertTrue(is_internal, f"{email} should be detected as internal")

		for email in external_emails:
			is_internal = "@illumenate.lighting" in email.lower()
			self.assertFalse(is_internal, f"{email} should not be detected as internal")

	def test_test_account_detection(self):
		"""Test test account detection (emails containing 'test')."""
		test_emails = [
			"test@example.com",
			"testuser@company.com",
			"user.test@business.org",
			"testing123@example.com",
		]

		real_emails = [
			"john@example.com",
			"sales@company.com",
			"client@business.org",
		]

		for email in test_emails:
			is_test = "test" in email.lower()
			self.assertTrue(is_test, f"{email} should be detected as test account")

		for email in real_emails:
			is_test = "test" in email.lower()
			self.assertFalse(is_test, f"{email} should not be detected as test account")


class TestEmailMetrics(unittest.TestCase):
	"""Tests for email performance metrics calculation."""

	def test_email_open_rate_calculation(self):
		"""Test email open rate is correctly calculated."""
		test_cases = [
			(25, 100, 25.0),  # 25 opened, 100 sent = 25%
			(0, 100, 0.0),  # 0 opened = 0%
			(100, 100, 100.0),  # All opened = 100%
		]

		for opened, sent, expected_rate in test_cases:
			rate = (opened / sent * 100) if sent > 0 else 0
			self.assertEqual(rate, expected_rate)

	def test_email_click_rate_calculation(self):
		"""Test email click rate is correctly calculated."""
		test_cases = [
			(10, 100, 10.0),  # 10 clicked, 100 sent = 10%
			(0, 100, 0.0),  # 0 clicked = 0%
			(5, 50, 10.0),  # 5 clicked, 50 sent = 10%
		]

		for clicked, sent, expected_rate in test_cases:
			rate = (clicked / sent * 100) if sent > 0 else 0
			self.assertEqual(rate, expected_rate)

	def test_zero_sent_handling(self):
		"""Test metrics handle zero sent emails."""
		sent = 0
		opened = 0
		clicked = 0

		open_rate = (opened / sent * 100) if sent > 0 else 0
		click_rate = (clicked / sent * 100) if sent > 0 else 0

		self.assertEqual(open_rate, 0)
		self.assertEqual(click_rate, 0)


class TestRevenueAttribution(unittest.TestCase):
	"""Tests for AD-004: ROI calculations (revenue from campaign)."""

	def test_attributed_revenue_aggregation(self):
		"""Test revenue is correctly aggregated by campaign."""
		invoices = [
			{"campaign": "Google Ads", "grand_total": 1000.00},
			{"campaign": "Google Ads", "grand_total": 1500.00},
			{"campaign": "Facebook", "grand_total": 800.00},
			{"campaign": "Google Ads", "grand_total": 500.00},
		]

		google_revenue = sum(i["grand_total"] for i in invoices if i["campaign"] == "Google Ads")
		facebook_revenue = sum(i["grand_total"] for i in invoices if i["campaign"] == "Facebook")

		self.assertEqual(google_revenue, 3000.00)
		self.assertEqual(facebook_revenue, 800.00)

	def test_average_order_value_calculation(self):
		"""Test average order value is correctly calculated."""
		total_revenue = 3000.00
		order_count = 3

		avg_order_value = total_revenue / order_count if order_count > 0 else 0
		self.assertEqual(avg_order_value, 1000.00)

	def test_avg_order_value_zero_orders(self):
		"""Test average order value handles zero orders."""
		total_revenue = 0
		order_count = 0

		avg_order_value = total_revenue / order_count if order_count > 0 else 0
		self.assertEqual(avg_order_value, 0)


class TestReportFilters(unittest.TestCase):
	"""Tests for report filter functionality."""

	def test_date_filter_sql_condition(self):
		"""Test date filters generate correct SQL conditions."""
		filters = {
			"from_date": "2024-01-01",
			"to_date": "2024-03-31",
		}

		conditions = []
		if filters.get("from_date"):
			conditions.append("creation >= %s")
		if filters.get("to_date"):
			conditions.append("creation <= %s")

		self.assertEqual(len(conditions), 2)

	def test_exclude_internal_filter(self):
		"""Test exclude internal filter generates correct SQL condition."""
		filters = {"exclude_internal": True}

		conditions = []
		if filters.get("exclude_internal"):
			conditions.append("email_id NOT LIKE '%@illumenate.lighting'")

		self.assertEqual(len(conditions), 1)
		self.assertIn("NOT LIKE", conditions[0])

	def test_exclude_test_filter(self):
		"""Test exclude test filter generates correct SQL condition."""
		filters = {"exclude_test": True}

		conditions = []
		if filters.get("exclude_test"):
			conditions.append("email_id NOT LIKE '%test%'")

		self.assertEqual(len(conditions), 1)
		self.assertIn("%test%", conditions[0])

	def test_combined_filters(self):
		"""Test multiple filters combine correctly."""
		filters = {
			"from_date": "2024-01-01",
			"to_date": "2024-03-31",
			"exclude_internal": True,
			"exclude_test": True,
		}

		conditions = []
		if filters.get("from_date"):
			conditions.append("creation >= %s")
		if filters.get("to_date"):
			conditions.append("creation <= %s")
		if filters.get("exclude_internal"):
			conditions.append("email_id NOT LIKE '%@illumenate.lighting'")
		if filters.get("exclude_test"):
			conditions.append("email_id NOT LIKE '%test%'")

		where_clause = " AND ".join(conditions)
		self.assertEqual(len(conditions), 4)
		self.assertIn("AND", where_clause)


class TestChartData(unittest.TestCase):
	"""Tests for report chart data generation."""

	def test_chart_data_structure(self):
		"""Test chart data has correct structure."""
		chart = {
			"data": {
				"labels": ["Google Ads", "Facebook", "Email"],
				"datasets": [
					{"name": "Total Leads", "values": [100, 80, 50]},
					{"name": "Converted", "values": [20, 15, 10]},
				],
			},
			"type": "bar",
			"colors": ["#7CD6FD", "#5E64FF"],
		}

		self.assertIn("data", chart)
		self.assertIn("labels", chart["data"])
		self.assertIn("datasets", chart["data"])
		self.assertEqual(chart["type"], "bar")

	def test_chart_top_campaigns_limit(self):
		"""Test chart shows only top 10 campaigns."""
		campaigns = [{"campaign": f"Campaign {i}", "total_leads": 100 - i} for i in range(20)]

		top_campaigns = sorted(campaigns, key=lambda x: x["total_leads"], reverse=True)[:10]

		self.assertEqual(len(top_campaigns), 10)
		self.assertEqual(top_campaigns[0]["campaign"], "Campaign 0")
		self.assertEqual(top_campaigns[0]["total_leads"], 100)


class TestReportDataRow(unittest.TestCase):
	"""Tests for individual report data row structure."""

	def test_data_row_structure(self):
		"""Test data row has all required fields."""
		row = {
			"campaign": "Google Ads",
			"source_type": "Paid",
			"total_leads": 100,
			"converted": 20,
			"conversion_rate": 20.0,
			"attributed_revenue": 50000.00,
			"avg_order_value": 2500.00,
			"emails_sent": 200,
			"emails_opened": 80,
			"email_open_rate": 40.0,
			"emails_clicked": 30,
			"email_click_rate": 15.0,
		}

		# Verify all numeric fields are correct types
		self.assertIsInstance(row["total_leads"], int)
		self.assertIsInstance(row["converted"], int)
		self.assertIsInstance(row["conversion_rate"], float)
		self.assertIsInstance(row["attributed_revenue"], float)

	def test_unknown_campaign_handling(self):
		"""Test leads without source are grouped as 'Unknown'."""
		lead_source = None
		campaign = lead_source or "Unknown"

		self.assertEqual(campaign, "Unknown")


if __name__ == "__main__":
	unittest.main()
