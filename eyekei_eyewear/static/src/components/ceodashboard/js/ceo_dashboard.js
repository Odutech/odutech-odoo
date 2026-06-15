/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

// ============================================
// CEO DASHBOARD COMPONENT (Odoo 19)
// Registered as a client action: tag="eyekei_ceo_dashboard"
// ============================================

class CEODashboard extends Component {
    static template = "eyekei_eyewear.CEODashboard";

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notification = useService("notification");

        this.state = useState({
            dateRange: "today",
            customDate: "",
            customDateTo: "",
            branchId: false,
            kpis: {},
            loading: true,
            alerts: [],
        });

        onWillStart(async () => {
            await this.loadDashboardData();
        });
    }

    // ============================================
    // DATA LOADING
    // ============================================

    async loadDashboardData() {
        this.state.loading = true;
        try {
            // Call the Python method we defined on eyekei.ceo.dashboard
            const kpis = await this.orm.call(
                "eyekei.ceo.dashboard",
                "get_dashboard_data",
                [this.state.dateRange, this.state.branchId, this.state.customDate || false, this.state.customDateTo || false]
            );
            this.state.kpis = kpis;

            // Fetch unresolved alerts
            this.state.alerts = await this.orm.searchRead(
                "eyekei.dashboard.alert",
                [["is_resolved", "=", false]],
                ["alert_type", "severity", "message", "branch_id", "created_date"],
                { limit: 10, order: "created_date desc" }
            );
        } catch (error) {
            this.notification.add(
                error.message || _t("Failed to load dashboard data"),
                { type: "danger", sticky: false }
            );
        } finally {
            this.state.loading = false;
        }
    }

    // ============================================
    // EVENT HANDLERS
    // ============================================

    async onDateRangeChange(ev) {
        this.state.dateRange = ev.target.value;
        this.state.customDate = "";
        this.state.customDateTo = "";
        await this.loadDashboardData();
    }

    async onCustomDateChange(ev) {
        const val = ev.target.value;
        this.state.customDate = val;
        if (val) {
            this.state.dateRange = "custom";
            // If "to" is now before "from", reset it
            if (this.state.customDateTo && this.state.customDateTo < val) {
                this.state.customDateTo = "";
            }
        } else {
            this.state.customDate = "";
            this.state.customDateTo = "";
            this.state.dateRange = "today";
        }
        await this.loadDashboardData();
    }

    async onCustomDateToChange(ev) {
        const val = ev.target.value;
        this.state.customDateTo = val;
        if (this.state.customDate) {
            this.state.dateRange = "custom";
        }
        await this.loadDashboardData();
    }

    async clearCustomDate() {
        this.state.customDate = "";
        this.state.customDateTo = "";
        this.state.dateRange = "today";
        await this.loadDashboardData();
    }

    async onBranchChange(ev) {
        this.state.branchId = ev.target.value ? parseInt(ev.target.value) : false;
        await this.loadDashboardData();
    }

    async onResolveAlert(alertId) {
        await this.orm.write("eyekei.dashboard.alert", [alertId], {
            is_resolved: true,
        });
        await this.loadDashboardData();
    }

    // ============================================
    // NAVIGATION ACTIONS
    // ============================================

    viewVisits() {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: _t("Patient Visits"),
            res_model: "eyekei.patient.visit",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: this._getCurrentDomain("visit_date"),
        });
    }

    _invoiceDomain() {
        const domain = [["move_type", "=", "out_invoice"]];
        if (this.state.kpis.date_from) {
            domain.push(["invoice_date", ">=", this.state.kpis.date_from]);
        }
        if (this.state.kpis.date_to) {
            domain.push(["invoice_date", "<=", this.state.kpis.date_to]);
        }
        if (this.state.branchId) {
            domain.push(["company_id", "=", this.state.branchId]);
        }
        return domain;
    }

    viewAllInvoices() {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: _t("Invoices"),
            res_model: "account.move",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: this._invoiceDomain(),
        });
    }

    viewPaidInvoices() {
        const domain = this._invoiceDomain();
        domain.push(["payment_state", "=", "paid"]);
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: _t("Paid Invoices"),
            res_model: "account.move",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain,
        });
    }

    viewOutstandingInvoices() {
        const domain = this._invoiceDomain();
        domain.push(["payment_state", "not in", ["paid", "reversed", "cancelled"]]);
        domain.push(["state", "=", "posted"]);
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: _t("Outstanding Invoices"),
            res_model: "account.move",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain,
        });
    }

    viewInsuranceClaims() {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: _t("Insurance Claims"),
            res_model: "eyekei.insurance.claim",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: this._getCurrentDomain("submission_date"),
        });
    }

    viewLabJobs() {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: _t("Lab Jobs"),
            res_model: "eyekei.lab.job",
            view_mode: "kanban,list,form",
            views: [[false, "kanban"], [false, "list"], [false, "form"]],
            domain: this._getCurrentDomain("create_date"),
        });
    }

    viewRemakes() {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: _t("Remake Orders"),
            res_model: "eyekei.remake.order",
            view_mode: "list,form,pivot",
            views: [[false, "list"], [false, "form"], [false, "pivot"]],
            domain: this._getCurrentDomain("create_date"),
        });
    }

    viewDetailedReport() {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: _t("Revenue Analysis"),
            res_model: "eyekei.ceo.dashboard",
            view_mode: "pivot,graph",
            views: [[false, "pivot"], [false, "graph"]],
            domain: this._getCurrentDomain("date"),
            context: { group_by: ["date:month", "branch_id"] },
        });
    }

    // ============================================
    // UTILITIES
    // ============================================

    _getCurrentDomain(dateField) {
        const domain = [];
        const kpis = this.state.kpis;
        if (kpis.date_from) {
            domain.push([dateField, ">=", kpis.date_from]);
        }
        if (kpis.date_to) {
            domain.push([dateField, "<=", kpis.date_to]);
        }
        if (this.state.branchId) {
            domain.push(["branch_id", "=", this.state.branchId]);
        }
        return domain;
    }

    getAlertClass(severity) {
        const classes = {
            critical: "alert-danger",
            high: "alert-warning",
            medium: "alert-info",
            low: "alert-secondary",
        };
        return classes[severity] || "alert-info";
    }

    getAlertRole(severity) {
        return severity === "critical" || severity === "high" ? "alert" : "status";
    }

    formatCurrency(value) {
        return new Intl.NumberFormat("en-KE", {
            style: "currency",
            currency: "KES",
            minimumFractionDigits: 0,
        }).format(value || 0);
    }

    formatNumber(value) {
        return (value || 0).toLocaleString();
    }

    formatPercent(value) {
        return `${(value || 0).toFixed(1)}%`;
    }
}

registry.category("actions").add("eyekei_ceo_dashboard", CEODashboard);

export default CEODashboard;