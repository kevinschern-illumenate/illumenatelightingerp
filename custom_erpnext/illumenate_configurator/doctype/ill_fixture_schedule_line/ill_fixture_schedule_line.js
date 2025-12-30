// Copyright (c) 2024, ilLumenate Lighting and contributors
// For license information, please see license.txt

frappe.ui.form.on("ILL Fixture Schedule Line", {
	fixture_template: function (frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		if (row.fixture_template && row.line_type === "ilLumenate") {
			load_template_data(frm, row);
		}
	},

	tape_spec: function (frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		if (row.tape_spec) {
			load_tape_variants(frm, row);
		}
	},

	driver_spec: function (frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		if (row.driver_spec) {
			load_driver_variants(frm, row);
		}
	},

	configure_fixture_button: function (frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		if (!row.fixture_template) {
			frappe.msgprint(__("Please select a Fixture Template first."));
			return;
		}
		validate_and_configure(frm, row, cdt, cdn);
	},

	requested_length_in: function (frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		// Clear computed fields when length changes
		clear_computed_fields(frm, row, cdt, cdn);
	},

	line_type: function (frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		if (row.line_type === "Other Manufacturer") {
			// Clear ilLumenate fields when switching to Other Manufacturer
			clear_illumenate_fields(frm, row, cdt, cdn);
		} else {
			// Clear Other Manufacturer fields when switching to ilLumenate
			clear_other_mfr_fields(frm, row, cdt, cdn);
		}
		frm.refresh_field("lines");
	},
});

function load_template_data(frm, row) {
	// Combined function: loads template data, sets filters and defaults in a single API call
	frappe.call({
		method: "frappe.client.get",
		args: {
			doctype: "ILL Fixture Template",
			name: row.fixture_template,
		},
		callback: function (r) {
			if (r.message) {
				var template = r.message;

				// Store allowed endcaps for filter
				if (template.endcap_options && template.endcap_options.length > 0) {
					row._allowed_endcaps = template.endcap_options.map(function (opt) {
						return opt.endcap_item;
					});

					// Set default endcap
					for (var i = 0; i < template.endcap_options.length; i++) {
						if (template.endcap_options[i].is_default) {
							row.endcap_item = template.endcap_options[i].endcap_item;
							break;
						}
					}
				}

				frm.refresh_field("lines");
			}
		},
	});
}

function load_tape_variants(frm, row) {
	frappe.call({
		method: "custom_erpnext.illumenate_configurator.api.get_tape_spec_variants",
		args: { tape_spec: row.tape_spec },
		callback: function (r) {
			if (r.message && r.message.variants) {
				// Store variants for combo selection
				row._tape_variants = r.message.variants;
				row._tape_attribute_map = {};
				r.message.variants.forEach(function (v) {
					row._tape_attribute_map[v.attribute_combination] =
						v.attribute_combination_full;
				});
			}
		},
	});
}

function load_driver_variants(frm, row) {
	frappe.call({
		method: "custom_erpnext.illumenate_configurator.api.get_driver_spec_variants",
		args: { driver_spec: row.driver_spec },
		callback: function (r) {
			if (r.message && r.message.variants) {
				// Store variants for combo selection
				row._driver_variants = r.message.variants;
				row._driver_attribute_map = {};
				r.message.variants.forEach(function (v) {
					row._driver_attribute_map[v.attribute_combination] =
						v.attribute_combination_full;
				});
			}
		},
	});
}

function validate_and_configure(frm, row, cdt, cdn) {
	// Validate required fields
	if (!row.fixture_template) {
		frappe.msgprint(__("Please select a Fixture Template."));
		return;
	}
	if (!row.tape_spec) {
		frappe.msgprint(__("Please select a Tape Spec."));
		return;
	}
	if (!row.tape_attribute_combination) {
		frappe.msgprint(__("Please select a Tape Attribute Combination."));
		return;
	}
	if (!row.requested_length_in || row.requested_length_in <= 0) {
		frappe.msgprint(__("Please enter a valid Requested Length (greater than 0)."));
		return;
	}

	// Resolve abbreviated attribute combinations to full versions
	var tape_attr_full = resolve_attribute_combination(
		row._tape_attribute_map,
		row.tape_attribute_combination
	);
	var driver_attr_full = resolve_attribute_combination(
		row._driver_attribute_map,
		row.driver_attribute_combination
	);

	// Build validation args
	var args = {
		template_code: row.fixture_template,
		tape_spec: row.tape_spec,
		tape_attribute_combination: tape_attr_full,
		requested_overall_in: row.requested_length_in,
		endcap_item: row.endcap_item || null,
	};

	// Add optional fields
	if (row.driver_spec && row.driver_attribute_combination) {
		args.driver_spec = row.driver_spec;
		args.driver_attribute_combination = driver_attr_full;
	}
	if (row.tape_type_token) args.tape_type_token = row.tape_type_token;
	if (row.environment_token) args.environment_token = row.environment_token;
	if (row.cct_token) args.cct_token = row.cct_token;
	if (row.cri_value) args.cri_value = row.cri_value;
	if (row.output_token) args.output_token = row.output_token;
	if (row.finish_token) args.finish_token = row.finish_token;
	if (row.lens_option) args.lens_option = row.lens_option;
	if (row.mounting_method) args.mounting_method = row.mounting_method;
	if (row.joiner_angle) args.joiner_angle = row.joiner_angle;

	frappe.call({
		method: "custom_erpnext.illumenate_configurator.api.validate_configuration",
		args: args,
		freeze: true,
		freeze_message: __("Validating configuration..."),
		callback: function (r) {
			if (r.message) {
				handle_validation_result(frm, row, cdt, cdn, r.message, args);
			}
		},
		error: function (r) {
			frappe.msgprint({
				title: __("Validation Error"),
				message: r.message || __("An unexpected error occurred"),
				indicator: "red",
			});
		},
	});
}

