import frappe
from frappe import _
from frappe.utils import (
    nowdate,
    get_link_to_form,
    date_diff,
    cint
)

from frappe.utils import random_string

from erpnext.manufacturing.doctype.work_order.work_order import WorkOrder ,split_qty_based_on_batch_size

class CapacityError(frappe.ValidationError):
	pass

class OverrideWorkOrder(WorkOrder):

    def create_job_card(self):
        manufacturing_settings_doc = frappe.get_doc("Manufacturing Settings")

        enable_capacity_planning = not cint(manufacturing_settings_doc.disable_capacity_planning)
        plan_days = cint(manufacturing_settings_doc.capacity_planning_for_days) or 30
        for op in range(self.qty):
            op_id = random_string(4) #'HNRirG'
            for index, row in enumerate(self.operations):
                row.custom_op_group_id = op_id
                # qty = self.qty
                qty = 1
                while qty > 0:
                    qty = split_qty_based_on_batch_size(self, row, qty)
                    if row.job_card_qty > 0:
                        self.prepare_data_for_job_card(row, index, plan_days, enable_capacity_planning)

        planned_end_date = self.operations and self.operations[-1].planned_end_time
        if planned_end_date:
            self.db_set("planned_end_date", planned_end_date)

    def prepare_data_for_job_card(self, row, index, plan_days, enable_capacity_planning):
        self.set_operation_start_end_time(index, row)

        job_card_doc = create_job_card(
            self, row, auto_create=True, enable_capacity_planning=enable_capacity_planning
        )

        if enable_capacity_planning and job_card_doc:
            row.planned_start_time = job_card_doc.scheduled_time_logs[-1].from_time
            row.planned_end_time = job_card_doc.scheduled_time_logs[-1].to_time

            if date_diff(row.planned_end_time, self.planned_start_date) > plan_days:
                frappe.message_log.pop()
                frappe.throw(
                    _(
                        "Unable to find the time slot in the next {0} days for the operation {1}. Please increase the 'Capacity Planning For (Days)' in the {2}."
                    ).format(
                        plan_days,
                        row.operation,
                        get_link_to_form("Manufacturing Settings", "Manufacturing Settings"),
                    ),
                    CapacityError,
                )

            row.db_update()

def create_job_card(work_order, row, enable_capacity_planning=False, auto_create=False):
    doc = frappe.new_doc("Job Card")
    doc.update(
        {
            "work_order": work_order.name,
            "workstation_type": row.get("workstation_type"),
            "operation": row.get("operation"),
            "workstation": row.get("workstation"),
            "posting_date": nowdate(),
            "for_quantity": row.job_card_qty or work_order.get("qty", 0),
            "operation_id": row.get("name"),
            "bom_no": work_order.bom_no,
            "project": work_order.project,
            "company": work_order.company,
            "sequence_id": row.get("sequence_id"),
            "wip_warehouse": work_order.wip_warehouse,
            "hour_rate": row.get("hour_rate"),
            "serial_no": row.get("serial_no"),
            "custom_job_status":"Ready" if row.idx == 1 else "Pending",
            "custom_op_group_id":f"""{row.custom_op_group_id}-{row.get("sequence_id")}"""
        }
    )

    if work_order.transfer_material_against == "Job Card" and not work_order.skip_transfer:
        doc.get_required_items()

    if auto_create:
        doc.flags.ignore_mandatory = True
        if enable_capacity_planning:
            doc.schedule_time_logs(row)

        doc.insert()
        frappe.msgprint(_("Job card {0} created").format(get_link_to_form("Job Card", doc.name)), alert=True)

    if enable_capacity_planning:
        # automatically added scheduling rows shouldn't change status to WIP
        doc.db_set("status", "Open")

    return doc