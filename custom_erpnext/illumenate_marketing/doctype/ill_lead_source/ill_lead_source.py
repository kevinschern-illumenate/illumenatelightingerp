# Copyright (c) 2024, ilLumenate Lighting and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class ILLLeadSource(Document):
	def validate(self):
		"""Validate lead source document."""
		self.validate_source_name()

	def validate_source_name(self):
		"""Validate source name is alphanumeric with allowed characters."""
		import re

		if not self.source_name:
			return

		# Allow alphanumeric, hyphens, underscores, spaces
		pattern = r"^[a-zA-Z0-9\-_\s]+$"
		if not re.match(pattern, self.source_name):
			frappe.throw(
				_("Source Name can only contain letters, numbers, hyphens, underscores, and spaces")
			)


def get_active_lead_sources():
	"""Get list of active lead source names for validation."""
	return frappe.get_all(
		"ILL Lead Source",
		filters={"is_active": 1},
		pluck="source_name",
	)


def validate_lead_source(source_name):
	"""Validate that a lead source exists and is active."""
	if not source_name:
		return True

	active_sources = get_active_lead_sources()
	return source_name in active_sources
