frappe.pages["configurator-test-harness"].on_page_load = function (wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: "Configurator Test Harness",
		single_column: true,
	});

	// Initialize controls
	page.template_field = page.add_field({
		label: "Template",
		fieldname: "template_code",
		fieldtype: "Link",
		options: "ILL Fixture Template",
		change: function () {
			// Reset endcap field when template changes
			page.endcap_field.set_value("");
			update_endcap_filter(page);
		},
	});

	page.endcap_field = page.add_field({
		label: "Endcap (optional)",
		fieldname: "endcap_item",
		fieldtype: "Link",
		options: "Item",
	});

	page.tape_field = page.add_field({
		label: "Tape Spec",
		fieldname: "tape_spec",
		fieldtype: "Link",
		options: "ILL LED Tape Spec",
		get_query: function () {
			return {
				filters: {
					is_active: 1,
				},
			};
		},
		change: function () {
			// Load available tape attribute combinations
			update_tape_attribute_options(page);
		},
	});

	page.tape_attribute_field = page.add_field({
		label: "Tape Attribute Combination",
		fieldname: "tape_attribute_combination",
		fieldtype: "Select",
		options: [""],
	});

	page.length_field = page.add_field({
		label: "Requested Overall Length (inches)",
		fieldname: "requested_overall_in",
		fieldtype: "Float",
	});

	page.driver_field = page.add_field({
		label: "Driver Spec (optional - auto-selects if empty)",
		fieldname: "driver_spec",
		fieldtype: "Link",
		options: "ILL Driver Spec",
		get_query: function () {
			return {
				filters: {
					is_active: 1,
				},
			};
		},
		change: function () {
			// Load available driver attribute combinations
			update_driver_attribute_options(page);
		},
	});

	page.driver_attribute_field = page.add_field({
		label: "Driver Attribute Combination",
		fieldname: "driver_attribute_combination",
		fieldtype: "Select",
		options: [""],
	});

	// === Sprint 3 Fields ===

	page.tape_type_field = page.add_field({
		label: "Tape Type",
		fieldname: "tape_type_token",
		fieldtype: "Select",
		options: ["", "SW", "TW", "RGBTW"],
	});

	page.environment_field = page.add_field({
		label: "Environment",
		fieldname: "environment_token",
		fieldtype: "Select",
		options: ["", "I", "O"],
	});

	page.cct_field = page.add_field({
		label: "CCT Token",
		fieldname: "cct_token",
		fieldtype: "Data",
	});

	page.cri_field = page.add_field({
		label: "CRI",
		fieldname: "cri_value",
		fieldtype: "Int",
	});

	page.output_field = page.add_field({
		label: "Output",
		fieldname: "output_token",
		fieldtype: "Int",
	});

	page.finish_field = page.add_field({
		label: "Finish",
		fieldname: "finish_token",
		fieldtype: "Data",
	});

	page.lens_option_field = page.add_field({
		label: "Lens Option",
		fieldname: "lens_option",
		fieldtype: "Link",
		options: "ILL Lens Option",
		get_query: function () {
			return { filters: { is_active: 1 } };
		},
	});

	page.mounting_method_field = page.add_field({
		label: "Mounting Method",
		fieldname: "mounting_method",
		fieldtype: "Link",
		options: "ILL Mounting Method",
		get_query: function () {
			return { filters: { is_active: 1 } };
		},
	});

	page.joiner_angle_field = page.add_field({
		label: "Joiner Angle",
		fieldname: "joiner_angle",
		fieldtype: "Select",
		options: ["", "Straight", "90", "Other"],
	});

	// === Sprint 4 Fields ===

	page.tier_field = page.add_field({
		label: "Pricing Tier",
		fieldname: "tier_name",
		fieldtype: "Select",
		options: ["MSRP", "Dealer A", "Dealer B", "Dealer C", "Dealer D"],
		default: "MSRP",
	});

	// Add validate button
	page.set_primary_action("Validate Configuration", function () {
		validate_configuration(page);
	});

	// Add result container
	$(wrapper).find(".layout-main-section").append(`
		<div class="configurator-results" style="margin-top: 20px;">
			<h4>Results</h4>
			<div class="results-summary" style="display: none; margin-bottom: 15px;">
				<div class="frappe-card p-4">
					<div class="row">
						<div class="col-md-3">
							<h5>Length</h5>
							<div class="length-summary"></div>
						</div>
						<div class="col-md-3">
							<h5>Electrical</h5>
							<div class="electrical-summary"></div>
						</div>
						<div class="col-md-3">
							<h5>Driver</h5>
							<div class="driver-summary"></div>
						</div>
						<div class="col-md-3">
							<h5>Pricing</h5>
							<div class="pricing-summary"></div>
						</div>
					</div>
					<div class="row mt-3">
						<div class="col-12">
							<div class="warning-message alert alert-warning" style="display: none;"></div>
						</div>
					</div>
				</div>
			</div>
			<div class="create-package-section" style="display: none; margin-bottom: 15px;">
				<button class="btn btn-success btn-create-package">
					<i class="fa fa-plus"></i> Create Manufacturing Package
				</button>
			</div>
			<div class="errors-container alert alert-danger" style="display: none;"></div>
			<div class="results-json" style="display: none;">
				<h5>Full Response (JSON)</h5>
				<pre class="json-output" style="background: #f5f5f5; padding: 15px; border-radius: 4px; overflow-x: auto;"></pre>
			</div>
		</div>
	`);

	page.results_container = $(wrapper).find(".configurator-results");

	// Attach click handler for Create Manufacturing Package button
	page.results_container.find(".btn-create-package").on("click", function () {
		create_manufacturing_package(page);
	});
};

