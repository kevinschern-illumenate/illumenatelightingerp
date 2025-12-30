# Copyright (c) 2024, ilLumenate Lighting and contributors
# For license information, please see license.txt

"""
Welcome Email Module

Provides functionality for sending automated welcome emails when leads are created.
Integrates with ILL Email Template Mapping to match lead sources to email templates
and ILL Email Log to track delivery status.
"""

import frappe
from frappe import _

from custom_erpnext.illumenate_marketing.doctype.ill_email_log.ill_email_log import create_email_log
from custom_erpnext.illumenate_marketing.doctype.ill_email_template_mapping.ill_email_template_mapping import (
	get_template_mapping_for_lead_source,
)


def send_welcome_email(doc, method=None):
	"""
	Hook function to send welcome email when a Lead is created.

	This function is called via the after_insert hook on the Lead doctype.
	It looks up the appropriate email template mapping based on the lead source
	and sends a welcome email to the lead's email address.

	Args:
		doc: The Lead document that was just created
		method: The method name (unused, standard hook parameter)
	"""
	# Skip if lead doesn't have an email
	email = getattr(doc, "email_id", None)
	if not email:
		return

	# Get lead source from the Lead document
	lead_source = getattr(doc, "source", None)

	# Find matching email template mapping
	mapping = get_template_mapping_for_lead_source(lead_source, trigger_event="Lead Created")
	if not mapping:
		# No active mapping found for this lead source
		return

	# Create email log entry first (in Pending status)
	email_log = create_email_log(
		recipient_email=email,
		email_type="Welcome Email",
		lead=doc.name,
		lead_source=lead_source,
		email_template=mapping.get("email_template"),
		email_template_mapping=mapping.get("name"),
	)

	# Check if there's a delay configured
	delay_minutes = mapping.get("delay_minutes", 0) or 0
	if delay_minutes > 0:
		# Queue the email to be sent later
		frappe.enqueue(
			"custom_erpnext.illumenate_marketing.email.send_email_from_template",
			queue="short",
			timeout=300,
			now=False,
			at_front=False,
			enqueue_after_commit=True,
			job_name=f"welcome_email_{doc.name}",
			email_log_name=email_log.name,
			lead_name=doc.name,
			mapping=mapping,
		)
	else:
		# Send immediately
		send_email_from_template(email_log.name, doc.name, mapping)


def send_email_from_template(email_log_name, lead_name, mapping):
	"""
	Send email using the specified template and update the email log.

	Args:
		email_log_name: Name of the ILL Email Log document
		lead_name: Name of the Lead document
		mapping: Email template mapping dict containing:
			- email_template: Name of the Email Template
			- subject_override: Optional subject override
			- from_email_override: Optional from email override
	"""
	try:
		email_log = frappe.get_doc("ILL Email Log", email_log_name)
		lead = frappe.get_doc("Lead", lead_name)
		email_template_name = mapping.get("email_template")

		if not email_template_name:
			email_log.mark_as_failed("No email template specified")
			return

		if not frappe.db.exists("Email Template", email_template_name):
			email_log.mark_as_failed(f"Email Template '{email_template_name}' not found")
			return

		email_template = frappe.get_doc("Email Template", email_template_name)

		# Prepare context for template rendering
		context = get_lead_context(lead)

		# Render subject and message
		subject = mapping.get("subject_override") or email_template.subject
		message = frappe.render_template(email_template.response, context)
		subject = frappe.render_template(subject, context)

		# Get sender email
		from_email = mapping.get("from_email_override")
		if not from_email:
			# Get default outgoing email from Email Account that is set as default outgoing
			from_email = frappe.db.get_value(
				"Email Account", {"default_outgoing": 1, "enable_outgoing": 1}, "email_id"
			)

		# Update log with email details
		email_log.subject = subject
		email_log.from_email = from_email
		email_log.save(ignore_permissions=True)

		# Send the email
		frappe.sendmail(
			recipients=[lead.email_id],
			subject=subject,
			message=message,
			reference_doctype="Lead",
			reference_name=lead.name,
			now=True,
		)

		# Mark as sent
		email_log.mark_as_sent()

	except Exception as e:
		frappe.log_error(f"Welcome email failed for {lead_name}: {e}", "Welcome Email Error")
		try:
			email_log = frappe.get_doc("ILL Email Log", email_log_name)
			email_log.mark_as_failed(str(e))
		except Exception:
			pass


def get_lead_context(lead):
	"""
	Build context dictionary for email template rendering.

	Args:
		lead: Lead document

	Returns:
		dict with template variables
	"""
	context = {
		"lead": lead,
		"lead_name": lead.lead_name or "",
		"first_name": getattr(lead, "first_name", "") or "",
		"last_name": getattr(lead, "last_name", "") or "",
		"email": lead.email_id or "",
		"company_name": getattr(lead, "company_name", "") or "",
		"phone": getattr(lead, "phone", "") or "",
	}

	# Add full name
	full_name = f"{context['first_name']} {context['last_name']}".strip()
	context["full_name"] = full_name or context["lead_name"]

	# Add greeting name (first name or lead name)
	context["greeting_name"] = context["first_name"] or context["lead_name"] or "there"

	return context


@frappe.whitelist(allow_guest=True)
def track_email_open(tracking_id):
	"""
	Track email open via tracking pixel.

	Args:
		tracking_id: Unique tracking identifier from email

	Returns:
		1x1 transparent GIF
	"""
	if tracking_id:
		try:
			from custom_erpnext.illumenate_marketing.doctype.ill_email_log.ill_email_log import (
				get_email_log_by_tracking_id,
			)

			email_log = get_email_log_by_tracking_id(tracking_id)
			if email_log:
				email_log.record_open()
		except Exception as e:
			frappe.log_error(f"Email open tracking failed: {e}", "Email Tracking Error")

	# Return 1x1 transparent GIF
	import base64

	gif = base64.b64decode("R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7")
	frappe.response["type"] = "binary"
	frappe.response["filename"] = "pixel.gif"
	frappe.response["filecontent"] = gif


@frappe.whitelist(allow_guest=True)
def track_email_click(tracking_id, redirect_url=None):
	"""
	Track email link click and redirect.

	Args:
		tracking_id: Unique tracking identifier from email
		redirect_url: URL to redirect to after tracking

	Returns:
		Redirect to the specified URL
	"""
	if tracking_id:
		try:
			from custom_erpnext.illumenate_marketing.doctype.ill_email_log.ill_email_log import (
				get_email_log_by_tracking_id,
			)

			email_log = get_email_log_by_tracking_id(tracking_id)
			if email_log:
				email_log.record_click()
		except Exception as e:
			frappe.log_error(f"Email click tracking failed: {e}", "Email Tracking Error")

	# Redirect to the specified URL or home page
	frappe.local.response["type"] = "redirect"
	frappe.local.response["location"] = redirect_url or "/"
