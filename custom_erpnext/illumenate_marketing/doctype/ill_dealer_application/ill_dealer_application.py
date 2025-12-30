# Copyright (c) 2024, ilLumenate Lighting and contributors
# For license information, please see license.txt

"""
ILL Dealer Application DocType

Handles dealer applications with workflow states:
- Pending: New application received
- Under Review: Sales team is reviewing
- Approved: Application approved, dealer account provisioned
- Rejected: Application rejected
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime


class ILLDealerApplication(Document):
	def validate(self):
		"""Validate dealer application."""
		self.validate_email()
		self.validate_status_change()

	def validate_email(self):
		"""Validate email format."""
		if self.email:
			import re

			pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
			if not re.match(pattern, self.email):
				frappe.throw(_("Invalid email format"))

	def validate_status_change(self):
		"""Handle status change logic."""
		if self.has_value_changed("status"):
			old_status = self.get_doc_before_save().status if self.get_doc_before_save() else None

			# Record reviewer info when status changes from Pending
			if old_status == "Pending" and self.status in ["Under Review", "Approved", "Rejected"]:
				self.reviewed_by = frappe.session.user
				self.reviewed_on = now_datetime()

			# Trigger provisioning when approved
			if self.status == "Approved" and old_status != "Approved":
				# Provisioning is done after save via on_update hook
				pass

	def on_update(self):
		"""Handle post-update actions."""
		if self.has_value_changed("status") and self.status == "Approved":
			# Trigger dealer account provisioning
			if not self.customer:
				self.provision_dealer_account()

	def provision_dealer_account(self):
		"""
		Provision dealer account upon approval.

		Creates:
		1. Customer (with Dealer price list)
		2. Contact (linked to Customer)
		3. User (with Portal access)
		4. Sends credentials email
		"""
		from custom_erpnext.illumenate_marketing.onboarding import provision_dealer_account

		provision_dealer_account(self.name)

	@frappe.whitelist()
	def approve_application(self):
		"""Approve the dealer application (one-click action)."""
		if self.status not in ["Pending", "Under Review"]:
			frappe.throw(_("Application must be in Pending or Under Review status to approve"))

		self.status = "Approved"
		self.reviewed_by = frappe.session.user
		self.reviewed_on = now_datetime()
		self.save()
		frappe.msgprint(_("Application approved successfully"))

	@frappe.whitelist()
	def reject_application(self, rejection_reason=None):
		"""Reject the dealer application (one-click action)."""
		if self.status not in ["Pending", "Under Review"]:
			frappe.throw(_("Application must be in Pending or Under Review status to reject"))

		if not rejection_reason:
			frappe.throw(_("Please provide a rejection reason"))

		self.status = "Rejected"
		self.rejection_reason = rejection_reason
		self.reviewed_by = frappe.session.user
		self.reviewed_on = now_datetime()
		self.save()
		frappe.msgprint(_("Application rejected"))

	@frappe.whitelist()
	def start_review(self):
		"""Move application to Under Review status."""
		if self.status != "Pending":
			frappe.throw(_("Only Pending applications can be moved to Under Review"))

		self.status = "Under Review"
		self.save()
		frappe.msgprint(_("Application is now under review"))
