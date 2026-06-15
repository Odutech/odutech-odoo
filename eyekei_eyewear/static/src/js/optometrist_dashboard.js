/** @odoo-module **/

import { kanbanView } from "@web/views/kanban/kanban_view";
import { KanbanController } from "@web/views/kanban/kanban_controller";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { browser } from "@web/core/browser/browser";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { onMounted, onWillUnmount, useState } from "@odoo/owl";
import { sprintf } from "@web/core/utils/strings";

// ============================================
// OPTOMETRIST DASHBOARD KANBAN CONTROLLER
// ============================================

export class OptometristDashboardController extends KanbanController {
    setup() {
        super.setup();

        // Services
        this.notification = useService("notification");
        this.actionService = useService("action");
        this.dialog = useService("dialog");
        this.orm = useService("orm");
        this.busService = useService("bus_service");

        // Reactive state
        this.state = useState({
            isRefreshing: false,
            lastRefresh: null,
            activeTimers: new Map(),
        });

        // Lifecycle hooks
        onMounted(() => this._onMounted());
        onWillUnmount(() => this._onWillUnmount());
    }

    _onMounted() {
        this._subscribeToBus();
        this._startAutoRefresh();
        this._initializeTimers();
    }

    _onWillUnmount() {
        this._stopAutoRefresh();
        this._clearAllTimers();
        this._unsubscribeFromBus();
    }

    // ============================================
    // BUS / REAL-TIME UPDATES
    // Bus is server→client only in Odoo 19.
    // Use busService.subscribe to receive, never publish from client.
    // ============================================

    _subscribeToBus() {
        // Subscribe to notifications pushed from the server
        this.busSubscription = this.busService.subscribe(
            "eyekei_eyewear/optometrist_dashboard",
            (payload) => this._handleBusNotification(payload)
        );
        this.busService.addChannel("eyekei_eyewear");
    }

    _unsubscribeFromBus() {
        if (this.busSubscription) {
            this.busSubscription();  // In Odoo 19 subscribe returns an unsubscribe function
        }
        this.busService.deleteChannel("eyekei_eyewear");
    }

    _handleBusNotification(payload) {
        const { type, data } = payload;
        switch (type) {
            case "patient_waiting":
                this._notifyNewPatient(data);
                this._triggerRefresh();
                break;
            case "patient_assigned":
                this._triggerRefresh();
                break;
            case "status_changed":
                this._triggerRefresh();
                break;
            case "consultation_started":
                this._stopTimer(data.visit_id);
                break;
        }
    }

    _notifyNewPatient(data) {
        const { patient_name, priority, wait_time } = data;
        const isEmergency = priority === "emergency";

        const title = isEmergency ? _t("🚨 EMERGENCY PATIENT") : _t("New Patient in Queue");
        const message = isEmergency
            ? sprintf(_t("Emergency patient %s has arrived (Wait: %s)"), patient_name, wait_time)
            : sprintf(_t("%s added to queue (Wait: %s)"), patient_name, wait_time);

        this.notification.add(message, {
            title,
            type: isEmergency ? "danger" : "info",
            sticky: isEmergency,
            buttons: isEmergency ? [{
                name: _t("View Now"),
                onClick: () => this._focusOnPatient(data.visit_id),
            }] : [],
        });

        if (isEmergency) {
            this._playAlertSound();
        }
    }

    _playAlertSound() {
        try {
            const AudioCtx = window.AudioContext || window.webkitAudioContext;
            if (!AudioCtx) return;
            const ctx = new AudioCtx();
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.frequency.setValueAtTime(880, ctx.currentTime);
            osc.frequency.exponentialRampToValueAtTime(440, ctx.currentTime + 0.5);
            gain.gain.setValueAtTime(0.5, ctx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.5);
            osc.start(ctx.currentTime);
            osc.stop(ctx.currentTime + 0.5);
        } catch (e) {
            console.warn("Audio playback failed:", e);
        }
    }

    // ============================================
    // AUTO-REFRESH
    // ============================================

    _startAutoRefresh() {
        this.refreshInterval = browser.setInterval(() => this._triggerRefresh(), 30000);
        this.timeUpdateInterval = browser.setInterval(() => this._updateRelativeTimes(), 60000);
    }

