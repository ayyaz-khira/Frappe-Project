import frappe

def run():
    orgs = frappe.get_all("User Registration", fields=["name", "first_name", "last_name", "work_email"])
    for org in orgs:
        members = frappe.get_all("Org User Item", filters={"parent": org.name, "email": org.work_email})
        if not members:
            user_name = frappe.db.get_value("User", {"email": org.work_email})
            if user_name:
                doc = frappe.get_doc("User Registration", org.name)
                doc.append("members", {
                    "name1": f"{org.first_name} {org.last_name}",
                    "email": org.work_email,
                    "user_ref": user_name,
                    "status": "Approved"
                })
                doc.save(ignore_permissions=True)
                print(f"Added {org.work_email} to org {org.name}")
    frappe.db.commit()
