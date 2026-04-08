import frappe

def get_context(context):
    if frappe.session.user == "Guest":
        frappe.local.status_code = 404
        raise frappe.PageDoesNotExistError
    
    # Restrict to System Managers / Admins. Return 404 to masquerade as non-existent.
    if "System Manager" not in frappe.get_roles() and frappe.session.user != "Administrator":
        frappe.local.status_code = 404
        raise frappe.PageDoesNotExistError
