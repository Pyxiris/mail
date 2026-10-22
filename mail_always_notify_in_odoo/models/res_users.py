# Copyright 2026 Pyxiris
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import Command, api, models

from odoo.addons.base.models.res_users import NO_GROUP_CHANGE_LOG


class ResUsers(models.Model):
    _inherit = "res.users"

    @api.model_create_multi
    def create(self, vals_list):
        users = super().create(vals_list)
        # An explicit notification_type in the create values is stored as-is
        # and does not run the compute.
        if not self.env.context.get("forcing_notification_type_inbox"):
            users._compute_notification_type()
        return users

    def write(self, vals):
        res = super().write(vals)
        # Writing notification_type marks the field as user-set, so the group
        # change made by its inverse does not recompute it.
        if (
            not self.env.context.get("forcing_notification_type_inbox")
            and "notification_type" in vals
        ):
            self._compute_notification_type()
        return res

    @api.depends("share", "all_group_ids")
    def _compute_notification_type(self):
        if not self.env.context.get("forcing_notification_type_inbox"):
            self._force_notification_type_inbox()
        return super()._compute_notification_type()

    def _force_notification_type_inbox(self):
        """Link the inbox group on internal users who are missing it."""
        inbox_group_id = self.env["ir.model.data"]._xmlid_to_res_id(
            "mail.group_mail_notification_type_inbox"
        )
        missing = self.filtered(
            lambda user: not user.share and inbox_group_id not in user.group_ids.ids
        )
        if not inbox_group_id or not missing:
            return
        missing.with_context(
            forcing_notification_type_inbox=True,
            no_group_change_log=NO_GROUP_CHANGE_LOG,
        ).sudo().write({"group_ids": [Command.link(inbox_group_id)]})

    @api.model
    def _initial_force_notification_type_inbox(self):
        """Recompute all users on install"""
        users = self.search([("share", "=", False)])
        users._compute_notification_type()
