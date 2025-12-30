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
		if form_data.get("business_type"):
			campaign_info.append(f"Business Type: {form_data['business_type']}")
		if form_data.get("years_in_business"):
			campaign_info.append(f"Years in Business: {form_data['years_in_business']}")
		if form_data.get("website"):
			campaign_info.append(f"Website: {form_data['website']}")
		if form_data.get("resale_certificate_url"):
			campaign_info.append(f"Resale Certificate: {form_data['resale_certificate_url']}")

		if campaign_info:
			lead.notes = "\n".join(campaign_info)

	lead.insert(ignore_permissions=True)

	# Attach resale certificate to lead if provided
	resale_cert_url = form_data.get("resale_certificate_url")
	if resale_cert_url:
		try:
			# Link the already uploaded file to the Lead document
			existing_file = frappe.db.get_value("File", {"file_url": resale_cert_url}, "name")
			if existing_file:
				file_doc = frappe.get_doc("File", existing_file)
				file_doc.attached_to_doctype = "Lead"
				file_doc.attached_to_name = lead.name
				file_doc.save(ignore_permissions=True)
		except Exception as e:
			frappe.log_error(f"Failed to attach resale certificate: {e}", "Dealer Inquiry File Attachment")

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


# ============================================================================
# n8n Integration Endpoints
# ============================================================================


def _validate_n8n_api_key():
	"""
	Validate the API key from the request against stored settings.

	Returns:
		bool indicating if the API key is valid

	Raises:
		frappe.AuthenticationError if API key is missing or invalid
	"""
	from custom_erpnext.illumenate_marketing.doctype.ill_n8n_settings.ill_n8n_settings import (
		get_n8n_settings,
	)

	settings = get_n8n_settings()
	if not settings.get("api_key"):
		frappe.throw(_("n8n API Key is not configured"), frappe.AuthenticationError)

	# Get API key from request headers or body
	request_api_key = None
	if frappe.request:
		request_api_key = frappe.request.headers.get("X-API-Key") or frappe.request.headers.get(
			"Authorization"
		)
		if request_api_key and request_api_key.startswith("Bearer "):
			request_api_key = request_api_key[7:]

	if not request_api_key:
		# Try getting from form data
		request_api_key = frappe.form_dict.get("api_key")

	if not request_api_key or request_api_key != settings["api_key"]:
		frappe.throw(_("Invalid API Key"), frappe.AuthenticationError)

	return True


@frappe.whitelist(allow_guest=False)
def n8n_webhook_handler(action=None, **kwargs):
	"""
	Receive callbacks from n8n workflows.

	This endpoint allows n8n to update contact status, journey stages,
	and other marketing data in ERPNext.

	Args:
		action: The action to perform. Supported actions:
			- update_journey_stage: Update a contact's journey stage
			- update_contact_status: Update contact/lead status
			- log_event: Log a marketing event
		**kwargs: Action-specific parameters

	Returns:
		dict with success status and result data
	"""
	from custom_erpnext.illumenate_marketing.doctype.ill_n8n_settings.ill_n8n_settings import (
		is_n8n_enabled,
	)

	if not is_n8n_enabled():
		return {"success": False, "error": "n8n integration is not enabled"}

	# Validate API key
	_validate_n8n_api_key()

	if not action:
		return {"success": False, "error": "Action is required"}

	# Handle different actions
	if action == "update_journey_stage":
		return _handle_update_journey_stage(kwargs)
	elif action == "update_contact_status":
		return _handle_update_contact_status(kwargs)
	elif action == "log_event":
		return _handle_log_event(kwargs)
	else:
		return {"success": False, "error": f"Unknown action: {action}"}


def _handle_update_journey_stage(data):
	"""Handle updating a contact's journey stage."""
	from custom_erpnext.illumenate_marketing.doctype.ill_marketing_journey.ill_marketing_journey import (
		get_or_create_journey,
	)

	email = data.get("email")
	new_stage = data.get("stage")
	reason = data.get("reason", "Updated via n8n webhook")

	if not email:
		return {"success": False, "error": "Email is required"}
	if not new_stage:
		return {"success": False, "error": "Stage is required"}

	try:
		journey = get_or_create_journey(email)
		journey.update_stage(new_stage, reason)
		return {
			"success": True,
			"message": f"Journey updated to {new_stage}",
			"journey_name": journey.name,
		}
	except Exception as e:
		frappe.log_error(f"n8n webhook error: {e}", "n8n Webhook Handler")
		return {"success": False, "error": str(e)}


