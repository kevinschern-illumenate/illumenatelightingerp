# Copyright (c) 2024, ilLumenate Lighting and contributors
# For license information, please see license.txt

"""
Portal page for viewing and editing fixture schedule details.
"""

import frappe

from custom_erpnext.illumenate_configurator.utils import get_customer_for_portal_user


def get_context(context):
	"""Get context for the schedule detail page."""
	context.no_cache = 1

	# Get schedule name from query string
	schedule_name = frappe.form_dict.get("name")

	if not schedule_name:
		context.error = "No schedule specified."
		return context

	# Get the customer for the current portal user
	customer = get_customer_for_portal_user()

	if not customer:
		context.error = "No customer linked to your account. Please contact support."
		return context

	# Load the schedule
	if not frappe.db.exists("ILL Fixture Schedule", schedule_name):
		context.error = "Schedule not found."
		return context

	schedule = frappe.get_doc("ILL Fixture Schedule", schedule_name)

	# Check customer access (via schedule.customer or project)
	schedule_customer = schedule.customer
	if not schedule_customer and schedule.project:
		schedule_customer = frappe.db.get_value("ILL Project", schedule.project, "customer")
	
	if schedule_customer != customer:
		context.error = "You do not have permission to view this schedule."
		return context

	context.schedule = schedule

	# Load the project
	if schedule.project:
		context.project = frappe.get_doc("ILL Project", schedule.project)
	else:
		context.project = None

	# Get fixture templates for the configurator dropdown
	context.templates = frappe.get_all(
		"ILL Fixture Template",
		fields=["name", "template_code", "template_name"],
		order_by="template_code",
	)

	# Calculate schedule totals
	context.schedule_total = sum(
		line.line_total or 0 for line in schedule.lines
		if line.line_type == "ilLumenate" and line.line_total
	)

	context.is_editable = schedule.status == "Draft"

	return context
