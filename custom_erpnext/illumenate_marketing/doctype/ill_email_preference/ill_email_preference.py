# Copyright (c) 2024, ilLumenate Lighting and contributors
# For license information, please see license.txt

import secrets

import frappe
from frappe.model.document import Document


class ILLEmailPreference(Document):
	def before_insert(self):
		"""Generate unsubscribe token on creation."""
		if not self.unsubscribe_token:
			self.unsubscribe_token = secrets.token_urlsafe(32)
		self.last_updated = frappe.utils.now()

	def before_save(self):
		"""Update last_updated timestamp."""
		self.last_updated = frappe.utils.now()

	def validate(self):
		"""Validate email preference."""
		self.validate_email()

	def validate_email(self):
		"""Validate email format."""
		if self.email:
			import re

			pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
			if not re.match(pattern, self.email):
				frappe.throw("Invalid email format")


def get_or_create_email_preference(email):
	"""
	Get or create email preference record for an email address.

	Args:
		email: The email address

	Returns:
		ILL Email Preference document
	"""
	if frappe.db.exists("ILL Email Preference", email):
		return frappe.get_doc("ILL Email Preference", email)

	pref = frappe.new_doc("ILL Email Preference")
	pref.email = email
	pref.insert(ignore_permissions=True)
	return pref


def can_send_email(email, email_type="marketing"):
	"""
	Check if we can send a specific type of email to this address.

	Args:
		email: The email address
		email_type: Type of email (marketing, newsletter, product_updates, dealer)

	Returns:
		bool indicating if email can be sent
	"""
	if not frappe.db.exists("ILL Email Preference", email):
		# No preference record means they haven't unsubscribed
		return True

	pref = frappe.get_doc("ILL Email Preference", email)

	# Global unsubscribe trumps all
	if pref.global_unsubscribe:
		return False

	# Check specific preference
	type_mapping = {
		"marketing": "marketing_emails",
		"newsletter": "newsletter_emails",
		"product_updates": "product_updates",
		"dealer": "dealer_communications",
	}

	field = type_mapping.get(email_type, "marketing_emails")
	return getattr(pref, field, True)


def process_unsubscribe(token, email_type=None):
	"""
	Process an unsubscribe request.

	Args:
		token: The unsubscribe token
		email_type: Optional specific email type to unsubscribe from.
			If None, performs global unsubscribe.

	Returns:
		dict with success status and message
	"""
	pref = frappe.db.get_value(
		"ILL Email Preference",
		{"unsubscribe_token": token},
		["name", "email"],
		as_dict=True,
	)

	if not pref:
		return {"success": False, "message": "Invalid unsubscribe link"}

	doc = frappe.get_doc("ILL Email Preference", pref.name)

	if email_type:
		# Unsubscribe from specific type
		type_mapping = {
			"marketing": "marketing_emails",
			"newsletter": "newsletter_emails",
			"product_updates": "product_updates",
			"dealer": "dealer_communications",
		}
		field = type_mapping.get(email_type)
		if field:
			setattr(doc, field, 0)
	else:
		# Global unsubscribe
		doc.global_unsubscribe = 1

	doc.save(ignore_permissions=True)

	return {
		"success": True,
		"message": "You have been successfully unsubscribed",
		"email": pref.email,
	}