def _handle_update_contact_status(data):
	"""Handle updating a contact or lead status."""
	doctype = data.get("doctype", "Lead")
	docname = data.get("docname")
	email = data.get("email")
	status = data.get("status")

	if not (docname or email):
		return {"success": False, "error": "Either docname or email is required"}
	if not status:
		return {"success": False, "error": "Status is required"}

	try:
		# Find the document
		if not docname and email:
			if doctype == "Lead":
				docname = frappe.db.get_value("Lead", {"email_id": email}, "name")
			elif doctype == "Contact":
				docname = frappe.db.get_value("Contact", {"email_id": email}, "name")

		if not docname:
			return {"success": False, "error": f"{doctype} not found"}

		doc = frappe.get_doc(doctype, docname)

		# Update status field (if it exists)
		if hasattr(doc, "status"):
			doc.status = status
			doc.save(ignore_permissions=True)
			return {"success": True, "message": f"{doctype} status updated to {status}"}
		else:
			return {"success": False, "error": f"{doctype} does not have a status field"}

	except Exception as e:
		frappe.log_error(f"n8n webhook error: {e}", "n8n Webhook Handler")
		return {"success": False, "error": str(e)}


def _handle_log_event(data):
	"""Handle logging a marketing event."""
	event_type = data.get("event_type")
	email = data.get("email")
	event_data = data.get("data", {})

	if not event_type:
		return {"success": False, "error": "Event type is required"}

	try:
		# Log the event using info logging (not error)
		frappe.logger("n8n").info(f"Marketing Event: {event_type} for {email} - Data: {event_data}")
		return {"success": True, "message": f"Event {event_type} logged"}
	except Exception as e:
		frappe.log_error(f"n8n webhook error: {e}", "n8n Webhook Handler")
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def emit_marketing_event(event_type, doctype=None, docname=None, data=None):
	"""
	Push events to n8n webhook URL.

	This function emits marketing events that n8n can consume to trigger
	automated workflows.

	Args:
		event_type: Type of event (e.g., 'lead_created', 'purchase_completed', 'journey_changed')
		doctype: Optional DocType that triggered the event
		docname: Optional document name that triggered the event
		data: Optional additional data to include in the event

	Returns:
		dict with success status
	"""
	import json

	import requests

	from custom_erpnext.illumenate_marketing.doctype.ill_n8n_settings.ill_n8n_settings import (
		get_n8n_settings,
	)

	settings = get_n8n_settings()

	if not settings.get("enabled"):
		return {"success": False, "message": "n8n integration is not enabled"}

	if not settings.get("n8n_webhook_url"):
		return {"success": False, "message": "n8n webhook URL is not configured"}

	# Check if this event type should be emitted
	event_settings_map = {
		"lead_created": "emit_lead_created",
		"lead_converted": "emit_lead_converted",
		"purchase_completed": "emit_purchase_completed",
		"journey_changed": "emit_journey_changed",
	}

	if event_type in event_settings_map:
		setting_key = event_settings_map[event_type]
		if not settings.get(setting_key):
			return {"success": False, "message": f"Event type {event_type} is disabled"}

	# Prepare the payload
	payload = {
		"event_type": event_type,
		"timestamp": frappe.utils.now(),
		"source": "erpnext",
		"doctype": doctype,
		"docname": docname,
		"data": data or {},
	}

	# Add document data if doctype and docname are provided
	if doctype and docname and frappe.db.exists(doctype, docname):
		try:
			doc = frappe.get_doc(doctype, docname)
			# Include basic document fields
			payload["document"] = {
				"name": doc.name,
				"doctype": doc.doctype,
				"creation": str(doc.creation) if doc.creation else None,
				"modified": str(doc.modified) if doc.modified else None,
			}
			# Add email if available
			email_fields = ["email", "email_id", "contact_email"]
			for field in email_fields:
				if hasattr(doc, field) and getattr(doc, field):
					payload["document"]["email"] = getattr(doc, field)
					break
		except Exception:
			pass

	# Send to n8n webhook
	webhook_url = f"{settings['n8n_webhook_url']}/marketing-events"

	try:
		headers = {"Content-Type": "application/json"}
		if settings.get("api_key"):
			headers["X-API-Key"] = settings["api_key"]

		# Use frappe's background job for async HTTP request
		frappe.enqueue(
			_send_webhook_request,
			queue="short",
			webhook_url=webhook_url,
			payload=json.dumps(payload),
			headers=headers,
			now=frappe.flags.in_test,
		)

		return {"success": True, "message": f"Event {event_type} queued for delivery"}

	except Exception as e:
		frappe.log_error(f"Failed to emit marketing event: {e}", "n8n Event Emission")
		return {"success": False, "error": str(e)}


