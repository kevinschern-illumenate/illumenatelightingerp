# Copyright (c) 2024, ilLumenate Lighting and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class ILLFixtureSchedule(Document):
	def validate(self):
		"""Validate schedule document."""
		self.validate_status_change()
		self.set_customer_from_project()
		self.compute_line_totals()

	def validate_status_change(self):
		"""Prevent modifications when status is Ordered."""
		old_doc = self.get_doc_before_save()
		if old_doc and old_doc.status == "Ordered":
			frappe.throw(_("Cannot modify schedule after it has been ordered"))

	def set_customer_from_project(self):
		"""Auto-populate customer from project."""
		if self.project:
			project_customer = frappe.db.get_value("ILL Project", self.project, "customer")
			if project_customer:
				self.customer = project_customer

	def compute_line_totals(self):
		"""Compute line_total for each ilLumenate line."""
		for line in self.lines:
			if line.line_type == "ilLumenate" and line.unit_net and line.qty:
				line.line_total = line.unit_net * line.qty
			else:
				line.line_total = 0
