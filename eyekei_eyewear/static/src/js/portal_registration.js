/** @odoo-module **/

import { Component, onMounted, useState, useRef, xml } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { browser } from "@web/core/browser/browser";

// Use native fetch instead of jsonrpc from rpc_service (not in frontend bundle)
class PortalPatientRegistration extends Component {
    static template = xml`
        <div>
            <!-- Your full form markup here, with OWL bindings -->
            <form t-ref="registrationForm" t-on-submit.prevent="onSubmit" class="needs-validation" novalidate="novalidate">
                <!-- CSRF Token - CRITICAL for Odoo 17 -->
                <input type="hidden" name="csrf_token" t-att-value="csrf_token"/>
                <input type="hidden" name="branch_code" t-att-value="branch_code" />

                <!-- Personal Information -->
                <h5 class="text-muted mb-3 mt-4">Personal Information</h5>
                <div class="row g-3">
                    <div class="col-12">
                        <label class="form-label">Full Name <span
                                class="text-danger">*</span></label>
                        <div class="input-group has-validation">
                            <span class="input-group-text"><i class="fa fa-user"></i></span>
                            <input type="text" class="form-control" name="name"
                                placeholder="Enter your full name" required="required" />
                            <div class="invalid-feedback">Full name is required</div>
                        </div>
                    </div>

                    <div class="col-md-6">
                        <label class="form-label">Date of Birth <span
                                class="text-danger">*</span></label>
                        <div class="input-group has-validation">
                            <span class="input-group-text"><i
                                    class="fa fa-calendar"></i></span>
                            <input type="date" class="form-control" name="dob"
                                required="required" />
                            <div class="invalid-feedback">Valid date of birth is required
                            </div>
                        </div>
                    </div>

                    <div class="col-md-6">
                        <label class="form-label">Gender <span
                                class="text-danger">*</span></label>
                        <div class="input-group has-validation">
                            <span class="input-group-text"><i
                                    class="fa fa-venus-mars"></i></span>
                            <select class="form-select" name="gender" required="required">
                                <option value="">Select Gender</option>
                                <option value="male">Male</option>
                                <option value="female">Female</option>
                                <option value="other">Other</option>
                                <option value="prefer_not">Prefer not to say</option>
                            </select>
                            <div class="invalid-feedback">Please select gender</div>
                        </div>
                    </div>

                    <div class="col-md-6">
                        <label class="form-label">ID Number <span
                                class="text-danger">*</span></label>
                        <div class="input-group has-validation">
                            <span class="input-group-text"><i
                                    class="fa fa-id-card"></i></span>
                            <input type="text" class="form-control" name="id_number"
                                placeholder="e.g., 12345678" required="required" />
                            <div class="invalid-feedback">ID number is required</div>
                        </div>
                    </div>

                    <div class="col-md-6">
                        <label class="form-label">Location <span
                                class="text-danger">*</span></label>
                        <div class="input-group has-validation">
                            <span class="input-group-text"><i
                                    class="fa fa-map-marker"></i></span>
                            <input type="text" class="form-control" name="place"
                                placeholder="e.g., Nairobi" required="required" />
                            <div class="invalid-feedback">Location is required</div>
                        </div>
                    </div>
                </div>

                <!-- Contact Information -->
                <h5 class="text-muted mb-3 mt-4">Contact Information</h5>
                <div class="row g-3">
                    <div class="col-md-6">
                        <label class="form-label">Phone Number <span
                                class="text-danger">*</span></label>
                        <div class="input-group has-validation">
                            <span class="input-group-text"><i
                                    class="fa fa-phone"></i></span>
                            <input type="tel" class="form-control" name="phone"
                                id="phone-input" placeholder="+254712345678"
                                required="required" pattern="^\+?[\d\s-]{10,15}$" />
                            <div class="invalid-feedback">Valid phone number required (e.g.,
                                +254712345678)</div>
                        </div>
                        <div class="form-text">Format: +254XXXXXXXXX</div>
                    </div>

                    <div class="col-md-6">
                        <label class="form-label">Email Address</label>
                        <div class="input-group">
                            <span class="input-group-text"><i
                                    class="fa fa-envelope"></i></span>
                            <input type="email" class="form-control" name="email"
                                placeholder="patient@example.com" />
                            <div class="invalid-feedback">Enter valid email address</div>
                        </div>
                    </div>
                </div>

                <!-- Insurance Information -->
                <h5 class="text-muted mb-3 mt-4">Insurance Information</h5>
                <div class="form-check mb-3">
                    <input class="form-check-input" type="checkbox" name="has_insurance"
                        id="has-insurance" />
                    <label class="form-check-label" for="has-insurance">
                        I have insurance coverage
                    </label>
                </div>

                <div id="insurance-fields" class="d-none">
                    <div class="row g-3">
                        <div class="col-md-6">
                            <label class="form-label">Insurance Provider</label>
                            <select class="form-select" name="insurance_provider">
                                <option value="">Select Provider</option>
                                <option value="JUB">Jubilee Insurance</option>
                                <option value="AAR">AAR Insurance</option>
                                <option value="MAD">Madison Insurance</option>
                                <option value="UAP">UAP Old Mutual</option>
                                <option value="CIC">CIC Insurance</option>
                                <option value="HER">Heritage Insurance</option>
                                <option value="SHIF">Social Health Insurance Fund</option>
                                <option value="other">Other</option>
                            </select>
                        </div>

                        <div class="col-md-6">
                            <label class="form-label">Member Number</label>
                            <input type="text" class="form-control" name="member_number"
                                placeholder="e.g., JUB123456" />
                        </div>

                        <div class="col-12">
                            <label class="form-label">Corporate/Company Name</label>
                            <input type="text" class="form-control" name="corporate_name"
                                placeholder="e.g., ABC Corporation Ltd" />
                        </div>
                    </div>
                </div>

                <!-- Consent -->
                <div class="form-check mt-4 mb-4">
                    <input class="form-check-input" type="checkbox" name="consent"
                        id="consent-check" required="required" />
                    <label class="form-check-label" for="consent-check">
                        I consent to the collection and processing of my personal data
                        for medical purposes in accordance with the Data Protection Act.
                    </label>
                    <div class="invalid-feedback">You must consent to proceed</div>
                </div>

                <!-- Submit Buttons -->
                <div class="d-grid gap-2 d-md-flex justify-content-md-end mt-4">
                    <button type="reset" class="btn btn-outline-secondary px-4">
                        <i class="fa fa-undo"></i> Clear
                    </button>
                    <button type="submit" t-ref="submitBtn" class="btn btn-primary px-5" id="submit-btn">
                        <i class="fa fa-check"></i> Complete Registration
                    </button>
                </div>
            </form>

            <!-- duplicate warning, alerts, etc. with t-if="state.duplicate" -->
        </div>
    `;

