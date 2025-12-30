# Copyright (c) 2024, ilLumenate Lighting and contributors
# For license information, please see license.txt

"""
Campaign Performance Marketing Report

This report provides marketing campaign performance metrics including:
- Total leads by campaign/source
- Conversion rates (Lead → Customer)
- Attributed revenue
- ROI calculations (when campaign cost is available)

Sprint 7: Marketing Analytics Dashboard (AD-001 to AD-004)
"""

import frappe
from frappe import _


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart_data(data)
	return columns, data, None, chart


def get_columns():
	return [
		{
			"fieldname": "campaign",
			"label": _("Campaign/Source"),
			"fieldtype": "Link",
			"options": "ILL Lead Source",
			"width": 200,
		},
		{
			"fieldname": "source_type",
			"label": _("Source Type"),
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"fieldname": "total_leads",
			"label": _("Total Leads"),
			"fieldtype": "Int",
			"width": 100,
		},
		{
			"fieldname": "converted",
			"label": _("Converted"),
			"fieldtype": "Int",
			"width": 100,
		},
		{
			"fieldname": "conversion_rate",
			"label": _("Conversion Rate %"),
			"fieldtype": "Percent",
			"width": 120,
		},
		{
			"fieldname": "attributed_revenue",
			"label": _("Attributed Revenue"),
			"fieldtype": "Currency",
			"width": 150,
		},
		{
			"fieldname": "avg_order_value",
			"label": _("Avg Order Value"),
			"fieldtype": "Currency",
			"width": 130,
		},
		{
			"fieldname": "emails_sent",
			"label": _("Emails Sent"),
			"fieldtype": "Int",
			"width": 100,
		},
		{
			"fieldname": "emails_opened",
			"label": _("Emails Opened"),
			"fieldtype": "Int",
			"width": 100,
		},
		{
			"fieldname": "email_open_rate",
			"label": _("Open Rate %"),
			"fieldtype": "Percent",
			"width": 100,
		},
		{
			"fieldname": "emails_clicked",
			"label": _("Emails Clicked"),
			"fieldtype": "Int",
			"width": 100,
		},
		{
			"fieldname": "email_click_rate",
			"label": _("Click Rate %"),
			"fieldtype": "Percent",
			"width": 100,
		},
	]


def get_data(filters):
	"""
	Aggregate lead and conversion data by campaign/source.

	Implements the following user stories:
	- AD-001: Email campaign performance
	- AD-002: Leads by source/campaign with conversion rates
	- AD-003: Exclude internal/test accounts from statistics
	- AD-004: ROI calculations (revenue from campaign)
	"""
	if filters is None:
		filters = {}

	conditions = []
	params = []

	# Date filters
	if filters.get("from_date"):
		conditions.append("l.creation >= %s")
		params.append(filters.get("from_date"))

	if filters.get("to_date"):
		conditions.append("l.creation <= %s")
		params.append(filters.get("to_date"))

	# Exclude internal accounts (emails containing @illumenate.lighting)
	if filters.get("exclude_internal"):
		conditions.append("l.email_id NOT LIKE '%@illumenate.lighting'")

	# Exclude test accounts (emails containing 'test')
	if filters.get("exclude_test"):
		conditions.append("l.email_id NOT LIKE '%test%'")

	where_clause = " AND ".join(conditions) if conditions else "1=1"

	# Main query for lead metrics by source
	lead_data = frappe.db.sql(
		f"""
		SELECT
			COALESCE(ls.source_name, l.source, 'Unknown') AS campaign,
			COALESCE(ls.source_type, 'Other') AS source_type,
			COUNT(DISTINCT l.name) AS total_leads,
			SUM(CASE WHEN l.status = 'Converted' THEN 1 ELSE 0 END) AS converted
		FROM `tabLead` l
		LEFT JOIN `tabILL Lead Source` ls ON l.source = ls.name
		WHERE {where_clause}
		GROUP BY COALESCE(ls.source_name, l.source, 'Unknown'), COALESCE(ls.source_type, 'Other')
		ORDER BY COUNT(DISTINCT l.name) DESC
		""",
		tuple(params),
		as_dict=True,
	)

	data = []

	for row in lead_data:
		campaign = row.get("campaign")

		# Calculate conversion rate
		total = row.get("total_leads", 0) or 0
		converted = row.get("converted", 0) or 0
		conversion_rate = (converted / total * 100) if total > 0 else 0

		# Get attributed revenue from converted leads
		revenue_data = get_attributed_revenue(campaign, filters)

		# Get email performance metrics
		email_data = get_email_metrics(campaign, filters)

		data.append(
			{
				"campaign": campaign,
				"source_type": row.get("source_type"),
				"total_leads": total,
				"converted": converted,
				"conversion_rate": round(conversion_rate, 2),
				"attributed_revenue": revenue_data.get("total_revenue", 0),
				"avg_order_value": revenue_data.get("avg_order_value", 0),
				"emails_sent": email_data.get("sent", 0),
				"emails_opened": email_data.get("opened", 0),
				"email_open_rate": email_data.get("open_rate", 0),
				"emails_clicked": email_data.get("clicked", 0),
				"email_click_rate": email_data.get("click_rate", 0),
			}
		)

	return data


