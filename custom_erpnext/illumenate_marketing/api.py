# Copyright (c) 2024, ilLumenate Lighting and contributors
# For license information, please see license.txt

"""
Marketing API Module

Provides endpoints for form submission, UTM parameter handling,
GDPR consent tracking, and unsubscribe management.
"""

import frappe
from frappe import _

from custom_erpnext.illumenate_marketing.doctype.ill_consent_record.ill_consent_record import (
	get_consent_status,
)
from custom_erpnext.illumenate_marketing.doctype.ill_email_preference.ill_email_preference import (
	get_or_create_email_preference,
	process_unsubscribe,
)
from custom_erpnext.illumenate_marketing.doctype.ill_lead_source.ill_lead_source import (
	validate_lead_source,
)

# Constants
MAX_USER_AGENT_LENGTH = 500


def parse_utm_parameters(request_data):
	"""
	Parse UTM parameters from request data.

	Args:
		request_data: dict containing form data (may include utm_* fields)

	Returns:
		dict with utm_source, utm_medium, utm_campaign, utm_content, utm_term
	"""
	return {
		"utm_source": request_data.get("utm_source", ""),
		"utm_medium": request_data.get("utm_medium", ""),
		"utm_campaign": request_data.get("utm_campaign", ""),
		"utm_content": request_data.get("utm_content", ""),
		"utm_term": request_data.get("utm_term", ""),
	}


def validate_form_submission(form_name, data):
	"""
	Validate form submission data.

	Args:
		form_name: The marketing form name
		data: Form submission data

	Returns:
		dict with validation result and any errors
	"""
	errors = []

	# Get the form configuration
	if not frappe.db.exists("ILL Marketing Form", form_name):
		return {"valid": False, "errors": [{"field": "form", "message": "Form not found"}]}

	form = frappe.get_doc("ILL Marketing Form", form_name)

	if not form.is_active:
		return {"valid": False, "errors": [{"field": "form", "message": "Form is not active"}]}

	# Validate required email
	email = data.get("email", "").strip()
	if not email:
		errors.append({"field": "email", "message": "Email is required"})
	else:
		# Validate email format
		import re

		pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
		if not re.match(pattern, email):
			errors.append({"field": "email", "message": "Invalid email format"})

	# Validate GDPR consent if required
	if form.require_gdpr_consent:
		consent_given = data.get("gdpr_consent", False)
		if isinstance(consent_given, str):
			consent_given = consent_given.lower() in ("true", "1", "yes", "on")
		if not consent_given:
			errors.append({"field": "gdpr_consent", "message": "Consent is required"})

	# Validate lead source if provided
	lead_source = data.get("lead_source", "")
	if lead_source and not validate_lead_source(lead_source):
		errors.append({"field": "lead_source", "message": "Invalid lead source"})

	return {"valid": len(errors) == 0, "errors": errors}


