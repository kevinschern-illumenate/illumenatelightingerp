# Copyright (c) 2024, ilLumenate Lighting and contributors
# For license information, please see license.txt

import secrets

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class ILLEmailLog(Document):
	"""
	ILL Email Log DocType.

	Tracks email delivery status including sent, opened, and clicked events.
	"""

	def before_insert(self):
		"""Generate tracking ID before insert."""
		if not self.tracking_id:
			self.tracking_id = secrets.token_urlsafe(32)

	def mark_as_sent(self):
		"""Mark email as sent."""
		self.status = "Sent"
		self.sent_at = now_datetime()
		self.save(ignore_permissions=True)

	def mark_as_failed(self, error_message=None):
		"""Mark email as failed."""
		self.status = "Failed"
		if error_message:
			self.error_message = str(error_message)[:500]
		self.save(ignore_permissions=True)

	def record_open(self):
		"""Record an email open event."""
		self.opened_count = (self.opened_count or 0) + 1
		if not self.opened_at:
			self.opened_at = now_datetime()
		if self.status in ("Sent", "Pending"):
			self.status = "Opened"
		self.save(ignore_permissions=True)

	def record_click(self):
		"""Record a link click event."""
		self.clicked_count = (self.clicked_count or 0) + 1
		if not self.clicked_at:
			self.clicked_at = now_datetime()
		# Clicked implies opened
		if not self.opened_at:
			self.opened_at = now_datetime()
			self.opened_count = (self.opened_count or 0) + 1
		if self.status in ("Sent", "Pending", "Opened"):
			self.status = "Clicked"
		self.save(ignore_permissions=True)


def create_email_log(
	recipient_email,
	email_type="Welcome Email",
	lead=None,
	lead_source=None,
	email_template=None,
	email_template_mapping=None,
	subject=None,
	from_email=None,
):
	"""
	Create a new email log entry.

	Args:
		recipient_email: Email address of the recipient
		email_type: Type of email (Welcome Email, Newsletter, etc.)
		lead: Lead document name (optional)
		lead_source: ILL Lead Source name (optional)
		email_template: Email Template name (optional)
		email_template_mapping: ILL Email Template Mapping name (optional)
		subject: Email subject (optional)
		from_email: Sender email address (optional)

	Returns:
		ILL Email Log document
	"""
	log = frappe.new_doc("ILL Email Log")
	log.recipient_email = recipient_email
	log.email_type = email_type
	log.status = "Pending"

	if lead:
		log.lead = lead
	if lead_source:
		log.lead_source = lead_source
	if email_template:
		log.email_template = email_template
	if email_template_mapping:
		log.email_template_mapping = email_template_mapping
	if subject:
		log.subject = subject
	if from_email:
		log.from_email = from_email

	log.insert(ignore_permissions=True)
	return log


def get_email_log_by_tracking_id(tracking_id):
	"""
	Get email log by tracking ID.

	Args:
		tracking_id: Unique tracking identifier

	Returns:
		ILL Email Log document or None
	"""
	log_name = frappe.db.get_value("ILL Email Log", {"tracking_id": tracking_id}, "name")
	if log_name:
		return frappe.get_doc("ILL Email Log", log_name)
	return None
