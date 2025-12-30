# Copyright (c) 2024, ilLumenate Lighting and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class ILLMarketingForm(Document):
	def validate(self):
		"""Validate marketing form document."""
		self.validate_route()
		self.validate_email()

	def validate_route(self):
		"""Validate route format."""
		if self.route:
			# Ensure route starts with /
			if not self.route.startswith("/"):
				self.route = "/" + self.route
			# Remove trailing slashes
			self.route = self.route.rstrip("/")

	def validate_email(self):
		"""Validate notification email format."""
		if self.notification_email:
			import re

			# Basic email validation pattern
			pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
			if not re.match(pattern, self.notification_email):
				frappe.throw(_("Invalid notification email format"))

	def get_utm_defaults(self):
		"""Get default UTM parameters for this form."""
		return {
			"utm_source": self.default_utm_source,
			"utm_medium": self.default_utm_medium,
			"utm_campaign": self.default_utm_campaign,
		}
