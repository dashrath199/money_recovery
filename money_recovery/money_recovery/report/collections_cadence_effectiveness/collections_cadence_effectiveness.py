from __future__ import unicode_literals

import frappe
from frappe import _


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    chart = get_chart(data)
    return columns, data, None, chart


def get_columns():
    return [
        {"label": _("Escalation Stage"), "fieldname": "stage", "fieldtype": "Data", "width": 150},
        {"label": _("Total Dunning Records"), "fieldname": "total", "fieldtype": "Int", "width": 140},
        {"label": _("Resolved"), "fieldname": "resolved", "fieldtype": "Int", "width": 120},
        {"label": _("Still Open"), "fieldname": "still_open", "fieldtype": "Int", "width": 120},
        {"label": _("Resolution Rate (%)"), "fieldname": "resolution_rate", "fieldtype": "Percent", "width": 140},
    ]


def get_data(filters):
    stages = ["Reminder 1", "Reminder 2", "Final Notice", "Legal Referral"]
    data = []

    for stage in stages:
        dunning_list = frappe.get_all(
            "Dunning",
            filters={"escalation_stage": stage},
            fields=["name", "status"],
        )

        total = len(dunning_list)
        resolved = len([d for d in dunning_list if d.status == "Resolved"])
        still_open = total - resolved
        resolution_rate = round((resolved / total * 100), 1) if total > 0 else 0

        data.append({
            "stage": stage,
            "total": total,
            "resolved": resolved,
            "still_open": still_open,
            "resolution_rate": resolution_rate,
        })

    return data


def get_chart(data):
    stages = [d["stage"] for d in data]
    resolved = [d["resolved"] for d in data]
    open_count = [d["still_open"] for d in data]

    return {
        "data": {
            "labels": stages,
            "datasets": [
                {"name": "Resolved", "values": resolved},
                {"name": "Still Open", "values": open_count},
            ],
        },
        "type": "bar",
        "colors": ["#28a745", "#dc3545"],
        "barOptions": {"stacked": True},
    }
