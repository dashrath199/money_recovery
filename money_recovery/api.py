from __future__ import unicode_literals

import frappe
import requests
from frappe import _
from frappe.utils import now_datetime

from money_recovery.utils import get_rendered_template


@frappe.whitelist()
def send_payment_reminder(dunning_name, channel, template_name=None, context=None):
    """Send a payment reminder via the specified channel.

    This is the primary integration point for WhatsApp Business API,
    SMS gateways (Gupshup, MSG91, etc.), and email.

    Args:
        dunning_name (str): Name of the Dunning record.
        channel (str): One of "WhatsApp", "SMS", "Email".
        template_name (str, optional): Message Template name. If omitted,
            a default is looked up by channel.
        context (dict, optional): Jinja context for template rendering.

    Returns:
        dict: Status of the send operation.
    """
    dunning = frappe.get_doc("Dunning", dunning_name)
    invoice = frappe.get_doc("Sales Invoice", dunning.sales_invoice)

    if context is None:
        context = {
            "customer_name": invoice.customer_name,
            "invoice_number": invoice.name,
            "outstanding_amount": f"{invoice.currency} {invoice.outstanding_amount:,.2f}",
            "due_date": str(invoice.due_date),
            "days_overdue": str(frappe.utils.date_diff(now_datetime(), invoice.due_date)),
            "company_name": invoice.company,
        }

    # Render message body
    message_body = get_rendered_template(
        template_name=template_name or f"Payment Reminder - {channel}",
        channel=channel,
        context=context,
    )

    # Route to the appropriate channel handler
    channel_handlers = {
        "WhatsApp": _send_whatsapp,
        "SMS": _send_sms,
        "Email": _send_email,
    }

    handler = channel_handlers.get(channel)
    if not handler:
        frappe.throw(_("Unsupported channel: {0}").format(channel))

    result = handler(
        recipient=invoice.customer_name,
        recipient_contact=_get_customer_contact(invoice.customer, channel),
        message=message_body,
        subject=context.get("subject", _("Payment Reminder - {0}").format(invoice.name)),
        reference_doctype="Dunning",
        reference_name=dunning_name,
    )

    # Update Dunning record
    frappe.db.set_value("Dunning", dunning_name, {
        "last_contact_channel": channel,
        "last_reminder_sent_on": now_datetime(),
    })

    if result.get("success"):
        return {"success": True, "message": _("{0} reminder sent").format(channel)}
    else:
        frappe.log_error(
            title=_("Money Recovery: {0} Send Failed").format(channel),
            message=f"Dunning {dunning_name}: {result.get('error')}",
        )
        return {"success": False, "error": result.get("error")}


def _get_customer_contact(customer, channel):
    """Retrieve the customer's contact for the given channel.

    Args:
        customer (str): Customer name.
        channel (str): Channel to get contact for.

    Returns:
        str | None: Contact value (mobile number, email, etc.).
    """
    if channel == "Email":
        email = frappe.db.get_value("Contact", {"customer": customer}, "email_id")
        if email:
            return email
        # Fall back to customer email
        return frappe.db.get_value("Customer", customer, "email_id")

    # WhatsApp / SMS — get mobile number
    mobile = frappe.db.get_value(
        "Contact", {"customer": customer, "is_primary_contact": 1}, "mobile_no"
    )
    if mobile:
        return mobile

    # Try any contact
    mobile = frappe.db.get_value("Contact", {"customer": customer}, "mobile_no")
    return mobile


