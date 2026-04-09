import frappe

no_cache = 1

def get_context(context):
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login"
        raise frappe.Redirect

    roles = frappe.get_roles()

    # System Managers and Organization Admins are allowed
    if "System Manager" in roles or "Organization Admin" in roles or frappe.session.user == "Administrator":
        return

    # Everyone else (Normal Users) must go to the live portal
    frappe.local.flags.redirect_location = "http://live.nuomics.io"
    raise frappe.Redirect
