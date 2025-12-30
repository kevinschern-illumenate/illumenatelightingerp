# Copyright (c) 2024, ilLumenate Lighting and contributors
# For license information, please see license.txt

"""
Pricing Service Module

Provides the price_configuration_unit function for computing unit MSRP and net prices
based on configuration details and tier discounts.
"""

import frappe


def price_configuration_unit(
	validated_result: dict,
	tier_name: str | None = None,
	customer: str | None = None,
) -> dict:
	"""
	Compute unit pricing for a validated configuration.

	Args:
		validated_result: The result from validate_configuration containing all computed values
		tier_name: Optional tier name (e.g., "MSRP", "Dealer A") for discount lookup
		customer: Optional customer name for tier lookup from customer record

	Returns:
		Dict with:
			- currency: Currency code (e.g., "USD")
			- tier_name: Name of the tier used
			- discount_percent: Discount percentage applied
			- unit_msrp: Unit MSRP price
			- unit_net_price: Unit net price after discount
			- breakdown: Optional breakdown dict (internal roles only)
			- error: Error code if pricing failed
			- message: Error message if pricing failed
	"""
	# Extract inputs from validated_result
	inputs = validated_result.get("inputs", {})
	template_code = inputs.get("template_code")
	length_data = validated_result.get("length", {})
	electrical = validated_result.get("electrical", {})
	driver = validated_result.get("driver", {})

	manufacturable_mm = length_data.get("manufacturable", {}).get("mm", 0)
	tape_cut_mm = length_data.get("tape_cut", {}).get("mm", 0)

	# Convert to meters
	m_profile = manufacturable_mm / 1000
	m_lens = manufacturable_mm / 1000
	m_tape = tape_cut_mm / 1000

	# Get driver info
	driver_item = driver.get("driver_item")
	driver_qty = driver.get("quantity", 0)
	runs_count = electrical.get("runs_count", 1)

	# Get joiner_qty from electrical if present (added in validate_configuration)
	joiner_qty = electrical.get("joiner_qty", 0)

	# Get optional inputs
	output_token = inputs.get("output_token")
	finish_token = inputs.get("finish_token")
	lens_option = inputs.get("lens_option")
	mounting_method = inputs.get("mounting_method")
	joiner_angle = inputs.get("joiner_angle")
	environment_token = inputs.get("environment_token")

	# 1. Load active Pricing Profile for template
	pricing_profile = frappe.db.get_value(
		"ILL Pricing Profile",
		{"fixture_template": template_code, "is_active": 1},
		[
			"name",
			"currency",
			"msrp_price_list",
			"base_fee",
			"profile_rate_per_m",
			"lens_rate_per_m",
			"tape_rate_per_m",
			"labor_fee",
			"labor_rate_per_m",
			"driver_markup_percent",
		],
		as_dict=True,
	)

	if not pricing_profile:
		return {
			"error": "PRICING_PROFILE_MISSING",
			"message": f"No active pricing profile found for template '{template_code}'",
		}

	# 2. Initialize MSRP with base fee
	msrp = float(pricing_profile.base_fee or 0)
	breakdown = {
		"base_fee": msrp,
		"profile_cost": 0,
		"lens_cost": 0,
		"tape_cost": 0,
		"labor_cost": 0,
		"option_adders": [],
		"driver_cost": 0,
	}

	# 3. Add length components
	profile_cost = float(pricing_profile.profile_rate_per_m or 0) * m_profile
	msrp += profile_cost
	breakdown["profile_cost"] = round(profile_cost, 2)

	lens_cost = float(pricing_profile.lens_rate_per_m or 0) * m_lens
	msrp += lens_cost
	breakdown["lens_cost"] = round(lens_cost, 2)

	# 4. Determine tape rate (check for output pricing override/adder)
	tape_rate = float(pricing_profile.tape_rate_per_m or 0)

	if output_token:
		output_pricing = frappe.db.get_value(
			"ILL Output Pricing",
			{"fixture_template": template_code, "output_token": output_token, "is_active": 1},
			["tape_rate_per_m_override", "tape_adder_per_m"],
			as_dict=True,
		)
		if output_pricing:
			if output_pricing.tape_rate_per_m_override:
				tape_rate = float(output_pricing.tape_rate_per_m_override)
			elif output_pricing.tape_adder_per_m:
				tape_rate += float(output_pricing.tape_adder_per_m)

	tape_cost = tape_rate * m_tape
	msrp += tape_cost
	breakdown["tape_cost"] = round(tape_cost, 2)

	# 5. Add labor
	labor_cost = float(pricing_profile.labor_fee or 0) + float(pricing_profile.labor_rate_per_m or 0) * m_profile
	msrp += labor_cost
	breakdown["labor_cost"] = round(labor_cost, 2)

	# 6. Apply option adders
	option_adders_total = 0
	adder_details = []

	# Query all active adders for this template
	adders = frappe.get_all(
		"ILL Option Price Adder",
		filters={"fixture_template": template_code, "is_active": 1},
		fields=["adder_type", "adder_key", "adder_mode", "amount"],
	)

	for adder in adders:
		# Check if this adder applies to current configuration
		applies = False
		adder_type = adder.get("adder_type")
		adder_key = adder.get("adder_key")

		if adder_type == "Finish" and finish_token and adder_key == finish_token:
			applies = True
		elif adder_type == "Lens Option" and lens_option and adder_key == lens_option:
			applies = True
		elif adder_type == "Mounting Method" and mounting_method and adder_key == mounting_method:
			applies = True
		elif adder_type == "Joiner Angle" and joiner_angle and adder_key == joiner_angle:
			applies = True
		elif adder_type == "Environment" and environment_token and adder_key == environment_token:
			applies = True
		# Dimming Protocol would require looking up driver variant dimming_protocol

		if applies:
			amount = float(adder.get("amount") or 0)
			adder_mode = adder.get("adder_mode")

			if adder_mode == "Flat Per Fixture":
				adder_amount = amount
			elif adder_mode == "Per Meter":
				adder_amount = amount * m_profile
			elif adder_mode == "Per Joiner":
				adder_amount = amount * joiner_qty
			elif adder_mode == "Per Driver":
				adder_amount = amount * driver_qty
			elif adder_mode == "Per Run":
				adder_amount = amount * runs_count
			else:
				adder_amount = 0

			option_adders_total += adder_amount
			adder_details.append({
				"type": adder_type,
				"key": adder_key,
				"mode": adder_mode,
				"amount": round(adder_amount, 2),
			})

	msrp += option_adders_total
	breakdown["option_adders"] = adder_details

	# 7. Add drivers (Item Price lookup)
	driver_cost = 0
	if driver_item and driver_qty > 0:
		price_list = pricing_profile.msrp_price_list or "MSRP"

		item_price = frappe.db.get_value(
			"Item Price",
			{"item_code": driver_item, "price_list": price_list, "selling": 1},
			"price_list_rate",
		)

		if not item_price:
			return {
				"error": "DRIVER_ITEM_PRICE_MISSING",
				"message": f"No Item Price found for driver '{driver_item}' in price list '{price_list}'",
			}

		driver_unit = float(item_price) * (1 + float(pricing_profile.driver_markup_percent or 0) / 100)
		driver_cost = driver_unit * driver_qty
		msrp += driver_cost

	breakdown["driver_cost"] = round(driver_cost, 2)

	# 8. Tier Resolution + Unit Net
	tier = None
	tier_name_used = "MSRP"
	discount = 0

	if tier_name:
		tier = frappe.db.get_value(
			"ILL Tier Rule",
			{"tier_name": tier_name, "is_active": 1},
			["tier_name", "discount_percent_off_msrp"],
			as_dict=True,
		)
	elif customer:
		tier_link = frappe.db.get_value("Customer", customer, "ill_pricing_tier")
		if tier_link:
			tier = frappe.db.get_value(
				"ILL Tier Rule",
				{"name": tier_link, "is_active": 1},
				["tier_name", "discount_percent_off_msrp"],
				as_dict=True,
			)

	if tier:
		discount = float(tier.get("discount_percent_off_msrp") or 0)
		tier_name_used = tier.get("tier_name") or "MSRP"

	net = msrp * (1 - discount / 100)

	# 9. Build result
	result = {
		"currency": pricing_profile.currency or "USD",
		"tier_name": tier_name_used,
		"discount_percent": round(discount, 2),
		"unit_msrp": round(msrp, 2),
		"unit_net_price": round(net, 2),
	}

	# 10. Only include breakdown for internal roles
	if frappe.has_role(["Illumenate Admin", "Illumenate Product Manager"]):
		result["breakdown"] = breakdown

	return result
