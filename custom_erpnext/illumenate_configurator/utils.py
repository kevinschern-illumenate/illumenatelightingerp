# Copyright (c) 2024, ilLumenate Lighting and contributors
# For license information, please see license.txt

"""
Utility functions for ilLumenate Configurator.

Provides helper functions for portal user mapping, customer lookup, and other common utilities.
"""

import frappe


def get_customer_for_portal_user(user=None):
	"""
	Map portal user to Customer via 'Portal Users' child table or Contact.

	Args:
		user: Optional user email. Defaults to current session user.

	Returns:
		Customer name or None if no mapping found.
	"""
	if not user:
		user = frappe.session.user

	# First check Customer portal_users child table
	customer = frappe.db.get_value(
		"Portal User",
		{"user": user},
		"parent",
	)

	if customer:
		return customer

	# Fallback: Check Contact -> Customer link
	contact = frappe.db.get_value("Contact", {"user": user}, "name")
	if contact:
		customer = frappe.db.get_value(
			"Dynamic Link",
			{"link_doctype": "Customer", "parent": contact, "parenttype": "Contact"},
			"link_name",
		)
		if customer:
			return customer

	return None


def is_portal_user():
	"""
	Check if the current user is a portal user (has Customer role).

	Returns:
		True if user has Customer role, False otherwise.
	"""
	user = frappe.session.user
	if user == "Administrator" or user == "Guest":
		return False

	return frappe.db.exists("Has Role", {"parent": user, "role": "Customer"})
