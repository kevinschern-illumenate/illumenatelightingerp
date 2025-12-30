# Copyright (c) 2024, ilLumenate Lighting and contributors
# For license information, please see license.txt

"""
PDF Engine Module.

Provides functions for filling and flattening PDF templates with fixture data.
"""

from datetime import date
from io import BytesIO

import frappe
from frappe import _

# Pricing keys that should be blocked in submittals
PRICING_KEYS = {"unit_msrp", "unit_net", "tier_name", "discount_percent"}


def format_value(value, format_rule: str) -> str:
	"""
	Apply formatting rule to value.

	Args:
		value: The value to format
		format_rule: One of: Raw, Uppercase, Currency_2dp, Inches_1_16,
					 MM_0dp, Meters_3dp, Percent_0dp, Date_YYYY_MM_DD

	Returns:
		Formatted string value
	"""
	if value is None:
		return ""

	if format_rule == "Raw":
		return str(value)

	elif format_rule == "Uppercase":
		return str(value).upper()

	elif format_rule == "Currency_2dp":
		try:
			return f"${float(value):,.2f}"
		except (ValueError, TypeError):
			return str(value)

	elif format_rule == "Inches_1_16":
		try:
			inches = float(value)
			whole = int(inches)
			fraction = inches - whole
			sixteenths = round(fraction * 16)
			if sixteenths == 0:
				return f'{whole}"'
			elif sixteenths == 16:
				return f'{whole + 1}"'
			else:
				# Simplify fraction
				from math import gcd

				g = gcd(sixteenths, 16)
				num = sixteenths // g
				den = 16 // g
				return f'{whole} {num}/{den}"'
		except (ValueError, TypeError):
			return str(value)

	elif format_rule == "MM_0dp":
		try:
			return f"{round(float(value))} mm"
		except (ValueError, TypeError):
			return str(value)

	elif format_rule == "Meters_3dp":
		try:
			return f"{float(value):.3f} m"
		except (ValueError, TypeError):
			return str(value)

	elif format_rule == "Percent_0dp":
		try:
			return f"{round(float(value))}%"
		except (ValueError, TypeError):
			return str(value)

	elif format_rule == "Date_YYYY_MM_DD":
		if isinstance(value, date):
			return value.strftime("%Y-%m-%d")
		else:
			return str(value)

	return str(value)


def fill_pdf_template(
	pdf_template_id: str,
	context: dict,
	enforce_submittal_guardrail: bool = True,
) -> tuple[bytes, list]:
	"""
	Fill PDF template fields from context and flatten.

	Args:
		pdf_template_id: The ILL PDF Template name
		context: Dictionary of data keys and values
		enforce_submittal_guardrail: If True and template is Fixture Submittal,
									 pricing keys are blocked

	Returns:
		Tuple of (pdf_bytes, warnings_list)

	Raises:
		frappe.ValidationError: If mapped field not in PDF
	"""
	from pypdf import PdfReader, PdfWriter

	# Load template
	template = frappe.get_doc("ILL PDF Template", pdf_template_id)

	# Load PDF file
	file_doc = frappe.get_doc("File", {"file_url": template.pdf_file})
	pdf_path = file_doc.get_full_path()

	# Load field mappings
	mappings = frappe.get_all(
		"ILL PDF Field Map",
		filters={"pdf_template": pdf_template_id, "is_active": 1},
		fields=["pdf_field_name", "data_key", "format_rule", "default_value"],
	)

	if not mappings:
		frappe.throw(_("No field mappings found for template '{0}'").format(pdf_template_id))

	warnings = []

	# Read the PDF
	reader = PdfReader(pdf_path)
	writer = PdfWriter()

	# Get available fields in PDF
	pdf_fields = reader.get_fields() or {}
	available_field_names = set(pdf_fields.keys())

	# Build field values dictionary
	field_values = {}
	for mapping in mappings:
		pdf_field = mapping["pdf_field_name"]
		data_key = mapping["data_key"]
		format_rule = mapping["format_rule"] or "Raw"
		default_value = mapping["default_value"]

		# Check if field exists in PDF
		if pdf_field not in available_field_names:
			frappe.throw(
				_("PDF field '{0}' not found in template. Available fields: {1}").format(
					pdf_field, ", ".join(sorted(available_field_names)[:10])
				)
			)

		# Check guardrail for pricing keys
		if (
			enforce_submittal_guardrail
			and template.template_type == "Fixture Submittal"
			and data_key in PRICING_KEYS
		):
			warnings.append(
				f"Pricing key '{data_key}' blocked for submittal template"
			)
			field_values[pdf_field] = ""
			continue

		# Get value from context
		value = context.get(data_key)
		if value is None and default_value:
			value = default_value

		# Format value
		formatted_value = format_value(value, format_rule)
		field_values[pdf_field] = formatted_value

	# Clone pages and update fields
	for page in reader.pages:
		writer.add_page(page)

	# Update form field values
	writer.update_page_form_field_values(writer.pages[0], field_values)

	# Flatten the PDF by removing annotations (AcroForm)
	for page in writer.pages:
		if "/Annots" in page:
			del page["/Annots"]

	# Write to bytes
	output = BytesIO()
	writer.write(output)
	output.seek(0)

	return output.read(), warnings
