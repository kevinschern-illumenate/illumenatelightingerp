# Copyright (c) 2024, ilLumenate Lighting and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ILLEmailTemplateMapping(Document):
	"""
	ILL Email Template Mapping DocType.

	Links Lead Source to Email Template with auto-send trigger configuration.
	Used for welcome email automation when leads are created.
	"""

	def validate(self):
		"""Validate the mapping configuration."""
		self.validate_email_template()
		self.validate_delay()

	def validate_email_template(self):
		"""Ensure the email template exists."""
		if self.email_template:
			if not frappe.db.exists("Email Template", self.email_template):
				frappe.throw(f"Email Template '{self.email_template}' does not exist")

	def validate_delay(self):
		"""Ensure delay is non-negative."""
		if self.delay_minutes and self.delay_minutes < 0:
			frappe.throw("Delay minutes cannot be negative")


def get_template_mapping_for_lead_source(lead_source=None, trigger_event="Lead Created"):
	"""
	Get active email template mapping for a lead source.

	Args:
		lead_source: The lead source name (optional - matches mappings with no source if None)
		trigger_event: The trigger event type

	Returns:
		ILL Email Template Mapping document or None
	"""
	# First try to find a mapping specific to this lead source
	if lead_source:
		mapping = frappe.db.get_value(
			"ILL Email Template Mapping",
			{"is_active": 1, "trigger_event": trigger_event, "lead_source": lead_source},
			["name", "email_template", "delay_minutes", "subject_override", "from_email_override"],
			as_dict=True,
		)
		if mapping:
			return mapping

	# Fall back to a mapping with no lead source (applies to all)
	mapping = frappe.db.get_value(
		"ILL Email Template Mapping",
		{"is_active": 1, "trigger_event": trigger_event, "lead_source": ["in", ["", None]]},
		["name", "email_template", "delay_minutes", "subject_override", "from_email_override"],
		as_dict=True,
	)

	return mapping
