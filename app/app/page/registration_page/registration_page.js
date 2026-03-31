frappe.pages['registration-page'].on_page_load = function (wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'User Registration',
		single_column: true
	});

	let form = new frappe.ui.FieldGroup({
		fields: [
			{
				label: "Name",
				fieldname: "name",
				fieldtype: "Data",
				reqd: 1
			},
			{
				label: "Email",
				fieldname: "email",
				fieldtype: "Data",
				options: "Email",
				reqd: 1
			},
			{
				label: "Password",
				fieldname: "password",
				fieldtype: "Password",
				reqd: 1
			},
			{
				label: "Role",
				fieldname: "role",
				fieldtype: "Select",
				options: ["User", "Admin"],
				reqd: 1
			}
			,
			{
				label: "Bulk CSV Upload",
				fieldtype: "Section Break"
			},
			{
				label: "Upload CSV File",
				fieldname: "csv_file",
				fieldtype: "Attach",
				description: "CSV must have columns: name, email, password, role"
			},
			{
				fieldtype: "HTML",
				options: '<button class="btn btn-default btn-sm" id="csv-upload-btn" style="margin-top: 8px;">⬆ Upload CSV</button>'
			}
		],
		body: page.body
	});

	form.make();

	page.set_primary_action("Create User", function () {
		let values = form.get_values();
		if (!values) return;

		frappe.call({
			method: "app.api.save_to_postgres", // Points to the new function
			args: {
				name: values.name,
				email: values.email,
				password: values.password,
				role: values.role
			},
			callback: function (r) {
				if (r.message && r.message.status === "success") {
					frappe.msgprint(r.message.message);
					form.clear();
				} else {
					frappe.msgprint({
						title: "Registration Failed",
						indicator: "red",
						message: r.message.message
					});
				}
			}
		});
	});

	document.getElementById("csv-upload-btn").addEventListener("click", function () {
		let fileUrl = form.get_value("csv_file");
		if (!fileUrl) {
			frappe.msgprint("Please attach a CSV file first.");
			return;
		}
		frappe.call({
			method: "app.api.save_csv_to_postgres",
			args: { file_url: fileUrl },
			callback: function (r) {
				if (r.message && r.message.status === "success") {
					frappe.msgprint({ title: "Upload Complete", indicator: "green", message: r.message.message });
					if (r.message.skipped > 0) {
						frappe.msgprint({
							title: "Duplicates Skipped",
							indicator: "orange",
							message: r.message.skipped + " email(s) already exist and were skipped."
						});
					}
					form.clear();
				} else {
					frappe.msgprint({ title: "Error", indicator: "red", message: r.message.message });
				}
			}
		});
	});

}