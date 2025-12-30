# Copyright (c) 2024, ilLumenate Lighting and contributors
# For license information, please see license.txt

"""
Portal page for listing customer projects.
"""

import frappe

from custom_erpnext.illumenate_configurator.utils import get_customer_for_portal_user


def get_context(context):
	"""Get context for the projects list page."""
	context.no_cache = 1

	# Get the customer for the current portal user
	customer = get_customer_for_portal_user()

	if not customer:
		context.projects = []
		context.customer = None
		context.error = "No customer linked to your account. Please contact support."
		return context

	context.customer = customer

	# Get all projects for this customer
	context.projects = frappe.get_all(
		"ILL Project",
		filters={"customer": customer},
		fields=["name", "project_name", "project_code", "status", "expected_start_date", "expected_end_date"],
		order_by="creation desc",
	)

	return context
