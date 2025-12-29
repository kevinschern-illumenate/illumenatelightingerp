# Copyright (c) 2024, ilLumenate Lighting and contributors
# For license information, please see license.txt

"""
ILL Configured Fixture DocType

Represents a fully configured fixture with computed dimensions, electrical specs,
and references to created Items and BOMs.
"""

import hashlib
import json

import frappe
from frappe import _
from frappe.model.document import Document

from custom_erpnext.illumenate_configurator.engine import (
	compute_length,
	compute_runs,
	select_driver,
)


class ILLConfiguredFixture(Document):
	def validate(self):
		self.compute_requested_mm()
		self.generate_configuration_signature()

	def before_save(self):
		# Check for existing fixture with same signature
		if self.configuration_signature:
			existing = frappe.db.get_value(
				"ILL Configured Fixture",
				{
					"configuration_signature": self.configuration_signature,
					"name": ("!=", self.name),
				},
				"name",
			)
			if existing:
				frappe.throw(
					_(
						"A configured fixture with this configuration already exists: {0}. "
						"Please use the existing configuration."
					).format(existing)
				)

	def compute_requested_mm(self):
		"""Convert requested_overall_in to mm."""
		if self.requested_overall_in:
			self.requested_overall_mm = round(self.requested_overall_in * 25.4, 2)
		else:
			self.requested_overall_mm = 0

	def generate_configuration_signature(self):
		"""Generate deterministic signature from normalized inputs."""
		signature_data = {
			"template_code": self.fixture_template,
			"tape_spec": self.tape_spec,
			"tape_attribute_combination": self.tape_attribute_combination or "",
			"endcap_item": self.endcap_item,
			"requested_overall_mm": round(self.requested_overall_mm, 2) if self.requested_overall_mm else 0,
			# Sprint 3 additions
			"tape_type_token": self.tape_type_token or "",
			"environment_token": self.environment_token or "",
			"cct_token": self.cct_token or "",
			"cri_value": self.cri_value or 0,
			"output_token": self.output_token or 0,
			"finish_token": self.finish_token or "",
			"lens_option": self.lens_option or "",
			"mounting_method": self.mounting_method or "",
			"joiner_angle": self.joiner_angle or "",
		}
		sorted_json = json.dumps(signature_data, sort_keys=True)
		self.configuration_signature = hashlib.md5(sorted_json.encode()).hexdigest()

	def generate_sku(self) -> str:
		"""Generate SKU with tokens and fraction-style length."""
		from custom_erpnext.illumenate_configurator.engine import format_length_as_fraction

		if not self.manufacturable_overall_in:
			return ""

		length_token = format_length_as_fraction(self.manufacturable_overall_in)

		# Build token string
		tokens = [
			"ILL",
			self.fixture_template,
			self.tape_type_token or "NA",
			self.environment_token or "NA",
			self.cct_token or "NA",
			f"CRI{self.cri_value}" if self.cri_value else "CRINA",
			str(self.output_token) if self.output_token else "NA",
			self.lens_color_token or "NA",
			self.mounting_token or "NA",
			self.finish_token or "NA",
			length_token,
			"PFNA",  # Powerfeed placeholder for later sprint
		]

		return "-".join(tokens)

	def compute_all(self):
		"""
		Compute all values from configuration inputs.
		This is called by the orchestration API after setting the input fields.
		"""
		# Load documents
		template = frappe.get_doc("ILL Fixture Template", self.fixture_template)
		tape_spec_doc = frappe.get_doc("ILL LED Tape Spec", self.tape_spec)

		# Get tape variant spec
		tape_variant_spec = tape_spec_doc.get_spec_for_attributes(self.tape_attribute_combination)
		if not tape_variant_spec:
			frappe.throw(_("Invalid tape attribute combination"))

		# Set allowances
		self.endcap_allowance_mm_per_side_used = template.get_endcap_allowance(self.endcap_item)
		self.leader_allowance_mm_used = template.leader_allowance_mm_per_fixture or 15.0

		# Compute length
		length_result = compute_length(
			requested_overall_in=self.requested_overall_in,
			endcap_allowance_mm_per_side=self.endcap_allowance_mm_per_side_used,
			leader_allowance_mm=self.leader_allowance_mm_used,
			cut_increment_mm=tape_variant_spec["cut_increment_mm"],
		)

		if length_result.get("error"):
			frappe.throw(_(length_result.get("message", "Length computation failed")))

		self.tape_cut_length_mm = length_result["tape_cut"]["mm"]
		self.manufacturable_overall_mm = length_result["manufacturable"]["mm"]
		self.manufacturable_overall_in = length_result["manufacturable"]["in_display_1_16"]
		self.delta_mm = length_result["delta"]["mm"]

		# Compute runs
		runs_result = compute_runs(
			tape_cut_mm=self.tape_cut_length_mm,
			watts_per_ft=tape_variant_spec["watts_per_ft"],
			voltage_drop_max_run_ft=tape_variant_spec.get("voltage_drop_max_run_ft"),
		)

		self.watts_per_ft = runs_result["watts_per_ft"]
		self.total_watts = runs_result["total_watts"]
		self.runs_count = runs_result["runs_count"]

		# Select driver
		voltage = tape_variant_spec["voltage"]

		if self.driver_spec and self.driver_attribute_combination:
			# Use specified driver
			driver_doc = frappe.get_doc("ILL Driver Spec", self.driver_spec)
			driver_variant_spec = driver_doc.get_spec_for_attributes(self.driver_attribute_combination)

			if not driver_variant_spec:
				frappe.throw(_("Invalid driver attribute combination"))

			if driver_variant_spec["voltage_out"] != voltage:
				frappe.throw(_("Driver voltage mismatch"))

			eligible_drivers = [
				{
					"name": self.driver_spec,
					"driver_item": driver_doc.driver_item,
					"max_wattage": driver_variant_spec["max_wattage"],
					"outputs_count": driver_variant_spec["outputs_count"],
				}
			]
		else:
			# Auto-select driver
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
							}
						)

		driver_result = select_driver(
			eligible_drivers=eligible_drivers,
			runs_count=self.runs_count,
			total_watts=self.total_watts,
		)

		if driver_result.get("error"):
			frappe.throw(_(driver_result.get("message", "No suitable driver found")))

		self.selected_driver_spec = driver_result["driver_spec"]
		self.selected_driver_qty = driver_result["quantity"]

		# Regenerate signature after computation
		self.generate_configuration_signature()


