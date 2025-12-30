// Copyright (c) 2024, ilLumenate Lighting and contributors
// For license information, please see license.txt

frappe.ui.form.on("ILL Fixture Schedule", {
	refresh: function (frm) {
		// Refresh the lines table to ensure child doctype JS is loaded
		frm.refresh_field("lines");
	},
});
