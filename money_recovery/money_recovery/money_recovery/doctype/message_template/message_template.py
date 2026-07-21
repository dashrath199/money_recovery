from frappe.model.document import Document


class MessageTemplate(Document):
    """DocType for storing templated messages used in collections.

    Supports multiple channels (WhatsApp, SMS, Email) and regional
    language variants so reminders stay context-appropriate.
    """
    pass
