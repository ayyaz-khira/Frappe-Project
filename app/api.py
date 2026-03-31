import frappe
import csv
import base64
from frappe import _

# Helper to validate if the current user has access to a specific organization registration
def validate_org_access(registration_id):
    if frappe.session.user == "Guest":
        frappe.throw(_("Please log in to access this information"), frappe.PermissionError)
        
    # Super Admin / System Manager bypass
    if "System Manager" in frappe.get_roles():
        return True
        
    # Check if the user is linked to this specific organization
    user_org = frappe.db.get_value("User", frappe.session.user, "organization")
    if user_org != registration_id:
        frappe.throw(_("You are not authorized to manage this organization"), frappe.PermissionError)
    
    return True

@frappe.whitelist()
def sync_custom_fields():
    if not frappe.db.exists('Custom Field', {'dt': 'User', 'fieldname': 'organization'}):
        frappe.get_doc({
            'doctype': 'Custom Field',
            'dt': 'User',
            'fieldname': 'organization',
            'label': 'Organization',
            'fieldtype': 'Link',
            'options': 'User Registration',
            'insert_after': 'email'
        }).insert(ignore_permissions=True)
        frappe.db.commit()
    return "Custom field checked and created if missing."

def get_user_permission_query(user=None):
    if not user: user = frappe.session.user
    
    # Administrators can see everything
    if "System Manager" in frappe.get_roles(user):
        return None
        
    # Get the organization for the current user
    org = frappe.db.get_value("User", user, "organization")
    
    if org:
        return f"(`tabUser`.organization = '{org}')"
    
    # If no reg_id, they can't see any other org users (or maybe just themselves)
    return "(`tabUser`.name = '{0}')".format(frappe.db.escape(user))



@frappe.whitelist(allow_guest=True)
def capture_registration_lead(first_name, last_name, work_email, organization_name):

    print("API HIT")
    
    if not first_name or not last_name or not work_email or not organization_name:
        frappe.throw(_("All fields are required"))

    if frappe.db.exists("Organization Registration", {"work_email": work_email}):
        return {
            "status": "already_exists",
            "message": _("A registration request with this email already exists.")
        }

    try:
        new_lead = frappe.get_doc({
            "doctype": "Organization Registration",   # ✅ FIXED
            "first_name": first_name,
            "last_name": last_name,
            "work_email": work_email,
            "organization_name": organization_name,
            "status": "Lead"
        })

        new_lead.insert(ignore_permissions=True)
        frappe.db.commit()

        print("DOC CREATED:", new_lead.name)   # ✅ FIXED

        return {
            "status": "success",
            "message": _("Lead captured successfully"),
            "name": new_lead.name
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), _("Lead Capture Failed"))
        return {
            "status": "error",
            "message": "Error saving request"
        }



@frappe.whitelist(allow_guest=True)
def submit_details(first_name, last_name, work_email, organization_name, contact_number, organization_type, payment_status):
    
    if not all([first_name, last_name, work_email, organization_name, contact_number, organization_type, payment_status]):
        frappe.throw(_("All fields are required"))

    if frappe.db.exists("User Registration", {"work_email": work_email}):
        return {
            "status": "already_exists",
            "message": _("A registration request with this email already exists.")
        }

    try:
        user = frappe.get_doc({
            "doctype": "User Registration",
            "first_name": first_name,
            "last_name": last_name,
            "work_email": work_email,
            "organization_name": organization_name,
            "contact_number": contact_number,
            "organization_type": organization_type,
            "payment_status": payment_status,
            "approval_status": "Pending Approval" 
        })

        user.insert(ignore_permissions=True)
        frappe.db.commit()

        return {
            "status": "success",
            "message": _("User captured successfully"),
            "name": user.name
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), _("Lead Capture Failed"))
        return {
            "status": "error",
            "message": "Error saving request"
        }   


@frappe.whitelist()
def get_user_capacity(registration_id):
    validate_org_access(registration_id)
    if not frappe.db.exists("User Registration", registration_id):
        return 0
    reg = frappe.get_doc("User Registration", registration_id)
    # Parse range like "Small Team (2-10)" or "Enterprise (200+)"
    if not reg.organization_type:
        return 5
        
    capacity_str = reg.organization_type.split('(')[-1].replace(')', '')
    if '+' in capacity_str:
        return 999999
    if '-' in capacity_str:
        try:
            return int(capacity_str.split('-')[-1].strip())
        except:
            return 5
    try:
        return int(capacity_str.strip())
    except:
        return 5 # Default

