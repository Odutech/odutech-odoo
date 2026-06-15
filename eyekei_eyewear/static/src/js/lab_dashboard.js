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
// LAB DASHBOARD KANBAN CONTROLLER (Odoo 19)
// ============================================

export class LabDashboardController extends KanbanController {
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
        });

        // Lifecycle
        onMounted(() => this._onMounted());
        onWillUnmount(() => this._onWillUnmount());
    }

    _onMounted() {
        this._subscribeToBus();
        this._startAutoRefresh();
    }

    _onWillUnmount() {
        this._stopAutoRefresh();
        this._unsubscribeFromBus();
    }

    // ============================================
    // BUS — server→client only in Odoo 19
    // ============================================

    _subscribeToBus() {
        this.busSubscription = this.busService.subscribe(
            "eyekei_eyewear/lab_dashboard",
            (payload) => this._handleBusNotification(payload)
        );
        this.busService.addChannel("eyekei_eyewear");
    }

    _unsubscribeFromBus() {
        if (this.busSubscription) {
            this.busSubscription();
        }
        this.busService.deleteChannel("eyekei_eyewear");
    }

    _handleBusNotification(payload) {
        const { type } = payload;
        switch (type) {
            case "job_received":
            case "job_dispatched":
            case "job_ready":
            case "lens_arrived":
                this._triggerRefresh();
                break;
        }
    }

    // ============================================
    // AUTO-REFRESH every 60 seconds
    // ============================================

    _startAutoRefresh() {
        this.refreshInterval = browser.setInterval(
            () => this._triggerRefresh(),
            60000
        );
    }

    _stopAutoRefresh() {
        if (this.refreshInterval) {
            browser.clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }

    async _triggerRefresh() {
        if (this.state.isRefreshing) return;
        this.state.isRefreshing = true;
        try {
            await this.model.load();
        } finally {
            this.state.isRefreshing = false;
        }
    }

    // ============================================
    // DRAG AND DROP — validate state transitions
    // ============================================

    async onRecordDrop(record, targetGroup) {
        const newState = targetGroup.groupByField.value;
        const oldState = record.data.state;
        const jobId = record.resId;

        if (!this._isValidTransition(oldState, newState)) {
            this.notification.add(
                sprintf(_t("Cannot move from '%s' to '%s'"), oldState, newState),
                { type: "danger" }
            );
            return false;
        }

        // Confirm dispatch
        if (newState === "dispatched") {
            const confirmed = await this._confirmDispatch();
            if (!confirmed) return false;
        }

        try {
            await this.orm.call(
                "eyekei.lab.job",
                "write",
                [[jobId], { state: newState }]
            );
            this.notification.add(_t("Job status updated"), { type: "success" });
            await this._triggerRefresh();
            return true;
        } catch (error) {
            this.notification.add(
                error.message || _t("Failed to update job status"),
                { type: "danger" }
            );
            return false;
        }
    }

    _isValidTransition(fromState, toState) {
        const transitions = {
            "draft":        ["received"],
            "received":     ["in_production", "waiting_lens"],
            "waiting_lens": ["in_production"],
            "in_production":["qc", "waiting_lens"],
            "qc":           ["ready", "in_production"],   // fail sends back to production
            "ready":        ["dispatched"],
            "dispatched":   ["delivered"],
            "delivered":    [],
            "remake":       ["draft"],
        };
        return transitions[fromState]?.includes(toState) || false;
    }

    async _confirmDispatch() {
        return new Promise((resolve) => {
            this.dialog.add(ConfirmationDialog, {
                title: _t("Dispatch to Clinic"),
                body: _t("Confirm dispatching this job to the clinic?"),
                confirmLabel: _t("Dispatch"),
                cancelLabel: _t("Cancel"),
                confirm: () => resolve(true),
                cancel: () => resolve(false),
                confirmClass: "btn-primary",
            });
        });
    }

    // ============================================
    // QUICK ACTIONS — called from kanban buttons
    // via type="object" so these are server-side,
    // but JS can also call them directly if needed.
    // ============================================

    async onReceiveJob(jobId) {
        try {
            await this.orm.call("eyekei.lab.job", "action_receive_job", [[jobId]]);
            await this._triggerRefresh();
            this.notification.add(_t("Job received by lab"), { type: "success" });
        } catch (error) {
            this.notification.add(error.message, { type: "danger" });
        }
    }

    async onDispatchJob(jobId) {
        const confirmed = await this._confirmDispatch();
        if (!confirmed) return;
        try {
            await this.orm.call("eyekei.lab.job", "action_dispatch", [[jobId]]);
            await this._triggerRefresh();
            this.notification.add(_t("Job dispatched to clinic"), { type: "success" });
        } catch (error) {
            this.notification.add(error.message, { type: "danger" });
        }
    }

    async onOpenJob(jobId) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "eyekei.lab.job",
            res_id: jobId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    // ============================================
    // UTILITY
    // ============================================

    /**
     * Get Bootstrap color class for a given job state
     */
    getStateColor(state) {
        const colors = {
            "draft":        "secondary",
            "received":     "info",
            "waiting_lens": "warning",
            "in_production":"primary",
            "qc":           "purple",
            "ready":        "success",
            "dispatched":   "teal",
            "delivered":    "dark",
            "remake":       "danger",
        };
        return colors[state] || "secondary";
    }

    /**
     * Format turnaround hours into a readable string
     */
    formatTurnaround(hours) {
        if (!hours || hours === 0) return _t("N/A");
        if (hours < 1) return sprintf(_t("%d min"), Math.round(hours * 60));
        if (hours < 24) return sprintf(_t("%.1f hrs"), hours);
        return sprintf(_t("%.1f days"), hours / 24);
    }
}

// ============================================
// VIEW REGISTRATION
// Key must match js_class="eyekei_lab_dashboard" in XML
// ============================================

export const labDashboardView = {
    ...kanbanView,
    Controller: LabDashboardController,
};

registry.category("views").add("eyekei_lab_dashboard", labDashboardView);

export default {
    LabDashboardController,
    labDashboardView,
};