// Copyright (c) 2024, ilLumenate Lighting and contributors
// For license information, please see license.txt

frappe.ui.form.on("ILL LED Tape Spec", {
	refresh: function(frm) {
		frm.trigger("render_available_attributes");
	},

	tape_item: function(frm) {
		// Clear variant specs when item changes
		frm.clear_table("variant_specs");
		frm.refresh_field("variant_specs");

		frm.trigger("render_available_attributes");
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
								<small>Use these attributes to create combinations in the Variant Specs table below. 
								Format: "Attribute1: Value1, Attribute2: Value2"</small>
							</p>
						</div>
					`;

					frm.get_field("available_attributes_html").$wrapper.html(html);
				}
			}
		});
	}
});
