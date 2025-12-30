# Copyright (c) 2024, ilLumenate Lighting and contributors
# For license information, please see license.txt

"""
Configurator API Module

Provides the validate_configuration endpoint for the fixture configurator.
"""

import math

import frappe
from frappe import _

from custom_erpnext.illumenate_configurator.engine import (
	compute_length,
	compute_runs,
	compute_segmentation,
	select_driver,
)
from custom_erpnext.illumenate_configurator.pricing import price_configuration_unit


def abbreviate_attribute_combination(attribute_combination: str) -> str:
	"""
	Convert an attribute combination string to use abbreviations.

	Takes a string like "LED Tape CCT: 3000K, LED Tape CRI: 90+"
	and returns an abbreviated version like "3000K, 90+" using the
	abbreviations defined in ERPNext's Item Attribute Value table.

	Args:
		attribute_combination: Full attribute combination string

	Returns:
		Abbreviated string, or original values if no abbreviation found
	"""
	if not attribute_combination:
		return ""

	abbreviated_parts = []

	# Parse "Attribute: Value, Attribute: Value" format
	for part in attribute_combination.split(","):
		part = part.strip()
		if ":" not in part:
			continue

		attribute_name, attribute_value = part.split(":", 1)
		attribute_name = attribute_name.strip()
		attribute_value = attribute_value.strip()

		# Look up abbreviation from Item Attribute Value
		abbr = frappe.db.get_value(
			"Item Attribute Value",
			{"parent": attribute_name, "attribute_value": attribute_value},
			"abbr",
		)

		# Use abbreviation if found, otherwise use the value itself
		if abbr:
			abbreviated_parts.append(abbr)
		else:
			# Fall back to just the value (without attribute name)
			abbreviated_parts.append(attribute_value)

	return "-".join(abbreviated_parts)


