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

