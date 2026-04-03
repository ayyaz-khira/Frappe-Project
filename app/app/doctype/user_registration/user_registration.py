import frappe
from frappe.model.document import Document

class UserRegistration(Document):
	def on_update(self):
		# SYNC LOGIC: Ensure emails are only sent when approval status is FIRST flipped to 'Approved'
		for member in self.get("members", []):
			# Resolve user reference
			if not member.user_ref:
				member.user_ref = frappe.db.get_value("User", {"email": member.email})
				
			if member.status == "Approved":
				# First check if the user even exists. If they don't, create them.
				if not member.user_ref:
					new_user = frappe.get_doc({
						"doctype": "User",
						"email": member.email,
						"first_name": member.name1,
						"enabled": 1,
						"send_welcome_email": 1, 
						"user_type": "Website User",
						"organization": self.name
					})
					new_user.insert(ignore_permissions=True)
					new_user.send_welcome_mail_to_user() 
					member.user_ref = new_user.name
					frappe.msgprint(f"User {member.email} created and welcome email sent.")
				else:
					# USER ALREADY EXISTS: Check if we JUST approved them (avoiding re-send on every save)
					# We only send if the user is currently DISABLED in the system.
					user = frappe.get_doc("User", member.user_ref)
					if not user.enabled:
						user.enabled = 1
						user.save(ignore_permissions=True)
						user.send_welcome_mail_to_user() # Trigger first-time approval email
						frappe.msgprint(f"User {member.email} has been approved and enabled.")
					# If user.enabled is ALREADY 1, we do NOTHING. This ensures "First Save Only" behavior.
				
			elif member.status == "Rejected" and member.user_ref:
				if frappe.db.get_value("User", member.user_ref, "enabled"):
					frappe.db.set_value("User", member.user_ref, "enabled", 0)
					frappe.msgprint(f"User {member.email} has been rejected and disabled.")
				
		frappe.db.commit()
