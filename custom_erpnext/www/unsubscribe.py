# Copyright (c) 2024, ilLumenate Lighting and contributors
# For license information, please see license.txt

"""
Unsubscribe and email preferences page handler.
"""

import frappe

from custom_erpnext.illumenate_marketing.api import get_email_preferences, unsubscribe


def get_context(context):
	"""Get context for the unsubscribe/preferences page."""
	context.no_cache = 1

	token = frappe.form_dict.get("token")
	action = frappe.form_dict.get("action")

	if not token:
		context.error = "Invalid or missing token. Please use the link from your email."
		return context

	# If action=unsubscribe, process immediate unsubscribe
	if action == "unsubscribe":
		email_type = frappe.form_dict.get("type")
		result = unsubscribe(token, email_type)

		if result.get("success"):
			context.success = True
			context.success_message = result.get("message")
		else:
			context.error = result.get("message")
		return context

	# Otherwise, show preferences form
	result = get_email_preferences(token)

	if not result.get("success"):
		context.error = result.get("message")
		return context

	context.token = token
	context.email = result.get("email")
	context.preferences = result.get("preferences")

	return context
