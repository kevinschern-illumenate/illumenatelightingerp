# Copyright (c) 2024, ilLumenate Lighting and contributors
# For license information, please see license.txt

"""
n8n Events Module

Handles document events that trigger n8n marketing automation.
This module contains the event handlers for Lead creation, purchase completion,
and journey updates.
"""

import frappe


def on_lead_created(doc, method=None):
	"""
	Handle Lead creation event.

	This function is called when a new Lead is created in ERPNext.
	It emits a marketing event to n8n and updates the marketing journey.

	Args:
		doc: The Lead document
		method: The event method (after_insert)
	"""
	from custom_erpnext.illumenate_marketing.api import emit_marketing_event
	from custom_erpnext.illumenate_marketing.doctype.ill_marketing_journey.ill_marketing_journey import (
		update_journey_to_lead,
	)
	from custom_erpnext.illumenate_marketing.doctype.ill_n8n_settings.ill_n8n_settings import (
		is_n8n_enabled,
	)

	email = doc.email_id if hasattr(doc, "email_id") else None
	if not email:
		return

	# Update the marketing journey to Lead stage
	try:
		update_journey_to_lead(email, lead=doc.name)
	except Exception as e:
		frappe.log_error(f"Failed to update journey for lead {doc.name}: {e}", "Lead Journey Update")

	# Emit event to n8n if enabled
	if is_n8n_enabled():
		try:
			emit_marketing_event(
				event_type="lead_created",
				doctype="Lead",
				docname=doc.name,
				data={
					"email": email,
					"lead_name": doc.lead_name,
					"source": doc.source if hasattr(doc, "source") else None,
					"company_name": doc.company_name if hasattr(doc, "company_name") else None,
				},
			)
		except Exception as e:
			frappe.log_error(f"Failed to emit lead_created event: {e}", "n8n Event Error")


def on_purchase_completed(doc, method=None):
	"""
	Handle Sales Order or Sales Invoice submission.

	This function is called when a Sales Order or Sales Invoice is submitted.
	It emits a purchase_completed event to n8n and updates the marketing journey
	to Customer stage.

	Args:
		doc: The Sales Order or Sales Invoice document
		method: The event method (on_submit)
	"""
	from custom_erpnext.illumenate_marketing.api import emit_marketing_event
	from custom_erpnext.illumenate_marketing.doctype.ill_marketing_journey.ill_marketing_journey import (
		update_journey_to_customer,
	)
	from custom_erpnext.illumenate_marketing.doctype.ill_n8n_settings.ill_n8n_settings import (
		is_n8n_enabled,
	)

	# Get email from contact or customer
	email = _get_email_from_order(doc)
	customer_name = doc.customer if hasattr(doc, "customer") else None

	if not email:
		return

	# Update the marketing journey to Customer stage
	try:
		update_journey_to_customer(email, customer=customer_name)
	except Exception as e:
		frappe.log_error(
			f"Failed to update journey for {doc.doctype} {doc.name}: {e}",
			"Purchase Journey Update",
		)

	# Emit event to n8n if enabled
	if is_n8n_enabled():
		try:
			emit_marketing_event(
				event_type="purchase_completed",
				doctype=doc.doctype,
				docname=doc.name,
				data={
					"email": email,
					"customer": customer_name,
					"customer_name": doc.customer_name if hasattr(doc, "customer_name") else None,
					"grand_total": float(doc.grand_total) if hasattr(doc, "grand_total") else None,
					"currency": doc.currency if hasattr(doc, "currency") else None,
				},
			)
		except Exception as e:
			frappe.log_error(f"Failed to emit purchase_completed event: {e}", "n8n Event Error")


def _get_email_from_order(doc):
	"""
	Get email address from a Sales Order or Sales Invoice.

	Attempts to find email from:
	1. contact_email field on document
	2. Customer's primary contact
	3. Customer's email_id field

	Args:
		doc: Sales Order or Sales Invoice document

	Returns:
		Email address string or None
	"""
	# Try direct email field
	if hasattr(doc, "contact_email") and doc.contact_email:
		return doc.contact_email

	# Try to get from customer
	customer = doc.customer if hasattr(doc, "customer") else None
	if not customer:
		return None

	# Check if Customer doctype has email
	customer_email = frappe.db.get_value("Customer", customer, "email_id")
	if customer_email:
		return customer_email

	# Try to find primary contact for customer
	contact = frappe.db.get_value(
		"Dynamic Link",
		{"link_doctype": "Customer", "link_name": customer, "parenttype": "Contact"},
		"parent",
	)
	if contact:
		contact_email = frappe.db.get_value("Contact", contact, "email_id")
		if contact_email:
			return contact_email

	return None
