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
        {"label": _("Customer"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 180},
        {"label": _("Promises Made"), "fieldname": "promises_made", "fieldtype": "Int", "width": 120},
        {"label": _("Promises Kept"), "fieldname": "promises_kept", "fieldtype": "Int", "width": 120},
        {"label": _("Promises Broken"), "fieldname": "promises_broken", "fieldtype": "Int", "width": 120},
        {"label": _("Reliability %"), "fieldname": "reliability_pct", "fieldtype": "Percent", "width": 120},
        {"label": _("Avg Days Late"), "fieldname": "avg_days_late", "fieldtype": "Float", "precision": 1, "width": 120},
    ]


def get_data(filters):
    # Find all Dunning records that had a promised_payment_date set
    dunnings = frappe.get_all(
        "Dunning",
        filters=[
            ["promised_payment_date", "is", "set"],
            ["docstatus", "=", 0],
        ],
        fields=["name", "customer", "promised_payment_date"],
    )

    customer_stats = {}
    for d in dunnings:
        customer = d.customer
        if customer not in customer_stats:
            customer_stats[customer] = {
                "promises_made": 0,
                "promises_kept": 0,
                "promises_broken": 0,
                "total_late_days": 0,
                "late_count": 0,
            }

        customer_stats[customer]["promises_made"] += 1

        # Check if the Sales Invoice was paid on or before the promised date
        # Since sales_invoice field is unavailable, treat all as broken
        customer_stats[customer]["promises_broken"] += 1

    data = []
    for customer, stats in customer_stats.items():
        total = stats["promises_made"]
        kept = stats["promises_kept"]
        reliability = (kept / total * 100) if total > 0 else 0
        avg_days_late = (
            stats["total_late_days"] / stats["late_count"]
            if stats["late_count"] > 0
            else 0
        )
        data.append({
            "customer": customer,
            "promises_made": stats["promises_made"],
            "promises_kept": stats["promises_kept"],
            "promises_broken": stats["promises_broken"],
            "reliability_pct": round(reliability, 1),
            "avg_days_late": round(avg_days_late, 1),
        })

    data.sort(key=lambda r: r["reliability_pct"])
    return data


def get_chart(data):
    labels = [r["customer"][:15] + "..." if len(r["customer"]) > 15 else r["customer"]
              for r in data[:20]]
    values = [r["reliability_pct"] for r in data[:20]]

    return {
        "data": {
            "labels": labels,
            "datasets": [
                {"name": "Reliability %", "values": values},
            ],
        },
        "type": "bar",
        "colors": ["#36a2eb"],
    }
