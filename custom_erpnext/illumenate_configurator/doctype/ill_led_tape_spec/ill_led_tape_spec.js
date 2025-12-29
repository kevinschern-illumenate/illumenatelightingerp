// Copyright (c) 2024, ilLumenate Lighting and contributors
// For license information, please see license.txt

frappe.ui.form.on("ILL LED Tape Spec", {
	refresh: function(frm) {
		// Filter variant_attributes to only show attributes from the linked Item Template
		frm.set_query("attribute", "variant_attributes", function() {
			if (!frm.doc.tape_item) {
				frappe.msgprint(__("Please select a Tape Item first"));
				return {
					filters: {
						name: ["in", []]
					}
				};
			}
			return {
				query: "custom_erpnext.illumenate_configurator.api.get_item_attributes",
				filters: {
					item: frm.doc.tape_item
				}
			};
		});
	},

	tape_item: function(frm) {
		// Clear variant attributes when item changes
		frm.clear_table("variant_attributes");
		frm.set_value("resolved_variant_item", "");
		frm.refresh_field("variant_attributes");

		// If item is a template, show the attributes section
		if (frm.doc.tape_item) {
			frappe.db.get_value("Item", frm.doc.tape_item, ["has_variants", "variant_of"], function(r) {
				if (r) {
					if (r.has_variants) {
						frm.set_df_property("section_break_attributes", "hidden", 0);
						frm.set_df_property("section_break_attributes", "collapsible", 0);
					} else if (r.variant_of) {
						// This is already a variant, hide attributes section
						frm.set_df_property("section_break_attributes", "hidden", 1);
						frappe.show_alert({
							message: __("Selected item is a variant. No need to specify attributes."),
							indicator: "blue"
						});
					} else {
						// Standard item, hide attributes section
						frm.set_df_property("section_break_attributes", "hidden", 1);
					}
				}
			});
		}
	}
});
