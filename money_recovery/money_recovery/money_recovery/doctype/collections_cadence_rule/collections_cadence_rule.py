from frappe.model.document import Document


class CollectionsCadenceRule(Document):
    """DocType for defining automated collections cadence rules.

    Each rule maps a range of days-overdue to a specific action
    (WhatsApp reminder, SMS, call flag, legal escalation) using a
    configurable message template.
    """
    pass
