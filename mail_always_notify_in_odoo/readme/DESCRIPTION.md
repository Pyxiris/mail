Force notification of internal users via odoo inbox regardless of whether their email was in To:/Cc:

Odoo avoids notifying internal users about inbound messages if their email is already in the To or CC header. The assumption is that the user will be notified via their email inbox and should not be notified again of the same message in odoo.

However, some companies may desire to force their users to engage with odoo-related mail exclusively via odoo in order to avoid situations where the user replies directly to the customer alone via email without CC'ing the odoo alias, thereby creating a situation where communication is divided between odoo and email.