    setup() {
        console.log("[EYEKEI] PortalPatientRegistration class instantiated");
        this.formRef = useRef("registrationForm");
        this.submitBtnRef = useRef("submitBtn");
        this.state = useState({
            loading: false,
            duplicate: null,
        });
        // this.branchCode = this.props.branch_code;

        this.csrfToken = document.querySelector('input[name="csrf_token"]')?.value;

        onMounted(() => {
            console.log("[EYEKEI][OWL] Patient registration mounted successfully");
            console.log("[EYEKEI] Component mounted");

            // Extract branch_code from current URL
            const path = window.location.pathname;
            console.log("[DEBUG] Current pathname:", path);

            // Split and take the last non-empty segment
            const parts = path.split('/').filter(Boolean); // remove empty strings
            if (parts.length > 0) {
                const lastPart = parts[parts.length - 1].toUpperCase().trim();
                this.branchCode = lastPart;
                console.log("[EYEKEI] Extracted branch_code from URL:", this.branchCode);
            } else {
                console.warn("[WARNING] Could not extract branch_code from URL");
            }
            this.bindEvents();
        });
    }

    bindEvents() {
        console.log("[EYEKEI][OWL] Binding events");
        // Bind phone input
        const phoneInput = document.getElementById('phone-input');
        if (phoneInput) {
            phoneInput.addEventListener('input', (ev) => this.onPhoneInput(ev));
        }

        // Bind insurance toggle
        const insuranceCheck = document.getElementById('has-insurance');
        if (insuranceCheck) {
            insuranceCheck.addEventListener('change', (ev) => this.toggleInsurance(ev));
        }

        // === CRITICAL: FORM SUBMIT (this was missing) ===
        const form = document.getElementById('patient-registration-form');
        if (form) {
            form.addEventListener('submit', (ev) => this.onSubmit(ev));
            console.log("[EYEKEI][OWL] Submit listener attached successfully");
        } else {
            console.error("[EYEKEI][OWL] Form not found! Check ID");
        }
    }