function handle_validation_result(frm, row, cdt, cdn, result, args) {
	if (result.errors && result.errors.length > 0) {
		// Display validation errors
		var error_html = "<ul>";
		result.errors.forEach(function (err) {
			error_html += "<li><strong>" + err.code + ":</strong> " + err.message;
			if (err.field) {
				error_html += " (" + __("field") + ": " + err.field + ")";
			}
			error_html += "</li>";
		});
		error_html += "</ul>";

		frappe.msgprint({
			title: __("Configuration Errors"),
			message: error_html,
			indicator: "red",
		});

		frappe.model.set_value(cdt, cdn, "configuration_valid", 0);
		return;
	}

	// Configuration is valid - update all computed fields
	var length = result.length;
	var electrical = result.electrical;
	var driver = result.driver;
	var pricing = result.pricing;

	// Update length fields
	frappe.model.set_value(cdt, cdn, "manufacturable_length_in", length.manufacturable.in);
	frappe.model.set_value(cdt, cdn, "manufacturable_length_mm", length.manufacturable.mm);
	frappe.model.set_value(cdt, cdn, "tape_cut_length_mm", length.tape_cut.mm);
	frappe.model.set_value(cdt, cdn, "led_tape_length_mm", length.tape_cut.mm);

	// Update electrical fields
	frappe.model.set_value(cdt, cdn, "watts_per_ft", electrical.watts_per_ft);
	frappe.model.set_value(cdt, cdn, "total_watts", electrical.total_watts);
	frappe.model.set_value(cdt, cdn, "max_run_length_ft", electrical.effective_max_run_ft);
	frappe.model.set_value(cdt, cdn, "runs_count", electrical.runs_count);

	// Update driver fields
	frappe.model.set_value(cdt, cdn, "selected_driver_spec", driver.driver_spec);
	frappe.model.set_value(cdt, cdn, "selected_driver_qty", driver.quantity);

	// Update pricing fields
	if (pricing && !pricing.error) {
		frappe.model.set_value(cdt, cdn, "unit_msrp", pricing.unit_msrp);
		frappe.model.set_value(cdt, cdn, "unit_net", pricing.unit_net_price);
		frappe.model.set_value(cdt, cdn, "tier_name", pricing.tier_name);
		frappe.model.set_value(cdt, cdn, "discount_percent", pricing.discount_percent);
		var qty = row.qty || 1;
		frappe.model.set_value(cdt, cdn, "line_total", pricing.unit_net_price * qty);
	}

	// Store full configuration JSON
	var config = {
		inputs: result.inputs,
		length: result.length,
		electrical: result.electrical,
		driver: result.driver,
		pricing: pricing,
	};
	frappe.model.set_value(cdt, cdn, "configuration_json", JSON.stringify(config));

	// Generate summary
	var summary = generate_configuration_summary(row, result);
	frappe.model.set_value(cdt, cdn, "configuration_summary", summary);

	// Mark as valid
	frappe.model.set_value(cdt, cdn, "configuration_valid", 1);

	frm.refresh_field("lines");

	// Show success message with summary
	var msg_html = '<div class="row">';
	msg_html += '<div class="col-md-6">';
	msg_html += "<h5>" + __("Length") + "</h5>";
	msg_html += "<p>" + __("Requested") + ": " + length.requested.in_display_1_16 + '"</p>';
	msg_html +=
		"<p>" + __("Manufacturable") + ": " + length.manufacturable.in_display_1_16 + '"</p>';
	msg_html += "</div>";
	msg_html += '<div class="col-md-6">';
	msg_html += "<h5>" + __("Electrical") + "</h5>";
	msg_html += "<p>" + __("Total Watts") + ": " + electrical.total_watts + " W</p>";
	msg_html += "<p>" + __("Runs") + ": " + electrical.runs_count + "</p>";
	msg_html += "</div>";
	msg_html += "</div>";

	if (pricing && !pricing.error) {
		msg_html += '<div class="row">';
		msg_html += '<div class="col-md-12">';
		msg_html += "<h5>" + __("Pricing") + "</h5>";
		msg_html +=
			"<p>" +
			__("Unit Net") +
			": $" +
			pricing.unit_net_price.toFixed(2) +
			" (" +
			pricing.tier_name +
			")</p>";
		msg_html += "</div>";
		msg_html += "</div>";
	}

	frappe.msgprint({
		title: __("Configuration Valid"),
		message: msg_html,
		indicator: "green",
	});
}

