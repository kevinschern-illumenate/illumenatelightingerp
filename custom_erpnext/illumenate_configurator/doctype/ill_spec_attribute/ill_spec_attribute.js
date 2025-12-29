// Copyright (c) 2024, ilLumenate Lighting and contributors
// For license information, please see license.txt

frappe.ui.form.on("ILL Spec Attribute", {
	attribute: function(frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		// Clear the value when attribute changes
		frappe.model.set_value(cdt, cdn, "attribute_value", "");
	},

	attribute_value: function(frm, cdt, cdn) {
		// Validate that the value exists in the attribute's values
		var row = locals[cdt][cdn];
		if (row.attribute && row.attribute_value) {
			frappe.call({
				method: "frappe.client.get",
				args: {
					doctype: "Item Attribute",
					name: row.attribute
				},
				callback: function(r) {
					if (r.message) {
						var attr = r.message;
						// For numeric attributes, validate range
						if (attr.numeric_values) {
							var val = parseFloat(row.attribute_value);
							if (isNaN(val) || val < attr.from_range || val > attr.to_range) {
								frappe.msgprint(__("Value must be between {0} and {1} for attribute {2}",
									[attr.from_range, attr.to_range, attr.attribute_name]));
								frappe.model.set_value(cdt, cdn, "attribute_value", "");
							}
						} else {
							// For non-numeric, check if value is in the list
							var valid_values = attr.item_attribute_values.map(function(v) {
								return v.attribute_value;
							});
							if (!valid_values.includes(row.attribute_value)) {
								frappe.msgprint(__("'{0}' is not a valid value for attribute '{1}'. Valid values: {2}",
									[row.attribute_value, attr.attribute_name, valid_values.join(", ")]));
								frappe.model.set_value(cdt, cdn, "attribute_value", "");
							}
						}
					}
				}
			});
		}
	}
});
