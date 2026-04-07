import frappe
import csv
import base64
from frappe import _
import frappe.utils

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
    
    try:
        # Administrators can see everything
        roles = frappe.get_roles(user)
        if "System Manager" in roles:
            return None
            
        # Get the organization for the current user
        org = frappe.db.get_value("User", user, "organization")
        
        if org:
            return f"(`tabUser`.organization = '{org}')"
        
        # If no org, restrict to self
        return "(`tabUser`.name = '{0}')".format(frappe.db.escape(user))
    except Exception:
        # Fallback to only seeing self in case of any issues during login phase
        return "(`tabUser`.name = '{0}')".format(frappe.db.escape(user))


def redirect_after_login(login_manager):
    user = frappe.session.user

    # Create Login Alert
    if user != "Guest":
        frappe.get_doc({
            "doctype": "System Alert",
            "alert_type": "Login",
            "message": f"User {user} logged in to the system",
            "user": user,
            "is_read": 0
        }).insert(ignore_permissions=True)
        frappe.db.commit()

    # Administrator should always go to Desk
    if user == "Administrator":
        return

    roles = frappe.get_roles(user)

    # Allow System Managers
    if "System Manager" in roles:
        return

    # Organization Admin redirect
    if "Organization Admin" in roles:
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = "/dashboard"
        return

    # If they are neither Organization Admin, System Manager, nor Administrator
    frappe.throw("NOT_ORG_ADMIN")




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
            "doctype": "Organization Registration",   
            "first_name": first_name,
            "last_name": last_name,
            "work_email": work_email,
            "organization_name": organization_name,
            "status": "Lead"
        })

        new_lead.insert(ignore_permissions=True)
        frappe.db.commit()

        print("DOC CREATED:", new_lead.name)   

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



import hashlib
import requests
import json

PAYU_PAYOUT_CLIENT_ID = "ccbb70745faad9c06092bb5c79bfd919b6f45fd454f34619d83920893e90ae6b"
PAYU_PAYOUT_CLIENT_SECRET = "534bcc8c227b0b5c4e0a62290e8faa17fd73e6d3dfa43f796572dda5044dd313" # Re-using secret from first prompt
PAYU_PAYOUT_BASE_URL = "https://payout-api-uat.payu.in" # UAT for Payouts

