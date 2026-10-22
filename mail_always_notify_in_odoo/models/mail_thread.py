# Copyright 2026 Pyxiris
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import Command, models
from odoo.tools.mail import email_normalize, email_split_and_format


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _notify_get_recipients(self, message, **kwargs):
        """Notify in odoo (inbox)internal users addressed on an incoming email.

        Core skips addresses on the incoming To/Cc, in order to avoid duplicate
        notifications.
        The point of this module is to notify internal users via odoo regardless.
        In order to acheive this we stash the original headers (incoming_email_to...)
        and the original partners called out on the message (partner_ids...).
        Then we add the internal partners found in the email headers as if they were
        mentioned or followers, and remove the addresses of the internal partners from
        the incoming email headers.
        This allows the super function to work as normal and build recipients_data
        without throwing out the internal partners in the email headers.
        Finally, we restore the original headers and partners to the message so as not
        to interfere with subsequent logic.
        """
        if message.message_type != "email":
            return super()._notify_get_recipients(message, **kwargs)

        partners_to, partners_cc = self._incoming_internal_partners(message)
        if not partners_to and not partners_cc:
            return super()._notify_get_recipients(message, **kwargs)

        message = message.sudo()
        saved_partners = message.partner_ids
        saved_partners_cc = message.partner_cc_ids
        saved_to = message.incoming_email_to
        saved_cc = message.incoming_email_cc
        partner_emails = {
            email
            for email in (partners_to | partners_cc).mapped("email_normalized")
            if email
        }
        message.write(
            {
                "partner_ids": [Command.link(partner.id) for partner in partners_to],
                "partner_cc_ids": [Command.link(partner.id) for partner in partners_cc],
                "incoming_email_to": self._emails_without(saved_to, partner_emails),
                "incoming_email_cc": self._emails_without(saved_cc, partner_emails),
            }
        )
        try:
            return super()._notify_get_recipients(message, **kwargs)
        finally:
            message.write(
                {
                    "partner_ids": [Command.set(saved_partners.ids)],
                    "partner_cc_ids": [Command.set(saved_partners_cc.ids)],
                    "incoming_email_to": saved_to,
                    "incoming_email_cc": saved_cc,
                }
            )

    def _incoming_internal_partners(self, message):
        """Internal users on the incoming To and Cc, as two recordsets."""
        message = message.sudo()
        partners_to = self._internal_partners_from_emails(message.incoming_email_to)
        partners_cc = self._internal_partners_from_emails(message.incoming_email_cc)
        # Prefer "To" when the same address appears in both "To" and "Cc".
        return partners_to, partners_cc - partners_to

    def _internal_partners_from_emails(self, value):
        emails = email_split_and_format(value or "")
        if not emails:
            return self.env["res.partner"]
        return self.env["mail.thread"]._partner_find_from_emails_single(
            emails,
            no_create=True,
            filter_found=lambda partner: any(
                not user.share for user in partner.user_ids
            ),
        )

    def _emails_without(self, header_value, emails_to_remove):
        """Rebuild a To/Cc header string without the given normalized addresses."""
        remaining = []
        for address in email_split_and_format(header_value or ""):
            if email_normalize(address) not in emails_to_remove:
                remaining.append(address)
        return ", ".join(remaining)
