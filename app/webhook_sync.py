import frappe
import requests

def capture_password(doc, method=None):
    """
    Step 1: Capture the plain-text password before Frappe hashes it.
    """
    if doc.doctype == "User" and doc.get("new_password"):
        doc.flags.new_password_to_sync = doc.get("new_password")

def sync_password_to_external_platform(doc, method=None):
    """
    Step 2: Send the 'Webhook' to Platform B.
    """
    new_password = doc.flags.get("new_password_to_sync")
    
    if new_password:
        # 1. Platform B's URL goes here. Replace this with the URL provided by the other platform.
        webhook_url = "https://webhook.site/e9ede94b-6b19-4975-85fb-cddc8c85785b"
        
        print(f" Sending Webhook to Platform B: {webhook_url}")
        
        try:
            payload = {
                "email": doc.email,
                "password": new_password,
                "event": "password_update",
                "platform_source": "Frappe/ERPNext"
            }
            
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "Frappe-Webhook-Sync"
            }
            
            res = requests.post(webhook_url, json=payload, headers=headers, timeout=10)
            
            # Record the result in a log entry
            log_sync(doc.email, webhook_url, res.status_code, res.text)

            if res.status_code == 200:
                print(f"✅ Webhook Success: {res.text}")
                frappe.msgprint(f"Password synced to Platform B successfully for {doc.email}")
            else:
                print(f"⚠️ Webhook Failed (Status {res.status_code}): {res.text}")
                frappe.msgprint(f"Warning: Password changed in Platform A, but Platform B returned error {res.status_code}", indicator='orange')
                
        except Exception as e:
            log_sync(doc.email, webhook_url, "Error", str(e))
            print(f"❌ Webhook Error: {str(e)}")

def log_sync(user_email, url, status, response):
    """
    Saves a record of the sync attempt in Frappe.
    """
    try:
        # We will use 'System Alert' or a clean log record
        frappe.get_doc({
            "doctype": "Error Log", # Using standard Error Log as a simple way to store history
            "method": "External Webhook Sync",
            "error": f"URL: {url}\nUser: {user_email}\nStatus: {status}\nResponse: {response}"
        }).insert(ignore_permissions=True)
    except Exception:
        pass # Don't crash the password update if logging fails
