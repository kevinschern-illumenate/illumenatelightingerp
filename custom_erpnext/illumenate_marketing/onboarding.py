# Copyright (c) 2024, ilLumenate Lighting and contributors
# For license information, please see license.txt

"""
Dealer Onboarding Module

Provides functionality for automated dealer account provisioning upon approval.
Creates Customer, Contact, User, and sends welcome email with credentials.
"""

import secrets

import frappe
from frappe import _
from frappe.utils import now_datetime


@frappe.whitelist()
def provision_dealer_account(application_name):
	"""
	Provision dealer account upon approval.

	Called by n8n upon approval or directly from ILL Dealer Application.
	Creates:
	1. Customer (with Dealer price list)
	2. Contact (linked to Customer)
	3. User (with Portal access)
	4. Sends credentials email

	Args:
		application_name: Name of the ILL Dealer Application document

	Returns:
		dict with created records and status
	"""
	if not frappe.db.exists("ILL Dealer Application", application_name):
		frappe.throw(_("Dealer Application {0} not found").format(application_name))

	app = frappe.get_doc("ILL Dealer Application", application_name)

	if app.status != "Approved":
		frappe.throw(_("Application must be approved before provisioning"))

	if app.customer:
		return {
			"success": True,
			"message": "Dealer account already provisioned",
			"customer": app.customer,
			"contact": app.contact,
			"user": app.user,
		}

	try:
		# 1. Create Customer
		customer = _create_customer(app)

		# 2. Create Contact linked to Customer
		contact = _create_contact(app, customer.name)

		# 3. Create User with portal access
		user, password = _create_user(app, contact.name)

		# 4. Update application with provisioned records
		app.customer = customer.name
		app.contact = contact.name
		app.user = user.name
		app.provisioned_on = now_datetime()
		app.save(ignore_permissions=True)

		# 5. Send welcome email with credentials
		send_dealer_welcome_email(user, password, app)

		# 6. Emit n8n event if enabled
		_emit_provisioning_event(app, customer.name, contact.name, user.name)

		return {
			"success": True,
			"message": "Dealer account provisioned successfully",
			"customer": customer.name,
			"contact": contact.name,
			"user": user.name,
		}

	except Exception as e:
		frappe.log_error(
			f"Failed to provision dealer account for {application_name}: {e}",
			"Dealer Provisioning Error",
		)
		raise


def _create_customer(app):
	"""
	Create a Customer record for the dealer.

	Args:
		app: ILL Dealer Application document

	Returns:
		Customer document
	"""
	customer = frappe.new_doc("Customer")
	customer.customer_name = app.company_name
	customer.customer_type = "Company"

	# Set customer group to "Dealer" if it exists, otherwise use default
	if frappe.db.exists("Customer Group", "Dealer"):
		customer.customer_group = "Dealer"

	# Set default price list based on requested tier
	price_list = app.requested_tier or "Dealer D"
	if frappe.db.exists("Price List", price_list):
		customer.default_price_list = price_list
	elif frappe.db.exists("Price List", "MSRP"):
		customer.default_price_list = "MSRP"

	customer.insert(ignore_permissions=True)

	# Create Address if provided
	if app.address_line1 or app.city:
		_create_address(app, customer.name)

	return customer


def _create_address(app, customer_name):
	"""
	Create an Address for the customer.

	Args:
		app: ILL Dealer Application document
		customer_name: Customer document name
	"""
	address = frappe.new_doc("Address")
	address.address_title = app.company_name
	address.address_type = "Billing"
	address.address_line1 = app.address_line1 or ""
	address.address_line2 = app.address_line2 or ""
	address.city = app.city or ""
	address.state = app.state or ""
	address.pincode = app.postal_code or ""
	address.country = app.country or "United States"

	# Link to Customer
	address.append("links", {"link_doctype": "Customer", "link_name": customer_name})

	address.insert(ignore_permissions=True)


def _create_contact(app, customer_name):
	"""
	Create a Contact record linked to the Customer.

	Args:
		app: ILL Dealer Application document
		customer_name: Customer document name

	Returns:
		Contact document
	"""
	contact = frappe.new_doc("Contact")
	contact.first_name = app.contact_first_name
	contact.last_name = app.contact_last_name
	contact.email_id = app.email

	# Add email to child table
	contact.append("email_ids", {"email_id": app.email, "is_primary": 1})

	# Add phone if provided
	if app.phone:
		contact.append("phone_nos", {"phone": app.phone, "is_primary_phone": 1})

	# Link to Customer
	contact.append("links", {"link_doctype": "Customer", "link_name": customer_name})

	contact.insert(ignore_permissions=True)

	return contact


