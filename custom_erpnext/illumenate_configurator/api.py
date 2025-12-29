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
	tape_attribute_combination: str,
	requested_overall_in: float,
	driver_spec: str | None = None,
	driver_attribute_combination: str | None = None,
	endcap_item: str | None = None,
):
	"""
	Validate a fixture configuration and return computed results.

	Args:
		template_code: The fixture template code (e.g., "SH01")
		tape_spec: The ILL LED Tape Spec name/ID
		tape_attribute_combination: Attribute combination string for tape (e.g., "Color Temperature: 2700K, CRI: 90")
		requested_overall_in: Requested overall length in inches
		driver_spec: Optional ILL Driver Spec name/ID. If not provided, auto-selects based on tape specs.
		driver_attribute_combination: Attribute combination string for driver (e.g., "Input Voltage: 120V, Dimming: 0-10V")
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
	tape_variant_spec = None
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
		else:
			# Get the variant spec for the given attribute combination
			tape_variant_spec = tape.get_spec_for_attributes(tape_attribute_combination)
			if not tape_variant_spec:
				errors.append(
					{
						"code": "TAPE_VARIANT_NOT_FOUND",
						"message": f"No specification found for attribute combination '{tape_attribute_combination}' in tape spec '{tape_spec}'.",
						"field": "tape_attribute_combination",
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
	cut_increment_mm = tape_variant_spec["cut_increment_mm"]
	voltage = tape_variant_spec["voltage"]
	watts_per_ft = tape_variant_spec["watts_per_ft"]
	voltage_drop_max_run_ft = tape_variant_spec.get("voltage_drop_max_run_ft")

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
		watts_per_ft=watts_per_ft,
		voltage_drop_max_run_ft=voltage_drop_max_run_ft,
	)

	# Find eligible drivers based on voltage and driver spec/attribute combination
	driver_result = None
	if driver_spec and driver_attribute_combination:
		# Use specified driver spec with attribute combination
		try:
			driver_doc = frappe.get_doc("ILL Driver Spec", driver_spec)
			if not driver_doc.is_active:
				errors.append(
					{
						"code": "DRIVER_INACTIVE",
						"message": f"Driver spec '{driver_spec}' is not active.",
						"field": "driver_spec",
					}
				)
				return {"errors": errors}

			driver_variant_spec = driver_doc.get_spec_for_attributes(driver_attribute_combination)
			if not driver_variant_spec:
				errors.append(
					{
						"code": "DRIVER_VARIANT_NOT_FOUND",
						"message": f"No specification found for attribute combination '{driver_attribute_combination}' in driver spec '{driver_spec}'.",
						"field": "driver_attribute_combination",
					}
				)
				return {"errors": errors}

			# Validate voltage compatibility
			if driver_variant_spec["voltage_out"] != voltage:
				errors.append(
					{
						"code": "VOLTAGE_MISMATCH",
						"message": f"Driver output voltage ({driver_variant_spec['voltage_out']}V) does not match tape voltage ({voltage}V).",
						"field": "driver_spec",
					}
				)
				return {"errors": errors}

			# Build driver info for select_driver
			eligible_drivers = [
				{
					"name": driver_spec,
					"driver_item": driver_doc.driver_item,
					"max_wattage": driver_variant_spec["max_wattage"],
					"outputs_count": driver_variant_spec["outputs_count"],
				}
			]

			driver_result = select_driver(
				eligible_drivers=eligible_drivers,
				runs_count=runs_result["runs_count"],
				total_watts=runs_result["total_watts"],
			)

		except frappe.DoesNotExistError:
			errors.append(
				{
					"code": "DRIVER_NOT_FOUND",
					"message": f"Driver spec '{driver_spec}' not found.",
					"field": "driver_spec",
				}
			)
			return {"errors": errors}
	else:
		# Auto-select driver: Find all active driver specs that have a variant with matching voltage
		all_driver_specs = frappe.get_all(
			"ILL Driver Spec",
			filters={"is_active": 1},
			fields=["name", "driver_item"],
		)

		eligible_drivers = []
		for ds in all_driver_specs:
			driver_doc = frappe.get_doc("ILL Driver Spec", ds.name)
			for variant in driver_doc.variant_specs:
				if variant.voltage_out == voltage:
					eligible_drivers.append(
						{
							"name": ds.name,
							"driver_item": ds.driver_item,
							"max_wattage": variant.max_wattage,
							"outputs_count": variant.outputs_count,
							"dimming_protocol": variant.dimming_protocol,
							"attribute_combination": variant.attribute_combination,
						}
					)

		if not eligible_drivers:
			errors.append(
				{
					"code": "NO_ELIGIBLE_DRIVERS",
					"message": f"No active drivers found with output voltage {voltage}V.",
				}
			)
			return {"errors": errors}

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
			"tape_attribute_combination": tape_attribute_combination,
			"requested_overall_in": requested_overall_in,
			"endcap_item": endcap_item,
			"voltage": voltage,
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
			"max_run_ft_by_voltage_drop": runs_result["max_run_ft_by_voltage_drop"],
			"effective_max_run_ft": runs_result["effective_max_run_ft"],
			"limiting_factor": runs_result["limiting_factor"],
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
def get_item_template_attributes(item):
	"""
	Get the variant attributes and their possible values for an Item Template.

	Used by the Tape Spec and Driver Spec forms to display available attributes.

	Args:
		item: Item name (should be a template with has_variants=1)

	Returns:
		Dict with:
			- has_variants: bool
			- attributes: list of dicts with attribute info and possible values
	"""
	if not item:
		return {"has_variants": False, "attributes": []}

	item_doc = frappe.get_doc("Item", item)

	if not item_doc.has_variants:
		return {"has_variants": False, "attributes": []}

	attributes = []
	for attr in item_doc.attributes:
		attr_doc = frappe.get_doc("Item Attribute", attr.attribute)

		attr_info = {
			"attribute": attr.attribute,
			"numeric_values": attr_doc.numeric_values,
		}

		if attr_doc.numeric_values:
			attr_info["from_range"] = attr_doc.from_range
			attr_info["to_range"] = attr_doc.to_range
			attr_info["increment"] = attr_doc.increment
			attr_info["values"] = []
		else:
			attr_info["from_range"] = None
			attr_info["to_range"] = None
			attr_info["increment"] = None
			attr_info["values"] = [v.attribute_value for v in attr_doc.item_attribute_values]

		attributes.append(attr_info)

	return {
		"has_variants": True,
		"attributes": attributes,
	}


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


@frappe.whitelist()
def get_tape_spec_variants(tape_spec):
	"""
	Get all variant specifications defined in a tape spec.

	Args:
		tape_spec: ILL LED Tape Spec name

	Returns:
		List of variant specs with their attribute combinations and electrical specs
	"""
	tape = frappe.get_doc("ILL LED Tape Spec", tape_spec)

	variants = []
	for row in tape.variant_specs:
		variants.append({
			"attribute_combination": row.attribute_combination,
			"voltage": row.voltage,
			"watts_per_ft": row.watts_per_ft,
			"cut_increment_in": row.cut_increment_in,
			"cut_increment_mm": row.cut_increment_mm,
		})

	return {
		"tape_spec": tape_spec,
		"tape_item": tape.tape_item,
		"is_active": tape.is_active,
		"variants": variants,
	}


@frappe.whitelist()
def get_driver_spec_variants(driver_spec):
	"""
	Get all variant specifications defined in a driver spec.

	Args:
		driver_spec: ILL Driver Spec name

	Returns:
		List of variant specs with their attribute combinations and electrical specs
	"""
	driver = frappe.get_doc("ILL Driver Spec", driver_spec)

	variants = []
	for row in driver.variant_specs:
		variants.append({
			"attribute_combination": row.attribute_combination,
			"voltage_out": row.voltage_out,
			"dimming_protocol": row.dimming_protocol,
			"max_wattage": row.max_wattage,
			"outputs_count": row.outputs_count,
			"usable_wattage": row.max_wattage * 0.8 if row.max_wattage else 0,
		})

	return {
		"driver_spec": driver_spec,
		"driver_item": driver.driver_item,
		"is_active": driver.is_active,
		"variants": variants,
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
