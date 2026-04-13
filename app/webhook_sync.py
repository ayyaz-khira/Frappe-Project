import frappe
import requests

PLATFORM_B_BASE_URL = "https://hq.nuomics.io"
PLATFORM_B_API_KEY = "daf4fc86d5a1ef2"
PLATFORM_B_API_SECRET = "16a2f752338e915"


def capture_password(doc, method=None):
    if doc.doctype == "User" and doc.get("new_password"):
        doc.flags.new_password_to_sync = doc.get("new_password")


def password_update(doc, method=None):
    new_password = doc.flags.get("new_password_to_sync")
    if not new_password:
        return

    api_url = f"{PLATFORM_B_BASE_URL}/api/resource/User/{doc.email}"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"token {PLATFORM_B_API_KEY}:{PLATFORM_B_API_SECRET}",
    }

    try:
        res = requests.put(api_url, json={"new_password": new_password}, headers=headers, timeout=10)
        _log_sync(doc.email, api_url, res.status_code, res.text)

        if res.status_code == 200:
            frappe.msgprint(f"✅ Password updated on Platform B for {doc.email}", indicator="green")
        else:
            frappe.msgprint(f"⚠️ Platform B returned {res.status_code}: {res.text}", indicator="orange")

    except requests.exceptions.ConnectionError:
        _log_sync(doc.email, api_url, "Error", "Could not reach Platform B")
        frappe.msgprint("❌ Could not connect to Platform B.", indicator="red")

    except Exception as e:
        _log_sync(doc.email, api_url, "Error", str(e))
        frappe.msgprint(f"❌ Unexpected error: {e}", indicator="red")


def _log_sync(user_email: str, url: str, status, response: str):
    try:
        frappe.get_doc({
            "doctype": "Error Log",
            "method": "Platform B – Password Sync",
            "error": (
                f"User   : {user_email}\n"
                f"URL    : {url}\n"
                f"Status : {status}\n"
                f"Response: {response}"
            ),
        }).insert(ignore_permissions=True)
    except Exception:
        pas