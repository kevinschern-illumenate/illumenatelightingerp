# Copyright (c) 2024, ilLumenate Lighting and contributors
# For license information, please see license.txt

"""
Configurator API Module

Provides the validate_configuration endpoint for the fixture configurator.
"""

import frappe
from frappe import _

from custom_erpnext.illumenate_configurator.engine import (
	compute_length,
	compute_runs,
	select_driver,
)


@frappe.whitelist()
def validate_configuration(
	template_code: str,
	tape_spec: str,
	requested_overall_in: float,
	dimming_protocol: str,
	endcap_item: str | None = None,
):
	"""
	Validate a fixture configuration and return computed results.

	Args:
		template_code: The fixture template code (e.g., "SH01")
		tape_spec: The ILL LED Tape Spec name/ID
		requested_overall_in: Requested overall length in inches
		dimming_protocol: Selected dimming protocol (0-10V, DALI, DMX, TRIAC, PWM, Other)
		endcap_item: Optional endcap Item name. Uses template default if omitted.

	Returns:
		A dict with configuration results or errors.
	"""
	errors = []

	# Validate inputs
	try:
		requested_overall_in = float(requested_overall_in)
	except (TypeError, ValueError):
		errors.append(
			{
				"code": "INVALID_INPUT",
				"message": "Requested overall length must be a number.",
				"field": "requested_overall_in",
			}
		)

	if requested_overall_in <= 0:
		errors.append(
			{
				"code": "INVALID_INPUT",
				"message": "Requested overall length must be greater than 0.",
				"field": "requested_overall_in",
			}
		)

	# Load template
	template = None
	try:
		template = frappe.get_doc("ILL Fixture Template", template_code)
	except frappe.DoesNotExistError:
		errors.append(
			{
				"code": "TEMPLATE_NOT_FOUND",
				"message": f"Fixture template '{template_code}' not found.",
				"field": "template_code",
			}
		)

	# Load tape spec
	tape = None
	try:
		tape = frappe.get_doc("ILL LED Tape Spec", tape_spec)
		if not tape.is_active:
			errors.append(
				{
					"code": "TAPE_INACTIVE",
					"message": f"Tape spec '{tape_spec}' is not active.",
					"field": "tape_spec",
				}
			)
	except frappe.DoesNotExistError:
		errors.append(
			{
				"code": "TAPE_NOT_FOUND",
				"message": f"LED tape spec '{tape_spec}' not found.",
				"field": "tape_spec",
			}
		)

	# Return early if critical errors
	if errors:
		return {"errors": errors}

	# Resolve endcap and allowances
	if endcap_item:
		endcap_allowance = template.get_endcap_allowance(endcap_item)
	else:
		endcap_item = template.get_default_endcap_item()
		endcap_allowance = template.get_endcap_allowance(endcap_item)

	leader_allowance = template.leader_allowance_mm_per_fixture or 15.0
	cut_increment_mm = tape.cut_increment_mm

	# Compute length
	length_result = compute_length(
		requested_overall_in=requested_overall_in,
		endcap_allowance_mm_per_side=endcap_allowance,
		leader_allowance_mm=leader_allowance,
		cut_increment_mm=cut_increment_mm,
	)

	if length_result.get("error"):
		errors.append(
			{
				"code": length_result["code"],
				"message": length_result["message"],
			}
		)
		return {"errors": errors}

	# Compute runs
	runs_result = compute_runs(
		tape_cut_mm=length_result["tape_cut"]["mm"],
		watts_per_ft=tape.watts_per_ft,
	)

	# Find eligible drivers
	eligible_drivers = frappe.get_all(
		"ILL Driver Spec",
		filters={
			"voltage_out": tape.voltage,
			"dimming_protocol": dimming_protocol,
			"is_active": 1,
		},
		fields=["name", "driver_item", "max_wattage", "outputs_count"],
	)

	# Select best driver
	driver_result = select_driver(
		eligible_drivers=eligible_drivers,
		runs_count=runs_result["runs_count"],
		total_watts=runs_result["total_watts"],
	)

	if driver_result.get("error"):
		errors.append(
			{
				"code": driver_result["code"],
				"message": driver_result["message"],
			}
		)
		return {"errors": errors}

	# Build response
	return {
		"inputs": {
			"template_code": template_code,
			"tape_spec": tape_spec,
			"tape_item": tape.tape_item,
			"requested_overall_in": requested_overall_in,
			"dimming_protocol": dimming_protocol,
			"endcap_item": endcap_item,
			"voltage": tape.voltage,
		},
		"length": {
			"requested": length_result["requested"],
			"tape_cut": length_result["tape_cut"],
			"manufacturable": length_result["manufacturable"],
			"delta": length_result["delta"],
			"warning": length_result["warning"],
		},
		"electrical": {
			"watts_per_ft": runs_result["watts_per_ft"],
			"total_watts": runs_result["total_watts"],
			"runs_count": runs_result["runs_count"],
			"max_run_ft_by_85w": runs_result["max_run_ft_by_85w"],
		},
		"driver": {
			"driver_spec": driver_result["driver_spec"],
			"driver_item": driver_result["driver_item"],
			"quantity": driver_result["quantity"],
			"usable_watts_each": driver_result["usable_watts_each"],
			"total_usable_watts": driver_result["total_usable_watts"],
		},
		"errors": [],
	}