@frappe.whitelist(allow_guest=True)
def submit_form(form_name, **kwargs):
	"""
	Submit a marketing form.

	This endpoint handles form submissions from public web pages,
	captures UTM parameters, logs GDPR consent, and creates a lead/contact.

	Args:
		form_name: The ILL Marketing Form name
		**kwargs: Form field values including:
			- email (required)
			- first_name, last_name
			- company
			- phone
			- message
			- utm_source, utm_medium, utm_campaign, utm_content
			- lead_source
			- gdpr_consent

	Returns:
		dict with success status and message
	"""
	# Rate limiting: Simple check to prevent abuse
	# In production, this should be more sophisticated
	ip_address = frappe.local.request.remote_addr if frappe.local.request else None

	# Validate the submission
	validation = validate_form_submission(form_name, kwargs)
	if not validation["valid"]:
		return {
			"success": False,
			"errors": validation["errors"],
		}

	# Get form configuration
	form = frappe.get_doc("ILL Marketing Form", form_name)

	# Parse UTM parameters from submission (captured from URL by JS)
	utm_params = parse_utm_parameters(kwargs)

	# Fall back to form defaults if not provided
	if not utm_params["utm_source"] and form.default_utm_source:
		utm_params["utm_source"] = form.default_utm_source
	if not utm_params["utm_medium"] and form.default_utm_medium:
		utm_params["utm_medium"] = form.default_utm_medium
	if not utm_params["utm_campaign"] and form.default_utm_campaign:
		utm_params["utm_campaign"] = form.default_utm_campaign

	# Determine lead source
	lead_source = kwargs.get("lead_source", "")
	if not lead_source and form.lead_source:
		lead_source = form.lead_source

	email = kwargs.get("email", "").strip()
	user_agent = frappe.local.request.headers.get("User-Agent", "") if frappe.local.request else ""

	# Record GDPR consent
	if form.require_gdpr_consent:
		consent_doc = frappe.new_doc("ILL Consent Record")
		consent_doc.email = email
		consent_doc.consent_type = "Marketing Communications"
		consent_doc.consent_given = 1
		# consent_timestamp is auto-set by before_insert hook
		consent_doc.marketing_form = form_name
		consent_doc.ip_address = ip_address
		consent_doc.user_agent = user_agent[:MAX_USER_AGENT_LENGTH] if user_agent else ""
		consent_doc.utm_source = utm_params.get("utm_source", "")
		consent_doc.utm_medium = utm_params.get("utm_medium", "")
		consent_doc.utm_campaign = utm_params.get("utm_campaign", "")
		consent_doc.utm_content = utm_params.get("utm_content", "")
		consent_doc.consent_text_shown = form.gdpr_consent_text or ""

		if lead_source and frappe.db.exists("ILL Lead Source", lead_source):
			consent_doc.lead_source = lead_source

		consent_doc.insert(ignore_permissions=True)

	# Create or update email preference
	get_or_create_email_preference(email)

	# Create Lead in ERPNext (if Lead doctype exists)
	lead_data = None
	if frappe.db.exists("DocType", "Lead"):
		try:
			lead_data = create_lead(email, kwargs, utm_params, lead_source, form.form_type)
		except Exception as e:
			frappe.log_error(f"Lead creation failed: {e}", "Marketing Form Submission")

	# Send notification email
	if form.notification_email:
		try:
			send_notification_email(form, email, kwargs, utm_params)
		except Exception as e:
			frappe.log_error(f"Notification email failed: {e}", "Marketing Form Submission")

	return {
		"success": True,
		"message": form.success_message or "Thank you for your submission.",
		"redirect_url": form.redirect_url or None,
		"lead_name": lead_data.get("name") if lead_data else None,
	}


def create_lead(email, form_data, utm_params, lead_source, form_type):
	"""
	Create a Lead record from form submission.

	Args:
		email: Submitter's email
		form_data: Form field values
		utm_params: UTM parameters
		lead_source: Lead source name
		form_type: Type of form submitted

	Returns:
		dict with lead name
	"""
	# Check if lead already exists
	existing_lead = frappe.db.get_value("Lead", {"email_id": email}, "name")
	if existing_lead:
		# Update existing lead with new campaign info if different
		return {"name": existing_lead, "is_new": False}

	lead = frappe.new_doc("Lead")
	lead.email_id = email
	lead.lead_name = f"{form_data.get('first_name', '')} {form_data.get('last_name', '')}".strip() or email
	lead.first_name = form_data.get("first_name", "")
	lead.last_name = form_data.get("last_name", "")
	lead.company_name = form_data.get("company", "")
	lead.phone = form_data.get("phone", "")

	# Set source if Lead has this field
	if hasattr(lead, "source") and lead_source:
		lead.source = lead_source

	# Add campaign info to notes if Lead has notes field
	if hasattr(lead, "notes"):
		campaign_info = []
		if utm_params.get("utm_source"):
			campaign_info.append(f"UTM Source: {utm_params['utm_source']}")
		if utm_params.get("utm_medium"):
			campaign_info.append(f"UTM Medium: {utm_params['utm_medium']}")
		if utm_params.get("utm_campaign"):
			campaign_info.append(f"UTM Campaign: {utm_params['utm_campaign']}")
		if form_data.get("message"):
			campaign_info.append(f"Message: {form_data['message']}")

		if campaign_info:
			lead.notes = "\n".join(campaign_info)

	lead.insert(ignore_permissions=True)
	return {"name": lead.name, "is_new": True}