function update_tape_attribute_options(page) {
	var tape_spec = page.tape_field.get_value();
	if (!tape_spec) {
		page.tape_attribute_field.df.options = [""];
		page.tape_attribute_field.set_value("");
		page.tape_attribute_field.refresh();
		page._tape_attribute_map = {};
		return;
	}

	frappe.call({
		method: "custom_erpnext.illumenate_configurator.api.get_tape_spec_variants",
		args: { tape_spec: tape_spec },
		callback: function (r) {
			if (r.message && r.message.variants) {
				// Store mapping from abbreviated to full attribute combination
				page._tape_attribute_map = {};
				var options = r.message.variants.map(function (v) {
					page._tape_attribute_map[v.attribute_combination] = v.attribute_combination_full;
					return v.attribute_combination;
				});
				page.tape_attribute_field.df.options = [""].concat(options);
				page.tape_attribute_field.set_value("");
				page.tape_attribute_field.refresh();
			}
		},
	});
}

function update_driver_attribute_options(page) {
	var driver_spec = page.driver_field.get_value();
	if (!driver_spec) {
		page.driver_attribute_field.df.options = [""];
		page.driver_attribute_field.set_value("");
		page.driver_attribute_field.refresh();
		page._driver_attribute_map = {};
		return;
	}

	frappe.call({
		method: "custom_erpnext.illumenate_configurator.api.get_driver_spec_variants",
		args: { driver_spec: driver_spec },
		callback: function (r) {
			if (r.message && r.message.variants) {
				// Store mapping from abbreviated to full attribute combination
				page._driver_attribute_map = {};
				var options = r.message.variants.map(function (v) {
					page._driver_attribute_map[v.attribute_combination] = v.attribute_combination_full;
					return v.attribute_combination;
				});
				page.driver_attribute_field.df.options = [""].concat(options);
				page.driver_attribute_field.set_value("");
				page.driver_attribute_field.refresh();
			}
		},
	});
}

function update_endcap_filter(page) {
	var template_code = page.template_field.get_value();
	if (!template_code) {
		return;
	}

	frappe.call({
		method: "frappe.client.get",
		args: {
			doctype: "ILL Fixture Template",
			name: template_code,
		},
		callback: function (r) {
			if (r.message && r.message.endcap_options) {
				var endcap_items = r.message.endcap_options.map(function (opt) {
					return opt.endcap_item;
				});

				page.endcap_field.df.get_query = function () {
					return {
						filters: {
							name: ["in", endcap_items],
						},
					};
				};
			}
		},
	});
}