@frappe.whitelist()
def get_item_attributes(doctype, txt, searchfield, start, page_len, filters):
	"""
	Get the attributes of an Item Template for use in Link field queries.

	Used by ILL Spec Attribute child table to filter available attributes
	based on the parent Item Template.

	Args:
		filters: Must contain 'item' key with the Item Template name

	Returns:
		List of [name, attribute_name] tuples for Item Attribute records
	"""
	item = filters.get("item")
	if not item:
		return []

	# Get the item's attributes
	item_doc = frappe.get_doc("Item", item)

	if not item_doc.has_variants:
		return []

	# Get attribute names from the item's variant attributes
	attribute_names = [attr.attribute for attr in item_doc.attributes]

	if not attribute_names:
		return []

	# Return matching attributes
	return frappe.db.sql(
		"""
		SELECT name, attribute_name
		FROM `tabItem Attribute`
		WHERE name IN %(attributes)s
		AND (name LIKE %(txt)s OR attribute_name LIKE %(txt)s)
		ORDER BY attribute_name
		LIMIT %(start)s, %(page_len)s
		""",
		{
			"attributes": attribute_names,
			"txt": f"%{txt}%",
			"start": start,
			"page_len": page_len,
		},
	)


@frappe.whitelist()
def get_attribute_values(attribute):
	"""
	Get the allowed values for an Item Attribute.

	Args:
		attribute: Item Attribute name

	Returns:
		Dict with attribute info and list of allowed values
	"""
	attr_doc = frappe.get_doc("Item Attribute", attribute)

	if attr_doc.numeric_values:
		return {
			"numeric": True,
			"from_range": attr_doc.from_range,
			"to_range": attr_doc.to_range,
			"increment": attr_doc.increment,
		}
	else:
		return {
			"numeric": False,
			"values": [v.attribute_value for v in attr_doc.item_attribute_values],
		}


def resolve_variant_item(template_item, variant_attributes):
	"""
	Resolve a template Item + variant attributes to a specific Item Variant.

	Args:
		template_item: Item name (must be a template with has_variants=1)
		variant_attributes: List of dicts with 'attribute' and 'attribute_value' keys

	Returns:
		Item name of the matching variant, or None if not found
	"""
	if not template_item or not variant_attributes:
		return None

	# Check if item is a template
	item_doc = frappe.get_doc("Item", template_item)
	if not item_doc.has_variants:
		# Not a template, return as-is
		return template_item

	# Build attribute dict
	attrs = {attr["attribute"]: attr["attribute_value"] for attr in variant_attributes}

	# Find matching variant using ERPNext's built-in function
	from erpnext.stock.doctype.item.item import get_variant

	try:
		variant_name = get_variant(template_item, attrs)
		return variant_name
	except Exception:
		return None


def get_or_create_variant(template_item, variant_attributes):
	"""
	Get an existing variant or create a new one if it doesn't exist.

	Args:
		template_item: Item name (must be a template with has_variants=1)
		variant_attributes: List of dicts with 'attribute' and 'attribute_value' keys

	Returns:
		Item name of the variant (existing or newly created)
	"""
	# First try to find existing
	variant = resolve_variant_item(template_item, variant_attributes)
	if variant:
		return variant

	# Create new variant
	from erpnext.stock.doctype.item.item import create_variant

	attrs = {attr["attribute"]: attr["attribute_value"] for attr in variant_attributes}

	try:
		variant_doc = create_variant(template_item, attrs)
		variant_doc.insert()
		return variant_doc.name
	except Exception as e:
		frappe.log_error(f"Failed to create variant: {e}")
		return None
