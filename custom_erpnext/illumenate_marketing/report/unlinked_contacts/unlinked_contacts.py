# Copyright (c) 2024, ilLumenate Lighting and contributors
# For license information, please see license.txt

"""
Unlinked Contacts Data Hygiene Report

This report identifies Contacts that are missing critical linkages:
- Contacts without a linked Company
- Contacts without a linked Customer
- Contacts without a User account

This helps sales ops maintain data quality for proper dealer tier inheritance.
"""

import frappe
from frappe import _


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{
			"fieldname": "contact_name",
			"label": _("Contact"),
			"fieldtype": "Link",
			"options": "Contact",
			"width": 180,
		},
		{
			"fieldname": "email_id",
			"label": _("Email"),
			"fieldtype": "Data",
			"width": 200,
		},
		{
			"fieldname": "full_name",
			"label": _("Full Name"),
			"fieldtype": "Data",
			"width": 180,
		},
		{
			"fieldname": "has_user",
			"label": _("Has User"),
			"fieldtype": "Check",
			"width": 80,
		},
		{
			"fieldname": "has_company",
			"label": _("Has Company"),
			"fieldtype": "Check",
			"width": 100,
		},
		{
			"fieldname": "has_customer",
			"label": _("Has Customer"),
			"fieldtype": "Check",
			"width": 100,
		},
		{
			"fieldname": "linked_company",
			"label": _("Linked Company"),
			"fieldtype": "Link",
			"options": "Company",
			"width": 180,
		},
		{
			"fieldname": "linked_customer",
			"label": _("Linked Customer"),
			"fieldtype": "Link",
			"options": "Customer",
			"width": 180,
		},
		{
			"fieldname": "issue_type",
			"label": _("Issue"),
			"fieldtype": "Data",
			"width": 200,
		},
		{
			"fieldname": "creation",
			"label": _("Created"),
			"fieldtype": "Date",
			"width": 100,
		},
	]


def get_data(filters):
	"""
	Find contacts with missing linkages.

	Identifies:
	1. Contacts without Company link
	2. Contacts without Customer link
	3. Contacts without User account
	"""
	# Get all contacts with their email and user info
	contacts = frappe.db.sql(
		"""
		SELECT
			c.name as contact_name,
			c.email_id,
			CONCAT(IFNULL(c.first_name, ''), ' ', IFNULL(c.last_name, '')) as full_name,
			c.user,
			c.creation
		FROM `tabContact` c
		ORDER BY c.creation DESC
		""",
		as_dict=True,
	)

	data = []

	for contact in contacts:
		# Check for linked Company
		company = frappe.db.get_value(
			"Dynamic Link",
			{"link_doctype": "Company", "parent": contact.contact_name, "parenttype": "Contact"},
			"link_name",
		)

		# Check for linked Customer
		customer = frappe.db.get_value(
			"Dynamic Link",
			{"link_doctype": "Customer", "parent": contact.contact_name, "parenttype": "Contact"},
			"link_name",
		)

		# Determine issues
		issues = []
		has_user = 1 if contact.user else 0
		has_company = 1 if company else 0
		has_customer = 1 if customer else 0

		if not contact.user:
			issues.append("No User Account")
		if not company:
			issues.append("No Company Link")
		if not customer:
			issues.append("No Customer Link")

		# Only include contacts with at least one issue
		if issues:
			data.append(
				{
					"contact_name": contact.contact_name,
					"email_id": contact.email_id,
					"full_name": contact.full_name.strip() if contact.full_name else "",
					"has_user": has_user,
					"has_company": has_company,
					"has_customer": has_customer,
					"linked_company": company or "",
					"linked_customer": customer or "",
					"issue_type": ", ".join(issues),
					"creation": contact.creation,
				}
			)

	return data
