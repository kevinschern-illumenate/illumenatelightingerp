# Copyright (c) 2024, ilLumenate Lighting and contributors
# For license information, please see license.txt

"""
Configurator Rules Engine v1 - Core Math Module

This module implements the core calculations for the fixture configurator:
- Length computation (round down to cut increment)
- Run count calculation (≤85W per run)
- Driver auto-selection (80% derating, multi-driver)

All internal math is in mm. Inputs are in inches. Outputs display to nearest 1/16".
"""

import math


def inches_to_mm(inches: float) -> float:
	"""Convert inches to millimeters."""
	return inches * 25.4


def mm_to_inches(mm: float) -> float:
	"""Convert millimeters to inches."""
	return mm / 25.4


def format_to_16th(inches: float) -> float:
	"""
	Round inches to the nearest 1/16" increment.
	in_display = round(in_value * 16) / 16
	"""
	return round(inches * 16) / 16


def format_length_output(mm: float) -> dict:
	"""
	Format a length value for output with mm, raw inches, and 1/16" display.
	"""
	in_raw = mm_to_inches(mm)
	return {
		"mm": round(mm, 4),
		"in_raw": round(in_raw, 6),
		"in_display_1_16": format_to_16th(in_raw),
	}


def compute_length(
	requested_overall_in: float,
	endcap_allowance_mm_per_side: float,
	leader_allowance_mm: float,
	cut_increment_mm: float,
) -> dict:
	"""
	Compute the manufacturable length based on requested overall length.

	Rules:
	- E = endcap_allowance_mm_per_side
	- A = leader_allowance_mm (15mm default)
	- C = cut_increment_mm
	- L_internal = L_req_mm - 2E - A
	- L_tape_cut = floor(L_internal / C) * C
	- L_mfg = L_tape_cut + 2E + A

	Returns a dict with length details or an error.
	"""
	L_req_mm = inches_to_mm(requested_overall_in)
	E = endcap_allowance_mm_per_side
	A = leader_allowance_mm

	L_internal = L_req_mm - (2 * E) - A

	if L_internal <= 0:
		return {
			"error": True,
			"code": "LENGTH_TOO_SHORT",
			"message": "Requested length too short for selected tape/endcaps.",
		}

	# Round down to nearest cut increment
	L_tape_cut = math.floor(L_internal / cut_increment_mm) * cut_increment_mm

	if L_tape_cut <= 0:
		return {
			"error": True,
			"code": "LENGTH_TOO_SHORT",
			"message": "Requested length too short for selected tape/endcaps.",
		}

	L_mfg = L_tape_cut + (2 * E) + A
	L_delta = L_req_mm - L_mfg

	warning = (
		f"Length has been rounded down to the nearest tape cut increment. "
		f"Requested: {format_to_16th(mm_to_inches(L_req_mm))}\" → "
		f"Manufacturable: {format_to_16th(mm_to_inches(L_mfg))}\""
	)

	return {
		"error": False,
		"requested": format_length_output(L_req_mm),
		"tape_cut": format_length_output(L_tape_cut),
		"manufacturable": format_length_output(L_mfg),
		"delta": format_length_output(L_delta),
		"warning": warning,
		"internal_mm": L_internal,
	}


