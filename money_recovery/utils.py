import frappe


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


@frappe.whitelist()
def get_rendered_template(template_name, channel, language=None, context=None):
    """Fetch and render a Message Template with the given context.

    Args:
        template_name (str): Name of the Message Template.
        channel (str): Channel to fetch for (WhatsApp / SMS / Email).
        language (str, optional): Language variant (e.g. 'en', 'hi', 'ta').
        context (dict, optional): Jinja context for rendering placeholders.

    Returns:
        str: Rendered message body.
    """
    filters = {"template_name": template_name, "channel": channel}
    if language:
        filters["language"] = language

    template = frappe.get_value("Message Template", filters, "message_body", cache=True)
    if not template:
        # Fall back to default language
        filters.pop("language", None)
        filters["is_default"] = 1
        template = frappe.get_value("Message Template", filters, "message_body", cache=True)

    if not template:
        frappe.throw(f"No matching template found for {template_name} / {channel}")

    if context:
        from frappe.utils import get_jenv
        env = get_jenv()
        rendered = env.from_string(template).render(**context)
        return rendered

    return template


@frappe.whitelist()
def get_90_days_overdue():
    """Return the sum of outstanding_amount for Sales Invoices overdue by 90+ days."""
    from frappe.utils import add_days, nowdate
    
    ninety_days_ago = add_days(nowdate(), -90)
    
    result = frappe.db.get_value(
        "Sales Invoice",
        filters={
            "docstatus": 1,
            "outstanding_amount": [">", 0],
            "due_date": ["<", ninety_days_ago],
        },
        fieldname="sum(outstanding_amount)",
    )
    return result or 0
