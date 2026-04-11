import frappe

def add_system_manager():
    user = frappe.get_doc('User', 'admin@testorg.com')
    user.add_roles('System Manager')
    frappe.db.commit()
    print('SUCCESS: System Manager added')
