# Copyright (c) 2024, ilLumenate Lighting and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ILLn8nSettings(Document):
	def validate(self):
		"""Validate n8n settings."""
		if self.enabled and not self.n8n_webhook_url:
			frappe.throw("n8n Webhook URL is required when integration is enabled")

		if self.n8n_webhook_url:
			self.n8n_webhook_url = self.n8n_webhook_url.rstrip("/")


def get_n8n_settings():
	"""
	Get the n8n settings document.

	Returns:
		dict with n8n settings values
	"""
	settings = frappe.get_single("ILL n8n Settings")
	return {
		"enabled": settings.enabled,
		"n8n_webhook_url": settings.n8n_webhook_url,
		"api_key": settings.get_password("api_key") if settings.api_key else None,
		"emit_lead_created": settings.emit_lead_created,
		"emit_lead_converted": settings.emit_lead_converted,
		"emit_purchase_completed": settings.emit_purchase_completed,
		"emit_journey_changed": settings.emit_journey_changed,
	}


def is_n8n_enabled():
	"""
	Check if n8n integration is enabled.

	Returns:
		bool indicating if n8n is enabled
	"""
	return frappe.db.get_single_value("ILL n8n Settings", "enabled")
