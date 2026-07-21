from __future__ import unicode_literals

import frappe
from frappe.utils import nowdate, date_diff
from frappe import _

from money_recovery.money_recovery.doctype.collections_cadence_rule.collections_cadence_rule import (
    get_applicable_rule,
)
from money_recovery.api import send_payment_reminder


def run_collections_cadence():
    """Daily scheduled job that drives the collections cadence.

    For every open Sales Invoice past its due date:
      1. Compute days_overdue.
      2. Match against the first applicable Collections Cadence Rule.
      3. Trigger the corresponding action (WhatsApp/SMS/Email or flag for call).
      4. Log the action against the linked Dunning record.
    """
    open_invoices = frappe.get_all(
        "Sales Invoice",
        filters={
            "docstatus": 1,
            "outstanding_amount": (">", 0),
            "due_date": ("<", nowdate()),
        },
        fields=["name", "customer", "customer_name", "outstanding_amount",
                "due_date", "company", "currency"],
    )

    for inv in open_invoices:
        days_overdue = date_diff(nowdate(), inv.due_date)
        rule = get_applicable_rule(days_overdue)

        if not rule:
            # No cadence rule defined for this bucket — skip
            continue

        # Find existing open Dunning record for this invoice
        dunning_name = get_or_create_dunning(inv.name, inv.customer)

        if rule.action in ("Send WhatsApp Reminder", "Send SMS", "Send Email Reminder"):
            channel_map = {
                "Send WhatsApp Reminder": "WhatsApp",
                "Send SMS": "SMS",
                "Send Email Reminder": "Email",
            }
            try:
                send_payment_reminder(
                    dunning_name=dunning_name,
                    channel=channel_map[rule.action],
                    template_name=rule.message_template,
                    context={
                        "customer_name": inv.customer_name,
                        "invoice_number": inv.name,
                        "outstanding_amount": f"{inv.currency} {inv.outstanding_amount:,.2f}",
                        "due_date": str(inv.due_date),
                        "days_overdue": str(days_overdue),
                        "company_name": inv.company,
                    },
                )
                log_contact(dunning_name, channel_map[rule.action], rule.name)
            except Exception as e:
                frappe.log_error(
                    title=_("Money Recovery: Reminder Failed"),
                    message=f"Invoice {inv.name}, Rule {rule.name}: {e}",
                )

        elif rule.action == "Flag for Manual Call":
            log_flag_for_call(dunning_name, rule.name)

        elif rule.action == "Escalate to Legal":
            frappe.db.set_value("Dunning", dunning_name, "escalation_stage", "Legal Referral")

    frappe.db.commit()


def check_broken_promises():
    """Daily check for promises that were not kept.

    Flags Dunning records where `promised_payment_date < today`
    and no corresponding Payment Entry exists for the linked invoice.
    Creates a system notification for a personal follow-up call.
    """
    broken = frappe.get_all(
        "Dunning",
        filters=[
            ["promised_payment_date", "<", nowdate()],
            ["docstatus", "=", 0],
            ["status", "=", "Overdue"],
        ],
        fields=["name", "sales_invoice"],
    )

    for d in broken:
        invoice = frappe.get_doc("Sales Invoice", d.sales_invoice)
        if invoice.outstanding_amount <= 0:
            # Paid since the promise was made
            continue

        frappe.publish_realtime(
            event="money_recovery_broken_promise",
            message={
                "dunning_name": d.name,
                "sales_invoice": d.sales_invoice,
                "customer": invoice.customer,
                "customer_name": invoice.customer_name,
            },
            user=frappe.db.get_value("Dunning", d.name, "owner"),
        )


def get_or_create_dunning(sales_invoice, customer):
    """Find an existing open Dunning for this invoice, or create one."""
    existing = frappe.db.get_value(
        "Dunning", {"sales_invoice": sales_invoice, "status": "Overdue"}, "name"
    )
    if existing:
        return existing

    dunning = frappe.get_doc({
        "doctype": "Dunning",
        "sales_invoice": sales_invoice,
        "customer": customer,
        "escalation_stage": "Reminder 1",
    })
    dunning.insert(ignore_permissions=True)
    return dunning.name


def log_contact(dunning_name, channel, rule_name):
    """Update the Dunning record with last contact info."""
    frappe.db.set_value("Dunning", dunning_name, {
        "last_contact_channel": channel,
        "last_reminder_sent_on": frappe.utils.now_datetime(),
    })
    frappe.db.set_value("Dunning", dunning_name, "escalation_stage",
                        get_next_stage(dunning_name))


def log_flag_for_call(dunning_name, rule_name):
    """Mark the Dunning for manual call follow-up."""
    frappe.db.set_value("Dunning", dunning_name, "escalation_stage", get_next_stage(dunning_name))


def get_next_stage(dunning_name):
    """Return the next escalation stage based on current stage."""
    stages = ["Reminder 1", "Reminder 2", "Final Notice", "Legal Referral"]
    current = frappe.db.get_value("Dunning", dunning_name, "escalation_stage")
    try:
        idx = stages.index(current)
        if idx < len(stages) - 1:
            return stages[idx + 1]
    except ValueError:
        pass
    return "Reminder 2"
