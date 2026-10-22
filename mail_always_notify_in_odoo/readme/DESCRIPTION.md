Force internal users to receive document notifications in Odoo, and notify
them when an incoming email is addressed to them directly.

Incoming mail that Odoo attaches to a document normally skips anyone already
listed on To or Cc, because those people received the original message.
If that mail is diverted before it reaches their inbox, they never see it.
This module adds an in-Odoo notification for active internal users found on
those headers, and removes the preference that would send them an email
instead.
