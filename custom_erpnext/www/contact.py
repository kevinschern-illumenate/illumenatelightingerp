# Copyright (c) 2024, ilLumenate Lighting and contributors
# For license information, please see license.txt

"""
Contact form page handler.
"""

import frappe


def get_context(context):
	"""Get context for the contact form page."""
	context.no_cache = 1

	# Try to get the Contact Form configuration
	form_name = "Contact"
	if frappe.db.exists("ILL Marketing Form", form_name):
		form = frappe.get_doc("ILL Marketing Form", form_name)
		context.require_consent = form.require_gdpr_consent
		context.consent_text = form.gdpr_consent_text
		context.privacy_url = form.privacy_policy_url
	else:
		# Default settings if form not configured
		context.require_consent = True
		context.consent_text = (
			"I agree to receive communications from ilLumenate Lighting. "
			"I understand I can unsubscribe at any time."
		)
		context.privacy_url = None

	return context
