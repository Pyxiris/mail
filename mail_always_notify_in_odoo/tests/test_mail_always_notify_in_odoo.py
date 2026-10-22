# Copyright 2026 Pyxiris
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

    def test_internal_user_is_forced_to_inbox(self):
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

    def test_portal_user_stays_on_email(self):
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
        self.assertFalse(self._notification(message, self.customer))
        self.assertNotSentEmail([self.internal_user.partner_id, self.customer])
        # Headers and partner_ids are restored after notify.
        self.assertIn(self.internal_user.email, message.incoming_email_to)
        self.assertIn(self.customer.email, message.incoming_email_to)
        self.assertNotIn(self.internal_user.partner_id, message.partner_ids)

    def test_incoming_cc_internal_user_gets_inbox_notification(self):
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
        self.assertNotIn(self.internal_user.partner_id, message.partner_ids)
        self.assertNotIn(self.internal_user.partner_id, message.partner_cc_ids)

    def test_incoming_to_and_cc_set_is_cc_correctly(self):
        cc_user = mail_new_test_user(
            self.env,
            login="always_notify_cc",
            groups="base.group_user",
            name="Always Notify Cc",
            email="always.notify.cc@example.com",
            notification_type="email",
        )
        message = self.document.message_post(
            body="To and Cc internals",
            message_type="email",
            subtype_xmlid="mail.mt_comment",
            author_id=self.customer.id,
            email_from=self.customer.email_formatted,
            incoming_email_to=self.internal_user.partner_id.email_formatted,
            incoming_email_cc=cc_user.partner_id.email_formatted,
        )
        recipients = {
            recipient["id"]: recipient
            for recipient in self.document._notify_get_recipients(message)
        }
        self.assertFalse(recipients[self.internal_user.partner_id.id]["is_cc"])
        self.assertTrue(recipients[cc_user.partner_id.id]["is_cc"])

    def test_comment_does_not_notify_address_from_incoming_headers(self):
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