function validate_configuration(page) {
	var template_code = page.template_field.get_value();
	var tape_spec = page.tape_field.get_value();
	var tape_attribute_combination_abbr = page.tape_attribute_field.get_value();
	var requested_overall_in = page.length_field.get_value();
	var endcap_item = page.endcap_field.get_value();
	var driver_spec = page.driver_field.get_value();
	var driver_attribute_combination_abbr = page.driver_attribute_field.get_value();

	// Sprint 3 fields
	var tape_type_token = page.tape_type_field.get_value();
	var environment_token = page.environment_field.get_value();
	var cct_token = page.cct_field.get_value();
	var cri_value = page.cri_field.get_value();
	var output_token = page.output_field.get_value();
	var finish_token = page.finish_field.get_value();
	var lens_option = page.lens_option_field.get_value();
	var mounting_method = page.mounting_method_field.get_value();
	var joiner_angle = page.joiner_angle_field.get_value();

	// Sprint 4 fields
	var tier_name = page.tier_field.get_value();

	// Validate required fields
	if (!template_code) {
		frappe.msgprint("Please select a Template");
		return;
	}
	if (!tape_spec) {
		frappe.msgprint("Please select a Tape Spec");
		return;
	}
	if (!tape_attribute_combination_abbr) {
		frappe.msgprint("Please select a Tape Attribute Combination");
		return;
	}
	if (!requested_overall_in || requested_overall_in <= 0) {
		frappe.msgprint("Please enter a valid length (greater than 0)");
		return;
	}

	// Resolve abbreviated attribute combinations to full versions for API
	var tape_attribute_combination = resolveAttributeCombination(page._tape_attribute_map, tape_attribute_combination_abbr);
	var driver_attribute_combination = resolveAttributeCombination(page._driver_attribute_map, driver_attribute_combination_abbr);

	// Build args
	var args = {
		template_code: template_code,
		tape_spec: tape_spec,
		tape_attribute_combination: tape_attribute_combination,
		requested_overall_in: requested_overall_in,
		endcap_item: endcap_item || null,
	};

	// Add optional driver params
	if (driver_spec && driver_attribute_combination_abbr) {
		args.driver_spec = driver_spec;
		args.driver_attribute_combination = driver_attribute_combination;
	}

	// Add Sprint 3 optional params
	if (tape_type_token) args.tape_type_token = tape_type_token;
	if (environment_token) args.environment_token = environment_token;
	if (cct_token) args.cct_token = cct_token;
	if (cri_value) args.cri_value = cri_value;
	if (output_token) args.output_token = output_token;
	if (finish_token) args.finish_token = finish_token;
	if (lens_option) args.lens_option = lens_option;
	if (mounting_method) args.mounting_method = mounting_method;
	if (joiner_angle) args.joiner_angle = joiner_angle;

	// Sprint 4 params
	if (tier_name) args.tier_name = tier_name;

	frappe.call({
		method: "custom_erpnext.illumenate_configurator.api.validate_configuration",
		args: args,
		freeze: true,
		freeze_message: "Validating configuration...",
		callback: function (r) {
			display_results(page, r.message);
		},
		error: function (r) {
			page.results_container.find(".results-summary").hide();
			page.results_container.find(".results-json").hide();
			page.results_container
				.find(".errors-container")
				.html("<strong>Error:</strong> " + (r.message || "An unexpected error occurred"))
				.show();
		},
	});
}

