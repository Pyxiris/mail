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
        if not self.env.context.get("mail_always_notify_in_odoo_forcing"):
            users._compute_notification_type()
        return users

    def write(self, vals):
        res = super().write(vals)
        # Writing notification_type marks the field as user-set, so the group
        # change made by its inverse does not recompute it.
        if (
            not self.env.context.get("mail_always_notify_in_odoo_forcing")
            and "notification_type" in vals
        ):
            self._compute_notification_type()
        return res

    @api.depends("share", "all_group_ids")
    def _compute_notification_type(self):
        """Keep every internal user in the in-Odoo notification group.

        The base compute reads ``group_ids`` with a SQL query, so the group has
        to be written and flushed before ``super()``.
        """
        if not self.env.context.get("mail_always_notify_in_odoo_forcing"):
            self._link_missing_inbox_notification_group()
        return super()._compute_notification_type()

    def _link_missing_inbox_notification_group(self):
        if not self:
            return
        inbox_group = self.env.ref("mail.group_mail_notification_type_inbox")
        missing = self.browse()
        for user in self:
            if not user.share and inbox_group not in user.group_ids:
                missing += user
        if not missing:
            return
        # The base compute writes this same group for portal users.
        missing.with_context(
            mail_always_notify_in_odoo_forcing=True,
            no_group_change_log=NO_GROUP_CHANGE_LOG,
        ).sudo().write(  # pylint: disable=no-write-in-compute
            {"group_ids": [Command.link(inbox_group.id)]}
        )

    @api.model
    def _force_internal_inbox_notifications(self):
        """Apply the inbox group to internal users already in the database."""
        users = self.search([("share", "=", False)])
        users._compute_notification_type()