@frappe.whitelist()
def get_payu_payout_token():
    auth_str = f"{PAYU_PAYOUT_CLIENT_ID}:{PAYU_PAYOUT_CLIENT_SECRET}"
    encoded_auth = base64.b64encode(auth_str.encode()).decode()
    
    url = f"{PAYU_PAYOUT_BASE_URL}/payout/v1/auth/token"
    headers = {
        "Authorization": f"Basic {encoded_auth}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    payload = "grant_type=client_credentials"
    
    try:
        response = requests.post(url, headers=headers, data=payload)
        if response.status_code == 200:
            return response.json().get("access_token")
        else:
            frappe.log_error(response.text, "PayU Payout Token Error")
            return None
    except Exception as e:
        frappe.log_error(str(e), "PayU Payout Token Exception")
        return None

@frappe.whitelist()
def create_payout(member, amount, account_number, ifsc_code):
    token = get_payu_payout_token()
    if not token:
        frappe.throw(_("Could not authenticate with PayU Payouts API"))
        
    url = f"{PAYU_PAYOUT_BASE_URL}/payout/v1/transfer"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Generate unique transfer ID
    transfer_id = frappe.generate_hash(length=20)
    
    payload = {
        "transferId": transfer_id,
        "amount": str(amount),
        "beneficiaryAccountNumber": account_number,
        "beneficiaryIfscCode": ifsc_code,
        "beneficiaryName": frappe.db.get_value("Org User Item", member, "name1") or "Beneficiary",
        "purpose": "Salary/Payment",
        "beneficiaryEmail": frappe.db.get_value("Org User Item", member, "email"),
        "transferMode": "IMPS"
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        res_json = response.json()
        
        # Save Payout Record
        payout = frappe.get_doc({
            "doctype": "PayU Payout",
            "member": member,
            "amount": amount,
            "account_number": account_number,
            "ifsc_code": ifsc_code,
            "payout_id": transfer_id,
            "full_response": json.dumps(res_json)
        })
        
        if response.status_code in [200, 202]:
            payout.status = "Pending" # Usually pending until success callback
            payout.insert(ignore_permissions=True)
            frappe.db.commit()
            return {"status": "success", "message": "Payout initiated", "payout_id": transfer_id}
        else:
            payout.status = "Failed"
            payout.insert(ignore_permissions=True)
            frappe.db.commit()
            return {"status": "error", "message": res_json.get("message", "Payout Failed")}
            
    except Exception as e:
        frappe.log_error(str(e), "Payout API Exception")
        return {"status": "error", "message": str(e)}

@frappe.whitelist()
def check_payout_status(payout_id):
    token = get_payu_payout_token()
    if not token: return None
    
    url = f"{PAYU_PAYOUT_BASE_URL}/payout/v1/transfer/status/{payout_id}"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(url, headers=headers)
        res_json = response.json()
        status = res_json.get("status") # SUCCESS/FAILURE/PENDING
        
        # Update record
        pt_name = frappe.db.get_value("PayU Payout", {"payout_id": payout_id}, "name")
        if pt_name:
            pt = frappe.get_doc("PayU Payout", pt_name)
            if status == "SUCCESS": pt.status = "Success"
            elif status == "FAILURE": pt.status = "Failed"
            pt.full_response = json.dumps(res_json)
            pt.save(ignore_permissions=True)
            frappe.db.commit()
            
        return {"status": pt.status}
    except Exception as e:
        return None

PAYU_KEY = "SCcYkX"
PAYU_SALT = "Vyi137dOKlxYSVlaF1jWHInS7zoLBbOS"
PAYU_URL = "https://test.payu.in/_payment" # Use test URL for now

def generate_payu_hash(data):
    # hashSequence = key|txnid|amount|productinfo|firstname|email|udf1|udf2|udf3|udf4|udf5||||||salt
    hash_args = [
        PAYU_KEY.strip(),
        data.get("txnid", ""),
        data.get("amount", ""),
        data.get("productinfo", ""),
        data.get("firstname", ""),
        data.get("email", ""),
        data.get("udf1", ""),
        data.get("udf2", ""),
        data.get("udf3", ""),
        data.get("udf4", ""),
        data.get("udf5", ""),
        "", "", "", "", "", # Placeholder for more udfs
        PAYU_SALT.strip()
    ]
    hash_string = "|".join(hash_args)
    return hashlib.sha512(hash_string.encode('utf-8')).hexdigest().lower()

def verify_payu_hash(data):
    # Hash reverse sequence for verifying response from PayU
    # salt|status|udf10|udf9|udf8|udf7|udf6|udf5|udf4|udf3|udf2|udf1|email|firstname|productinfo|amount|txnid|key
    response_hash_args = [
        PAYU_SALT.strip(),
        data.get("status", ""),
        data.get("udf10", ""),
        data.get("udf9", ""),
        data.get("udf8", ""),
        data.get("udf7", ""),
        data.get("udf6", ""),
        data.get("udf5", ""),
        data.get("udf4", ""),
        data.get("udf3", ""),
        data.get("udf2", ""),
        data.get("udf1", ""),
        data.get("email", ""),
        data.get("firstname", ""),
        data.get("productinfo", ""),
        data.get("amount", ""),
        data.get("txnid", ""),
        data.get("key", "")
    ]
    hash_string = "|".join(response_hash_args)
    calculated_hash = hashlib.sha512(hash_string.encode('utf-8')).hexdigest().lower()
    return calculated_hash == data.get("hash")

@frappe.whitelist(allow_guest=True)
def initiate_payment(user_registration_id, amount):
    if not frappe.db.exists("User Registration", user_registration_id):
        frappe.throw(_("Invalid registration ID"))
        
    try:
        amount_float = float(amount)
        if amount_float <= 0:
            frappe.throw(_("Amount must be greater than zero"))
    except ValueError:
        frappe.throw(_("Invalid amount format"))

    # Generate strictly alphanumeric transaction ID (max 100 char, but hex is safe)
    txnid = frappe.generate_hash(length=12) 
    
    # Create Payment Transaction record
    pt = frappe.get_doc({
        "doctype": "Payment Transaction",
        "user_registration": user_registration_id,
        "amount": amount_float,
        "status": "Pending",
        "transaction_id": txnid,
        "payment_gateway": "PayU India"
    })
    pt.insert(ignore_permissions=True)
    frappe.db.commit()
    
    reg_doc = frappe.get_doc("User Registration", user_registration_id)
    
    # Clean phone number (only digits)
    phone = "".join(filter(str.isdigit, str(reg_doc.contact_number or "")))
    phone = str(phone)[-10:]
    
    # Strictly alphanumeric firstname and productinfo
    firstname = "".join(filter(str.isalnum, (reg_doc.first_name or "User").split(" ")[0]))[:20]
    productinfo = "".join(filter(str.isalnum, (reg_doc.name or "Payment")))[:50]
        
    payment_data = {
        "key": PAYU_KEY.strip(),
        "txnid": txnid,
        "amount": "{:.2f}".format(float(amount)),
        "productinfo": productinfo,
        "firstname": firstname,
        "email": reg_doc.work_email,
        "phone": phone,
        "surl": frappe.utils.get_url("/api/method/app.api.payu_success"),
        "furl": frappe.utils.get_url("/api/method/app.api.payu_failure"),
        # Removed service_provider to avoid 500 errors on specific gatewy accounts
        "udf1": "", "udf2": "", "udf3": "", "udf4": "", "udf5": "",
        "udf6": "", "udf7": "", "udf8": "", "udf9": "", "udf10": ""
    }
    
    payment_data["hash"] = generate_payu_hash(payment_data)
    
    return {
        "status": "success",
        "payment_url": PAYU_URL,
        "params": payment_data
    }

@frappe.whitelist(allow_guest=True)
def payu_success():
    # Finalize transaction
    data = frappe.local.form_dict
    
    # Security: Verify Hash
    if not verify_payu_hash(data):
        frappe.log_error(title="PayU Success Signature Fail", message=json.dumps(data, indent=4))
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = "/contact-us?error=invalid_signature"
        return

    txnid = data.get("txnid")
    if txnid:
        pt_name = frappe.db.get_value("Payment Transaction", {"transaction_id": txnid}, "name")
        if pt_name:
            pt = frappe.get_doc("Payment Transaction", pt_name)
            pt.status = "Success"
            pt.full_response = json.dumps(data)
            pt.save(ignore_permissions=True)
            
            # Update User Registration
            reg = frappe.get_doc("User Registration", pt.user_registration)
            reg.payment_status = "True"
            reg.save(ignore_permissions=True)
            frappe.db.commit()
            
    # Redirect to success page or dashboard
    reg_id = ""
    if txnid:
        reg_id = frappe.db.get_value("Payment Transaction", {"transaction_id": txnid}, "user_registration") or ""
        
    frappe.local.response["type"] = "redirect"
    frappe.local.response["location"] = "/contact-us?status=received"
    return

@frappe.whitelist(allow_guest=True)
def payu_failure():
    data = frappe.local.form_dict
    
    # Security: Verify Hash (Optional but good for logging)
    if not verify_payu_hash(data):
        frappe.log_error(title="PayU Failure Signature Fail", message=json.dumps(data, indent=4))

    txnid = data.get("txnid")
    if txnid:
        pt_name = frappe.db.get_value("Payment Transaction", {"transaction_id": txnid}, "name")
        if pt_name:
            pt = frappe.get_doc("Payment Transaction", pt_name)
            pt.status = "Failed"
            pt.full_response = json.dumps(data)
            pt.save(ignore_permissions=True)
            frappe.db.commit()
            
    frappe.local.response["type"] = "redirect"
    frappe.local.response["location"] = "/contact-us?error=payment_failed"
    return

@frappe.whitelist(allow_guest=True)
def submit_details(first_name, last_name, work_email, organization_name, contact_number, organization_type, payment_status, country_code, number_of_users=1):
    
    if not all([first_name, last_name, work_email, organization_name, contact_number, organization_type, country_code]):
        frappe.throw(_("All main fields are required"))

    # Email Validation
    if not frappe.utils.validate_email_address(work_email):
        frappe.throw(_("Invalid email address: {0}").format(work_email))

    # Organization Specific Validations
    email_lower = work_email.lower()
    org_name_clean = "".join(filter(str.isalnum, organization_name.lower()))
    
    if organization_type == "Educational":
        if not email_lower.endswith(".edu"):
            frappe.throw(_("Educational organizations require a .edu email address."))
    elif organization_type in ["Industrial", "Enterprise"]:
        domain = email_lower.split("@")[-1].split(".")[0]
        if org_name_clean not in domain and domain not in org_name_clean:
            frappe.throw(_("For {0} organizations, the email domain should match the organization name.").format(organization_type))
        
    # Phone number validation (Country Specific)
    import re
    phone_raw = "".join(filter(str.isdigit, str(contact_number)))
    if country_code in ["+91", "+1"]:
        if len(phone_raw) != 10:
            frappe.throw(_("Please enter a valid 10-digit number for {0}.").format(country_code))
    elif len(phone_raw) < 8 or len(phone_raw) > 15:
        frappe.throw(_("Invalid contact number length."))

    # Combine for full contact number
    full_contact_number = f"{country_code} {contact_number}"

    if frappe.db.exists("User Registration", {"work_email": work_email}):
        # Handle update if needed, but here we'll stick to error per current logic
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
            "contact_number": full_contact_number,
            "organization_type": organization_type,
            "number_of_users": number_of_users,
            "payment_status": payment_status,
            "approval_status": "Pending Approval" 
        })

        user.insert(ignore_permissions=True)

        # Create a matching Lead doc in the CRM Lead DocType
        try:
            lead = frappe.get_doc({
                "doctype": "CRM Lead",
                "first_name": first_name,
                "last_name": last_name,
                "email": work_email,
                "mobile_no": full_contact_number,
                "organization": organization_name,
                "status": "New",
                "source": "Website",
                "custom_no_of_users": number_of_users,
                "custom_organization_type": organization_type
            })
            lead.insert(ignore_permissions=True)
        except Exception as lead_err:
            # We don't want to fail the main registration if lead creation fails
            # but we should log it
            frappe.log_error(f"Lead Creation Failed: {str(lead_err)}", "Registration Lead Error")

        frappe.db.commit()

        return {
            "status": "success",
            "message": _("User registration captured successfully"),
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
    
    # Priority 1: Direct Number of Users field
    if reg.number_of_users:
        try:
            return int(reg.number_of_users)
        except (ValueError, TypeError):
            pass
            
    # Priority 2: Fallback to Plan Range parsing
    if not reg.organization_type:
        return 5 # Safe Default
        
    if reg.organization_type == "Individual":
        return 1
        
    capacity_str = reg.organization_type.split('(')[-1].replace(')', '')
    if '+' in capacity_str:
        return 999999 # Enterprise
    if '-' in capacity_str:
        try:
            return int(capacity_str.split('-')[-1].strip())
        except (ValueError, TypeError):
            return 5
    try:
        return int(capacity_str.strip())
    except (ValueError, TypeError):
        return 5 # Balanced Default

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
        return {"status": "error", "message": f"Organization Capacity reached. You have already utilized your limit of {capacity} users."}
    
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
    final_msg = f"Created {inserted} users. ({skipped} duplicates skipped)."
    if current_count + inserted >= capacity:
        final_msg = f"Partial Success: Created {inserted} users, but reached your limit of {capacity}. Some rows were skipped."
        
    return {"status": "success", "message": final_msg}


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
def update_member_status(registration_id, email, status):
    validate_org_access(registration_id)
    if not registration_id or not email or not status:
        return {"status": "error", "message": "Missing required information"}
        
    # Valid status values
    if status not in ["Approved", "Rejected", "Pending Approval"]:
        return {"status": "error", "message": "Invalid status value"}

    # 1. Check organization status - cannot enable user if org is disabled
    org_status = frappe.db.get_value("User Registration", registration_id, "approval_status")
    if status == "Approved" and org_status != "Approved":
        return {"status": "error", "message": "Cannot enable a member while the organization is disabled."}

    # 1. Update core user enabled state
    if frappe.db.exists("User", email):
        u = frappe.get_doc("User", email)
        was_disabled = not u.enabled
        u.enabled = 1 if status == "Approved" else 0
        u.save(ignore_permissions=True)
        
        # Trigger welcome email if freshly approved
        if status == "Approved" and was_disabled:
            u.send_welcome_mail_to_user()

    org_doc = frappe.get_doc("User Registration", registration_id)
    user_found = False
    for m in org_doc.members:
        if m.email == email:
            m.status = status
            user_found = True
            break
            
    if user_found:
        org_doc.save(ignore_permissions=True)
        frappe.db.commit()
        msg = f"User {email} has been {'enabled and approved. An email has been sent to the email.' if status == 'Approved' else 'disabled and rejected.'}"
        return {"status": "success", "message": msg}

    else:
        return {"status": "error", "message": "Member not found in your organization record."}


@frappe.whitelist()
def get_org_users(registration_id):
    validate_org_access(registration_id)
    if not registration_id:
        return {"status": "error", "message": "Missing registration ID"}
    # Get the parent organization's full details to filter out the main admin
    org_doc = frappe.db.get_value("User Registration", registration_id, ["approval_status", "work_email"], as_dict=True)
    org_status = org_doc.get("approval_status")
    org_email = org_doc.get("work_email")
    
    members = frappe.get_all("Org User Item", 
        fields=["name1 as name", "email", "status", "creation"], 
        filters={"parent": registration_id, "parenttype": "User Registration"},
        order_by="creation desc"
    )
    
    # Filter out the organization main admin from showing up as an inner user
    filtered_members = [m for m in members if m.email != org_email]
    
    # If the parent org is Pending Approval, forcibly mask all members to Pending Approval
    if org_status == "Pending Approval":
        for m in filtered_members:
            m.status = "Pending Approval"
            
    return {"status": "success", "users": filtered_members}



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
        new_user.send_welcome_mail_to_user() # Explicitly trigger welcome email
        
        # 4. Add the specific role we just created
        new_user.add_roles("Organization Admin") 
        
        frappe.db.commit()
        frappe.msgprint(f"Core User account created for {doc.work_email}")

# Helper to validate super admin
def validate_super_admin():
    if frappe.session.user == "Guest":
        frappe.throw(_("Please log in"), frappe.PermissionError)
    if "System Manager" not in frappe.get_roles() and frappe.session.user != "Administrator":
        frappe.throw(_("Not authorized - Super Admin only"), frappe.PermissionError)

@frappe.whitelist()
def get_admin_stats():
    validate_super_admin()
    
    # 1. Get all organizations
    orgs = frappe.get_all("User Registration", 
        fields=["name", "organization_name", "organization_type", "first_name", "last_name", "work_email", "creation", "approval_status", "number_of_users"],
        order_by="creation desc"
    )
    
    for org in orgs:
        # Count all users (enabled or disabled) for seat occupancy
        org.member_count = frappe.db.count("User", {"organization": org.name})
        # Count only enabled users for the "X enabled" stat
        org.enabled_count = frappe.db.count("User", {"organization": org.name, "enabled": 1})
        # Format some display fields
        org.admin_name = f"{org.first_name} {org.last_name}"
        
    return {"status": "success", "organizations": orgs}

@frappe.whitelist()
def toggle_registration_status(registration_id, status):
    validate_super_admin()
    
    if status not in ["Approved", "Rejected", "Inactive", "Active", "Pending Approval"]:
        return {"status": "error", "message": "Invalid status value"}
        
    if not frappe.db.exists("User Registration", registration_id):
        return {"status": "error", "message": "Organization not found"}
        
    org_doc = frappe.get_doc("User Registration", registration_id)
    org_doc.approval_status = status
    org_doc.save(ignore_permissions=True)
    
    # 1. Update the Main Admin User
    if frappe.db.exists("User", org_doc.work_email):
        main_user = frappe.get_doc("User", org_doc.work_email)
        main_user.enabled = 1 if status == "Approved" else 0
        main_user.save(ignore_permissions=True)
        
    # 2. Update all Organization Members
    # We find all users where organization link matches this registration
    users = frappe.get_all("User", filters={"organization": registration_id}, fields=["name"])
    for u_info in users:
        u = frappe.get_doc("User", u_info.name)
        u.enabled = 1 if status == "Approved" else 0
        u.save(ignore_permissions=True)
        
    # 3. Update the members child table in the registration doc for UI consistency
    for member in org_doc.members:
        member.status = status
    org_doc.save(ignore_permissions=True)
    
    frappe.db.commit()
    
    msg = f"Organization and all its users have been {'activated' if status == 'Approved' else 'disabled'} successfully."
    return {"status": "success", "message": msg}

@frappe.whitelist()
def get_org_growth_data():
    validate_super_admin()
    
    # Get data for the entire current year only
    from datetime import datetime
    from dateutil.relativedelta import relativedelta
    
    end_date = datetime.now()
    start_date = end_date.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    
    query = """
        SELECT 
            DATE_FORMAT(creation, '%%b %%Y') as month,
            COUNT(*) as count,
            DATE_FORMAT(creation, '%%Y-%%m') as month_sort
        FROM `tabUser Registration`
        WHERE creation >= %s AND creation <= %s
        GROUP BY month_sort
        ORDER BY month_sort ASC
    """
    
    raw_data = frappe.db.sql(query, (start_date, end_date), as_dict=1)
    
    # Yearly Calculation
    total_this_year = sum(item['count'] for item in raw_data)
    elapsed_months = end_date.month
    year_avg = round(total_this_year / elapsed_months, 1) if elapsed_months > 0 else 0
    
    # Fill in missing months from Jan to current
    labels = []
    values = []
    
    current = start_date
    while current <= end_date:
        m_label = current.strftime('%b %Y')
        m_sort = current.strftime('%Y-%m')
        
        labels.append(m_label)
        
        # Find if we have data for this month
        found = next((item['count'] for item in raw_data if item['month_sort'] == m_sort), 0)
        values.append(found)
        
        current += relativedelta(months=1)
    
    # ... rest of function (Plan Distribution)
        
    # 2. Get Plan Distribution
    plan_data = frappe.db.sql("""
        SELECT organization_type, count(*) as count 
        FROM `tabUser Registration` 
        GROUP BY organization_type
    """, as_dict=1)
    
    plans = {
        "labels": [p.get("organization_type") or "Unspecified" for p in plan_data],
        "values": [p.get("count") for p in plan_data]
    }
    
    return {
        "status": "success",
        "data": {
            "labels": labels,
            "values": values,
            "year_avg": year_avg
        },
        "plans": plans
    }

@frappe.whitelist()
def get_system_alerts():
    validate_super_admin()
    alerts = frappe.get_all("System Alert",
        fields=["name", "alert_type", "message", "user", "creation", "is_read"],
        filters={"is_read": 0},
        order_by="creation desc",
        limit=20
    )
    return {"status": "success", "alerts": alerts}

@frappe.whitelist()
def mark_alert_as_read(alert_id):
    validate_super_admin()
    if frappe.db.exists("System Alert", alert_id):
        frappe.db.set_value("System Alert", alert_id, "is_read", 1)
        frappe.db.commit()
    return {"status": "success"}

@frappe.whitelist()
def get_all_users():
    validate_super_admin()
    users = frappe.get_all("User",
        fields=["name", "full_name", "email", "user_type", "creation", "enabled", "organization"],
        filters={
            "user_type": ["!=", "System User"],
            "name": ["!=", "Guest"]
        },
        order_by="creation desc"
    )
    
    # Map the explicit status from Org User Item for each user
    final_users = []
    
    for u in users:
        status_val = None
        org_status = None
        is_main_admin = False
        
        # 1. First see if there is an exact member item match in a registration
        if u.organization:
            status_val = frappe.db.get_value("Org User Item", {"user_ref": u.name, "parent": u.organization}, "status")
            reg_data = frappe.db.get_value("User Registration", u.organization, ["approval_status", "work_email"], as_dict=True)
            if reg_data:
                org_status = reg_data.get("approval_status")
                if reg_data.get("work_email") == u.email:
                    is_main_admin = True
            
        # 2. Alternatively they might be the main admin of the org, check User Registration directly
        if not status_val and not org_status:
            reg_status = frappe.db.get_value("User Registration", {"work_email": u.email}, "approval_status")
            if reg_status:
                status_val = reg_status
                org_status = reg_status
                is_main_admin = True
                
        # 3. Mask child member status if parent org is pending. 
        if org_status == "Pending Approval":
            status_val = "Pending Approval"
                
        u.actual_status = status_val or ("Approved" if u.enabled else "Disabled")
        u.is_org_admin = is_main_admin
        final_users.append(u)
        
    return {"status": "success", "users": final_users}

@frappe.whitelist(allow_guest=True)
def request_password_reset(email):
    if not email:
        return {"status": "error", "message": "Email is required."}
    
    # Check if user exists
    user = frappe.db.get_value("User", {"email": email}, "name")
    if not user:
        return {"status": "error", "message": "This email is not registered."}
        
    try:
        ur = frappe.get_doc("User", user)
        if not ur.enabled:
            return {"status": "error", "message": "Your account is disabled. Please wait for approval or contact your administrator."}
        ur.reset_password(send_email=True)
        return {"status": "success"}
    except Exception as e:
        # Standardize the error message if it is a frappe error, else generic Support message.
        err_msg = str(e) if hasattr(e, 'message') else "Failed to send reset email. Please contact support."
        frappe.log_error(frappe.get_traceback(), "Password Reset Failed")
        return {"status": "error", "message": err_msg}
