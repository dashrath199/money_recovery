from __future__ import unicode_literals
from frappe import _

def get_data():
    return [
        {
            "module_name": "Money Recovery",
            "color": "green",
            "icon": "octicon octicon-dollar",
            "type": "module",
            "label": _("Money Recovery"),
        }
    ]