function display_results(page, result) {
	var summary = page.results_container.find(".results-summary");
	var errors_container = page.results_container.find(".errors-container");
	var json_container = page.results_container.find(".results-json");
	var json_output = page.results_container.find(".json-output");
	var create_package_section = page.results_container.find(".create-package-section");

	// Reset
	summary.hide();
	errors_container.hide();
	json_container.hide();
	create_package_section.hide();

	if (result.errors && result.errors.length > 0) {
		var error_html = "<strong>Validation Errors:</strong><ul>";
		result.errors.forEach(function (err) {
			error_html += "<li><strong>" + err.code + ":</strong> " + err.message;
			if (err.field) {
				error_html += " (field: " + err.field + ")";
			}
			error_html += "</li>";
		});
		error_html += "</ul>";
		errors_container.html(error_html).show();
	} else {
		// Display summary
		var length = result.length;
		var electrical = result.electrical;
		var driver = result.driver;

		var length_html = `
			<table class="table table-sm table-borderless">
				<tr><td>Requested:</td><td><strong>${length.requested.in_display_1_16}"</strong> (${length.requested.mm} mm)</td></tr>
				<tr><td>Manufacturable:</td><td><strong>${length.manufacturable.in_display_1_16}"</strong> (${length.manufacturable.mm} mm)</td></tr>
				<tr><td>Tape Cut:</td><td>${length.tape_cut.in_display_1_16}" (${length.tape_cut.mm} mm)</td></tr>
				<tr><td>Delta:</td><td>${length.delta.in_display_1_16}" (${length.delta.mm} mm)</td></tr>
			</table>
		`;

		var voltage_drop_row = electrical.max_run_ft_by_voltage_drop 
			? `<tr><td>Max Run (V-Drop):</td><td>${electrical.max_run_ft_by_voltage_drop} ft</td></tr>`
			: "";
		var limiting_factor_display = electrical.limiting_factor === "voltage_drop" 
			? "Voltage Drop" 
			: "85W Rule";

		var electrical_html = `
			<table class="table table-sm table-borderless">
				<tr><td>Watts per Foot:</td><td><strong>${electrical.watts_per_ft} W/ft</strong></td></tr>
				<tr><td>Total Watts:</td><td><strong>${electrical.total_watts} W</strong></td></tr>
				<tr><td>Run Count:</td><td><strong>${electrical.runs_count}</strong></td></tr>
				<tr><td>Max Run (85W):</td><td>${electrical.max_run_ft_by_85w} ft</td></tr>
				${voltage_drop_row}
				<tr><td>Effective Max Run:</td><td><strong>${electrical.effective_max_run_ft} ft</strong> (${limiting_factor_display})</td></tr>
			</table>
		`;

		var driver_html = `
			<table class="table table-sm table-borderless">
				<tr><td>Driver Spec:</td><td><strong>${driver.driver_spec}</strong></td></tr>
				<tr><td>Driver Item:</td><td>${driver.driver_item}</td></tr>
				<tr><td>Quantity:</td><td><strong>${driver.quantity}</strong></td></tr>
				<tr><td>Usable W (each):</td><td>${driver.usable_watts_each} W</td></tr>
				<tr><td>Total Usable W:</td><td>${driver.total_usable_watts} W</td></tr>
			</table>
		`;

		// Build pricing HTML
		var pricing_html = "";
		if (result.pricing) {
			var p = result.pricing;
			if (p.error) {
				pricing_html = `<div class="text-muted">${p.message || "Pricing unavailable"}</div>`;
			} else {
				pricing_html = `
					<table class="table table-sm table-borderless">
						<tr><td>Unit MSRP:</td><td><strong>$${p.unit_msrp.toFixed(2)}</strong></td></tr>
						<tr><td>Tier:</td><td>${p.tier_name}</td></tr>
						<tr><td>Discount:</td><td>${p.discount_percent}%</td></tr>
						<tr><td>Unit Net:</td><td><strong>$${p.unit_net_price.toFixed(2)}</strong></td></tr>
					</table>
				`;
				// Show breakdown for internal roles
				if (p.breakdown) {
					pricing_html += `<details><summary>Breakdown</summary>
						<pre style="font-size: 10px;">${JSON.stringify(p.breakdown, null, 2)}</pre>
					</details>`;
				}
			}
		} else {
			pricing_html = `<div class="text-muted">Pricing not available</div>`;
		}

		summary.find(".length-summary").html(length_html);
		summary.find(".electrical-summary").html(electrical_html);
		summary.find(".driver-summary").html(driver_html);
		summary.find(".pricing-summary").html(pricing_html);

		if (length.warning) {
			summary.find(".warning-message").html("<strong>Note:</strong> " + length.warning).show();
		} else {
			summary.find(".warning-message").hide();
		}

		summary.show();

		// Show "Create Manufacturing Package" button after successful validation
		page.results_container.find(".create-package-section").show();
	}

	// Always show JSON
	json_output.text(JSON.stringify(result, null, 2));
	json_container.show();
}

