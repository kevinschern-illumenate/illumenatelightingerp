# Copyright (c) 2024, ilLumenate Lighting and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class ILLFixtureTemplate(Document):
	def validate(self):
		self.validate_profile_item()
		self.validate_endcap_options()
		self.compute_max_assembled_length_mm()
		self._validate_piece_lengths()

	def validate_profile_item(self):
		"""Validate that the profile item has Stock UOM = Meter."""
		if self.profile_item:
			item = frappe.get_doc("Item", self.profile_item)
			if item.stock_uom != "Meter":
				frappe.throw(
					_("Profile item must have Stock UOM = Meter. Current UOM: {0}").format(item.stock_uom)
				)

	def validate_endcap_options(self):
		if not self.endcap_options:
			return

		# Validate exactly one default
		default_count = sum(1 for option in self.endcap_options if option.is_default)
		if default_count != 1:
			frappe.throw(_("Exactly one endcap option must be marked as default. Found {0}.").format(default_count))

		# Validate allowance_mm_per_side if set
		for option in self.endcap_options:
			if option.allowance_mm_per_side is not None and option.allowance_mm_per_side <= 0:
				frappe.throw(
					_("Endcap allowance must be greater than 0 if specified. Row {0} has invalid value.").format(
						option.idx
					)
				)

	def _validate_piece_lengths(self):
		"""Validate piece length fields."""
		if self.profile_piece_length_mm and self.profile_piece_length_mm <= 0:
			frappe.throw(_("Profile piece length must be > 0"))
		if self.lens_piece_length_mm and self.lens_piece_length_mm <= 0:
			frappe.throw(_("Lens piece length must be > 0"))

	def compute_max_assembled_length_mm(self):
		if self.max_assembled_length_in:
			self.max_assembled_length_mm = self.max_assembled_length_in * 25.4
		else:
			self.max_assembled_length_mm = 0

	def get_endcap_allowance(self, endcap_item=None):
		"""Get the endcap allowance for a specific endcap item or the default."""
		if not self.endcap_options:
			return self.default_endcap_allowance_mm_per_side or 2.0

		for option in self.endcap_options:
			if endcap_item and option.endcap_item == endcap_item:
				return option.allowance_mm_per_side or self.default_endcap_allowance_mm_per_side or 2.0
			elif option.is_default and not endcap_item:
				return option.allowance_mm_per_side or self.default_endcap_allowance_mm_per_side or 2.0

		# Fallback to template default
		return self.default_endcap_allowance_mm_per_side or 2.0

	def get_default_endcap_item(self):
		"""Get the default endcap item."""
		if not self.endcap_options:
			return None

		for option in self.endcap_options:
			if option.is_default:
				return option.endcap_item

		return None
