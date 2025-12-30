# Copyright (c) 2024, ilLumenate Lighting and contributors
# For license information, please see license.txt

"""
Portal page for viewing project details and schedules.
"""

import frappe

from custom_erpnext.illumenate_configurator.utils import (
	get_customer_for_portal_user,
	get_customer_price_list_for_user,
)


def get_customer_price_list(user=None):
	"""
	Determine pricing tier based on logged-in user's company linkage.

	Follows the chain: User → Contact → Company → Customer → Price List

	Args:
		user: Optional user email. Defaults to current session user.

	Returns:
		Price list name (e.g., "Dealer A", "MSRP") or "MSRP" as fallback for retail.
	"""
	result = get_customer_price_list_for_user(user)
	return result["price_list"]


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

	# Add pricing tier for the current user (Sprint 4 - auto-detect tier)
	pricing_info = get_customer_price_list_for_user()
	context.pricing_tier = pricing_info["price_list"]

	return context
