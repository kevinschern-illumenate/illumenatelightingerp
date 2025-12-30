# Copyright (c) 2024, ilLumenate Lighting and contributors
# For license information, please see license.txt

"""
Portal page for creating a new fixture schedule.
"""

import frappe

from custom_erpnext.illumenate_configurator.utils import get_customer_for_portal_user


def get_context(context):
	"""Get context for the new schedule page."""
	context.no_cache = 1

	# Get project from query string
	project_name = frappe.form_dict.get("project")

	# Get the customer for the current portal user
	customer = get_customer_for_portal_user()

	if not customer:
		context.error = "No customer linked to your account. Please contact support."
		return context

	context.customer = customer

	# If project specified, validate access
	if project_name:
		if not frappe.db.exists("ILL Project", project_name):
			context.error = "Project not found."
			return context

		project = frappe.get_doc("ILL Project", project_name)

		# Check customer access
		if project.customer != customer:
			context.error = "You do not have permission to access this project."
			return context

		context.project = project
	else:
		context.project = None

	# Get all projects for this customer (for dropdown if no project specified)
	context.projects = frappe.get_all(
		"ILL Project",
		filters={"customer": customer},
		fields=["name", "project_name", "project_code"],
		order_by="creation desc",
	)

	return context