def compute_runs(tape_cut_mm: float, watts_per_ft: float, voltage_drop_max_run_ft: float | None = None) -> dict:
	"""
	Compute the number of runs based on 85W maximum per run AND voltage drop max run length.

	Rules:
	- Total_ft = L_tape_cut_mm / 304.8
	- W_total = Total_ft * watts_per_ft
	- MaxRun_ft_by_85w = 85 / watts_per_ft
	- MaxRun_ft_by_voltage_drop = voltage_drop_max_run_ft (if provided)
	- Effective MaxRun_ft = min(MaxRun_ft_by_85w, MaxRun_ft_by_voltage_drop)
	- runs_count = ceil(Total_ft / Effective_MaxRun_ft) (minimum 1)

	Returns a dict with electrical calculations.
	"""
	# Constants
	MAX_WATTS_PER_RUN = 85.0
	MM_PER_FOOT = 304.8

	total_ft = tape_cut_mm / MM_PER_FOOT
	w_total = total_ft * watts_per_ft
	max_run_ft_by_85w = MAX_WATTS_PER_RUN / watts_per_ft

	# Determine effective max run (minimum of 85W rule and voltage drop limit)
	if voltage_drop_max_run_ft and voltage_drop_max_run_ft > 0:
		effective_max_run_ft = min(max_run_ft_by_85w, voltage_drop_max_run_ft)
		limiting_factor = "voltage_drop" if voltage_drop_max_run_ft < max_run_ft_by_85w else "85w_rule"
	else:
		effective_max_run_ft = max_run_ft_by_85w
		limiting_factor = "85w_rule"

	if total_ft > 0:
		runs_count = max(1, math.ceil(total_ft / effective_max_run_ft))
	else:
		runs_count = 1

	return {
		"watts_per_ft": watts_per_ft,
		"total_watts": round(w_total, 2),
		"runs_count": runs_count,
		"max_run_ft_by_85w": round(max_run_ft_by_85w, 4),
		"max_run_ft_by_voltage_drop": round(voltage_drop_max_run_ft, 4) if voltage_drop_max_run_ft else None,
		"effective_max_run_ft": round(effective_max_run_ft, 4),
		"limiting_factor": limiting_factor,
		"total_ft": round(total_ft, 4),
	}


def select_driver(
	eligible_drivers: list,
	runs_count: int,
	total_watts: float,
) -> dict:
	"""
	Auto-select the best driver and quantity based on runs and wattage.

	Eligibility is pre-filtered by caller (voltage, dimming_protocol, is_active).

	Sizing rules:
	- W_usable = 0.8 * max_wattage
	- N_out = ceil(runs_count / outputs_count)
	- N_w = ceil(W_total / W_usable)
	- N = max(N_out, N_w)

	Ranking:
	1. Lowest N
	2. Then lowest max_wattage
	3. Tie-breaker: driver_item code/name sort

	Returns the best driver spec with quantity, or an error if none found.
	"""
	if not eligible_drivers:
		return {
			"error": True,
			"code": "NO_MATCHING_DRIVER",
			"message": "No driver found matching the required voltage and dimming protocol.",
		}

	candidates = []

	for driver in eligible_drivers:
		max_wattage = driver.get("max_wattage", 0)
		outputs_count = driver.get("outputs_count", 1)
		usable_wattage = max_wattage * 0.8

		if usable_wattage <= 0:
			continue

		N_out = math.ceil(runs_count / outputs_count)
		N_w = math.ceil(total_watts / usable_wattage)
		N = max(N_out, N_w)

		candidates.append(
			{
				"driver": driver,
				"quantity": N,
				"usable_watts_each": round(usable_wattage, 2),
				"total_usable_watts": round(usable_wattage * N, 2),
				"N_out": N_out,
				"N_w": N_w,
			}
		)

	if not candidates:
		return {
			"error": True,
			"code": "NO_MATCHING_DRIVER",
			"message": "No driver found matching the required voltage and dimming protocol.",
		}

	# Sort by: 1) quantity ascending, 2) max_wattage ascending, 3) driver_item name
	candidates.sort(
		key=lambda x: (
			x["quantity"],
			x["driver"].get("max_wattage", 0),
			x["driver"].get("driver_item", "") or x["driver"].get("name", ""),
		)
	)

	best = candidates[0]

	return {
		"error": False,
		"driver_spec": best["driver"].get("name"),
		"driver_item": best["driver"].get("driver_item"),
		"quantity": best["quantity"],
		"usable_watts_each": best["usable_watts_each"],
		"total_usable_watts": best["total_usable_watts"],
	}