def _create_user(app, contact_name):
	"""
	Create a User with portal access for the dealer.

	Args:
		app: ILL Dealer Application document
		contact_name: Contact document name

	Returns:
		tuple of (User document, plaintext password)
	"""
	# Check if user already exists
	if frappe.db.exists("User", app.email):
		user = frappe.get_doc("User", app.email)
		# Generate new password for existing user
		password = secrets.token_urlsafe(12)
		user.new_password = password
		user.save(ignore_permissions=True)
		return user, password

	# Generate secure password
	password = secrets.token_urlsafe(12)

	user = frappe.new_doc("User")
	user.email = app.email
	user.first_name = app.contact_first_name
	user.last_name = app.contact_last_name
	user.new_password = password
	user.send_welcome_email = 0  # We'll send our own welcome email

	# Set user type for portal access
	user.user_type = "Website User"

	user.insert(ignore_permissions=True)

	# Add Customer role for portal access
	user.add_roles("Customer")

	# Link User to Contact
	contact = frappe.get_doc("Contact", contact_name)
	contact.user = user.name
	contact.save(ignore_permissions=True)

	return user, password


def send_dealer_welcome_email(user, password, app):
	"""
	Send welcome email with login credentials to new dealer.

	Args:
		user: User document
		password: Plaintext password
		app: ILL Dealer Application document
	"""
	# Get the site URL
	site_url = frappe.utils.get_url()

	subject = "Welcome to ilLumenate Lighting - Your Dealer Account is Ready!"

	message = f"""
	<p>Dear {app.contact_first_name},</p>

	<p>Congratulations! Your dealer application for <strong>{app.company_name}</strong> has been approved.</p>

	<p>Your dealer account has been created with the following details:</p>

	<table style="border-collapse: collapse; margin: 20px 0;">
		<tr>
			<td style="padding: 8px; border: 1px solid #ddd;"><strong>Login Email:</strong></td>
			<td style="padding: 8px; border: 1px solid #ddd;">{user.email}</td>
		</tr>
		<tr>
			<td style="padding: 8px; border: 1px solid #ddd;"><strong>Temporary Password:</strong></td>
			<td style="padding: 8px; border: 1px solid #ddd;">{password}</td>
		</tr>
		<tr>
			<td style="padding: 8px; border: 1px solid #ddd;"><strong>Pricing Tier:</strong></td>
			<td style="padding: 8px; border: 1px solid #ddd;">{app.requested_tier or "Dealer D"}</td>
		</tr>
	</table>

	<p>Please log in at <a href="{site_url}">{site_url}</a> and change your password immediately.</p>

	<p>As a dealer, you now have access to:</p>
	<ul>
		<li>Exclusive dealer pricing</li>
		<li>Product configurator</li>
		<li>Project management portal</li>
		<li>Fixture schedule builder</li>
	</ul>

	<p>If you have any questions, please don't hesitate to contact us.</p>

	<p>Best regards,<br>
	The ilLumenate Lighting Team</p>
	"""

	try:
		frappe.sendmail(
			recipients=[user.email],
			subject=subject,
			message=message,
			now=True,
		)
	except Exception as e:
		frappe.log_error(f"Failed to send dealer welcome email to {user.email}: {e}", "Dealer Welcome Email Error")


def _emit_provisioning_event(app, customer_name, contact_name, user_name):
	"""
	Emit n8n event for dealer provisioning.

	Args:
		app: ILL Dealer Application document
		customer_name: Created Customer name
		contact_name: Created Contact name
		user_name: Created User name
	"""
	from custom_erpnext.illumenate_marketing.doctype.ill_n8n_settings.ill_n8n_settings import (
		is_n8n_enabled,
	)

	if not is_n8n_enabled():
		return

	from custom_erpnext.illumenate_marketing.api import emit_marketing_event

	try:
		emit_marketing_event(
			event_type="dealer_provisioned",
			doctype="ILL Dealer Application",
			docname=app.name,
			data={
				"email": app.email,
				"company_name": app.company_name,
				"customer": customer_name,
				"contact": contact_name,
				"user": user_name,
				"pricing_tier": app.requested_tier,
			},
		)
	except Exception as e:
		frappe.log_error(f"Failed to emit dealer_provisioned event: {e}", "n8n Event Error")