def get_attributed_revenue(campaign, filters):
	"""
	Calculate revenue attributed to a campaign source.

	This queries Sales Invoices for customers that were converted from
	leads with the given source.
	"""
	conditions = []
	params = [campaign]

	if filters.get("from_date"):
		conditions.append("si.posting_date >= %s")
		params.append(filters.get("from_date"))

	if filters.get("to_date"):
		conditions.append("si.posting_date <= %s")
		params.append(filters.get("to_date"))

	date_condition = " AND ".join(conditions) if conditions else "1=1"

	# Get revenue from customers that came from leads with this source
	result = frappe.db.sql(
		f"""
		SELECT
			COALESCE(SUM(si.grand_total), 0) AS total_revenue,
			COUNT(DISTINCT si.name) AS order_count
		FROM `tabSales Invoice` si
		JOIN `tabCustomer` c ON si.customer = c.name
		JOIN `tabLead` l ON c.lead_name = l.name
		LEFT JOIN `tabILL Lead Source` ls ON l.source = ls.name
		WHERE si.docstatus = 1
		  AND COALESCE(ls.source_name, l.source, 'Unknown') = %s
		  AND {date_condition}
		""",
		tuple(params),
		as_dict=True,
	)

	if result and result[0]:
		total_revenue = result[0].get("total_revenue", 0) or 0
		order_count = result[0].get("order_count", 0) or 0
		avg_order_value = (total_revenue / order_count) if order_count > 0 else 0

		return {
			"total_revenue": total_revenue,
			"order_count": order_count,
			"avg_order_value": round(avg_order_value, 2),
		}

	return {"total_revenue": 0, "order_count": 0, "avg_order_value": 0}


def get_email_metrics(campaign, filters):
	"""
	Get email performance metrics for a campaign source.

	Uses the ILL Email Log to track sent, opened, and clicked emails.
	"""
	conditions = []
	params = [campaign]

	if filters.get("from_date"):
		conditions.append("el.sent_at >= %s")
		params.append(filters.get("from_date"))

	if filters.get("to_date"):
		conditions.append("el.sent_at <= %s")
		params.append(filters.get("to_date"))

	date_condition = " AND ".join(conditions) if conditions else "1=1"

	# Query email log metrics
	result = frappe.db.sql(
		f"""
		SELECT
			COUNT(*) AS sent,
			SUM(CASE WHEN el.status IN ('Opened', 'Clicked') THEN 1 ELSE 0 END) AS opened,
			SUM(CASE WHEN el.status = 'Clicked' THEN 1 ELSE 0 END) AS clicked
		FROM `tabILL Email Log` el
		LEFT JOIN `tabILL Lead Source` ls ON el.lead_source = ls.name
		WHERE COALESCE(ls.source_name, 'Unknown') = %s
		  AND el.status != 'Pending'
		  AND {date_condition}
		""",
		tuple(params),
		as_dict=True,
	)

	if result and result[0]:
		sent = result[0].get("sent", 0) or 0
		opened = result[0].get("opened", 0) or 0
		clicked = result[0].get("clicked", 0) or 0

		open_rate = (opened / sent * 100) if sent > 0 else 0
		click_rate = (clicked / sent * 100) if sent > 0 else 0

		return {
			"sent": sent,
			"opened": opened,
			"clicked": clicked,
			"open_rate": round(open_rate, 2),
			"click_rate": round(click_rate, 2),
		}

	return {"sent": 0, "opened": 0, "clicked": 0, "open_rate": 0, "click_rate": 0}


def get_chart_data(data):
	"""Generate chart data for the report."""
	if not data:
		return None

	# Get top 10 campaigns by leads
	top_campaigns = sorted(data, key=lambda x: x.get("total_leads", 0), reverse=True)[:10]

	labels = [row.get("campaign", "Unknown") for row in top_campaigns]
	leads_data = [row.get("total_leads", 0) for row in top_campaigns]
	converted_data = [row.get("converted", 0) for row in top_campaigns]

	return {
		"data": {
			"labels": labels,
			"datasets": [
				{"name": _("Total Leads"), "values": leads_data},
				{"name": _("Converted"), "values": converted_data},
			],
		},
		"type": "bar",
		"colors": ["#7CD6FD", "#5E64FF"],
	}
