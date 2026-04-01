frappe.ui.form.on("PayU Payout", {
	refresh(frm) {
        if (frm.doc.status === 'Pending' && frm.doc.payout_id) {
            frm.add_custom_button('Check Status', () => {
                frappe.call({
                    method: 'app.api.check_payout_status',
                    args: { payout_id: frm.doc.payout_id },
                    callback: (r) => {
                        if (r.message) {
                            frappe.msgprint(__('Status updated to: ') + r.message.status);
                            frm.reload_doc();
                        }
                    }
                });
            });
        }
	},
});