def _send_webhook_request(webhook_url, payload, headers):
	"""
	Send webhook request to n8n.

	This runs as a background job to avoid blocking the main request.

	Args:
		webhook_url: The n8n webhook endpoint URL
		payload: JSON-serialized payload string
		headers: HTTP headers dict
	"""
	import requests

	try:
		response = requests.post(
			webhook_url,
			data=payload.encode("utf-8") if isinstance(payload, str) else payload,
			headers=headers,
			timeout=30,
		)
		if response.status_code >= 400:
			frappe.log_error(
				f"n8n webhook failed: {response.status_code} - {response.text}",
				"n8n Webhook Error",
			)
	except Exception as e:
		frappe.log_error(f"n8n webhook request failed: {e}", "n8n Webhook Error")


# ============================================================================
# Customer Lifetime Value (LTV) APIs - Sprint 6
# ============================================================================


@frappe.whitelist()
def get_customer_ltv(customer_name):
	"""
	Return lifetime value metrics for a customer.

	This API is designed for n8n workflows to consume customer LTV data
	for targeted promotions and marketing automation.

	Args:
		customer_name: The Customer doctype name/ID

	Returns:
		dict with lifetime_value, order_count, last_order, product_categories
	"""
	if not customer_name:
		frappe.throw(_("Customer name is required"))

	# Validate customer exists
	if not frappe.db.exists("Customer", customer_name):
		frappe.throw(_("Customer not found: {0}").format(customer_name))

	# Query Sales Invoice for LTV metrics
	result = frappe.db.sql(
		"""
		SELECT
			COALESCE(SUM(grand_total), 0) as lifetime_value,
			COUNT(*) as order_count,
			MAX(posting_date) as last_order
		FROM `tabSales Invoice`
		WHERE customer = %s AND docstatus = 1
		""",
		customer_name,
		as_dict=True,
	)

	ltv_data = result[0] if result else {"lifetime_value": 0, "order_count": 0, "last_order": None}

	# Get distinct product categories from Sales Invoice Items
	categories = frappe.db.sql(
		"""
		SELECT DISTINCT sii.item_group
		FROM `tabSales Invoice Item` sii
		JOIN `tabSales Invoice` si ON sii.parent = si.name
		WHERE si.customer = %s AND si.docstatus = 1 AND sii.item_group IS NOT NULL
		""",
		customer_name,
	)

	ltv_data["product_categories"] = [row[0] for row in categories] if categories else []
	ltv_data["customer_name"] = customer_name

	return ltv_data


@frappe.whitelist()
def get_high_ltv_customers(min_lifetime_value=1000, limit=100):
	"""
	Query customers who have spent at or above a minimum lifetime value.

	This API is designed for n8n workflows to identify high-value customers
	for targeted promotions.

	Args:
		min_lifetime_value: Minimum lifetime value threshold (default $1000)
		limit: Maximum number of customers to return (default 100)

	Returns:
		list of customers with their LTV metrics
	"""
	min_lifetime_value = float(min_lifetime_value)
	limit = int(limit)

	# Query customers with LTV >= threshold
	customers = frappe.db.sql(
		"""
		SELECT
			si.customer as customer_name,
			c.customer_name as customer_display_name,
			c.email_id as customer_email,
			SUM(si.grand_total) as lifetime_value,
			COUNT(si.name) as order_count,
			MAX(si.posting_date) as last_order
		FROM `tabSales Invoice` si
		JOIN `tabCustomer` c ON si.customer = c.name
		WHERE si.docstatus = 1
		GROUP BY si.customer, c.customer_name, c.email_id
		HAVING SUM(si.grand_total) >= %s
		ORDER BY lifetime_value DESC
		LIMIT %s
		""",
		(min_lifetime_value, limit),
		as_dict=True,
	)

	return customers