@frappe.whitelist()
def validate_configuration(
	template_code: str,
	tape_spec: str,
	tape_attribute_combination: str,
	requested_overall_in: float,
	driver_spec: str | None = None,
	driver_attribute_combination: str | None = None,
	endcap_item: str | None = None,
	# Sprint 3 additions
	tape_type_token: str | None = None,
	environment_token: str | None = None,
	cct_token: str | None = None,
	cri_value: int | None = None,
	output_token: int | None = None,
	finish_token: str | None = None,
	lens_option: str | None = None,
	mounting_method: str | None = None,
	joiner_angle: str | None = None,
	# Sprint 4 additions
	tier_name: str | None = None,
	customer: str | None = None,
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
		tape_type_token: Optional tape type token (SW, TW, RGBTW)
		environment_token: Optional environment token (I, O)
		cct_token: Optional CCT token
		cri_value: Optional CRI value
		output_token: Optional output token
		finish_token: Optional finish token
		lens_option: Optional ILL Lens Option name
		mounting_method: Optional ILL Mounting Method name
		joiner_angle: Optional joiner angle (Straight, 90, Other)
		tier_name: Optional pricing tier name (MSRP, Dealer A/B/C/D)
		customer: Optional customer name for tier lookup

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

	# Validate against template allowed sets (Sprint 3)
	if tape_type_token:
		allowed_tape_types = [t.tape_type_token for t in (template.allowed_tape_types or [])]
		if allowed_tape_types and tape_type_token not in allowed_tape_types:
			errors.append(
				{
					"code": "INVALID_TAPE_TYPE",
					"message": f"Tape type '{tape_type_token}' not allowed for this template",
					"field": "tape_type_token",
				}
			)

	if environment_token:
		allowed_envs = [e.environment_token for e in (template.allowed_environments or [])]
		if allowed_envs and environment_token not in allowed_envs:
			errors.append(
				{
					"code": "INVALID_ENVIRONMENT",
					"message": f"Environment '{environment_token}' not allowed for this template",
					"field": "environment_token",
				}
			)

	if finish_token:
		allowed_finishes = [f.finish_token for f in (template.allowed_finishes or [])]
		if allowed_finishes and finish_token not in allowed_finishes:
			errors.append(
				{
					"code": "INVALID_FINISH",
					"message": f"Finish '{finish_token}' not allowed for this template",
					"field": "finish_token",
				}
			)

	if output_token:
		allowed_outputs = [o.output_token for o in (template.allowed_outputs or [])]
		if allowed_outputs and output_token not in allowed_outputs:
			errors.append(
				{
					"code": "INVALID_OUTPUT",
					"message": f"Output '{output_token}' not allowed for this template",
					"field": "output_token",
				}
			)

	if cct_token and cri_value:
		allowed_cct_cri = [(c.cct_token, c.cri_value) for c in (template.allowed_cct_cri or [])]
		if allowed_cct_cri and (cct_token, cri_value) not in allowed_cct_cri:
			errors.append(
				{
					"code": "INVALID_CCT_CRI",
					"message": f"CCT/CRI combination '{cct_token}/{cri_value}' not allowed for this template",
					"field": "cct_token",
				}
			)

	if lens_option:
		allowed_lens_opts = [l.lens_option for l in (template.allowed_lens_options or [])]
		if allowed_lens_opts and lens_option not in allowed_lens_opts:
			errors.append(
				{
					"code": "INVALID_LENS_OPTION",
					"message": f"Lens option '{lens_option}' not allowed for this template",
					"field": "lens_option",
				}
			)

	if mounting_method:
		allowed_mounting = [m.mounting_method for m in (template.allowed_mounting_methods or [])]
		if allowed_mounting and mounting_method not in allowed_mounting:
			errors.append(
				{
					"code": "INVALID_MOUNTING_METHOD",
					"message": f"Mounting method '{mounting_method}' not allowed for this template",
					"field": "mounting_method",
				}
			)

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

	# Compute joiner_qty for pricing (based on segmentation logic)
	profile_piece_length_mm = template.profile_piece_length_mm if hasattr(template, 'profile_piece_length_mm') else 2000
	seg = compute_segmentation(length_result["manufacturable"]["mm"], profile_piece_length_mm or 2000)
	joiner_qty = seg["joiner_qty_target"]

	# Build response
	response = {
		"inputs": {
			"template_code": template_code,
			"tape_spec": tape_spec,
			"tape_item": tape.tape_item,
			"tape_attribute_combination": tape_attribute_combination,
			"requested_overall_in": requested_overall_in,
			"endcap_item": endcap_item,
			"voltage": voltage,
			"output_token": output_token,
			"finish_token": finish_token,
			"lens_option": lens_option,
			"mounting_method": mounting_method,
			"joiner_angle": joiner_angle,
			"environment_token": environment_token,
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
			"joiner_qty": joiner_qty,
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

	# Compute pricing
	pricing_result = price_configuration_unit(
		validated_result=response,
		tier_name=tier_name,
		customer=customer,
	)

	if pricing_result.get("error"):
		# Include pricing error but don't fail the whole validation
		response["pricing"] = {
			"error": pricing_result.get("error"),
			"message": pricing_result.get("message"),
		}
	else:
		response["pricing"] = pricing_result

	return response


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


def create_or_get_configured_item(sku: str, description: str) -> str:
	"""
	Create or retrieve an Item for the configured fixture.

	Args:
		sku: The item code (SKU) for the configured fixture
		description: The item description

	Returns:
		The item code of the created or existing item
	"""
	if frappe.db.exists("Item", sku):
		return sku

	# Ensure item group exists
	if not frappe.db.exists("Item Group", "Configured Fixtures"):
		frappe.get_doc(
			{
				"doctype": "Item Group",
				"item_group_name": "Configured Fixtures",
				"parent_item_group": "All Item Groups",
			}
		).insert(ignore_permissions=True)

	item = frappe.get_doc(
		{
			"doctype": "Item",
			"item_code": sku,
			"item_name": description,
			"item_group": "Configured Fixtures",
			"stock_uom": "Nos",
			"is_stock_item": 1,
			"has_serial_no": 1,
		}
	)
	item.insert(ignore_permissions=True)
	return sku


def create_bom(configured_fixture) -> str:
	"""
	Create BOM for configured fixture.

	Args:
		configured_fixture: The ILL Configured Fixture document

	Returns:
		The BOM name
	"""
	cf = configured_fixture
	template = frappe.get_doc("ILL Fixture Template", cf.fixture_template)
	tape_spec = frappe.get_doc("ILL LED Tape Spec", cf.tape_spec)
	driver_spec = (
		frappe.get_doc("ILL Driver Spec", cf.selected_driver_spec) if cf.selected_driver_spec else None
	)

	# Check for existing BOM with same signature
	existing_bom = frappe.db.get_value(
		"BOM",
		{
			"item": cf.configured_item,
			"is_active": 1,
			"is_default": 1,
		},
		"name",
	)
	if existing_bom:
		return existing_bom

	bom_items = []

	# 1. Profile (meters)
	bom_items.append(
		{
			"item_code": template.profile_item,
			"qty": round(cf.manufacturable_overall_mm / 1000, 3),
			"uom": "Meter",
		}
	)

	# 2. LED Tape (meters)
	bom_items.append(
		{
			"item_code": tape_spec.tape_item,
			"qty": round(cf.tape_cut_length_mm / 1000, 3),
			"uom": "Meter",
		}
	)

	# 3. Endcaps (qty 4 = 2 required + 2 extra)
	bom_items.append(
		{
			"item_code": cf.endcap_item,
			"qty": 4,
			"uom": "Nos",
		}
	)

	# 4. Leader Cable (qty = runs_count)
	# Only add if leader cable item exists
	leader_item = "FML-2C-6"
	if frappe.db.exists("Item", leader_item):
		bom_items.append(
			{
				"item_code": leader_item,
				"qty": cf.runs_count,
				"uom": "Nos",
			}
		)

	# 5. Driver(s)
	if driver_spec:
		bom_items.append(
			{
				"item_code": driver_spec.driver_item,
				"qty": cf.selected_driver_qty,
				"uom": "Nos",
			}
		)

	# === Sprint 3 Additions ===

	# 6. Lens (meters)
	if cf.lens_option and cf.lens_qty_m and cf.lens_qty_m > 0:
		lens_opt = frappe.get_doc("ILL Lens Option", cf.lens_option)
		bom_items.append(
			{
				"item_code": lens_opt.lens_item,
				"qty": round(cf.lens_qty_m, 3),
				"uom": "Meter",
			}
		)

	# 7. Joiners (Nos)
	if cf.joiner_item and cf.joiner_qty and cf.joiner_qty > 0:
		bom_items.append(
			{
				"item_code": cf.joiner_item,
				"qty": cf.joiner_qty,
				"uom": "Nos",
			}
		)

	# 8. Mounting Hardware (Nos)
	if cf.mounting_hardware_item and cf.mounting_hardware_qty and cf.mounting_hardware_qty > 0:
		bom_items.append(
			{
				"item_code": cf.mounting_hardware_item,
				"qty": cf.mounting_hardware_qty,
				"uom": "Nos",
			}
		)

	bom = frappe.get_doc(
		{
			"doctype": "BOM",
			"item": cf.configured_item,
			"quantity": 1,
			"is_active": 1,
			"is_default": 1,
			"items": bom_items,
		}
	)
	bom.insert(ignore_permissions=True)
	bom.submit()

	return bom.name


@frappe.whitelist()
def create_manufacturing_package(
	template_code: str,
	tape_spec: str,
	tape_attribute_combination: str,
	requested_overall_in: float,
	endcap_item: str | None = None,
	driver_spec: str | None = None,
	driver_attribute_combination: str | None = None,
	qty: int = 1,
	# Sprint 3 additions
	tape_type_token: str | None = None,
	environment_token: str | None = None,
	cct_token: str | None = None,
	cri_value: int | None = None,
	output_token: int | None = None,
	finish_token: str | None = None,
	lens_option: str | None = None,
	mounting_method: str | None = None,
	joiner_angle: str | None = None,
	# Sprint 4 additions
	tier_name: str | None = None,
	customer: str | None = None,
):
	"""
	Orchestrate creation of configured fixture, item, BOM, and work order.
	Reuses validate_configuration logic internally.

	Args:
		template_code: The fixture template code
		tape_spec: The ILL LED Tape Spec name
		tape_attribute_combination: Attribute combination string for tape
		requested_overall_in: Requested overall length in inches
		endcap_item: Optional endcap Item name
		driver_spec: Optional ILL Driver Spec name
		driver_attribute_combination: Attribute combination string for driver
		qty: Quantity for work order (default 1)
		tape_type_token: Optional tape type token
		environment_token: Optional environment token
		cct_token: Optional CCT token
		cri_value: Optional CRI value
		output_token: Optional output token
		finish_token: Optional finish token
		lens_option: Optional lens option
		mounting_method: Optional mounting method
		joiner_angle: Optional joiner angle
		tier_name: Optional pricing tier name (MSRP, Dealer A/B/C/D)
		customer: Optional customer name for tier lookup

	Returns:
		Dict with configured_fixture, item_code, bom_no, and optionally work_order
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

	# Validate template exists
	if not frappe.db.exists("ILL Fixture Template", template_code):
		errors.append(
			{
				"code": "TEMPLATE_NOT_FOUND",
				"message": f"Fixture template '{template_code}' not found.",
				"field": "template_code",
			}
		)

	# Validate tape spec exists and is active
	tape_doc = None
	if frappe.db.exists("ILL LED Tape Spec", tape_spec):
		tape_doc = frappe.get_doc("ILL LED Tape Spec", tape_spec)
		if not tape_doc.is_active:
			errors.append(
				{
					"code": "TAPE_INACTIVE",
					"message": f"Tape spec '{tape_spec}' is not active.",
					"field": "tape_spec",
				}
			)
		elif not tape_doc.get_spec_for_attributes(tape_attribute_combination):
			errors.append(
				{
					"code": "TAPE_VARIANT_NOT_FOUND",
					"message": f"No specification found for attribute combination '{tape_attribute_combination}'.",
					"field": "tape_attribute_combination",
				}
			)
	else:
		errors.append(
			{
				"code": "TAPE_NOT_FOUND",
				"message": f"LED tape spec '{tape_spec}' not found.",
				"field": "tape_spec",
			}
		)

	if errors:
		return {"error": True, "errors": errors}

	# Resolve endcap if not provided
	template = frappe.get_doc("ILL Fixture Template", template_code)
	if not endcap_item:
		endcap_item = template.get_default_endcap_item()

	if not endcap_item:
		return {
			"error": True,
			"errors": [
				{
					"code": "NO_ENDCAP",
					"message": "No endcap item specified and no default endcap configured.",
					"field": "endcap_item",
				}
			],
		}

	# Create or find Configured Fixture
	cf = frappe.new_doc("ILL Configured Fixture")
	cf.fixture_template = template_code
	cf.tape_spec = tape_spec
	# Use full attribute combination for computation (matching against variant specs)
	cf.tape_attribute_combination = tape_attribute_combination
	cf.endcap_item = endcap_item
	cf.requested_overall_in = requested_overall_in

	if driver_spec:
		cf.driver_spec = driver_spec
	if driver_attribute_combination:
		# Use full attribute combination for computation
		cf.driver_attribute_combination = driver_attribute_combination

	# Sprint 3: Set option fields
	cf.tape_type_token = tape_type_token
	cf.environment_token = environment_token
	cf.cct_token = cct_token
	cf.cri_value = cri_value
	cf.output_token = output_token
	cf.finish_token = finish_token
	cf.lens_option = lens_option
	cf.mounting_method = mounting_method
	cf.joiner_angle = joiner_angle

	# Set lens_color_token and mounting_token from linked documents
	if lens_option:
		lens_doc = frappe.get_doc("ILL Lens Option", lens_option)
		cf.lens_color_token = lens_doc.lens_color_token
	if mounting_method:
		mounting_doc = frappe.get_doc("ILL Mounting Method", mounting_method)
		cf.mounting_token = mounting_doc.mounting_token

	# Compute all values (requires full attribute combination strings for matching)
	try:
		cf.compute_all()
	except Exception as e:
		return {
			"error": True,
			"errors": [{"code": "COMPUTATION_ERROR", "message": str(e)}],
		}

	# Sprint 3: Compute segmentation and adders
	profile_piece_length_mm = template.profile_piece_length_mm or 2000
	lens_piece_length_mm = template.lens_piece_length_mm or 2000

	seg = compute_segmentation(cf.manufacturable_overall_mm, profile_piece_length_mm)
	cf.profile_pieces_count = seg["profile_pieces_count"]
	cf.profile_last_piece_length_mm = seg["profile_last_piece_length_mm"]

	# Resolve joiner
	if mounting_method and joiner_angle and seg["joiner_qty_target"] > 0:
		joiner_result = resolve_joiner(template_code, mounting_method, joiner_angle)
		if joiner_result.get("found"):
			cf.joiner_item = joiner_result.get("joiner_item")
			cf.joiner_qty = seg["joiner_qty_target"]
		else:
			# No joiner found - log warning but continue
			cf.joiner_item = None
			cf.joiner_qty = 0
	else:
		cf.joiner_qty = 0

	# Compute lens qty
	if lens_option:
		cf.lens_qty_m = round(cf.manufacturable_overall_mm / 1000, 3)
		lens_doc = frappe.get_doc("ILL Lens Option", lens_option)
		if lens_doc.is_continuous_reel:
			cf.lens_piece_count = 1
		else:
			cf.lens_piece_count = math.ceil(cf.manufacturable_overall_mm / lens_piece_length_mm)
	else:
		cf.lens_qty_m = 0
		cf.lens_piece_count = 0

	# Compute mounting hardware
	if mounting_method:
		hw = compute_mounting_hardware(
			mounting_method, cf.manufacturable_overall_mm / 1000, cf.profile_pieces_count
		)
		cf.mounting_hardware_item = hw["hardware_item"]
		cf.mounting_hardware_qty = hw["qty"]
	else:
		cf.mounting_hardware_qty = 0

	# After computation, abbreviate attribute combinations for storage
	# to fit within field character limits
	cf.tape_attribute_combination = abbreviate_attribute_combination(tape_attribute_combination)
	if driver_attribute_combination:
		cf.driver_attribute_combination = abbreviate_attribute_combination(driver_attribute_combination)

	# Regenerate signature with abbreviated combinations for consistent matching
	cf.generate_configuration_signature()

	# Check if a fixture with this signature already exists
	existing_cf = frappe.db.get_value(
		"ILL Configured Fixture",
		{"configuration_signature": cf.configuration_signature},
		["name", "configured_item", "bom"],
		as_dict=True,
	)

	if existing_cf:
		return {
			"error": False,
			"configured_fixture": existing_cf.name,
			"item_code": existing_cf.configured_item,
			"bom_no": existing_cf.bom,
			"message": "Using existing configuration",
		}

	# Compute pricing for snapshot
	# Build a minimal validation result for pricing computation
	validation_data = {
		"inputs": {
			"template_code": template_code,
			"output_token": output_token,
			"finish_token": finish_token,
			"lens_option": lens_option,
			"mounting_method": mounting_method,
			"joiner_angle": joiner_angle,
			"environment_token": environment_token,
		},
		"length": {
			"manufacturable": {"mm": cf.manufacturable_overall_mm},
			"tape_cut": {"mm": cf.tape_cut_length_mm},
		},
		"electrical": {
			"runs_count": cf.runs_count,
			"joiner_qty": cf.joiner_qty or 0,
		},
		"driver": {
			"driver_item": frappe.db.get_value("ILL Driver Spec", cf.selected_driver_spec, "driver_item") if cf.selected_driver_spec else None,
			"quantity": cf.selected_driver_qty or 0,
		},
	}

	pricing_result = price_configuration_unit(
		validated_result=validation_data,
		tier_name=tier_name,
		customer=customer,
	)

	# Store pricing snapshot (only if empty - no overwrite on reruns)
	if not cf.unit_msrp_at_time and not pricing_result.get("error"):
		cf.unit_msrp_at_time = pricing_result.get("unit_msrp")
		cf.unit_net_price_at_time = pricing_result.get("unit_net_price")
		cf.tier_at_time = pricing_result.get("tier_name")
		cf.discount_percent_at_time = pricing_result.get("discount_percent")
		if pricing_result.get("breakdown"):
			cf.pricing_breakdown_json = frappe.as_json(pricing_result["breakdown"])

	# Save the configured fixture
	cf.insert(ignore_permissions=True)

	# Generate SKU and create/get Item
	sku = cf.generate_sku()
	description = f"Configured Fixture: {template_code} - {cf.manufacturable_overall_in}\""

	item_code = create_or_get_configured_item(sku, description)
	cf.configured_item = item_code

	# Create BOM
	bom_name = create_bom(cf)
	cf.bom = bom_name

	cf.save(ignore_permissions=True)

	return {
		"error": False,
		"configured_fixture": cf.name,
		"item_code": item_code,
		"bom_no": bom_name,
	}


def resolve_joiner(fixture_template: str, mounting_method: str, joiner_angle: str) -> dict:
	"""Find the joiner item for the given template/mounting/angle combination."""
	joiner = frappe.db.get_value(
		"ILL Joiner Option",
		{
			"fixture_template": fixture_template,
			"mounting_method": mounting_method,
			"joiner_angle": joiner_angle,
			"is_active": 1,
		},
		["joiner_item"],
		as_dict=True,
	)
	if joiner:
		return {"joiner_item": joiner.joiner_item, "found": True}
	return {"joiner_item": None, "found": False, "warning": "No joiner SKU configured for selected mounting+angle; joiners omitted."}


def compute_mounting_hardware(mounting_method_name: str, manufacturable_m: float, profile_pieces_count: int) -> dict:
	"""Compute mounting hardware quantity based on method rules."""
	mm = frappe.get_doc("ILL Mounting Method", mounting_method_name)
	if not mm.hardware_item:
		return {"hardware_item": None, "qty": 0}

	qty_per_unit = mm.hardware_qty_per_unit or 0

	if mm.hardware_qty_rule == "Per Fixture":
		qty = math.ceil(qty_per_unit)
	elif mm.hardware_qty_rule == "Per Meter":
		qty = math.ceil(manufacturable_m * qty_per_unit)
	elif mm.hardware_qty_rule == "Per 2m Piece":
		qty = math.ceil(profile_pieces_count * qty_per_unit)
	else:
		qty = 0

	return {"hardware_item": mm.hardware_item, "qty": qty}


# ============================================================================
# Sprint 5: Portal Ordering Functions
# ============================================================================


@frappe.whitelist()
def create_sales_order_from_schedule(schedule_name):
	"""
	Create Sales Order from ILL Fixture Schedule (portal-accessible).

	Rules:
	- Include only ilLumenate lines with configuration_json
	- SO item: ILL-CONFIGURED-FIXTURE (placeholder)
	- SO item.rate = schedule_line.unit_net
	- SO item.description = configuration_summary
	- Store config JSON in SO item custom fields

	Args:
		schedule_name: The ILL Fixture Schedule name

	Returns:
		Dict with sales_order name or error info
	"""
	from custom_erpnext.illumenate_configurator.utils import get_customer_for_portal_user

	# Load the schedule
	if not frappe.db.exists("ILL Fixture Schedule", schedule_name):
		frappe.throw(_("Schedule not found: {0}").format(schedule_name))

	schedule = frappe.get_doc("ILL Fixture Schedule", schedule_name)

	# Permission check for portal users
	if frappe.db.exists("Has Role", {"parent": frappe.session.user, "role": "Customer"}):
		customer = get_customer_for_portal_user()
		if not customer or schedule.customer != customer:
			frappe.throw(_("Unauthorized: You can only access your own schedules"))

	# Validate schedule status
	if schedule.status != "Draft":
		frappe.throw(_("Schedule has already been ordered"))

	# Check for at least one valid ilLumenate line
	ilumenate_lines = [
		line for line in schedule.lines
		if line.line_type == "ilLumenate" and line.configuration_json
	]

	if not ilumenate_lines:
		frappe.throw(_("No configured ilLumenate lines found in schedule"))

	# Ensure placeholder item exists
	ensure_placeholder_item_exists()

	# Create Sales Order
	so = frappe.new_doc("Sales Order")
	so.customer = schedule.customer
	so.delivery_date = frappe.utils.add_days(frappe.utils.today(), 30)

	for line in ilumenate_lines:
		so.append("items", {
			"item_code": "ILL-CONFIGURED-FIXTURE",
			"qty": line.qty,
			"rate": line.unit_net or 0,
			"description": line.configuration_summary or line.description or "Configured Fixture",
			# Custom fields for configuration tracking
			"ill_configuration_json": line.configuration_json,
			"ill_configuration_summary": line.configuration_summary,
			"ill_tier_name": line.tier_name,
			"ill_discount_percent": line.discount_percent,
			"ill_unit_msrp": line.unit_msrp,
			"ill_unit_net": line.unit_net,
		})

	so.insert()

	# Update schedule to Ordered status
	schedule.status = "Ordered"
	schedule.sales_order = so.name
	schedule.save()

	return {
		"success": True,
		"sales_order": so.name,
		"message": _("Sales Order {0} created successfully").format(so.name),
	}


def ensure_placeholder_item_exists():
	"""Ensure the ILL-CONFIGURED-FIXTURE placeholder item exists."""
	if frappe.db.exists("Item", "ILL-CONFIGURED-FIXTURE"):
		return

	# Ensure item group exists
	if not frappe.db.exists("Item Group", "Configured Fixtures"):
		frappe.get_doc({
			"doctype": "Item Group",
			"item_group_name": "Configured Fixtures",
			"parent_item_group": "All Item Groups",
		}).insert(ignore_permissions=True)

	# Create placeholder item
	frappe.get_doc({
		"doctype": "Item",
		"item_code": "ILL-CONFIGURED-FIXTURE",
		"item_name": "Configured Fixture (Placeholder)",
		"item_group": "Configured Fixtures",
		"stock_uom": "Nos",
		"is_stock_item": False,  # Not a stock item - just a placeholder
		"is_sales_item": True,
		"description": "Placeholder item for ilLumenate configured fixtures. Actual configuration details stored in custom fields.",
	}).insert(ignore_permissions=True)


@frappe.whitelist()
def generate_manufacturing_packages_from_so(sales_order_name):
	"""
	Generate configured items/BOMs/WOs from Sales Order lines.

	Requires: Illumenate Admin or Illumenate Product Manager role.

	Args:
		sales_order_name: The Sales Order name

	Returns:
		Dict with results for each processed line or error info
	"""
	import json

	# Check permissions
	if not (
		frappe.db.exists("Has Role", {"parent": frappe.session.user, "role": "Illumenate Admin"})
		or frappe.db.exists("Has Role", {"parent": frappe.session.user, "role": "Illumenate Product Manager"})
		or frappe.session.user == "Administrator"
	):
		frappe.throw(_("Insufficient permissions. Requires Illumenate Admin or Product Manager role."))

	if not frappe.db.exists("Sales Order", sales_order_name):
		frappe.throw(_("Sales Order not found: {0}").format(sales_order_name))

	so = frappe.get_doc("Sales Order", sales_order_name)
	results = []
	updated = False

	for item in so.items:
		# Only process placeholder items with configuration JSON
		if item.item_code != "ILL-CONFIGURED-FIXTURE":
			continue

		config_json = getattr(item, "ill_configuration_json", None)
		if not config_json:
			continue

		# Skip if already processed
		if getattr(item, "ill_work_order", None):
			results.append({
				"row": item.idx,
				"status": "skipped",
				"message": "Already processed",
				"work_order": item.ill_work_order,
			})
			continue

		# Parse stored config
		try:
			config = json.loads(config_json)
		except json.JSONDecodeError:
			results.append({
				"row": item.idx,
				"status": "error",
				"message": "Invalid configuration JSON",
			})
			continue

		# Extract inputs from config
		inputs = config.get("inputs", {})
		if not inputs:
			results.append({
				"row": item.idx,
				"status": "error",
				"message": "No inputs found in configuration",
			})
			continue

		# Call create_manufacturing_package with stored inputs
		try:
			result = create_manufacturing_package(
				template_code=inputs.get("template_code"),
				tape_spec=inputs.get("tape_spec"),
				tape_attribute_combination=inputs.get("tape_attribute_combination"),
				requested_overall_in=inputs.get("requested_overall_in"),
				endcap_item=inputs.get("endcap_item"),
				driver_spec=inputs.get("driver_spec"),
				driver_attribute_combination=inputs.get("driver_attribute_combination"),
				qty=int(item.qty),
				tape_type_token=inputs.get("tape_type_token"),
				environment_token=inputs.get("environment_token"),
				cct_token=inputs.get("cct_token"),
				cri_value=inputs.get("cri_value"),
				output_token=inputs.get("output_token"),
				finish_token=inputs.get("finish_token"),
				lens_option=inputs.get("lens_option"),
				mounting_method=inputs.get("mounting_method"),
				joiner_angle=inputs.get("joiner_angle"),
				tier_name=inputs.get("tier_name"),
				customer=so.customer,
			)

			if result.get("error"):
				results.append({
					"row": item.idx,
					"status": "error",
					"message": str(result.get("errors", [])),
				})
				continue

			# Update SO item row with manufacturing links
			item.ill_configured_fixture = result.get("configured_fixture")
			item.ill_configured_item = result.get("item_code")
			item.ill_bom = result.get("bom_no")
			# Note: Work Order creation would require additional implementation
			# For now, we just mark that manufacturing package was created
			updated = True

			results.append({
				"row": item.idx,
				"status": "success",
				"configured_fixture": result.get("configured_fixture"),
				"item_code": result.get("item_code"),
				"bom_no": result.get("bom_no"),
			})

		except Exception as e:
			results.append({
				"row": item.idx,
				"status": "error",
				"message": str(e),
			})

	if updated:
		so.save()

	return {
		"success": True,
		"sales_order": sales_order_name,
		"results": results,
	}


# ============================================================================
# Sprint 6: PDF Template Management & Export Functions
# ============================================================================


@frappe.whitelist()
def list_pdf_fields(pdf_template_name: str) -> list:
	"""
	List all AcroForm field names in a PDF template.

	Args:
		pdf_template_name: The ILL PDF Template name

	Returns:
		List of field names found in the PDF
	"""
	from pypdf import PdfReader

	template = frappe.get_doc("ILL PDF Template", pdf_template_name)
	file_doc = frappe.get_doc("File", {"file_url": template.pdf_file})
	reader = PdfReader(file_doc.get_full_path())

	fields = reader.get_fields()
	return list(fields.keys()) if fields else []


@frappe.whitelist()
def export_schedule_csv(schedule_name: str):
	"""
	Export schedule as CSV with both line types.

	Args:
		schedule_name: The ILL Fixture Schedule name

	Returns:
		CSV file download response
	"""
	import csv
	import json
	from io import StringIO

	from custom_erpnext.illumenate_configurator.utils import get_customer_for_portal_user

	# Load the schedule
	if not frappe.db.exists("ILL Fixture Schedule", schedule_name):
		frappe.throw(_("Schedule not found: {0}").format(schedule_name))

	schedule = frappe.get_doc("ILL Fixture Schedule", schedule_name)

	# Permission check for portal users
	if frappe.db.exists("Has Role", {"parent": frappe.session.user, "role": "Customer"}):
		customer = get_customer_for_portal_user()
		if not customer or schedule.customer != customer:
			frappe.throw(_("Unauthorized"))

	# Get project info
	project = frappe.get_doc("ILL Project", schedule.project) if schedule.project else None

	# Build CSV
	output = StringIO()
	writer = csv.writer(output)

	# Headers
	headers = [
		"Project Name",
		"Schedule Name",
		"Line No",
		"Line Type",
		"Qty",
		"Tag",
		"Location",
		"Notes",
		"Configuration Summary",
		"Template Code",
		"Tape Spec",
		"Output",
		"CCT",
		"CRI",
		"Lens",
		"Mounting",
		"Finish",
		"Driver",
		"Unit Net",
		"Line Subtotal",
		"Manufacturer Name",
		"Model Number",
		"Description",
	]
	writer.writerow(headers)

	# Data rows
	for idx, line in enumerate(schedule.lines, start=1):
		config = {}
		if line.configuration_json:
			try:
				config = json.loads(line.configuration_json)
			except json.JSONDecodeError:
				pass

		inputs = config.get("inputs", {})

		row = [
			project.project_name if project else "",
			schedule.schedule_name,
			idx,
			line.line_type,
			line.qty,
			inputs.get("tag", ""),
			inputs.get("location", ""),
			inputs.get("notes", ""),
			line.configuration_summary or "",
			line.fixture_template or "",
			inputs.get("tape_spec", ""),
			inputs.get("output_token", ""),
			inputs.get("cct_token", ""),
			inputs.get("cri_value", ""),
			inputs.get("lens_option", ""),
			inputs.get("mounting_method", ""),
			inputs.get("finish_token", ""),
			inputs.get("driver_spec", ""),
			line.unit_net if line.line_type == "ilLumenate" else "",
			line.line_total if line.line_type == "ilLumenate" else "",
			line.manufacturer_name or "",
			line.model_number or "",
			line.description or "",
		]
		writer.writerow(row)

	# Return as download
	output.seek(0)
	csv_content = output.getvalue()

	frappe.response["filename"] = f"{schedule_name}.csv"
	frappe.response["filecontent"] = csv_content
	frappe.response["type"] = "download"


@frappe.whitelist()
def export_schedule_pdf(schedule_name: str, include_pricing: int = 0):
	"""
	Export schedule as PDF with optional pricing columns.

	Args:
		schedule_name: The ILL Fixture Schedule name
		include_pricing: If 1, include pricing columns

	Returns:
		PDF file download response
	"""
	import json

	from frappe.utils.pdf import get_pdf

	from custom_erpnext.illumenate_configurator.utils import get_customer_for_portal_user

	# Load the schedule
	if not frappe.db.exists("ILL Fixture Schedule", schedule_name):
		frappe.throw(_("Schedule not found: {0}").format(schedule_name))

	schedule = frappe.get_doc("ILL Fixture Schedule", schedule_name)

	# Permission check for portal users
	if frappe.db.exists("Has Role", {"parent": frappe.session.user, "role": "Customer"}):
		customer = get_customer_for_portal_user()
		if not customer or schedule.customer != customer:
			frappe.throw(_("Unauthorized"))

	# Get project info
	project = frappe.get_doc("ILL Project", schedule.project) if schedule.project else None

	# Calculate totals
	schedule_total = sum(
		line.line_total or 0
		for line in schedule.lines
		if line.line_type == "ilLumenate" and line.line_total
	)

	# Parse configuration data for each line
	lines_data = []
	for idx, line in enumerate(schedule.lines, start=1):
		config = {}
		if line.configuration_json:
			try:
				config = json.loads(line.configuration_json)
			except json.JSONDecodeError:
				pass

		lines_data.append({
			"idx": idx,
			"line": line,
			"config": config,
		})

	# Render HTML template
	html = frappe.render_template(
		"custom_erpnext/illumenate_configurator/templates/schedule_pdf.html",
		{
			"schedule": schedule,
			"project": project,
			"lines_data": lines_data,
			"include_pricing": int(include_pricing),
			"schedule_total": schedule_total,
			"generated_date": frappe.utils.today(),
		},
	)

	# Convert to PDF
	pdf_content = get_pdf(html)

	# Return as download
	frappe.response["filename"] = f"{schedule_name}.pdf"
	frappe.response["filecontent"] = pdf_content
	frappe.response["type"] = "download"


@frappe.whitelist()
def generate_line_submittal(schedule_name: str, line_idx: int) -> bytes:
	"""
	Generate spec submittal PDF for a single ilLumenate line.

	Args:
		schedule_name: The ILL Fixture Schedule name
		line_idx: The line index (1-based)

	Returns:
		PDF bytes
	"""
	import json

	from custom_erpnext.illumenate_configurator.pdf_engine import fill_pdf_template
	from custom_erpnext.illumenate_configurator.utils import get_customer_for_portal_user

	# Load the schedule
	if not frappe.db.exists("ILL Fixture Schedule", schedule_name):
		frappe.throw(_("Schedule not found: {0}").format(schedule_name))

	schedule = frappe.get_doc("ILL Fixture Schedule", schedule_name)

	# Permission check for portal users
	if frappe.db.exists("Has Role", {"parent": frappe.session.user, "role": "Customer"}):
		customer = get_customer_for_portal_user()
		if not customer or schedule.customer != customer:
			frappe.throw(_("Unauthorized"))

	# Get the line
	line_idx = int(line_idx)
	if line_idx < 1 or line_idx > len(schedule.lines):
		frappe.throw(_("Invalid line index"))

	line = schedule.lines[line_idx - 1]

	if line.line_type != "ilLumenate":
		frappe.throw(_("Submittals can only be generated for ilLumenate lines"))

	if not line.configuration_json:
		frappe.throw(_("Line has no configuration data"))

	# Parse configuration
	try:
		config = json.loads(line.configuration_json)
	except json.JSONDecodeError:
		frappe.throw(_("Invalid configuration JSON"))

	inputs = config.get("inputs", {})
	template_code = inputs.get("template_code") or line.fixture_template

	if not template_code:
		frappe.throw(_("No fixture template specified for line"))

	# Find active PDF template for this fixture family
	pdf_template = frappe.db.get_value(
		"ILL PDF Template",
		{
			"template_type": "Fixture Submittal",
			"applies_to_fixture_template": template_code,
			"is_active": 1,
		},
		"name",
	)

	if not pdf_template:
		frappe.throw(
			_("No active PDF template found for fixture template '{0}'").format(template_code)
		)

	# Get project info
	project = frappe.get_doc("ILL Project", schedule.project) if schedule.project else None
	customer_doc = frappe.get_doc("Customer", schedule.customer) if schedule.customer else None

	# Build context from schedule/project/line/config data
	context = {
		# Project/Schedule
		"project_name": project.project_name if project else "",
		"project_code": project.name if project else "",
		"schedule_name": schedule.schedule_name,
		"customer_name": customer_doc.customer_name if customer_doc else "",
		"generated_date": frappe.utils.today(),
		# Line
		"line_no": line_idx,
		"qty": line.qty,
		"tag": inputs.get("tag", ""),
		"location": inputs.get("location", ""),
		"line_notes": inputs.get("notes", ""),
		"configuration_summary": line.configuration_summary or "",
		# Configuration data
		"template_code": template_code,
		"requested_overall_in": inputs.get("requested_overall_in", ""),
		"manufacturable_overall_in": config.get("length", {}).get("manufacturable", {}).get("in", ""),
		"requested_overall_mm": config.get("length", {}).get("requested", {}).get("mm", ""),
		"manufacturable_overall_mm": config.get("length", {}).get("manufacturable", {}).get("mm", ""),
		"tape_spec": inputs.get("tape_spec", ""),
		"watts_per_ft": config.get("electrical", {}).get("watts_per_ft", ""),
		"total_watts": config.get("electrical", {}).get("total_watts", ""),
		"runs_count": config.get("electrical", {}).get("runs_count", ""),
		"selected_driver_spec": config.get("driver", {}).get("driver_spec", ""),
		"selected_driver_qty": config.get("driver", {}).get("quantity", ""),
		"tape_type_token": inputs.get("tape_type_token", ""),
		"environment_token": inputs.get("environment_token", ""),
		"cct_token": inputs.get("cct_token", ""),
		"cri_value": inputs.get("cri_value", ""),
		"output_token": inputs.get("output_token", ""),
		"lens_option": inputs.get("lens_option", ""),
		"lens_color_token": inputs.get("lens_color_token", ""),
		"mounting_method": inputs.get("mounting_method", ""),
		"mounting_token": inputs.get("mounting_token", ""),
		"finish_token": inputs.get("finish_token", ""),
		"joiner_angle": inputs.get("joiner_angle", ""),
		"joiner_item": config.get("electrical", {}).get("joiner_item", ""),
		"joiner_qty": config.get("electrical", {}).get("joiner_qty", ""),
		"mounting_hardware_item": "",
		"mounting_hardware_qty": "",
		# Pricing (will be blocked by guardrail)
		"unit_msrp": line.unit_msrp or "",
		"unit_net": line.unit_net or "",
		"tier_name": line.tier_name or "",
		"discount_percent": line.discount_percent or "",
	}

	# Fill PDF template with guardrail enabled
	pdf_bytes, _warnings = fill_pdf_template(
		pdf_template_id=pdf_template,
		context=context,
		enforce_submittal_guardrail=True,
	)

	return pdf_bytes


@frappe.whitelist()
def generate_submittal_package(schedule_name: str, include_pricing_in_schedule: int = 0):
	"""
	Generate combined PDF: schedule + all ilLumenate submittals.

	Args:
		schedule_name: The ILL Fixture Schedule name
		include_pricing_in_schedule: If 1, include pricing in schedule section

	Returns:
		PDF file download response
	"""
	import json
	from io import BytesIO

	from frappe.utils.pdf import get_pdf
	from pypdf import PdfReader, PdfWriter

	from custom_erpnext.illumenate_configurator.pdf_engine import fill_pdf_template
	from custom_erpnext.illumenate_configurator.utils import get_customer_for_portal_user

	# Load the schedule
	if not frappe.db.exists("ILL Fixture Schedule", schedule_name):
		frappe.throw(_("Schedule not found: {0}").format(schedule_name))

	schedule = frappe.get_doc("ILL Fixture Schedule", schedule_name)

	# Permission check for portal users
	if frappe.db.exists("Has Role", {"parent": frappe.session.user, "role": "Customer"}):
		customer = get_customer_for_portal_user()
		if not customer or schedule.customer != customer:
			frappe.throw(_("Unauthorized"))

	# Get project info
	project = frappe.get_doc("ILL Project", schedule.project) if schedule.project else None

	# Calculate totals
	schedule_total = sum(
		line.line_total or 0
		for line in schedule.lines
		if line.line_type == "ilLumenate" and line.line_total
	)

	# Parse configuration data for each line
	lines_data = []
	for idx, line in enumerate(schedule.lines, start=1):
		config = {}
		if line.configuration_json:
			try:
				config = json.loads(line.configuration_json)
			except json.JSONDecodeError:
				pass

		lines_data.append({
			"idx": idx,
			"line": line,
			"config": config,
		})

	# Generate schedule PDF
	html = frappe.render_template(
		"custom_erpnext/illumenate_configurator/templates/schedule_pdf.html",
		{
			"schedule": schedule,
			"project": project,
			"lines_data": lines_data,
			"include_pricing": int(include_pricing_in_schedule),
			"schedule_total": schedule_total,
			"generated_date": frappe.utils.today(),
		},
	)

	schedule_pdf_bytes = get_pdf(html)

	# Create PDF writer for merging
	writer = PdfWriter()

	# Add schedule PDF pages
	schedule_reader = PdfReader(BytesIO(schedule_pdf_bytes))
	for page in schedule_reader.pages:
		writer.add_page(page)

	# Generate submittals for each ilLumenate line
	for idx, line in enumerate(schedule.lines, start=1):
		if line.line_type != "ilLumenate" or not line.configuration_json:
			continue

		try:
			config = json.loads(line.configuration_json)
		except json.JSONDecodeError:
			continue

		inputs = config.get("inputs", {})
		template_code = inputs.get("template_code") or line.fixture_template

		if not template_code:
			continue

		# Find active PDF template for this fixture family
		pdf_template = frappe.db.get_value(
			"ILL PDF Template",
			{
				"template_type": "Fixture Submittal",
				"applies_to_fixture_template": template_code,
				"is_active": 1,
			},
			"name",
		)

		if not pdf_template:
			continue

		# Get customer info
		customer_doc = (
			frappe.get_doc("Customer", schedule.customer)
			if schedule.customer
			else None
		)

		# Build context
		context = {
			"project_name": project.project_name if project else "",
			"project_code": project.name if project else "",
			"schedule_name": schedule.schedule_name,
			"customer_name": customer_doc.customer_name if customer_doc else "",
			"generated_date": frappe.utils.today(),
			"line_no": idx,
			"qty": line.qty,
			"tag": inputs.get("tag", ""),
			"location": inputs.get("location", ""),
			"line_notes": inputs.get("notes", ""),
			"configuration_summary": line.configuration_summary or "",
			"template_code": template_code,
			"requested_overall_in": inputs.get("requested_overall_in", ""),
			"manufacturable_overall_in": config.get("length", {})
			.get("manufacturable", {})
			.get("in", ""),
			"requested_overall_mm": config.get("length", {})
			.get("requested", {})
			.get("mm", ""),
			"manufacturable_overall_mm": config.get("length", {})
			.get("manufacturable", {})
			.get("mm", ""),
			"tape_spec": inputs.get("tape_spec", ""),
			"watts_per_ft": config.get("electrical", {}).get("watts_per_ft", ""),
			"total_watts": config.get("electrical", {}).get("total_watts", ""),
			"runs_count": config.get("electrical", {}).get("runs_count", ""),
			"selected_driver_spec": config.get("driver", {}).get("driver_spec", ""),
			"selected_driver_qty": config.get("driver", {}).get("quantity", ""),
			"tape_type_token": inputs.get("tape_type_token", ""),
			"environment_token": inputs.get("environment_token", ""),
			"cct_token": inputs.get("cct_token", ""),
			"cri_value": inputs.get("cri_value", ""),
			"output_token": inputs.get("output_token", ""),
			"lens_option": inputs.get("lens_option", ""),
			"lens_color_token": inputs.get("lens_color_token", ""),
			"mounting_method": inputs.get("mounting_method", ""),
			"mounting_token": inputs.get("mounting_token", ""),
			"finish_token": inputs.get("finish_token", ""),
			"joiner_angle": inputs.get("joiner_angle", ""),
			"joiner_item": config.get("electrical", {}).get("joiner_item", ""),
			"joiner_qty": config.get("electrical", {}).get("joiner_qty", ""),
			"mounting_hardware_item": "",
			"mounting_hardware_qty": "",
			"unit_msrp": line.unit_msrp or "",
			"unit_net": line.unit_net or "",
			"tier_name": line.tier_name or "",
			"discount_percent": line.discount_percent or "",
		}

		try:
			submittal_bytes, _warnings = fill_pdf_template(
				pdf_template_id=pdf_template,
				context=context,
				enforce_submittal_guardrail=True,
			)

			# Add submittal pages to writer
			submittal_reader = PdfReader(BytesIO(submittal_bytes))
			for page in submittal_reader.pages:
				writer.add_page(page)
		except Exception:
			# Skip lines where submittal generation fails
			continue

	# Write merged PDF
	output = BytesIO()
	writer.write(output)
	output.seek(0)

	# Return as download
	frappe.response["filename"] = f"{schedule_name}_submittal_package.pdf"
	frappe.response["filecontent"] = output.read()
	frappe.response["type"] = "download"


@frappe.whitelist()
def create_project(project_name, project_code=None, description=None, expected_start_date=None, expected_end_date=None):
	"""
	Create a new project for the current portal user's customer.

	Args:
		project_name: Name of the project (required)
		project_code: Optional project code
		description: Optional project description
		expected_start_date: Optional expected start date
		expected_end_date: Optional expected end date

	Returns:
		dict with project name on success
	"""
	from custom_erpnext.illumenate_configurator.utils import get_customer_for_portal_user

	customer = get_customer_for_portal_user()

	if not customer:
		frappe.throw("No customer linked to your account. Please contact support.")

	# Create the project
	project = frappe.get_doc({
		"doctype": "ILL Project",
		"customer": customer,
		"project_name": project_name,
		"project_code": project_code,
		"description": description,
		"expected_start_date": expected_start_date,
		"expected_end_date": expected_end_date,
		"status": "Draft",
	})

	project.insert()

	return {"name": project.name, "project_name": project.project_name}


@frappe.whitelist()
def create_schedule(project, schedule_name):
	"""
	Create a new fixture schedule for a project.

	Args:
		project: The ILL Project name (required)
		schedule_name: Name of the schedule (required)

	Returns:
		dict with schedule name on success
	"""
	from custom_erpnext.illumenate_configurator.utils import get_customer_for_portal_user

	customer = get_customer_for_portal_user()

	if not customer:
		frappe.throw("No customer linked to your account. Please contact support.")

	# Validate project access
	if not frappe.db.exists("ILL Project", project):
		frappe.throw("Project not found.")

	project_customer = frappe.db.get_value("ILL Project", project, "customer")
	if project_customer != customer:
		frappe.throw("You do not have permission to access this project.")

	# Create the schedule
	schedule = frappe.get_doc({
		"doctype": "ILL Fixture Schedule",
		"project": project,
		"schedule_name": schedule_name,
		"status": "Draft",
	})

	schedule.insert()

	return {"name": schedule.name, "schedule_name": schedule.schedule_name}
