// Copyright (c) 2024, ilLumenate Lighting and contributors
// For license information, please see license.txt

frappe.ui.form.on("ILL LED Tape Spec", {
	refresh: function(frm) {
		frm.trigger("render_available_attributes");
		frm.trigger("add_attribute_builder_button");
	},

	tape_item: function(frm) {
		// Clear variant specs when item changes
		frm.clear_table("variant_specs");
		frm.refresh_field("variant_specs");

		frm.trigger("render_available_attributes");
	},

	add_attribute_builder_button: function(frm) {
		// Add a custom button to build attribute combinations
		if (frm.doc.tape_item) {
			frm.add_custom_button(__("Add Variant Spec"), function() {
				frm.trigger("open_attribute_builder");
			}, __("Tools"));
		}
	},

	open_attribute_builder: function(frm) {
		if (!frm.doc.tape_item) {
			frappe.msgprint(__("Please select a Tape Item Template first."));
			return;
		}

		frappe.call({
			method: "custom_erpnext.illumenate_configurator.api.get_item_template_attributes",
			args: { item: frm.doc.tape_item },
			callback: function(r) {
				if (r.message && r.message.has_variants) {
					// Store attributes on frm for the dialog to use
					frm._variant_attributes = r.message.attributes;
					frm.trigger("show_attribute_builder_dialog");
				} else {
					// No variants - just add a row with empty combination
					let row = frm.add_child("variant_specs", {
						attribute_combination: "(No variants - single item)"
					});
					frm.refresh_field("variant_specs");
					frappe.show_alert({
						message: __("Added row for single item (no variants)."),
						indicator: "green"
					});
				}
			}
		});
	},

	show_attribute_builder_dialog: function(frm) {
		let attributes = frm._variant_attributes || [];
		let fields = [];

		// Build the dialog fields based on attributes
		attributes.forEach((attr, idx) => {
			if (attr.numeric_values) {
				// Numeric attribute - use a field with range info
				fields.push({
					fieldtype: "Float",
					fieldname: `attr_${idx}`,
					label: attr.attribute,
					description: `Range: ${attr.from_range} to ${attr.to_range} (increment: ${attr.increment})`,
					reqd: 1
				});
			} else {
				// Select from predefined values
				let options = attr.values.map(v => ({ label: v, value: v }));
				fields.push({
					fieldtype: "Select",
					fieldname: `attr_${idx}`,
					label: attr.attribute,
					options: [{ label: "-- Select --", value: "" }].concat(options),
					reqd: 1
				});
			}
		});

		// Add separator and spec fields
		fields.push({ fieldtype: "Section Break", label: "Electrical Specifications" });
		fields.push({
			fieldtype: "Select",
			fieldname: "voltage",
			label: "Voltage",
			options: ["", "12", "24", "48"],
			reqd: 1
		});
		fields.push({
			fieldtype: "Float",
			fieldname: "watts_per_ft",
			label: "Watts per Foot",
			reqd: 1
		});
		fields.push({ fieldtype: "Column Break" });
		fields.push({
			fieldtype: "Float",
			fieldname: "cut_increment_in",
			label: "Cut Increment (inches)",
			reqd: 1
		});
		fields.push({
			fieldtype: "Float",
			fieldname: "voltage_drop_max_run_ft",
			label: "Voltage Drop Max Run (ft)",
			description: "Maximum run length before voltage drop becomes unacceptable. Used alongside 85W rule.",
			reqd: 1
		});

		let d = new frappe.ui.Dialog({
			title: __("Build Variant Specification"),
			fields: fields,
			size: "large",
			primary_action_label: __("Add Variant Spec"),
			primary_action: function(values) {
				// Build the attribute combination string
				let combination_parts = [];
				attributes.forEach((attr, idx) => {
					let val = values[`attr_${idx}`];
					if (val) {
						combination_parts.push(`${attr.attribute}: ${val}`);
					}
				});

				let combination_str = combination_parts.join(", ");

				// Check for duplicates
				let exists = (frm.doc.variant_specs || []).some(
					row => row.attribute_combination === combination_str
				);
				if (exists) {
					frappe.msgprint(__("This attribute combination already exists."));
					return;
				}

				// Add the new row
				let row = frm.add_child("variant_specs", {
					attribute_combination: combination_str,
					voltage: values.voltage,
					watts_per_ft: values.watts_per_ft,
					cut_increment_in: values.cut_increment_in,
					voltage_drop_max_run_ft: values.voltage_drop_max_run_ft
				});

				frm.refresh_field("variant_specs");
				d.hide();

				frappe.show_alert({
					message: __("Added variant spec: {0}", [combination_str]),
					indicator: "green"
				});
			}
		});

		d.show();
	},

	render_available_attributes: function(frm) {
		// Render the available attributes for the selected tape item
		if (!frm.doc.tape_item) {
			frm.get_field("available_attributes_html").$wrapper.html(`
				<div class="alert alert-warning">
					<i class="fa fa-info-circle"></i>
					Please select a Tape Item Template to see available variant attributes.
				</div>
			`);
			return;
		}

		frappe.call({
			method: "custom_erpnext.illumenate_configurator.api.get_item_template_attributes",
			args: { item: frm.doc.tape_item },
			callback: function(r) {
				if (r.message) {
					const data = r.message;

					if (!data.has_variants) {
						frm.get_field("available_attributes_html").$wrapper.html(`
							<div class="alert alert-info">
								<i class="fa fa-info-circle"></i>
								<strong>${frm.doc.tape_item}</strong> is not an Item Template.
								It does not have variants, so all specifications will apply to this single item.
							</div>
						`);
						return;
					}

					let html = `
						<div class="alert alert-success">
							<h5><i class="fa fa-tags"></i> Available Variant Attributes for ${frm.doc.tape_item}</h5>
							<table class="table table-bordered table-sm" style="margin-top: 10px;">
								<thead>
									<tr>
										<th>Attribute</th>
										<th>Possible Values</th>
									</tr>
								</thead>
								<tbody>
					`;

					data.attributes.forEach(attr => {
						let valuesDisplay = "";
						if (attr.numeric_values) {
							valuesDisplay = `Range: ${attr.from_range} to ${attr.to_range} (increment: ${attr.increment})`;
						} else {
							valuesDisplay = attr.values.join(", ");
						}
						html += `
							<tr>
								<td><strong>${attr.attribute}</strong></td>
								<td>${valuesDisplay}</td>
							</tr>
						`;
					});

					html += `
								</tbody>
							</table>
							<p class="text-muted">
								<small>Use the <strong>Tools → Add Variant Spec</strong> button to easily add variant specifications.</small>
							</p>
						</div>
					`;

					frm.get_field("available_attributes_html").$wrapper.html(html);
				}
			}
		});
	}
});

// Child table events for ILL LED Tape Variant
frappe.ui.form.on("ILL LED Tape Variant", {
	variant_specs_add: function(frm, cdt, cdn) {
		// When a new row is added manually, offer to use the builder
		if (frm.doc.tape_item) {
			frappe.confirm(
				__("Would you like to use the Attribute Builder to fill this row?"),
				function() {
					// Yes - remove the empty row and open builder
					frm.get_field("variant_specs").grid.grid_rows_by_docname[cdn].remove();
					frm.trigger("open_attribute_builder");
				},
				function() {
					// No - let them fill manually
				}
			);
		}
	}
});