def send_notification_email(form, submitter_email, form_data, utm_params):
	"""
	Send notification email about form submission.

	Args:
		form: ILL Marketing Form document
		submitter_email: Email of form submitter
		form_data: Form field values
		utm_params: UTM parameters
	"""
	subject = f"New {form.form_type} Submission from {submitter_email}"

	# Build message content
	lines = [
		"<p>A new form submission was received:</p>",
		f"<p><strong>Form:</strong> {form.form_name}</p>",
		f"<p><strong>Email:</strong> {submitter_email}</p>",
	]

	if form_data.get("first_name") or form_data.get("last_name"):
		lines.append(
			f"<p><strong>Name:</strong> {form_data.get('first_name', '')} {form_data.get('last_name', '')}</p>"
		)
	if form_data.get("company"):
		lines.append(f"<p><strong>Company:</strong> {form_data.get('company')}</p>")
	if form_data.get("phone"):
		lines.append(f"<p><strong>Phone:</strong> {form_data.get('phone')}</p>")
	if form_data.get("message"):
		lines.append(f"<p><strong>Message:</strong> {form_data.get('message')}</p>")

	# Add UTM info
	if any(utm_params.values()):
		lines.append("<hr><p><strong>Campaign Info:</strong></p>")
		for key, value in utm_params.items():
			if value:
				lines.append(f"<p>{key}: {value}</p>")

	message = "\n".join(lines)

	frappe.sendmail(
		recipients=[form.notification_email],
		subject=subject,
		message=message,
		now=True,
	)


@frappe.whitelist(allow_guest=True)
def unsubscribe(token, email_type=None):
	"""
	Process an unsubscribe request.

	Args:
		token: Unsubscribe token from email link
		email_type: Optional specific email type to unsubscribe from

	Returns:
		dict with success status and message
	"""
	if not token:
		return {"success": False, "message": "Invalid request"}

	result = process_unsubscribe(token, email_type)
	return result


@frappe.whitelist(allow_guest=True)
def get_email_preferences(token):
	"""
	Get email preferences for preference center.

	Args:
		token: Unsubscribe token for authentication

	Returns:
		dict with current email preferences
	"""
	if not token:
		return {"success": False, "message": "Invalid request"}

	pref = frappe.db.get_value(
		"ILL Email Preference",
		{"unsubscribe_token": token},
		[
			"email",
			"global_unsubscribe",
			"marketing_emails",
			"newsletter_emails",
			"product_updates",
			"dealer_communications",
		],
		as_dict=True,
	)

	if not pref:
		return {"success": False, "message": "Invalid token"}

	return {
		"success": True,
		"email": pref.email,
		"preferences": {
			"global_unsubscribe": pref.global_unsubscribe,
			"marketing_emails": pref.marketing_emails,
			"newsletter_emails": pref.newsletter_emails,
			"product_updates": pref.product_updates,
			"dealer_communications": pref.dealer_communications,
		},
	}


@frappe.whitelist(allow_guest=True)
def update_email_preferences(token, **kwargs):
	"""
	Update email preferences from preference center.

	Args:
		token: Unsubscribe token for authentication
		**kwargs: Preference values to update

	Returns:
		dict with success status
	"""
	if not token:
		return {"success": False, "message": "Invalid request"}

	pref_name = frappe.db.get_value(
		"ILL Email Preference",
		{"unsubscribe_token": token},
		"name",
	)

	if not pref_name:
		return {"success": False, "message": "Invalid token"}

	doc = frappe.get_doc("ILL Email Preference", pref_name)

	# Update preferences
	for field in [
		"global_unsubscribe",
		"marketing_emails",
		"newsletter_emails",
		"product_updates",
		"dealer_communications",
	]:
		if field in kwargs:
			value = kwargs[field]
			if isinstance(value, str):
				value = value.lower() in ("true", "1", "yes", "on")
			setattr(doc, field, 1 if value else 0)

	doc.save(ignore_permissions=True)

	return {"success": True, "message": "Preferences updated successfully"}


@frappe.whitelist(allow_guest=True)
def get_active_lead_sources():
	"""
	Get list of active lead sources for form dropdowns.

	Returns:
		list of active lead source names
	"""
	return frappe.get_all(
		"ILL Lead Source",
		filters={"is_active": 1},
		fields=["source_name", "source_type"],
		order_by="source_name",
	)
