# Copyright (c) 2024, ilLumenate Lighting and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class ILLLensOption(Document):
	def validate(self):
		self._validate_lens_item_uom()
		self._validate_continuous_reel()

	def _validate_lens_item_uom(self):
		"""Validate that the lens item has Stock UOM = Meter."""
		if self.lens_item:
			lens_item = frappe.get_doc("Item", self.lens_item)
			if lens_item.stock_uom != "Meter":
				frappe.throw(_("Lens Item must have Stock UOM = Meter"))

	def _validate_continuous_reel(self):
		"""Validate continuous reel settings."""
		if self.is_continuous_reel and (not self.max_continuous_length_m or self.max_continuous_length_m <= 0):
			frappe.throw(_("Continuous reel lenses require max_continuous_length_m > 0"))
