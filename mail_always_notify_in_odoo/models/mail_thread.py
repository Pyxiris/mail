# Copyright 2026 Pyxiris
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models
from odoo.tools.mail import email_normalize_all, email_split_and_format


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _notify_get_recipients(self, message, **kwargs):
        """Notify internal users addressed on an incoming email.

        Core skips addresses already present on the incoming message, and the
        gateway writes those partners onto the message only after post. Users
        whose mail is diverted before it reaches their inbox still need the
        in-Odoo notification.
        """
        skip_existing = kwargs.get("skip_existing")
        recipients = super()._notify_get_recipients(message, **kwargs)
        if (
            kwargs.get("notify_skip_followers")
            or message.message_type != "email"
            or len(self) != 1
        ):
            return recipients
        extra = self._notify_internal_direct_recipients(message, recipients, **kwargs)
        if skip_existing and extra and message.ids:
            existing = (
                self.env["mail.notification"]
                .sudo()
                .search(
                    [
                        ("res_partner_id", "in", [item["id"] for item in extra]),
                        ("mail_message_id", "in", message.ids),
                    ]
                )
            )
            skip_ids = set(existing.res_partner_id.ids)
            extra = [item for item in extra if item["id"] not in skip_ids]
        return recipients + extra

    def _notify_internal_direct_recipients(self, message, recipients, **kwargs):
        """Return recipient dicts for internal users on the incoming To/Cc."""
        self.ensure_one()
        msg_sudo = message.sudo()
        incoming_to = msg_sudo.incoming_email_to or ""
        incoming_cc = msg_sudo.incoming_email_cc or ""
        if not incoming_to and not incoming_cc:
            return []
        incoming_emails = email_split_and_format(f"{incoming_to}, {incoming_cc}")
        if not incoming_emails:
            return []
        partners = self._partner_find_from_emails_single(
            incoming_emails,
            no_create=True,
            filter_found=self._is_notified_internal_partner,
        )
        notified_partner_ids = (msg_sudo.partner_ids | msg_sudo.partner_cc_ids).ids
        skip_author_id = self._notify_skip_author_id(
            message, notified_partner_ids, **kwargs
        )
        already = {item["id"] for item in recipients if item.get("id")}
        missing = self.env["res.partner"]
        for partner in partners:
            if (
                partner.id
                and partner.id not in already
                and partner.id != skip_author_id
            ):
                missing |= partner
        if not missing:
            return []
        recipient_data = self.env["mail.followers"]._get_recipient_data(
            self, "email", msg_sudo.subtype_id.id, missing.ids
        )[self.id]
        cc_normalized = set(email_normalize_all(incoming_cc))
        extra = []
        missing_ids = set(missing.ids)
        for partner_id, pdata in recipient_data.items():
            if partner_id not in missing_ids:
                continue
            if not pdata["active"] or pdata["type"] != "user":
                continue
            pdata = dict(pdata)
            pdata["is_cc"] = pdata.get("email_normalized") in cc_normalized
            extra.append(pdata)
        return extra

    def _notify_skip_author_id(self, message, notified_partner_ids, **kwargs):
        """Match the author exclusion used by ``_notify_get_recipients``."""
        if kwargs.get("notify_author") or self.env.context.get("mail_notify_author"):
            return False
        notify_author_mention = kwargs.get(
            "notify_author_mention"
        ) or self.env.context.get("mail_notify_author_mention")
        skip_author_id = self._message_compute_real_author(message.author_id.id).id
        if notify_author_mention and skip_author_id in notified_partner_ids:
            return False
        return skip_author_id

    def _is_notified_internal_partner(self, partner):
        if not partner.active or partner.partner_share:
            return False
        return any(user.active and not user.share for user in partner.user_ids)
