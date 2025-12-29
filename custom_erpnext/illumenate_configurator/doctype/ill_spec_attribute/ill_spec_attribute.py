# Copyright (c) 2024, ilLumenate Lighting and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class ILLSpecAttribute(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		attribute: DF.Link
		attribute_value: DF.Data
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
	# end: auto-generated types

	pass
