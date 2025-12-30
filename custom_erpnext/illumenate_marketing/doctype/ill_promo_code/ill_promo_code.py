# Copyright (c) 2024, ilLumenate Lighting and contributors
# For license information, please see license.txt

"""
ILL Promo Code DocType

Stores unique promotional discount codes generated per customer
for lifetime value-based promotions via n8n workflows.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, now_datetime


class ILLPromoCode(Document):
	def validate(self):
		"""Validate promo code before saving."""
		self.validate_dates()
		self.validate_discount()

	def validate_dates(self):
		"""Ensure valid_until is after valid_from."""
		if self.valid_from and self.valid_until:
			if getdate(self.valid_until) < getdate(self.valid_from):
				frappe.throw(_("Valid Until date must be after Valid From date"))

	def validate_discount(self):
		"""Ensure discount percent is within valid range."""
		if self.discount_percent < 0 or self.discount_percent > 100:
			frappe.throw(_("Discount percent must be between 0 and 100"))

	def mark_as_used(self):
		"""
		Mark the promo code as used.

		Uses reload() before update to minimize race condition window.
		The unique constraint on the promo_code field provides additional protection.
		"""
		self.reload()  # Get latest state from DB

		if self.is_used:
			frappe.throw(_("This promo code has already been used"))

		self.is_used = 1
		self.used_at = now_datetime()
		self.save(ignore_permissions=True)

	def is_valid(self):
		"""Check if promo code is still valid (not used and within date range)."""
		if self.is_used:
			return False

		today = getdate()
		if self.valid_from and getdate(self.valid_from) > today:
			return False
		if self.valid_until and getdate(self.valid_until) < today:
			return False

		return True


def get_valid_promo_code(customer, promo_code):
	"""
	Get a valid promo code for a customer.

	Args:
		customer: Customer name
		promo_code: The promo code string

	Returns:
		ILLPromoCode document if valid, None otherwise
	"""
	if not frappe.db.exists("ILL Promo Code", promo_code):
		return None

	doc = frappe.get_doc("ILL Promo Code", promo_code)

	# Check customer matches
	if doc.customer != customer:
		return None

	# Check if valid
	if not doc.is_valid():
		return None

	return doc
