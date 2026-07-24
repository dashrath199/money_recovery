from __future__ import unicode_literals

import frappe
from frappe import _


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {"label": _("Dunning ID"), "fieldname": "dunning_name", "fieldtype": "Link", "options": "Dunning", "width": 140},
        {"label": _("Customer"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 180},
        {"label": _("Sales Invoice"), "fieldname": "sales_invoice", "fieldtype": "Link", "options": "Sales Invoice", "width": 140},
        {"label": _("Outstanding Amount"), "fieldname": "outstanding_amount", "fieldtype": "Currency", "width": 140},
        {"label": _("Due Date"), "fieldname": "due_date", "fieldtype": "Date", "width": 100},
        {"label": _("Days Overdue"), "fieldname": "days_overdue", "fieldtype": "Int", "width": 100},
        {"label": _("Dispute Reason"), "fieldname": "dispute_reason", "fieldtype": "Small Text", "width": 250},
        {"label": _("Escalation Stage"), "fieldname": "escalation_stage", "fieldtype": "Data", "width": 130},
    ]


def get_data(filters):
    dunnings = frappe.get_all(
        "Dunning",
        filters={"dispute_flag": 1},
        fields=["name", "customer", "dispute_reason",
                "escalation_stage", "creation"],
    )

    data = []
    for d in dunnings:
        data.append({
            "dunning_name": d.name,
            "customer": d.customer,
            "sales_invoice": "N/A",
            "outstanding_amount": 0,
            "due_date": None,
            "days_overdue": 0,
            "dispute_reason": d.dispute_reason,
            "escalation_stage": d.escalation_stage,
        })

    data.sort(key=lambda r: r["days_overdue"], reverse=True)
    return data
