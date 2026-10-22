# Copyright 2026 Pyxiris
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Always Notify In Odoo",
    "summary": "Notify internal users in Odoo, including mail sent to them",
    "version": "20.0.1.0.0",
    "category": "Productivity/Discuss",
    "website": "https://github.com/OCA/mail",
    "author": "Pyxiris, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "development_status": "Beta",
    "depends": ["mail"],
    "data": [
        "data/force_internal_inbox.xml",
        "views/res_users_views.xml",
    ],
    "installable": True,
}
