# Copyright (c) 2024, ilLumenate Lighting and contributors
# For license information, please see license.txt

"""
Portal page for viewing project details and schedules.
"""

import frappe

from custom_erpnext.illumenate_configurator.utils import get_customer_for_portal_user


def get_context(context):
	"""Get context for the project detail page."""
	context.no_cache = 1

	# Get project name from query string
	project_name = frappe.form_dict.get("name")

	if not project_name:
		context.error = "No project specified."
		return context

	# Get the customer for the current portal user
	customer = get_customer_for_portal_user()

	if not customer:
		context.error = "No customer linked to your account. Please contact support."
		return context

	# Load the project
	if not frappe.db.exists("ILL Project", project_name):
		context.error = "Project not found."
		return context

	project = frappe.get_doc("ILL Project", project_name)

	# Check customer access
	if project.customer != customer:
		context.error = "You do not have permission to view this project."
		return context

	context.project = project

	# Get schedules for this project
	context.schedules = frappe.get_all(
		"ILL Fixture Schedule",
		filters={"project": project_name},
		fields=["name", "schedule_name", "status", "sales_order", "creation"],
		order_by="creation desc",
	)

	return context
