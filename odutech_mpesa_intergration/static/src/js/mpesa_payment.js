/** @odoo-module **/

import publicWidget from '@web/legacy/js/public/public_widget';

publicWidget.registry.PaymentForm.include({

    /**
     * Force direct flow for M-Pesa
     */
    _getPaymentFlow(radio) {
        const { providerCode } = radio.dataset;
        if (providerCode === 'mpesa') {
            console.log('M-Pesa: Forcing direct flow');
            return 'direct';
        }
        return this._super(...arguments);
    },

    /**
     * Redirect user to M-Pesa phone entry page
     */
    async _initiatePaymentFlow(providerCode, paymentOptionId, paymentMethodCode, flow) {
        if (providerCode === 'mpesa') {
            console.log('M-Pesa: Redirecting to phone entry page');

            // Try to find the sale.order id from any DOM element rendered by Odoo
            let orderId = null;

            // 1️⃣ Try the element that holds amount_total_summary (it has data-oe-id)
            const orderDataEl = document.querySelector('[data-oe-model="sale.order"][data-oe-id]');
            if (orderDataEl) {
                orderId = orderDataEl.dataset.oeId;
            }

            // 2️⃣ Fallback: try form dataset or hidden inputs
            if (!orderId) {
                const form = document.querySelector('#o_payment_form');
                if (form?.dataset?.orderId) {
                    orderId = form.dataset.orderId;
                } else {
                    const input =
                        form?.querySelector('input[name="order_id"]') ||
                        form?.querySelector('input[name="o_payment_reference"]') ||
                        form?.querySelector('input[name="reference"]');
                    if (input?.value) {
                        const match = input.value.match(/\d+/);
                        orderId = match ? match[0] : input.value;
                    }
                }
            }

            // 3️⃣ If still not found, abort
            if (!orderId) {
                console.error('M-Pesa: Could not extract order ID.');
                alert('Error: Could not determine your order. Please refresh and try again.');
                return;
            }

            // Redirect to controller for phone number input
            const redirectUrl = `/payment/mpesa/start?order_id=${orderId}`;
            console.log('M-Pesa: Redirecting to', redirectUrl);
            window.location.href = redirectUrl;

            // Stop Odoo spinner
            return;
        }

        return this._super(providerCode, paymentOptionId, paymentMethodCode, flow);
    },
});

console.log('M-Pesa payment form override loaded ✅');