@frappe.whitelist()
def add_org_user(registration_id, name, email):
    validate_org_access(registration_id)
    if not registration_id:
        return {"status": "error", "message": "No registration ID provided"}
        
    capacity = get_user_capacity(registration_id)
    current_count = frappe.db.count("User", {"organization": registration_id, "enabled": 1})
    
    if current_count >= capacity:
        return {"status": "error", "message": f"Organization Capacity reached ({capacity} users limit)"}
            
    if not frappe.db.exists("User", email):
        new_user = frappe.get_doc({
            "doctype": "User",
            "email": email,
            "first_name": name,
            "send_welcome_email": 0,
            "enabled": 0,
            "user_type": "Website User",
            "organization": registration_id  # ENSURE ISOLATION
        })
        new_user.insert(ignore_permissions=True)
        
        # Append to the child table in User Registration
        org_doc = frappe.get_doc("User Registration", registration_id)
        org_doc.append("members", {
            "name1": name,
            "email": email,
            "user_ref": new_user.name,
            "status": "Pending Approval"
        })
        org_doc.save(ignore_permissions=True)
        
        frappe.db.commit()
        return {"status": "success", "message": f"User {name} created successfully!"}
    else:
        # Check if the user already belongs to this org
        existing_user = frappe.get_doc("User", email)
        if existing_user.organization == registration_id:
            return {"status": "error", "message": f"A user with email {email} already exists in your organization."}
        else:
            return {"status": "error", "message": f"User with email {email} is already registered in another organization."}


@frappe.whitelist()
def upload_org_users_csv(registration_id, file_url):
    validate_org_access(registration_id)
    # Correctly resolve the absolute path for public/private files
    if file_url.startswith("/files/"):
        file_path = frappe.get_site_path("public", file_url.lstrip("/"))
    elif file_url.startswith("/private/files/"):
        file_path = frappe.get_site_path(file_url.lstrip("/"))
    else:
        file_path = frappe.get_site_path(file_url.lstrip("/"))
    capacity = get_user_capacity(registration_id)
    current_count = frappe.db.count("User", {"organization": registration_id, "enabled": 1})

    if current_count >= capacity:
        return {"status": "error", "message": "Capacity reached."}
    
    inserted = 0
    skipped = 0
    org_doc = frappe.get_doc("User Registration", registration_id)
    
    with open(file_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            email = row.get('email', '').strip()
            name = row.get('name', 'N/A')
            
            if not email or frappe.db.exists("User", email):
                skipped += 1
                continue
            
            if current_count + inserted >= capacity:
                break
            
            new_user = frappe.get_doc({
                "doctype": "User",
                "email": email,
                "first_name": name,
                "send_welcome_email": 0,
                "enabled": 0,
                "user_type": "Website User",
                "organization": registration_id # ENSURE ISOLATION
            })
            new_user.insert(ignore_permissions=True)
            
            # Append to the child table
            org_doc.append("members", {
                "name1": name,
                "email": email,
                "user_ref": new_user.name,
                "status": "Pending Approval"
            })
            
            inserted += 1
        
    org_doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"status": "success", "message": f"Created {inserted} users. ({skipped} duplicates skipped)."}


@frappe.whitelist()
def upload_csv_base64(registration_id, filename, filedata):
    validate_org_access(registration_id)
    try:
        if "," in filedata:
            filedata = filedata.split(",")[1]
        
        decoded_data = base64.b64decode(filedata)
        
        # Save file to Frappe
        file_doc = frappe.get_doc({
            "doctype": "File",
            "file_name": filename,
            "content": decoded_data,
            "is_private": 0
        })
        file_doc.insert(ignore_permissions=True)
        frappe.db.commit()
        
        # Process it using existing logic
        return upload_org_users_csv(registration_id, file_doc.file_url)
    except Exception as e:
        return {"status": "error", "message": str(e)}
        

@frappe.whitelist()
def get_org_users(registration_id):
    validate_org_access(registration_id)
    if not registration_id:
        return {"status": "error", "message": "Missing registration ID"}
        
    members = frappe.get_all("Org User Item", 
        fields=["name1 as name", "email", "status", "creation"], 
        filters={"parent": registration_id, "parenttype": "User Registration"},
        order_by="creation desc"
    )
    return {"status": "success", "users": members}



# Registration approval handler
# Around line 364 in api.py
def handle_registration_approval(doc, method):
    if doc.approval_status == "Approved" and not frappe.db.exists("User", doc.work_email):
        
        # 1. Create the core User
        new_user = frappe.get_doc({
            "doctype": "User",
            "email": doc.work_email,
            "first_name": doc.first_name,
            "last_name": doc.last_name,
            "enabled": 1,
            "send_welcome_email": 1,
            "user_type": "Website User"
        })
        
        # 2. Tag them with the organization correctly
        new_user.organization = doc.name
        
        # 3. Insert and save
        new_user.insert(ignore_permissions=True)
        
        # 4. Add the specific role we just created
        new_user.add_roles("Organization Admin") 
        
        # 5. Add the admin themselves to the members child table
        doc.append("members", {
            "name1": f"{doc.first_name} {doc.last_name}",
            "email": doc.work_email,
            "user_ref": new_user.name,
            "status": "Approved"
        })
        
        frappe.db.commit()
        frappe.msgprint(f"Core User account created for {doc.work_email}")
