import frappe

def get_context(context):
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login"
        raise frappe.Redirect
    
    # Also restrict the Master Command Center to only System Managers / Admins
    if "System Manager" not in frappe.get_roles() and frappe.session.user != "Administrator":
        frappe.local.flags.redirect_location = "/dashboard"
        raise frappe.Redirect
