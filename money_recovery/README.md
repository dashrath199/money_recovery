# Money Recovery — ERPNext v15 Custom App

**Delayed Payment / Receivables Recovery Tooling** — Active multi-channel collections workflow built on top of ERPNext's native `Dunning` DocType.

## What this solves

MSMEs have receivables sitting unpaid for 90–120+ days with no systematic follow-up — no escalation ladder, no WhatsApp/SMS reminders, no visibility into which debtor is chronically late vs. genuinely disputing an invoice. This app provides a structured, automated collections workflow.

## Installation

```bash
cd ~/frappe-bench
bench get-app https://github.com/bizaxl/money_recovery
bench --site yoursite.local install-app money_recovery
```

## Architecture

### Built on native `Dunning`, not a replacement

ERPNext v15's Dunning DocType already holds a table of overdue payments. This app extends it via Custom Fields (not monkey-patching) and adds the workflow layer on top.

### Extended Dunning Fields

| Field | Type | Purpose |
|---|---|---|
| `escalation_stage` | Select | Reminder 1 / Reminder 2 / Final Notice / Legal Referral |
| `dispute_flag` | Check | Marks disputed invoices (excluded from automated reminders) |
| `dispute_reason` | Small Text | Reason for dispute |
| `last_contact_channel` | Select | WhatsApp / SMS / Email / Call |
| `promised_payment_date` | Date | Captured during a call — distinguishes "will pay Friday" from silence |
| `last_reminder_sent_on` | Datetime | Timestamp of the most recent automated reminder |

### DocTypes

#### Collections Cadence Rule
Maps a range of days-overdue to an automated action:

- `days_overdue_from` / `days_overdue_to` — Int range
- `action` — Select: Send WhatsApp Reminder / Send SMS / Send Email Reminder / Flag for Manual Call / Escalate to Legal
- `message_template` — Link → Message Template

#### Message Template
Stores templated messages with language variants:

- `channel` — WhatsApp / SMS / Email
- `language` — Regional language support (English, Hindi, Tamil, Telugu, etc.)
- `subject` — Email subject line
- `message_body` — Jinja-templated body with placeholders

### Scheduled Jobs

| Job | Frequency | Description |
|---|---|---|
| `run_collections_cadence` | Daily | Matches overdue invoices against cadence rules and triggers actions |
| `check_broken_promises` | Daily | Flags Dunning records where `promised_payment_date` has passed |

### API Endpoints

| Method | Description |
|---|---|
| `send_payment_reminder(dunning_name, channel, template_name)` | Send a payment reminder via WhatsApp / SMS / Email |
| `get_rendered_template(template_name, channel, language, context)` | Render a message template with Jinja context |

### Reports

1. **Aging Bucket Summary** — Standard 0-30 / 31-60 / 61-90 / 90+ buckets with stacked bar chart
2. **Promise-to-Pay Reliability** — Compares promised dates against actual payment dates, produces a reliability % per customer (de facto credit score)
3. **Collections Cadence Effectiveness** — % of Dunning records resolved after each escalation stage
4. **Dispute Register** — Separate view for flagged disputes (excluded from standard aging)

### Workspace: "Receivables & Collections"

Desk workspace with:
- Shortcuts to open Dunning records, overdue Sales Invoices, Cadence Rules, Message Templates
- Number cards: Total Overdue, 90+ Days Overdue, Disputed Amount
- Charts: Aging Bucket Summary (stacked bar), Collections Cadence Effectiveness (stacked bar)

### Roles & Permissions

| Role | Access |
|---|---|
| **Collections Manager** | Full access to all DocTypes including escalation actions |
| **Sales Rep** | Read-only on own customers' Dunning records; can update `last_contact_channel` and `promised_payment_date` after a call; **cannot** change `escalation_stage` |

## Integration Points

### WhatsApp / SMS Gateways

The `api.py` module provides stub handlers for:
- **WhatsApp Business API** — (Gupshup, Twilio, etc.)
- **SMS Gateways** — (MSG91, Twilio, etc.)

Replace the TODO stubs with your actual provider API calls and add your API keys to `site_config.json`.

### Email

Uses ERPNext's built-in `frappe.sendmail()` — configure your email account in ERPNext as usual.

## Known Gaps

- This tooling helps you **chase** payment; it does nothing for the underlying credit gap (factoring/invoice discounting against receivables) — that's a separate fintech product.
- Legal escalation should link out to an actual recovery/legal service via a custom integration.

## Development

```bash
bench --site yoursite.local set-config developer_mode 1
```

### Adding Custom Fields

Custom fields are stored as fixtures in `money_recovery/fixtures/custom_fields.json`. After editing:

```bash
bench --site yoursite.local export-fixtures
```

## License

MIT
