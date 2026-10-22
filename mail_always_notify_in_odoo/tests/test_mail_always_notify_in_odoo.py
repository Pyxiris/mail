# Copyright 2026 Liam Noonan
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import Command
from odoo.tests import tagged

from odoo.addons.mail.tests.common import MailCommon, mail_new_test_user


@tagged("post_install", "-at_install")
class TestMailAlwaysNotifyInOdoo(MailCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.inbox_group = cls.env.ref("mail.group_mail_notification_type_inbox")
        cls.internal_user = mail_new_test_user(
            cls.env,
            login="always_notify_internal",
            groups="base.group_user",
            name="Always Notify Internal",
            email="always.notify.internal@example.com",
            notification_type="email",
        )
        cls.customer = cls.env["res.partner"].create(
            {
                "name": "Always Notify Customer",
                "email": "always.notify.customer@example.com",
            }
        )
        cls.document = cls.env["res.partner"].create(
            {"name": "Always Notify Document", "email": "always.notify.doc@example.com"}
        )

    def _notification(self, message, partner):
        return self.env["mail.notification"].search(
            [
                ("mail_message_id", "=", message.id),
                ("res_partner_id", "=", partner.id),
            ]
        )

    def _recipients_by_id(self, message):
        return {
            recipient["id"]: recipient
            for recipient in self.document._notify_get_recipients(message)
            if recipient.get("id")
        }

    def test_internal_user_is_forced_to_inbox(self):
        """Create/write cannot leave an internal user on email notifications."""
        self.assertEqual(self.internal_user.notification_type, "inbox")
        self.assertIn(self.inbox_group, self.internal_user.group_ids)
        self.assertIn(self.env.ref("base.group_user"), self.internal_user.all_group_ids)

        self.internal_user.write({"notification_type": "email"})
        self.assertEqual(self.internal_user.notification_type, "inbox")
        self.assertIn(self.inbox_group, self.internal_user.group_ids)

        self.internal_user.with_user(self.internal_user).write(
            {"notification_type": "email"}
        )
        self.assertEqual(self.internal_user.notification_type, "inbox")

        # Unlinking the inbox group alone is corrected on the next compute.
        self.internal_user.write({"group_ids": [Command.unlink(self.inbox_group.id)]})
        self.assertEqual(self.internal_user.notification_type, "inbox")
        self.assertIn(self.inbox_group, self.internal_user.group_ids)

    def test_portal_user_stays_on_email(self):
        """Portal users are left on email; the force only targets internals."""
        portal_user = mail_new_test_user(
            self.env,
            login="always_notify_portal",
            groups="base.group_portal",
            name="Always Notify Portal",
            email="always.notify.portal@example.com",
            notification_type="email",
        )
        self.assertEqual(portal_user.notification_type, "email")
        self.assertNotIn(self.inbox_group, portal_user.group_ids)

    def test_internal_user_converted_to_portal_uses_email(self):
        """Once share=True, core can move the user off inbox and we do not
        force the group back.
        """
        user = mail_new_test_user(
            self.env,
            login="always_notify_convert",
            groups="base.group_user",
            name="Always Notify Convert",
            email="always.notify.convert@example.com",
            notification_type="email",
        )
        self.assertEqual(user.notification_type, "inbox")
        user.write(
            {
                "group_ids": [
                    Command.unlink(self.env.ref("base.group_user").id),
                    Command.link(self.env.ref("base.group_portal").id),
                ]
            }
        )
        self.assertTrue(user._is_portal())
        self.assertEqual(user.notification_type, "email")
        self.assertNotIn(self.inbox_group, user.group_ids)

    def test_incoming_to_internal_user_gets_inbox_notification(self):
        """Internal To addresses get an inbox notification; headers and
        partner_ids are restored after notify so the message still looks like
        a gateway email.
        """
        self.document.message_subscribe(partner_ids=self.customer.ids)
        with self.mock_mail_gateway():
            message = self.document.message_post(
                body="Hello from the customer",
                message_type="email",
                subtype_xmlid="mail.mt_comment",
                author_id=self.customer.id,
                email_from=self.customer.email_formatted,
                incoming_email_to=(
                    f"{self.internal_user.partner_id.email_formatted}, "
                    f"{self.customer.email_formatted}"
                ),
            )
        internal_notif = self._notification(message, self.internal_user.partner_id)
        self.assertEqual(len(internal_notif), 1)
        self.assertEqual(internal_notif.notification_type, "inbox")
        # Customer is already on incoming To, so core skips notifying them.
        self.assertFalse(self._notification(message, self.customer))
        self.assertNotSentEmail([self.internal_user.partner_id, self.customer])
        self.assertIn(self.internal_user.email, message.incoming_email_to)
        self.assertIn(self.customer.email, message.incoming_email_to)
        self.assertNotIn(self.internal_user.partner_id, message.partner_ids)
        self.assertNotIn(self.internal_user.partner_id, message.partner_cc_ids)

    def test_incoming_cc_internal_user_gets_inbox_notification(self):
        """Internal Cc addresses get an inbox notification; Cc header and
        partner links are restored after notify.
        """
        with self.mock_mail_gateway():
            message = self.document.message_post(
                body="Copied to an internal user",
                message_type="email",
                subtype_xmlid="mail.mt_comment",
                author_id=self.customer.id,
                email_from=self.customer.email_formatted,
                incoming_email_cc=self.internal_user.partner_id.email_formatted,
            )
        internal_notif = self._notification(message, self.internal_user.partner_id)
        self.assertEqual(len(internal_notif), 1)
        self.assertEqual(internal_notif.notification_type, "inbox")
        self.assertNotSentEmail([self.internal_user.partner_id])
        self.assertIn(self.internal_user.email, message.incoming_email_cc)
        self.assertNotIn(self.internal_user.partner_id, message.partner_ids)
        self.assertNotIn(self.internal_user.partner_id, message.partner_cc_ids)

    def test_incoming_to_and_cc_set_is_cc_correctly(self):
        """Temporary partner_cc_ids links make Cc recipients is_cc during
        notify; To wins when the same address is listed on both headers.
        """
        cc_user = mail_new_test_user(
            self.env,
            login="always_notify_cc",
            groups="base.group_user",
            name="Always Notify Cc",
            email="always.notify.cc@example.com",
            notification_type="email",
        )
        both_user = mail_new_test_user(
            self.env,
            login="always_notify_both",
            groups="base.group_user",
            name="Always Notify Both",
            email="always.notify.both@example.com",
            notification_type="email",
        )
        with self.mock_mail_gateway():
            message = self.document.message_post(
                body="To and Cc internals",
                message_type="email",
                subtype_xmlid="mail.mt_comment",
                author_id=self.customer.id,
                email_from=self.customer.email_formatted,
                incoming_email_to=(
                    f"{self.internal_user.partner_id.email_formatted}, "
                    f"{both_user.partner_id.email_formatted}"
                ),
                incoming_email_cc=(
                    f"{cc_user.partner_id.email_formatted}, "
                    f"{both_user.partner_id.email_formatted}"
                ),
            )

        for partner in (
            self.internal_user.partner_id,
            cc_user.partner_id,
            both_user.partner_id,
        ):
            notif = self._notification(message, partner)
            self.assertEqual(len(notif), 1)
            self.assertEqual(notif.notification_type, "inbox")

        recipients = self._recipients_by_id(message)
        self.assertFalse(recipients[self.internal_user.partner_id.id]["is_cc"])
        self.assertTrue(recipients[cc_user.partner_id.id]["is_cc"])
        self.assertFalse(recipients[both_user.partner_id.id]["is_cc"])

        self.assertIn(self.internal_user.email, message.incoming_email_to)
        self.assertIn(both_user.email, message.incoming_email_to)
        self.assertIn(cc_user.email, message.incoming_email_cc)
        self.assertIn(both_user.email, message.incoming_email_cc)
        self.assertFalse(
            message.partner_ids
            & (
                self.internal_user.partner_id
                | cc_user.partner_id
                | both_user.partner_id
            )
        )
        self.assertFalse(
            message.partner_cc_ids
            & (
                self.internal_user.partner_id
                | cc_user.partner_id
                | both_user.partner_id
            )
        )

    def test_comment_does_not_notify_address_from_incoming_headers(self):
        """Only message_type=email triggers the incoming To/Cc inbox path."""
        with self.mock_mail_gateway():
            message = self.document.message_post(
                body="A normal comment",
                message_type="comment",
                subtype_xmlid="mail.mt_comment",
                author_id=self.customer.id,
                email_from=self.customer.email_formatted,
                incoming_email_to=self.internal_user.partner_id.email_formatted,
            )
        self.assertFalse(self._notification(message, self.internal_user.partner_id))
