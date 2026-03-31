frappe.ui.form.on("User Registration", {
	refresh(frm) {
		if (frappe.user_roles.includes("System Manager")) {
			frm.fields_dict['members'].grid.add_custom_button(__('Approve All Pending'), () => {
				let changed = false;
				frm.doc.members.forEach(m => {
					if (m.status === "Pending Approval") {
						frappe.model.set_value(m.doctype, m.name, "status", "Approved");
						changed = true;
					}
				});
				if (changed) {
					frm.save().then(() => {
						frappe.show_alert({message: __('All pending users approved'), indicator: 'green'});
					});
				} else {
					frappe.msgprint(__('No pending users to approve'));
				}
			});
		}
	},
});
