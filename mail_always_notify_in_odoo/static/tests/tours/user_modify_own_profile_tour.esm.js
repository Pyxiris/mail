import "@mail/../tests/tours/user_modify_own_profile_tour";
import {patch} from "@web/core/utils/patch";
import {registry} from "@web/core/registry";

const TOUR = "mail/static/tests/tours/user_modify_own_profile_tour.js";

/**
 * Core's profile tour clicks the notification_type radio to dirty the form.
 * This module hides that field and forces inbox, so replace that step with a
 * normal preference edit.
 */
patch(registry.category("web_tour.tours").get(TOUR), {
    steps() {
        const steps = super.steps();
        const index = steps.findIndex((step) =>
            step.trigger?.includes('div[name="notification_type"]')
        );
        if (index === -1) {
            return steps;
        }
        steps.splice(index, 1, {
            content:
                "Update signature (notification type is hidden and forced to inbox)",
            trigger: '.modal .o_field_html[name="signature"] .odoo-editor-editable',
            run: "editor Tour signature",
        });
        return steps;
    },
});
