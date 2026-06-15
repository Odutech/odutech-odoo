/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosGlobalState } from "@point_of_sale/app/store/pos_global_state";

patch(PosGlobalState.prototype, {
    async _processData(loadedData) {
        await super._processData(loadedData);
        console.log("🔹 M-Pesa: syncing payment methods with is_mpesa flag");

        for (const method of loadedData['pos.payment.method']) {
            const posMethod = this.payment_methods.find(pm => pm.id === method.id);
            if (posMethod) {
                posMethod.is_mpesa = method.is_mpesa;
                console.log(`💡 ${posMethod.name}: is_mpesa=${posMethod.is_mpesa}`);
            }
        }
    },
});
