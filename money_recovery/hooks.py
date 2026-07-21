from __future__ import unicode_literals
from . import __version__ as app_version

app_name = "money_recovery"
app_title = "Money Recovery"
app_publisher = "Bizaxl"
app_description = "Delayed Payment / Receivables Recovery Tooling — Active multi-channel collections workflow for ERPNext"
app_icon = "octicon octicon-dollar"
app_color = "green"
app_email = "support@bizaxl.com"
app_license = "MIT"

# Fixtures
fixtures = [
    {"dt": "Custom Field", "filters": [["dt", "in", ["Dunning"]]]},
    {"dt": "Workspace"},
]

# Scheduled Tasks
scheduler_events = {
    "daily": [
        "money_recovery.tasks.run_collections_cadence",
        "money_recovery.tasks.check_broken_promises",
    ],
}

# DocType Class Overrides
doctype_js = {}
doctype_list_js = {}
doctype_tree_js = {}

# Document Events
doc_events = {}

# User Data Protection
user_data_fields = []

# Website
website_context = {}

# Boot Session
boot_session = []