def _send_whatsapp(recipient, recipient_contact, message, **kwargs):
    """Send a WhatsApp message via Gupshup.

    Expects the following in site config (site_config.json / common_site_config.json):
        - gupshup_api_key: Gupshup API key
        - whatsapp_source_number: Registered WhatsApp sender number
          (with country code, e.g. "917834811114")

    Args:
        recipient (str): Customer name (for logging).
        recipient_contact (str): Mobile number with country code.
        message (str): Plain-text message body.

    Returns:
        dict: {"success": True} on success, {"success": False, "error": ...} on failure.
    """
    if not recipient_contact:
        return {"success": False, "error": _("No mobile number found for customer")}

    api_key = frappe.conf.gupshup_api_key
    source = frappe.conf.whatsapp_source_number

    if not api_key:
        return {"success": False, "error": _("Gupshup API key not configured. Set gupshup_api_key in site config.")}
    if not source:
        return {"success": False, "error": _("WhatsApp source number not configured. Set whatsapp_source_number in site config.")}

    try:
        resp = requests.post(
            "https://api.gupshup.io/sm/api/v1/msg",
            headers={
                "apikey": api_key,
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "channel": "whatsapp",
                "source": source,
                "destination": recipient_contact,
                "message": message,
            },
            timeout=30,
        )
        resp.raise_for_status()
        result = resp.json()
        frappe.logger().info(
            f"[Money Recovery] WhatsApp sent to {recipient_contact}: "
            f"status={result.get('status')}, messageId={result.get('messageId')}"
        )
        return {"success": True, "provider_response": result}

    except requests.exceptions.RequestException as e:
        error_msg = f"Gupshup WhatsApp API error: {e}"
        frappe.log_error(title=_("WhatsApp Send Failed"), message=error_msg)
        return {"success": False, "error": error_msg}
    except Exception as e:
        error_msg = f"WhatsApp send error: {e}"
        frappe.log_error(title=_("WhatsApp Send Failed"), message=error_msg)
        return {"success": False, "error": error_msg}


def _send_sms(recipient, recipient_contact, message, **kwargs):
    """Send an SMS message via Gupshup Enterprise SMS Gateway.

    Expects the following in site config (site_config.json):
        - gupshup_sms_userid: Gupshup Enterprise SMS User ID
        - gupshup_sms_password: Gupshup Enterprise SMS Password
        - sms_sender_id: Registered SMS Sender ID / Header (optional, used if
          provided as part of your DLT registration)

    Args:
        recipient (str): Customer name (for logging).
        recipient_contact (str): Mobile number with country code.
        message (str): SMS text content.

    Returns:
        dict: {"success": True} on success, {"success": False, "error": ...} on failure.
    """
    if not recipient_contact:
        return {"success": False, "error": _("No mobile number found for customer")}

    userid = frappe.conf.gupshup_sms_userid
    password = frappe.conf.gupshup_sms_password

    if not userid or not password:
        return {"success": False, "error": _(
            "SMS credentials not configured. Set gupshup_sms_userid and "
            "gupshup_sms_password in site config."
        )}

    try:
        params = {
            "userid": userid,
            "password": password,
            "send_to": recipient_contact,
            "msg": message,
            "method": "SendMessage",
            "msg_type": "text",
            "format": "text",
            "auth_scheme": "plain",
            "v": "1.1",
        }
        if frappe.conf.sms_sender_id:
            params["mask"] = frappe.conf.sms_sender_id

        resp = requests.get(
            "https://enterprise.smsgupshup.com/GatewayAPI/rest",
            params=params,
            timeout=30,
        )
        resp.raise_for_status()
        response_text = resp.text.strip()

        if response_text.startswith("success"):
            frappe.logger().info(
                f"[Money Recovery] SMS sent to {recipient_contact}: {response_text}"
            )
            return {"success": True, "provider_response": response_text}
        else:
            error_msg = f"Gupshup SMS error: {response_text}"
            frappe.log_error(title=_("SMS Send Failed"), message=error_msg)
            return {"success": False, "error": error_msg}

    except requests.exceptions.RequestException as e:
        error_msg = f"Gupshup SMS API error: {e}"
        frappe.log_error(title=_("SMS Send Failed"), message=error_msg)
        return {"success": False, "error": error_msg}
    except Exception as e:
        error_msg = f"SMS send error: {e}"
        frappe.log_error(title=_("SMS Send Failed"), message=error_msg)
        return {"success": False, "error": error_msg}


def _send_email(recipient, recipient_contact, message, subject=None, **kwargs):
    """Send an email reminder."""
    if not recipient_contact:
        return {"success": False, "error": _("No email address found for customer")}

    frappe.sendmail(
        recipients=[recipient_contact],
        subject=subject or _("Payment Reminder"),
        message=message,
        reference_doctype=kwargs.get("reference_doctype"),
        reference_name=kwargs.get("reference_name"),
    )
    return {"success": True}
