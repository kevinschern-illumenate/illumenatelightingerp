# Copyright (c) 2024, ilLumenate Lighting and contributors
# For license information, please see license.txt

"""
Utility functions for ilLumenate Configurator.

Provides helper functions for portal user mapping, customer lookup, and other common utilities.
"""

import frappe


def abbreviate_attribute_combination(attribute_combination: str) -> str:
	"""
	Convert an attribute combination string to use abbreviations.

	Takes a string like "LED Tape CCT: 3000K, LED Tape CRI: 90+"
	and returns an abbreviated version like "3000K-90+" using the
	abbreviations defined in ERPNext's Item Attribute Value table.

	Args:
		attribute_combination: Full attribute combination string

	Returns:
		Abbreviated string, or original values if no abbreviation found
	"""
	if not attribute_combination:
		return ""

	abbreviated_parts = []

	# Parse "Attribute: Value, Attribute: Value" format
	for part in attribute_combination.split(","):
		part = part.strip()
		if ":" not in part:
			continue

		attribute_name, attribute_value = part.split(":", 1)
		attribute_name = attribute_name.strip()
		attribute_value = attribute_value.strip()

		# Look up abbreviation from Item Attribute Value
		abbr = frappe.db.get_value(
			"Item Attribute Value",
			{"parent": attribute_name, "attribute_value": attribute_value},
			"abbr",
		)

		# Use abbreviation if found, otherwise use the value itself
		if abbr:
			abbreviated_parts.append(abbr)
		else:
			# Fall back to just the value (without attribute name)
			abbreviated_parts.append(attribute_value)

	return "-".join(abbreviated_parts)


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


def get_company_for_contact(contact_name):
	"""
	Get the Company linked to a Contact.

	Args:
		contact_name: The Contact document name.

	Returns:
		Company name or None if no link found.
	"""
	if not contact_name:
		return None

	# Check Dynamic Link for Company
	company = frappe.db.get_value(
		"Dynamic Link",
		{"link_doctype": "Company", "parent": contact_name, "parenttype": "Contact"},
		"link_name",
	)
	return company


def get_customer_for_company(company_name):
	"""
	Get the Customer linked to a Company (for dealer inheritance).

	This supports the scenario where an employee of a dealer company
	should inherit the company's customer/discount tier.

	Args:
		company_name: The Company name.

	Returns:
		Customer name or None if no link found.
	"""
	if not company_name:
		return None

	# Look for a Customer that has this company in its customer_primary_contact
	# or find via a Link field if exists
	# First try: Customer with matching company name
	customer = frappe.db.get_value(
		"Customer",
		{"customer_name": company_name},
		"name",
	)
	if customer:
		return customer

	# Second try: Find via Dynamic Link where a Contact linked to this company
	# is also linked to a Customer
	contacts = frappe.get_all(
		"Dynamic Link",
		filters={"link_doctype": "Company", "link_name": company_name, "parenttype": "Contact"},
		pluck="parent",
	)

	for contact in contacts:
		customer = frappe.db.get_value(
			"Dynamic Link",
			{"link_doctype": "Customer", "parent": contact, "parenttype": "Contact"},
			"link_name",
		)
		if customer:
			return customer

	return None


def get_customer_price_list_for_user(user=None):
	"""
	Determine pricing tier/price list based on user's company linkage.

	Follows the chain: User → Contact → Company → Customer → Price List
	This supports:
	- Direct customer portal users (User → Customer)
	- Employee inheritance (User → Contact → Company → Customer)

	Args:
		user: Optional user email. Defaults to current session user.

	Returns:
		dict with:
			- price_list: Price list name (e.g., "Dealer A", "MSRP")
			- customer: Customer name if found
			- source: How the price list was determined
	"""
	if not user:
		user = frappe.session.user

	result = {
		"price_list": "MSRP",
		"customer": None,
		"source": "default",
	}

	# Path 1: Direct customer mapping via Portal Users
	customer = frappe.db.get_value("Portal User", {"user": user}, "parent")
	if customer:
		price_list = frappe.db.get_value("Customer", customer, "default_price_list")
		if price_list:
			result["price_list"] = price_list
			result["customer"] = customer
			result["source"] = "portal_user"
			return result

	# Path 2: User → Contact → Customer
	contact = frappe.db.get_value("Contact", {"user": user}, "name")
	if contact:
		# Try direct Customer link from Contact
		customer = frappe.db.get_value(
			"Dynamic Link",
			{"link_doctype": "Customer", "parent": contact, "parenttype": "Contact"},
			"link_name",
		)
		if customer:
			price_list = frappe.db.get_value("Customer", customer, "default_price_list")
			if price_list:
				result["price_list"] = price_list
				result["customer"] = customer
				result["source"] = "contact_customer"
				return result

		# Path 3: User → Contact → Company → Customer (employee inheritance)
		company = get_company_for_contact(contact)
		if company:
			customer = get_customer_for_company(company)
			if customer:
				price_list = frappe.db.get_value("Customer", customer, "default_price_list")
				if price_list:
					result["price_list"] = price_list
					result["customer"] = customer
					result["source"] = "company_inheritance"
					return result

	# Fallback: MSRP for retail customers
	return result


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
