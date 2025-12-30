# Copyright (c) 2024, ilLumenate Lighting and contributors
# For license information, please see license.txt

"""
Portal page for creating a new project.
"""

import frappe

from custom_erpnext.illumenate_configurator.utils import get_customer_for_portal_user


def get_context(context):
	"""Get context for the new project page."""
	context.no_cache = 1

	# Get the customer for the current portal user
	customer = get_customer_for_portal_user()

	if not customer:
		context.error = "No customer linked to your account. Please contact support."
		return context

	context.customer = customer
	context.customer_name = frappe.db.get_value("Customer", customer, "customer_name")

	return context


@frappe.whitelist()
def create_project(project_name, project_code=None, description=None, expected_start_date=None, expected_end_date=None):
	"""
	Create a new project for the current portal user's customer.

	Args:
		project_name: Name of the project (required)
		project_code: Optional project code
		description: Optional project description
		expected_start_date: Optional expected start date
		expected_end_date: Optional expected end date

	Returns:
		dict with project name on success
	"""
	customer = get_customer_for_portal_user()

	if not customer:
		frappe.throw("No customer linked to your account. Please contact support.")

	# Create the project
	project = frappe.get_doc({
		"doctype": "ILL Project",
		"customer": customer,
		"project_name": project_name,
		"project_code": project_code,
		"description": description,
		"expected_start_date": expected_start_date,
		"expected_end_date": expected_end_date,
		"status": "Draft",
	})

	project.insert()

	return {"name": project.name, "project_name": project.project_name}
