# Copyright (c) 2024, ilLumenate Lighting and contributors
# For license information, please see license.txt

import json

import frappe
from frappe.model.document import Document


class ILLMarketingJourney(Document):
	def before_insert(self):
		"""Set initial dates on creation."""
		if not self.prospect_date:
			self.prospect_date = frappe.utils.today()
		if not self.last_stage_change:
			self.last_stage_change = frappe.utils.now()
		self._log_stage_change("Prospect", "Initial creation")

	def validate(self):
		"""Validate journey record."""
		self.validate_email()

	def validate_email(self):
		"""Validate email format."""
		if self.contact_email:
			import re

			pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
			if not re.match(pattern, self.contact_email):
				frappe.throw("Invalid email format")

	def update_stage(self, new_stage, reason=None):
		"""
		Update the journey stage.

		Args:
			new_stage: The new stage (Prospect, Lead, or Customer)
			reason: Optional reason for the stage change
		"""
		valid_stages = ["Prospect", "Lead", "Customer"]
		if new_stage not in valid_stages:
			frappe.throw(f"Invalid stage: {new_stage}. Must be one of: {', '.join(valid_stages)}")

		old_stage = self.current_stage
		if old_stage == new_stage:
			return

		self.current_stage = new_stage
		self.last_stage_change = frappe.utils.now()

		# Set stage date
		if new_stage == "Lead" and not self.lead_date:
			self.lead_date = frappe.utils.today()
		elif new_stage == "Customer" and not self.customer_date:
			self.customer_date = frappe.utils.today()

		self._log_stage_change(new_stage, reason or f"Changed from {old_stage}")
		self.save(ignore_permissions=True)

		# Emit event for n8n
		from custom_erpnext.illumenate_marketing.api import emit_marketing_event

		emit_marketing_event(
			event_type="journey_changed",
			doctype="ILL Marketing Journey",
			docname=self.name,
			data={"old_stage": old_stage, "new_stage": new_stage, "email": self.contact_email},
		)

	def _log_stage_change(self, new_stage, reason):
		"""Log stage change to history."""
		history = []
		if self.stage_history:
			try:
				history = json.loads(self.stage_history)
			except (json.JSONDecodeError, TypeError):
				history = []

		history.append(
			{
				"stage": new_stage,
				"timestamp": frappe.utils.now(),
				"reason": reason,
			}
		)
		self.stage_history = json.dumps(history)


def get_or_create_journey(email, initial_stage="Prospect", lead=None, customer=None):
	"""
	Get or create a marketing journey for an email.

	Args:
		email: Contact email address
		initial_stage: Initial stage if creating new journey
		lead: Link to Lead doctype
		customer: Link to Customer doctype

	Returns:
		ILL Marketing Journey document
	"""
	existing = frappe.db.get_value("ILL Marketing Journey", {"contact_email": email}, "name")

	if existing:
		return frappe.get_doc("ILL Marketing Journey", existing)

	journey = frappe.new_doc("ILL Marketing Journey")
	journey.contact_email = email
	journey.current_stage = initial_stage
	if lead:
		journey.lead = lead
	if customer:
		journey.customer = customer
	journey.insert(ignore_permissions=True)
	return journey


def update_journey_to_customer(email, customer=None):
	"""
	Update a contact's journey to Customer stage.

	This is called when a purchase is completed.

	Args:
		email: Contact email address
		customer: Link to Customer doctype
	"""
	journey = get_or_create_journey(email, initial_stage="Customer", customer=customer)
	if journey.current_stage != "Customer":
		if customer:
			journey.customer = customer
		journey.update_stage("Customer", "Purchase completed")


def update_journey_to_lead(email, lead=None):
	"""
	Update a contact's journey to Lead stage.

	This is called when a lead is created.

	Args:
		email: Contact email address
		lead: Link to Lead doctype
	"""
	journey = get_or_create_journey(email, initial_stage="Lead", lead=lead)
	if journey.current_stage == "Prospect":
		if lead:
			journey.lead = lead
		journey.update_stage("Lead", "Lead created")


def get_journey_stage(email):
	"""
	Get the current journey stage for an email.

	Args:
		email: Contact email address

	Returns:
		Current stage or None if no journey exists
	"""
	return frappe.db.get_value("ILL Marketing Journey", {"contact_email": email}, "current_stage")