function create_manufacturing_package(page) {
	// Resolve abbreviated attribute combinations to full versions for API
	var tape_attribute_combination_abbr = page.tape_attribute_field.get_value();
	var driver_attribute_combination_abbr = page.driver_attribute_field.get_value();
	var tape_attribute_combination = resolveAttributeCombination(page._tape_attribute_map, tape_attribute_combination_abbr);
	var driver_attribute_combination = resolveAttributeCombination(page._driver_attribute_map, driver_attribute_combination_abbr);

	var args = {
		template_code: page.template_field.get_value(),
		tape_spec: page.tape_field.get_value(),
		tape_attribute_combination: tape_attribute_combination,
		requested_overall_in: page.length_field.get_value(),
		endcap_item: page.endcap_field.get_value() || null,
		driver_spec: page.driver_field.get_value() || null,
		driver_attribute_combination: driver_attribute_combination || null,
		qty: 1,
		// Sprint 3 fields
		tape_type_token: page.tape_type_field.get_value() || null,
		environment_token: page.environment_field.get_value() || null,
		cct_token: page.cct_field.get_value() || null,
		cri_value: page.cri_field.get_value() || null,
		output_token: page.output_field.get_value() || null,
		finish_token: page.finish_field.get_value() || null,
		lens_option: page.lens_option_field.get_value() || null,
		mounting_method: page.mounting_method_field.get_value() || null,
		joiner_angle: page.joiner_angle_field.get_value() || null,
		// Sprint 4 fields
		tier_name: page.tier_field.get_value() || "MSRP",
	};

	frappe.call({
		method: "custom_erpnext.illumenate_configurator.api.create_manufacturing_package",
		args: args,
		freeze: true,
		freeze_message: "Creating manufacturing package...",
		callback: function (r) {
			if (r.message && !r.message.error) {
				// Escape values to prevent XSS
				var escape_html = function(str) {
					if (!str) return '';
					return String(str)
						.replace(/&/g, '&amp;')
						.replace(/</g, '&lt;')
						.replace(/>/g, '&gt;')
						.replace(/"/g, '&quot;')
						.replace(/'/g, '&#39;');
				};
				var configured_fixture = escape_html(r.message.configured_fixture);
				var item_code = escape_html(r.message.item_code);
				var bom_no = escape_html(r.message.bom_no);
				var message_text = r.message.message ? escape_html(r.message.message) : '';
				
				frappe.msgprint({
					title: "Manufacturing Package Created",
					message: `
						<p><strong>Configured Fixture:</strong> <a href="/app/ill-configured-fixture/${configured_fixture}" target="_blank">${configured_fixture}</a></p>
						<p><strong>Item:</strong> <a href="/app/item/${item_code}" target="_blank">${item_code}</a></p>
						<p><strong>BOM:</strong> <a href="/app/bom/${bom_no}" target="_blank">${bom_no}</a></p>
						${message_text ? '<p class="text-muted">' + message_text + "</p>" : ""}
					`,
					indicator: "green",
				});
			} else if (r.message && r.message.error) {
				var error_html = "<strong>Errors:</strong><ul>";
				r.message.errors.forEach(function (err) {
					// Escape error messages to prevent XSS
					var safe_msg = String(err.message || '')
						.replace(/&/g, '&amp;')
						.replace(/</g, '&lt;')
						.replace(/>/g, '&gt;');
					error_html += "<li>" + safe_msg + "</li>";
				});
				error_html += "</ul>";
				frappe.msgprint({
					title: "Error Creating Package",
					message: error_html,
					indicator: "red",
				});
			}
		},
		error: function (r) {
			frappe.msgprint({
				title: "Error",
				message: r.message || "An unexpected error occurred",
				indicator: "red",
			});
		},
	});
}

/**
 * Resolve an abbreviated attribute combination to its full version.
 * @param {object} map - The mapping object from abbreviated to full values
 * @param {string} abbreviatedValue - The abbreviated attribute combination
 * @returns {string} The full attribute combination, or the abbreviated value if not found
 */
function resolveAttributeCombination(map, abbreviatedValue) {
	if (!abbreviatedValue) {
		return abbreviatedValue;
	}
	var fullValue = (map || {})[abbreviatedValue];
	return fullValue || abbreviatedValue;
}
