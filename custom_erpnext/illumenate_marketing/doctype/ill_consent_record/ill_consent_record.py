# Copyright (c) 2024, ilLumenate Lighting and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ILLConsentRecord(Document):
	def before_insert(self):
		"""Set consent timestamp if not provided."""
		if not self.consent_timestamp:
			self.consent_timestamp = frappe.utils.now()

	def validate(self):
		"""Validate consent record."""
		self.validate_email()

	def validate_email(self):
		"""Validate email format."""
		if self.email:
			import re

			pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
			if not re.match(pattern, self.email):
				frappe.throw("Invalid email format")


def get_consent_status(email, consent_type="Marketing Communications"):
	"""
	Check if a user has given consent.

	Args:
		email: The email address to check
		consent_type: Type of consent to check for

	Returns:
		dict with consent_given status and timestamp
	"""
	record = frappe.db.get_value(
		"ILL Consent Record",
		{"email": email, "consent_type": consent_type},
		["consent_given", "consent_timestamp"],
		order_by="consent_timestamp desc",
		as_dict=True,
	)

	if record:
		return {
			"has_record": True,
			"consent_given": record.consent_given,
			"consent_timestamp": record.consent_timestamp,
		}

	return {
		"has_record": False,
		"consent_given": False,
		"consent_timestamp": None,
	}
