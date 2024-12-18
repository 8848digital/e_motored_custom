import frappe
from frappe.utils import (
	flt,
)

from erpnext.manufacturing.doctype.production_plan.production_plan import ProductionPlan

class OverrideProductionPlan(ProductionPlan):

    def create_work_order(self, item):
        from erpnext.manufacturing.doctype.work_order.work_order import OverProductionError

        qty = flt(item.get("qty"))
        if qty <= 0:
            return

        # Store all created work order names
        work_order_names = []

        for i in range(int(qty)):  # Loop for the quantity
            item["qty"] = 1  # Override quantity to 1 for each work order
            wo = frappe.new_doc("Work Order")
            wo.update(item)
            wo.planned_start_date = item.get("planned_start_date") or item.get("schedule_date")

            if item.get("warehouse"):
                wo.fg_warehouse = item.get("warehouse")

            wo.set_work_order_operations()
            wo.set_required_items()

            try:
                wo.flags.ignore_mandatory = True
                wo.flags.ignore_validate = True
                wo.insert()
                # Append the name of the created work order to the list
                work_order_names.append(wo.name)
            except OverProductionError:
                # Handle the exception but continue to the next iteration
                pass

        return work_order_names