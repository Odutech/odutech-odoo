/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { showMpesaVerificationPopup } from "@odutech_mpesa_intergration/js/mpesa_verification_popup";

console.log("✅ M-Pesa POS patch with overlay verification popup loaded");

patch(PaymentScreen.prototype, {
    setup() {
        super.setup();
        this.pos = usePos();
        this.notification = useService("notification");
        this.dialog = useService("dialog");
        this.orm = useService("orm");
    },



async addNewPaymentLine(paymentMethod) {
        const result = await super.addNewPaymentLine(paymentMethod);
        console.log("🟢 addNewPaymentLine fired for:", paymentMethod.name);

        if (paymentMethod && paymentMethod.name === "M-pesa") {
            const order = this.pos.get_order();
            const paymentLine = order?.selected_paymentline;

            // Use popup service correctly
            showMpesaVerificationPopup({
                paymentLine,
                order,
                orm: this.orm,
                notification: this.notification,
                onClose: () => {
                    console.warn("❌ Popup closed callback triggered");
                },
            });
        }
        return result; // return result to follow PoS flow
    },


// NOTE: showMpesaVerificationPopup must be imported at the top of this file.
});
