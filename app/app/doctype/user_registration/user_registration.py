import frappe
from frappe.model.document import Document

class UserRegistration(Document):
	def on_update(self):
		# Sync members status with core User accounts
		for member in self.get("members", []):
			if not member.user_ref:
				continue
				
			user = frappe.get_doc("User", member.user_ref)
			
			if member.status == "Approved" and not user.enabled:
				user.enabled = 1
				user.send_welcome_email = 1
				user.save(ignore_permissions=True)
				frappe.msgprint(f"User {member.email} has been approved and enabled.")
				
			elif member.status == "Rejected" and user.enabled:
				user.enabled = 0
				user.save(ignore_permissions=True)
				frappe.msgprint(f"User {member.email} has been rejected and disabled.")
				
			elif member.status == "Pending Approval" and user.enabled:
				# If somehow it was enabled but status is pending, maybe disable it?
				# But for now, we just handle transitions.
				pass