    _stopAutoRefresh() {
        if (this.refreshInterval) {
            browser.clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
        if (this.timeUpdateInterval) {
            browser.clearInterval(this.timeUpdateInterval);
            this.timeUpdateInterval = null;
        }
    }

    async _triggerRefresh() {
        if (this.state.isRefreshing) return;
        this.state.isRefreshing = true;
        this.state.lastRefresh = new Date();
        try {
            await this.model.load();
        } finally {
            this.state.isRefreshing = false;
        }
    }

    // ============================================
    // DRAG AND DROP
    // ============================================

    async onRecordDrop(record, targetGroup) {
        // FIX: use correct state names matching eyekei.patient.visit state field
        const newState = targetGroup.groupByField.value;
        const oldState = record.data.state;
        const visitId = record.resId;

        if (!this._isValidTransition(oldState, newState)) {
            this.notification.add(
                sprintf(_t("Cannot move from %s to %s"), oldState, newState),
                { type: "danger" }
            );
            return false;
        }

        if (newState === "closed") {
            const confirmed = await this._confirmCloseVisit();
            if (!confirmed) return false;
        }

        if (newState === "in_consultation") {
            this._startTimer(visitId);
        }

        try {
            // FIX: correct model name eyekei.patient.visit
            await this.orm.write("eyekei.patient.visit", [visitId], { state: newState });
            this.notification.add(_t("Status updated"), { type: "success" });
            await this._triggerRefresh();
            return true;
        } catch (error) {
            this.notification.add(
                error.message || _t("Failed to update status"),
                { type: "danger" }
            );
            return false;
        }
    }

    // FIX: state names corrected to match eyekei.patient.visit state selection
    _isValidTransition(fromState, toState) {
        const transitions = {
            "waiting":            ["in_consultation", "cancelled"],
            "in_consultation":    ["prescription_done", "pending_insurance", "approved", "cancelled", "waiting"],
            "prescription_done":  ["pending_insurance", "approved", "cancelled"],
            "pending_insurance":  ["approved", "rejected", "cancelled", "in_consultation"],
            "approved":           ["sent_to_lab", "cancelled"],
            "sent_to_lab":        ["in_lab", "cancelled"],
            "in_lab":             ["lab_ready", "cancelled"],
            "lab_ready":          ["ready_collection"],
            "ready_collection":   ["closed", "cancelled", "remake"],
            "closed":             ["remake"],
            "cancelled":          ["waiting"],
            "remake":             ["waiting"],
        };
        return transitions[fromState]?.includes(toState) || false;
    }

    async _confirmCloseVisit() {
        return new Promise((resolve) => {
            this.dialog.add(ConfirmationDialog, {
                title: _t("Close Visit"),
                body: _t("Are you sure you want to close this visit? This will finalize billing and cannot be undone."),
                confirmLabel: _t("Close Visit"),
                cancelLabel: _t("Cancel"),
                confirm: () => resolve(true),
                cancel: () => resolve(false),
                confirmClass: "btn-primary",
            });
        });
    }

    // ============================================
    // QUICK ACTIONS
    // ============================================

    async onStartConsultation(record) {
        const visitId = record.resId;
        try {
            // FIX: correct model name
            await this.orm.call("eyekei.patient.visit", "action_start_consultation", [[visitId]]);
            this._startTimer(visitId);
            // FIX: use this.actionService not this.action
            this.actionService.doAction({
                type: "ir.actions.act_window",
                res_model: "eyekei.patient.visit",
                res_id: visitId,
                views: [[false, "form"]],
                target: "current",
            });
        } catch (error) {
            this.notification.add(
                error.message || _t("Failed to start consultation"),
                { type: "danger" }
            );
        }
    }

    async onSendToLab(record) {
        const visitId = record.resId;
        this.dialog.add(ConfirmationDialog, {
            title: _t("Send to Lab"),
            body: _t("Confirm sending this job to the lab for glazing?"),
            confirmLabel: _t("Send to Lab"),
            confirm: async () => {
                try {
                    // FIX: correct model name
                    await this.orm.call("eyekei.patient.visit", "action_send_to_lab", [[visitId]]);
                    await this._triggerRefresh();
                    this.notification.add(_t("Job sent to lab"), { type: "success" });
                } catch (error) {
                    this.notification.add(error.message, { type: "danger" });
                }
            },
        });
    }

    async onCreateRemake(record) {
        const visitId = record.resId;
        // FIX: correct model name eyekei.remake.wizard, use actionService
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "eyekei.remake.wizard",
            views: [[false, "form"]],
            target: "new",
            context: {
                default_original_visit_id: visitId,
            },
        });
    }

    // ============================================
    // TIMERS
    // ============================================

    _initializeTimers() {
        const activeVisits = this.model.root.records?.filter(
            (r) => r.data.state === "in_consultation"
        ) || [];
        activeVisits.forEach((visit) => this._startTimer(visit.resId));
    }

    _startTimer(visitId) {
        if (this.state.activeTimers.has(visitId)) return;
        const startTime = Date.now();
        const interval = browser.setInterval(() => this._updateTimerDisplay(visitId), 1000);
        this.state.activeTimers.set(visitId, { startTime, interval });
    }

    _stopTimer(visitId) {
        const timer = this.state.activeTimers.get(visitId);
        if (timer) {
            browser.clearInterval(timer.interval);
            this.state.activeTimers.delete(visitId);
        }
    }

    _clearAllTimers() {
        this.state.activeTimers.forEach((timer) => browser.clearInterval(timer.interval));
        this.state.activeTimers.clear();
    }

    _updateTimerDisplay(visitId) {
        const timer = this.state.activeTimers.get(visitId);
        if (!timer) return;
        const elapsed = Date.now() - timer.startTime;
        const formatted = this._formatDuration(elapsed);
        const element = document.querySelector(
            `[data-visit-id="${visitId}"] .o_consultation_timer`
        );
        if (element) {
            element.textContent = formatted;
            element.classList.toggle("o_overdue", elapsed > 1800000);
        }
    }

    _formatDuration(ms) {
        const totalSeconds = Math.floor(ms / 1000);
        const hours = Math.floor(totalSeconds / 3600);
        const minutes = Math.floor((totalSeconds % 3600) / 60);
        const seconds = totalSeconds % 60;
        if (hours > 0) return sprintf("%02d:%02d:%02d", hours, minutes, seconds);
        return sprintf("%02d:%02d", minutes, seconds);
    }

    // ============================================
    // UTILITY
    // ============================================

    _focusOnPatient(visitId) {
        const element = document.querySelector(`[data-visit-id="${visitId}"]`);
        if (element) {
            element.scrollIntoView({ behavior: "smooth", block: "center" });
            element.classList.add("o_highlighted");
            setTimeout(() => element.classList.remove("o_highlighted"), 3000);
        }
    }

    _updateRelativeTimes() {
        document.querySelectorAll(".o_relative_time").forEach((el) => {
            const timestamp = el.dataset.timestamp;
            if (timestamp) el.textContent = this._getRelativeTime(new Date(timestamp));
        });
    }

    _getRelativeTime(date) {
        const diff = Math.floor((new Date() - date) / 1000);
        if (diff < 60) return _t("Just now");
        if (diff < 3600) return sprintf(_t("%d min ago"), Math.floor(diff / 60));
        if (diff < 86400) return sprintf(_t("%d hours ago"), Math.floor(diff / 3600));
        return sprintf(_t("%d days ago"), Math.floor(diff / 86400));
    }
}

