# Copyright (c) 2024, ilLumenate Lighting and contributors
# For license information, please see license.txt

"""
Installation and setup functions for the ilLumenate Lighting ERP app.
"""

import frappe


def after_install():
	"""Run after installing the app."""
	ensure_marketing_forms_exist()


def after_migrate():
	"""Run after bench migrate."""
	ensure_marketing_forms_exist()


def ensure_marketing_forms_exist():
	"""
	Ensure required marketing forms exist in the database.

	This function creates the default marketing forms if they don't exist,
	ensuring that form submissions work even if fixtures haven't been imported.
	"""
	# Skip if DocType doesn't exist yet (during initial install)
	if not frappe.db.exists("DocType", "ILL Marketing Form"):
		return

	marketing_forms = [
		{
			"doctype": "ILL Marketing Form",
			"form_name": "Dealer Inquiry",
			"form_type": "Dealer Inquiry",
			"is_active": 1,
			"route": "/dealer_inquiry",
			"require_gdpr_consent": 1,
			"gdpr_consent_text": (
				"I agree to receive communications from ilLumenate Lighting "
				"regarding my dealer application. I understand I can unsubscribe at any time."
			),
			"success_message": (
				"Thank you for your interest in becoming an ilLumenate dealer. "
				"Our dealer team will review your application and contact you within 2 business days."
			),
		},
		{
			"doctype": "ILL Marketing Form",
			"form_name": "Contact",
			"form_type": "Contact",
			"is_active": 1,
			"route": "/contact",
			"require_gdpr_consent": 1,
			"gdpr_consent_text": (
				"I agree to receive communications from ilLumenate Lighting. "
				"I understand I can unsubscribe at any time."
			),
			"success_message": "Thank you for your inquiry. We will be in touch shortly.",
		},
	]

	for form_data in marketing_forms:
		form_name = form_data["form_name"]
		if not frappe.db.exists("ILL Marketing Form", form_name):
			doc = frappe.get_doc(form_data)
			doc.insert(ignore_permissions=True)
			frappe.db.commit()
