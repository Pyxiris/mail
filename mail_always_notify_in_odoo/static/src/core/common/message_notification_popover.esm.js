import {MessageNotificationPopover} from "@mail/core/common/message_notification_popover";

import {patch} from "@web/core/utils/patch";

patch(MessageNotificationPopover.prototype, {
    /**
     * An incoming address means this person was on the original email.
     * The inbox notification is already implied for an internal user, so the
     * popover keeps the email row and skips that notification.
     */
    get recipientsData() {
        const recipients = super.recipientsData;
        const incomingEmails = new Set(
            recipients
                .filter((recipient) => !recipient.notification && recipient.email)
                .map((recipient) => recipient.email.trim().toLowerCase())
        );
        return recipients.filter((recipient) => {
            if (!recipient.notification || recipient.failure || !recipient.email) {
                return true;
            }
            return !incomingEmails.has(recipient.email.trim().toLowerCase());
        });
    },
});