    // =========================
    // PHONE INPUT (DEBOUNCE)
    // =========================
    onPhoneInput(ev) {
        const phone = ev.target.value.trim();
        clearTimeout(this.debounceTimer);

        if (phone.length < 10) {
            this.hideDuplicateWarning();
            return;
        }

        this.debounceTimer = setTimeout(() => {
            this.checkDuplicatePhone(phone);
        }, 500);
    }

    async checkDuplicatePhone(phone) {
        try {
            // Use native fetch instead of jsonrpc
            const response = await fetch('/eyekei/api/check-duplicate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                },
                body: JSON.stringify({ phone }),
            });

            if (!response.ok) throw new Error('Network error');

            const result = await response.json();

            if (result.duplicate) {
                this.showDuplicateWarning(result);
            } else {
                this.hideDuplicateWarning();
            }
        } catch (error) {
            console.error("[EYEKEI] Duplicate check failed:", error);
        }
    }

    // =========================
    // INSURANCE TOGGLE
    // =========================
    toggleInsurance(ev) {
        const fields = document.getElementById("insurance-fields");
        if (fields) {
            fields.classList.toggle("d-none", !ev.target.checked);
        }
    }

    // =========================
    // FORM SUBMIT
    // =========================
    async onSubmit(ev) {
        ev.preventDefault();      // ← this now actually runs
        ev.stopPropagation();

        const form = this.formRef.el;
        const submitBtn = this.submitBtnRef.el;

        console.log("[EYEKEI][OWL] Submit triggered");  // ← useful debug

        if (!form) return;

        // Bootstrap validation
        if (!form.checkValidity()) {
            form.classList.add("was-validated");
            return;
        }

        this.state.loading = true;
        submitBtn.disabled = true;

        const originalContent = submitBtn.innerHTML;
        submitBtn.innerHTML = '<i class="fa fa-spinner fa-spin"></i> ' + _t("Processing...");

        try {
            const formData = new FormData(form);

            // Ensure CSRF token
            if (!formData.get('csrf_token') && this.csrfToken) {
                formData.append('csrf_token', this.csrfToken);
            }
            formData.set("branch_code", this.branchCode);

            // Optional: also log what is being sent
            console.log("branch_code added to formData:", this.branchCode);

            const response = await fetch("/eyekei/register/submit", {
                method: "POST",
                body: formData,
                headers: {
                    "X-Requested-With": "XMLHttpRequest",
                },
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();

            if (result.status === "success") {
                browser.location.href = result.redirect_url;
            } else if (result.status === "duplicate") {
                this.showDuplicateWarning(result);
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalContent;
            } else {
                this.showAlert("danger", result.message || _t("An error occurred"));
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalContent;
            }
        } catch (error) {
            console.error("[EYEKEI] Submit error:", error);
            this.showAlert("danger", _t("Network error. Please try again.") + " " + error.message);
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalContent;
        } finally {
            this.state.loading = false;
        }
    }

    // =========================
    // UI HELPERS
    // =========================
    showDuplicateWarning(data) {
        const warningEl = document.getElementById('duplicate-warning');
        if (!warningEl) return;

        document.getElementById('dup-patient-id').textContent = data.patient_id || 'N/A';
        document.getElementById('dup-name').textContent = data.patient_name || data.name || 'Unknown';
        document.getElementById('dup-last-visit').textContent = data.last_visit || 'N/A';
        document.getElementById('dup-branch').textContent = data.branch || 'Unknown';

        const profileLink = document.getElementById('dup-profile-link');
        if (profileLink && data.patient_url) {
            profileLink.href = data.patient_url;
        }

        warningEl.classList.remove('d-none');
        warningEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    hideDuplicateWarning() {
        const warningEl = document.getElementById('duplicate-warning');
        if (warningEl) {
            warningEl.classList.add('d-none');
        }
    }

    showAlert(type, message) {
        const container = document.getElementById("alert-container");
        if (!container) {
            browser.alert(message);
            return;
        }

        const alert = document.createElement("div");
        alert.className = `alert alert-${type} alert-dismissible fade show`;
        alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        container.innerHTML = "";
        container.appendChild(alert);
        alert.scrollIntoView({ behavior: "smooth", block: "center" });
    }
}

// =========================
// REGISTER AS PUBLIC COMPONENT
// =========================
registry.category("public_components").add("eyekei_eyewear.portal_registration", PortalPatientRegistration);



                // <button t-ref="submitBtn" type="submit" t-att-disabled="state.loading">
                //     <t t-if="state.loading">
                //         <i class="fa fa-spinner fa-spin"/> Processing...
                //     </t>
                //     <t t-else="">Submit</t>
                // </button>