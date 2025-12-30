# Copyright (c) 2024, ilLumenate Lighting and contributors
# For license information, please see license.txt

import re

import frappe
from frappe.model.document import Document


class ILLMarketingEventType(Document):
	def validate(self):
		"""Validate event type configuration."""
		self.validate_event_code()

	def validate_event_code(self):
		"""Validate event code format."""
		if self.event_code:
			# Event code should be lowercase with underscores only
			pattern = r"^[a-z][a-z0-9_]*$"
			if not re.match(pattern, self.event_code):
				frappe.throw(
					"Event Code must be lowercase, start with a letter, "
					"and contain only letters, numbers, and underscores"
				)


def get_active_event_types():
	"""
	Get list of active event types.

	Returns:
		list of active event type records
	"""
	return frappe.get_all(
		"ILL Marketing Event Type",
		filters={"is_active": 1},
		fields=["event_name", "event_code", "source_doctype", "description"],
		order_by="event_name",
	)


def is_event_type_active(event_code):
	"""
	Check if an event type is active.

	Args:
		event_code: The event code to check

	Returns:
		bool indicating if the event type is active
	"""
	return frappe.db.exists("ILL Marketing Event Type", {"event_code": event_code, "is_active": 1})
