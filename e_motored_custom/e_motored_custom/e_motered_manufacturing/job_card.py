import frappe

def change_job_status(doc,methods = None):
    work_order_doc = frappe.get_doc('Work Order', doc.work_order)
    total_jobs = len(work_order_doc.operations)

    if doc.custom_job_status == "Completed":
        if doc.sequence_id != total_jobs:
            next_sequence_id  = int(doc.sequence_id) + 1

            job_card_name = frappe.db.get_value('Job Card', {'work_order': doc.work_order,"sequence_id":next_sequence_id})

            job_card_doc = frappe.get_doc('Job Card', job_card_name)
            job_card_doc.custom_job_status ="Ready"
            job_card_doc.save()
