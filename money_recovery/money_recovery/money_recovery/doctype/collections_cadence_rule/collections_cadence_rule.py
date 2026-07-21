from __future__ import unicode_literals

import frappe
from frappe.model.document import Document


class CollectionsCadenceRule(Document):
    """DocType for defining automated collections cadence rules.

    Each rule maps a range of days-overdue to a specific action
    (WhatsApp reminder, SMS, call flag, legal escalation) using a
    configurable message template.
    """
    pass


def get_applicable_rule(days_overdue):
    """Return the first Collections Cadence Rule that matches `days_overdue`.

    Args:
        days_overdue (int): Number of days the invoice is past due.

    Returns:
        dict | None: The matching rule's fields, or None if no rule matches.
    """
    rules = frappe.get_all(
        "Collections Cadence Rule",
        fields=["name", "action", "message_template", "days_overdue_from", "days_overdue_to"],
        order_by="days_overdue_from asc",
    )
    for rule in rules:
        if rule.days_overdue_from <= days_overdue <= rule.days_overdue_to:
            return rule
    return None
