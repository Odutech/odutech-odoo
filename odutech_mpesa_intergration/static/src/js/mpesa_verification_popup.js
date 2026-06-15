/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";

/**
 * Displays an overlay popup for M-Pesa payment verification.
 * Designed for the Odoo POS frontend; uses vanilla DOM manipulation.
 */
export function showMpesaVerificationPopup({ paymentLine, order, orm, notification, onClose }) {
    console.log("🔵 Opening M-Pesa verification overlay");

    // Ensure POS content exists
    const posContent = document.querySelector(".pos-content, .o_pos_content, .o_content");
    if (!posContent) {
        console.error("❌ POS content container not found");
        if (onClose) onClose();
        return;
    }

    // Remove any existing M-Pesa overlay
    const existingOverlay = document.getElementById("mpesa-verification-overlay");
    if (existingOverlay) existingOverlay.remove();

    // Overlay HTML
    const overlayHtml = `
        <div id="mpesa-verification-overlay"
            style="position: fixed; inset: 0; background: rgba(0, 0, 0, 0.5);
                   display: flex; align-items: center; justify-content: center; z-index: 999998;">
            <div style="background: white; border-radius: 10px; padding: 16px; width: 360px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);">
                <h2 style="font-size: 18px; font-weight: 600; margin-bottom: 8px; color: #333;">
                    ${_t("Verify M-Pesa Payment")}
                </h2>
                <p style="font-size: 14px; margin-bottom: 12px; color: #555;">
                    ${_t("Enter customer's phone number (format: 2547XXXXXXXX)")}
                </p>
                <input id="mpesa-phone-input" type="text" placeholder="2547XXXXXXXX"
                       style="width: 100%; padding: 8px; border: 1px solid #ccc; border-radius: 6px; margin-bottom: 12px;"/>
                <div style="display: flex; justify-content: flex-end; gap: 8px;">
                    <button id="mpesa-cancel"
                            style="padding: 6px 12px; background: #e0e0e0; border: none; border-radius: 6px; cursor: pointer;">
                        ${_t("Cancel")}
                    </button>
                    <button id="mpesa-verify"
                            style="padding: 6px 12px; background: #16a34a; color: white; border: none; border-radius: 6px; cursor: pointer;">
                        ${_t("Verify")}
                    </button>
                </div>
            </div>
        </div>
    `;

    // Insert into DOM
    posContent.insertAdjacentHTML("beforeend", overlayHtml);
    console.log("🟢 M-Pesa verification overlay added to DOM.");

    // Fetch DOM nodes
    const overlay = document.getElementById("mpesa-verification-overlay");
    const phoneInput = document.getElementById("mpesa-phone-input");
    const btnCancel = document.getElementById("mpesa-cancel");
    const btnVerify = document.getElementById("mpesa-verify");

    // Close and cleanup function
    const closePopup = () => {
        overlay?.remove();
        if (onClose) onClose();
    };

    // Cancel button logic
    btnCancel.onclick = () => {
        console.warn("❌ M-Pesa popup manually closed; removing payment line.");
        if (paymentLine && order) {
            order.remove_paymentline(paymentLine);
        }
        closePopup();
    };

    // Verify button logic
    btnVerify.onclick = async () => {
        const phone = phoneInput.value.trim();
        if (!/^254\d{9}$/.test(phone)) {
            notification.add(_t("Invalid phone number. Use 254XXXXXXXX format."), { type: "warning" });
            return;
        }

        // Disable button during processing
        btnVerify.disabled = true;
        btnVerify.textContent = _t("Verifying...");

        try {
            const amount = order.get_total_with_tax();
            console.log(`🔍 Verifying M-Pesa payment for phone: ${phone}, amount: ${amount}`);
            const response = await orm.call("pos.order", "check_mpesa_payment", [phone, amount]);

            if (response?.status === "done") {
                notification.add(_t("M-Pesa payment verified!"), { type: "success" });
                if (paymentLine) {
                    paymentLine.set_note(`M-Pesa Phone: ${phone}`);
                    paymentLine.mpesa_phone = phone;
                }
                closePopup();
            } else {
                notification.add(
                    _t(response?.message || "Payment not received yet, please retry."),
                    { type: "warning" }
                );
            }
        } catch (err) {
            console.error("🚨 RPC Error:", err);
            notification.add(_t("Verification failed, please try again."), { type: "danger" });
        } finally {
            btnVerify.disabled = false;
            btnVerify.textContent = _t("Verify");
        }
    };

    // Focus on the input for quicker user experience
    phoneInput.focus();
}
