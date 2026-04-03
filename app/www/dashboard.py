import frappe

def get_context(context):
    if frappe.session.user == "Guest":
        # Hard redirect for anyone not logged in
        frappe.local.flags.redirect_location = "/login"
        raise frappe.Redirect
    
    # Organization Admin check:
    # Ensure they actually have the Organization Admin or System Manager role
    roles = frappe.get_roles()
    if "Organization Admin" not in roles and "System Manager" not in roles:
        # If they don't have the right role, send them back to login or home
        frappe.local.flags.redirect_location = "/login"
        raise frappe.Redirect
