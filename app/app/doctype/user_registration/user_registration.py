import frappe
from frappe.model.document import Document

class UserRegistration(Document):
	def on_update(self):
		# Sync members status with core User accounts
		for member in self.get("members", []):
			# If manual entry in Desk, user_ref might be empty. Find by email.
			if not member.user_ref:
				member.user_ref = frappe.db.get_value("User", member.email)
				
			if member.status == "Approved":
				if not member.user_ref:
					# Create the user if they don't exist yet
					new_user = frappe.get_doc({
						"doctype": "User",
						"email": member.email,
						"first_name": member.name1,
						"enabled": 1,
						"send_welcome_email": 1, # Triggers standard welcome
						"user_type": "Website User",
						"organization": self.name
					})
					new_user.insert(ignore_permissions=True)
					new_user.send_welcome_mail_to_user() # Explicitly trigger welcome email
					member.user_ref = new_user.name
					frappe.msgprint(f"Created and approved user {member.email}")
				else:
					# Enable existing user
					user = frappe.get_doc("User", member.user_ref)
					if not user.enabled:
						user.enabled = 1
						user.save(ignore_permissions=True)
						user.send_welcome_mail_to_user() # Re-send welcome for newly enabled user
						frappe.msgprint(f"User {member.email} has been approved and enabled.")
				
			elif member.status == "Rejected" and member.user_ref:
				user_name = frappe.db.get_value("User", member.user_ref, "name")
				if user_name:
					frappe.db.set_value("User", user_name, "enabled", 0)
					frappe.msgprint(f"User {member.email} has been rejected and disabled.")
				
		frappe.db.commit()