@frappe.whitelist()
def generate_promo_code(customer_name, discount_percent, valid_days=30, campaign=None):
	"""
	Generate a unique promotional code for a customer.

	This API creates a unique discount code that can be used for
	lifetime value-based promotions via n8n workflows.

	Args:
		customer_name: The Customer doctype name/ID
		discount_percent: Discount percentage (0-100)
		valid_days: Number of days the code is valid (default 30)
		campaign: Optional campaign name for tracking

	Returns:
		dict with promo_code and validity information
	"""
	import secrets

	if not customer_name:
		frappe.throw(_("Customer name is required"))

	# Validate customer exists
	if not frappe.db.exists("Customer", customer_name):
		frappe.throw(_("Customer not found: {0}").format(customer_name))

	# Validate discount percent
	discount_percent = float(discount_percent)
	if discount_percent < 0 or discount_percent > 100:
		frappe.throw(_("Discount percent must be between 0 and 100"))

	valid_days = int(valid_days)
	if valid_days < 1:
		frappe.throw(_("Valid days must be at least 1"))

	# Generate unique code
	code = f"ILL-{secrets.token_hex(4).upper()}"

	# Ensure uniqueness
	while frappe.db.exists("ILL Promo Code", code):
		code = f"ILL-{secrets.token_hex(4).upper()}"

	# Calculate validity dates
	from frappe.utils import add_days, today

	valid_from = today()
	valid_until = add_days(valid_from, valid_days)

	# Create Promo Code record
	promo = frappe.new_doc("ILL Promo Code")
	promo.promo_code = code
	promo.customer = customer_name
	promo.discount_percent = discount_percent
	promo.valid_from = valid_from
	promo.valid_until = valid_until
	promo.campaign = campaign
	promo.insert(ignore_permissions=True)

	return {
		"promo_code": code,
		"customer": customer_name,
		"discount_percent": discount_percent,
		"valid_from": valid_from,
		"valid_until": valid_until,
		"campaign": campaign,
	}


@frappe.whitelist()
def validate_promo_code(promo_code, customer_name=None):
	"""
	Validate a promo code and optionally check if it belongs to a specific customer.

	Args:
		promo_code: The promo code string
		customer_name: Optional customer to validate ownership

	Returns:
		dict with validation result and promo code details
	"""
	if not promo_code:
		return {"valid": False, "error": "Promo code is required"}

	if not frappe.db.exists("ILL Promo Code", promo_code):
		return {"valid": False, "error": "Promo code not found"}

	doc = frappe.get_doc("ILL Promo Code", promo_code)

	# Check customer if provided
	if customer_name and doc.customer != customer_name:
		return {"valid": False, "error": "Promo code does not belong to this customer"}

	# Check if already used
	if doc.is_used:
		return {"valid": False, "error": "Promo code has already been used"}

	# Check validity dates
	from frappe.utils import getdate, today

	today_date = getdate(today())

	if doc.valid_from and getdate(doc.valid_from) > today_date:
		return {"valid": False, "error": "Promo code is not yet valid"}

	if doc.valid_until and getdate(doc.valid_until) < today_date:
		return {"valid": False, "error": "Promo code has expired"}

	return {
		"valid": True,
		"promo_code": doc.promo_code,
		"customer": doc.customer,
		"discount_percent": doc.discount_percent,
		"valid_from": str(doc.valid_from),
		"valid_until": str(doc.valid_until),
	}


@frappe.whitelist()
def redeem_promo_code(promo_code, customer_name):
	"""
	Redeem a promo code, marking it as used.

	Args:
		promo_code: The promo code string
		customer_name: The customer redeeming the code

	Returns:
		dict with redemption result
	"""
	# First validate the code
	validation = validate_promo_code(promo_code, customer_name)

	if not validation.get("valid"):
		return {"success": False, "error": validation.get("error")}

	# Mark as used
	doc = frappe.get_doc("ILL Promo Code", promo_code)
	doc.mark_as_used()

	return {
		"success": True,
		"message": "Promo code redeemed successfully",
		"discount_percent": doc.discount_percent,
	}