// ============================================
// VIEW REGISTRATION
// FIX: key changed to "eyekei_optometrist_dashboard" to match js_class in XML
// FIX: removed buttonTemplate — no custom OWL template defined
// ============================================

export const optometristDashboardView = {
    ...kanbanView,
    Controller: OptometristDashboardController,
};

registry.category("views").add("eyekei_optometrist_dashboard", optometristDashboardView);

// ============================================
// UTILITY EXPORTS
// ============================================

export function formatPatientAge(birthDate) {
    if (!birthDate) return "";
    const birth = new Date(birthDate);
    const now = new Date();
    let years = now.getFullYear() - birth.getFullYear();
    let months = now.getMonth() - birth.getMonth();
    if (months < 0 || (months === 0 && now.getDate() < birth.getDate())) {
        years--;
        months += 12;
    }
    if (years < 1) return sprintf(_t("%d months"), months);
    if (years < 2) return sprintf(_t("%d year %d months"), years, months);
    return sprintf(_t("%d years"), years);
}

export function calculateWaitTime(dateString) {
    const diffMins = Math.floor((new Date() - new Date(dateString)) / 60000);
    if (diffMins < 1) return _t("Just now");
    if (diffMins < 60) return sprintf(_t("%d min"), diffMins);
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return sprintf(_t("%d hours"), diffHours);
    return sprintf(_t("%d days"), Math.floor(diffHours / 24));
}

export default {
    OptometristDashboardController,
    optometristDashboardView,
    formatPatientAge,
    calculateWaitTime,
};