def generate_traveler_instructions(cf) -> str:
	"""Generate traveler instructions from configured fixture."""

	# Build options summary
	options_summary = f"""
Options Selected:
- Tape Type: {cf.tape_type_token or 'N/A'}
- Environment: {cf.environment_token or 'N/A'}
- CCT: {cf.cct_token or 'N/A'}, CRI: {cf.cri_value or 'N/A'}
- Output: {cf.output_token or 'N/A'}
- Finish: {cf.finish_token or 'N/A'}
- Lens: {cf.lens_option or 'N/A'} ({cf.lens_color_token or ''})
- Mounting: {cf.mounting_method or 'N/A'} ({cf.mounting_token or ''})
- Joiner Angle: {cf.joiner_angle or 'N/A'}
"""

	# Build segmentation section
	segmentation = ""
	if cf.profile_pieces_count:
		segmentation = f"""
Profile Segmentation:
- Total Pieces: {cf.profile_pieces_count}
- Last Piece Length: {cf.profile_last_piece_length_mm} mm
- Joiner: {cf.joiner_item or 'None'} x {cf.joiner_qty}
"""

	# Lens note
	lens_note = ""
	if cf.lens_option:
		lens_opt = frappe.get_doc("ILL Lens Option", cf.lens_option)
		if lens_opt.is_continuous_reel:
			lens_note = f"- Lens: Continuous reel, {cf.lens_qty_m}m"
		else:
			lens_note = f"- Lens: Segmented, {cf.lens_piece_count} pieces @ 2m each"

	header = "Configuration Instructions"
	return f"""
{header}
{"=" * len(header)}
Requested Overall Length: {cf.requested_overall_in}" ({cf.requested_overall_mm} mm)
Manufacturable Overall Length: {cf.manufacturable_overall_in}" ({cf.manufacturable_overall_mm} mm)
Delta (rounded down): {round(cf.delta_mm / 25.4, 4)}" ({cf.delta_mm} mm)
Tape Cut Length: {cf.tape_cut_length_mm} mm ({round(cf.tape_cut_length_mm / 25.4, 4)}")
Runs: {cf.runs_count}
Driver: {cf.selected_driver_spec} x {cf.selected_driver_qty} (80% derated)
{options_summary}
{segmentation}
Components:
- Profile: {round(cf.manufacturable_overall_mm / 1000, 3)} m
- Tape: {round(cf.tape_cut_length_mm / 1000, 3)} m
- Endcaps: 4 (includes extra pair)
- Leader cables: {cf.runs_count}
- Drivers: {cf.selected_driver_qty}
{lens_note}
- Mounting Hardware: {cf.mounting_hardware_item or 'None'} x {cf.mounting_hardware_qty}
"""
