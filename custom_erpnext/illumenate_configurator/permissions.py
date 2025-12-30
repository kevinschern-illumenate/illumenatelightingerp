# Copyright (c) 2024, ilLumenate Lighting and contributors
# For license information, please see license.txt

"""
Permission hooks for ilLumenate Configurator DocTypes.

Provides customer scoping for portal users on ILL Project and ILL Fixture Schedule.
"""

import frappe

from custom_erpnext.illumenate_configurator.utils import get_customer_for_portal_user


def has_permission_project(doc, ptype=None, user=None):
	"""
	Permission hook for ILL Project.

	Portal users can only access projects for their linked Customer.
	Internal users (Illumenate Admin, Illumenate Product Manager) have full access.

	Args:
		doc: The ILL Project document
		ptype: Permission type (read, write, create, delete, etc.)
		user: Optional user email. Defaults to current session user.

	Returns:
		True if user has permission, False otherwise.
	"""
	if not user:
		user = frappe.session.user

	# System users have full access
	if user == "Administrator":
		return True

	# Check if user has internal admin/manager roles
	if frappe.db.exists("Has Role", {"parent": user, "role": "Illumenate Admin"}):
		return True
	if frappe.db.exists("Has Role", {"parent": user, "role": "Illumenate Product Manager"}):
		return True

	# For portal users (Customer role), check customer scoping
	customer = get_customer_for_portal_user(user)
	if not customer:
		return False

	# User can only access projects for their customer
	return doc.customer == customer


def has_permission_schedule(doc, ptype=None, user=None):
	"""
	Permission hook for ILL Fixture Schedule.

	Portal users can only access schedules for their linked Customer.
	Internal users (Illumenate Admin, Illumenate Product Manager) have full access.

	Args:
		doc: The ILL Fixture Schedule document
		ptype: Permission type (read, write, create, delete, etc.)
		user: Optional user email. Defaults to current session user.

	Returns:
		True if user has permission, False otherwise.
	"""
	if not user:
		user = frappe.session.user

	# System users have full access
	if user == "Administrator":
		return True

	# Check if user has internal admin/manager roles
	if frappe.db.exists("Has Role", {"parent": user, "role": "Illumenate Admin"}):
		return True
	if frappe.db.exists("Has Role", {"parent": user, "role": "Illumenate Product Manager"}):
		return True

	# For portal users (Customer role), check customer scoping
	customer = get_customer_for_portal_user(user)
	if not customer:
		return False

	# User can only access schedules for their customer
	return doc.customer == customer


def get_permission_query_conditions_project(user=None):
	"""
	Permission query conditions for ILL Project list view.

	Restricts portal users to seeing only their customer's projects.

	Args:
		user: Optional user email. Defaults to current session user.

	Returns:
		SQL WHERE clause string or None for unrestricted access.
	"""
	if not user:
		user = frappe.session.user

	# System users have full access
	if user == "Administrator":
		return None

	# Check if user has internal admin/manager roles
	if frappe.db.exists("Has Role", {"parent": user, "role": "Illumenate Admin"}):
		return None
	if frappe.db.exists("Has Role", {"parent": user, "role": "Illumenate Product Manager"}):
		return None

	# For portal users, restrict to their customer
	customer = get_customer_for_portal_user(user)
	if not customer:
		return "1=0"  # No access if no customer mapping

	return f"`tabILL Project`.customer = {frappe.db.escape(customer)}"


def get_permission_query_conditions_schedule(user=None):
	"""
	Permission query conditions for ILL Fixture Schedule list view.

	Restricts portal users to seeing only their customer's schedules.

	Args:
		user: Optional user email. Defaults to current session user.

	Returns:
		SQL WHERE clause string or None for unrestricted access.
	"""
	if not user:
		user = frappe.session.user

	# System users have full access
	if user == "Administrator":
		return None

	# Check if user has internal admin/manager roles
	if frappe.db.exists("Has Role", {"parent": user, "role": "Illumenate Admin"}):
		return None
	if frappe.db.exists("Has Role", {"parent": user, "role": "Illumenate Product Manager"}):
		return None

	# For portal users, restrict to their customer
	customer = get_customer_for_portal_user(user)
	if not customer:
		return "1=0"  # No access if no customer mapping

	return f"`tabILL Fixture Schedule`.customer = {frappe.db.escape(customer)}"
