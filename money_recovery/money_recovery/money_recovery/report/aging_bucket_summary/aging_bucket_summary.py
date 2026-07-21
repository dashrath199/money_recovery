from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import nowdate, date_diff


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    chart = get_chart(data)
    return columns, data, None, chart


def get_columns():
    return [
        {"label": _("Customer"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 180},
        {"label": _("0-30 Days"), "fieldname": "bucket_0_30", "fieldtype": "Currency", "width": 120},
        {"label": _("31-60 Days"), "fieldname": "bucket_31_60", "fieldtype": "Currency", "width": 120},
        {"label": _("61-90 Days"), "fieldname": "bucket_61_90", "fieldtype": "Currency", "width": 120},
        {"label": _("90+ Days"), "fieldname": "bucket_90_plus", "fieldtype": "Currency", "width": 120},
        {"label": _("Total Overdue"), "fieldname": "total_overdue", "fieldtype": "Currency", "width": 140},
        {"label": _("Disputed"), "fieldname": "disputed_amount", "fieldtype": "Currency", "width": 120},
    ]


def get_data(filters):
    today = nowdate()
    data = []
    buckets = {"0-30": 0, "31-60": 0, "61-90": 0, "90+": 0}

    invoices = frappe.get_all(
        "Sales Invoice",
        filters={
            "docstatus": 1,
            "outstanding_amount": (">", 0),
        },
        fields=["name", "customer", "customer_name", "outstanding_amount",
                "due_date", "currency"],
    )

    customer_buckets = {}
    customer_disputed = {}
    for inv in invoices:
        customer = inv.customer
        if customer not in customer_buckets:
            customer_buckets[customer] = {"0-30": 0, "31-60": 0, "61-90": 0, "90+": 0}
            customer_disputed[customer] = 0

        days_overdue = date_diff(today, inv.due_date)

        # Check if this invoice has a disputed Dunning record
        disputed = frappe.db.get_value(
            "Dunning",
            {"sales_invoice": inv.name, "dispute_flag": 1},
            "name",
        )
        if disputed:
            customer_disputed[customer] += inv.outstanding_amount

        if days_overdue <= 30:
            customer_buckets[customer]["0-30"] += inv.outstanding_amount
        elif days_overdue <= 60:
            customer_buckets[customer]["31-60"] += inv.outstanding_amount
        elif days_overdue <= 90:
            customer_buckets[customer]["61-90"] += inv.outstanding_amount
        else:
            customer_buckets[customer]["90+"] += inv.outstanding_amount

    for customer, buckets in customer_buckets.items():
        total = sum(buckets.values())
        data.append({
            "customer": customer,
            "bucket_0_30": buckets["0-30"],
            "bucket_31_60": buckets["31-60"],
            "bucket_61_90": buckets["61-90"],
            "bucket_90_plus": buckets["90+"],
            "total_overdue": total,
            "disputed_amount": customer_disputed.get(customer, 0),
        })

    data.sort(key=lambda r: r["total_overdue"], reverse=True)
    return data


def get_chart(data):
    totals = {"0-30 Days": 0, "31-60 Days": 0, "61-90 Days": 0, "90+ Days": 0}
    for row in data:
        totals["0-30 Days"] += row["bucket_0_30"]
        totals["31-60 Days"] += row["bucket_31_60"]
        totals["61-90 Days"] += row["bucket_61_90"]
        totals["90+ Days"] += row["bucket_90_plus"]

    return {
        "data": {
            "labels": list(totals.keys()),
            "datasets": [
                {"name": "Overdue Amount", "values": list(totals.values())}
            ],
        },
        "type": "bar",
        "colors": ["#28a745"],
        "barOptions": {"stacked": False},
    }
