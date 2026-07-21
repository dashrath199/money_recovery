from __future__ import unicode_literals

import frappe
from frappe.model.document import Document


class MessageTemplate(Document):
    """DocType for storing templated messages used in collections.

    Supports multiple channels (WhatsApp, SMS, Email) and regional
    language variants so reminders stay context-appropriate.
    """
    pass


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
