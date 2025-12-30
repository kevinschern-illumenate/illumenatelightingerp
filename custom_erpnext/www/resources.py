# Copyright (c) 2024, ilLumenate Lighting and contributors
# For license information, please see license.txt

"""
Portal page for viewing resource documents.
"""

import frappe

from custom_erpnext.illumenate_configurator.utils import get_customer_for_portal_user


def get_context(context):
	"""Get context for the resources page."""
	context.no_cache = 1

	# Check if user is logged in
	is_logged_in = frappe.session.user != "Guest"

	# Build filters based on login status
	filters = {"is_active": 1}

	if not is_logged_in:
		# Public users only see public resources
		filters["is_public"] = 1
	else:
		# Logged-in users see all active resources
		# Check if they're a portal customer
		customer = get_customer_for_portal_user()
		context.customer = customer

	# Get all active resources
	resources = frappe.get_all(
		"ILL Resource Document",
		filters=filters,
		fields=[
			"name",
			"title",
			"category",
			"applies_to_template",
			"applies_to_lens_option",
			"file",
			"is_public",
			"sort_order",
		],
		order_by="sort_order asc, category asc, title asc",
	)

	# Group resources by category
	categories = {}
	category_order = [
		"Installation",
		"Cut Sheet",
		"Warranty",
		"Certifications",
		"Wiring Diagrams",
		"Other",
	]

	for resource in resources:
		cat = resource.category
		if cat not in categories:
			categories[cat] = []
		categories[cat].append(resource)

	# Build ordered category list
	context.categories = []
	for cat in category_order:
		if cat in categories:
			context.categories.append({
				"name": cat,
				"resources": categories[cat],
			})

	context.is_logged_in = is_logged_in

	return context