function generate_configuration_summary(row, result) {
	var parts = [];

	parts.push(row.fixture_template);
	parts.push(result.length.manufacturable.in_display_1_16 + '"');

	if (row.cct_token) parts.push(row.cct_token);
	if (row.cri_value) parts.push(row.cri_value + " CRI");
	if (row.output_token) parts.push(row.output_token + "lm");
	if (row.finish_token) parts.push(row.finish_token);
	if (row.lens_option) parts.push(row.lens_option);
	if (row.mounting_method) parts.push(row.mounting_method);

	return parts.join(" | ");
}

function clear_computed_fields(frm, row, cdt, cdn) {
	frappe.model.set_value(cdt, cdn, "configuration_valid", 0);
	frappe.model.set_value(cdt, cdn, "manufacturable_length_in", null);
	frappe.model.set_value(cdt, cdn, "manufacturable_length_mm", null);
	frappe.model.set_value(cdt, cdn, "tape_cut_length_mm", null);
	frappe.model.set_value(cdt, cdn, "led_tape_length_mm", null);
	frappe.model.set_value(cdt, cdn, "watts_per_ft", null);
	frappe.model.set_value(cdt, cdn, "total_watts", null);
	frappe.model.set_value(cdt, cdn, "max_run_length_ft", null);
	frappe.model.set_value(cdt, cdn, "runs_count", null);
	frappe.model.set_value(cdt, cdn, "selected_driver_spec", null);
	frappe.model.set_value(cdt, cdn, "selected_driver_qty", null);
	frappe.model.set_value(cdt, cdn, "configuration_json", null);
	frappe.model.set_value(cdt, cdn, "configuration_summary", null);
}

function clear_illumenate_fields(frm, row, cdt, cdn) {
	clear_computed_fields(frm, row, cdt, cdn);
	frappe.model.set_value(cdt, cdn, "fixture_template", null);
	frappe.model.set_value(cdt, cdn, "requested_length_in", null);
	frappe.model.set_value(cdt, cdn, "tape_spec", null);
	frappe.model.set_value(cdt, cdn, "tape_attribute_combination", null);
	frappe.model.set_value(cdt, cdn, "tape_type_token", null);
	frappe.model.set_value(cdt, cdn, "environment_token", null);
	frappe.model.set_value(cdt, cdn, "cct_token", null);
	frappe.model.set_value(cdt, cdn, "cri_value", null);
	frappe.model.set_value(cdt, cdn, "output_token", null);
	frappe.model.set_value(cdt, cdn, "endcap_item", null);
	frappe.model.set_value(cdt, cdn, "finish_token", null);
	frappe.model.set_value(cdt, cdn, "lens_option", null);
	frappe.model.set_value(cdt, cdn, "mounting_method", null);
	frappe.model.set_value(cdt, cdn, "joiner_angle", null);
	frappe.model.set_value(cdt, cdn, "driver_spec", null);
	frappe.model.set_value(cdt, cdn, "driver_attribute_combination", null);
	frappe.model.set_value(cdt, cdn, "unit_msrp", null);
	frappe.model.set_value(cdt, cdn, "unit_net", null);
	frappe.model.set_value(cdt, cdn, "tier_name", null);
	frappe.model.set_value(cdt, cdn, "discount_percent", null);
	frappe.model.set_value(cdt, cdn, "line_total", null);
}

function clear_other_mfr_fields(frm, row, cdt, cdn) {
	frappe.model.set_value(cdt, cdn, "manufacturer_name", null);
	frappe.model.set_value(cdt, cdn, "model_number", null);
	// Clear spec_data table
	row.spec_data = [];
}

function resolve_attribute_combination(map, abbr_value) {
	if (!abbr_value) return abbr_value;
	var full_value = (map || {})[abbr_value];
	return full_value !== undefined ? full_value : abbr_value;
}
