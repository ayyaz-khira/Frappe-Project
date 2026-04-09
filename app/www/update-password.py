import frappe

def get_context(context):
    # Enforce that a 'key' must be present in the URL for this page to load.
    # This prevents users from navigating directly to /update-password without a reset link.
    key = frappe.form_dict.get('key')
    
    if not key:
        frappe.local.status_code = 404
        raise frappe.PageDoesNotExistError
    
    # Optionally, we could verify the key here, but the standard 
    # frappe.core.doctype.user.user.update_password method will handle verification on submit.
    # To keep it lightweight, we just ensure the parameter exists.
