from datetime import timedelta, date
from datetime import date as date_cls
from odoo import api, fields, models, tools


class CEODashboard(models.Model):
    _name = "eyekei.ceo.dashboard"
    _description = "CEO Dashboard Aggregates"
    _auto = False  # Database view

    # Date dimensions
    date = fields.Date("Date")
    month = fields.Char("Month")
    year = fields.Integer("Year")
    week = fields.Integer("Week")

    # Branch dimensions
    branch_id = fields.Many2one("res.company", "Branch")

    # KPIs - Daily Business
    patients_seen = fields.Integer("Patients Seen")
    orders_created = fields.Integer("Orders Created")
    spectacles_delivered = fields.Integer("Spectacles Delivered")
    cash_collected = fields.Float("Cash Collected")
    insurance_sales = fields.Float("Insurance Sales")
    total_revenue = fields.Float("Total Revenue")

    # Conversion
    conversion_rate = fields.Float("Conversion Rate %")

    # Visits
    total_visits = fields.Integer("Total Visits")

    # Invoices
    invoices_generated = fields.Integer("Invoices Generated")
    invoices_paid = fields.Integer("Invoices Paid")
    invoices_outstanding = fields.Integer("Invoices Outstanding")
    invoice_paid_amount = fields.Float("Invoice Paid Amount")
    invoice_outstanding_amount = fields.Float("Invoice Outstanding Amount")

    # Insurance
    claims_submitted = fields.Integer("Claims Submitted")
    claims_received = fields.Integer("Claims Paid")
    outstanding_claims = fields.Integer("Outstanding Claims")
    collection_efficiency = fields.Float("Collection Efficiency %")

    # Lab
    jobs_in_lab = fields.Integer("Jobs in Lab")
    avg_turnaround_hours = fields.Float("Avg Turnaround (Hours)")
    remake_count = fields.Integer("Remake Count")
    remake_rate = fields.Float("Remake Rate %")

    # Inventory
    frame_stock_value = fields.Float("Frame Stock Value")
    lens_stock_value = fields.Float("Lens Stock Value")
    low_stock_alerts = fields.Integer("Low Stock Alerts")

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW eyekei_ceo_dashboard AS (
                SELECT
                    row_number() OVER () AS id,
                    date_trunc('day', v.visit_date)::date                   AS date,
                    to_char(date_trunc('day', v.visit_date), 'YYYY-MM')     AS month,
                    extract(year from date_trunc('day', v.visit_date))::int AS year,
                    extract(week from date_trunc('day', v.visit_date))::int AS week,
                    v.branch_id,
                    COUNT(DISTINCT v.patient_id)                            AS patients_seen,
                    COUNT(CASE WHEN v.state NOT IN ('draft', 'cancelled') THEN 1 END)
                                                                            AS orders_created,
                    COUNT(CASE WHEN v.state = 'closed' THEN 1 END)         AS spectacles_delivered,
                    COALESCE(SUM(CASE WHEN NOT v.is_insurance THEN v.amount_paid END), 0)
                                                                            AS cash_collected,
                    COALESCE(SUM(CASE WHEN v.is_insurance THEN v.total_amount END), 0)
                                                                            AS insurance_sales,
                    COALESCE(SUM(v.total_amount), 0)                        AS total_revenue,
                    0::float                                                AS conversion_rate,
                    COUNT(ic.id)                                            AS claims_submitted,
                    COUNT(CASE WHEN ic.state = 'payment_received' THEN 1 END)
                                                                            AS claims_received,
                    COUNT(CASE WHEN ic.state IN ('submitted', 'partial_approved') THEN 1 END)
                                                                            AS outstanding_claims,
                    0::float                                                AS collection_efficiency,
                    COUNT(CASE WHEN lj.state IN ('received', 'waiting_lens', 'in_production') THEN 1 END)
                                                                            AS jobs_in_lab,
                    COALESCE(AVG(lj.turnaround_hours), 0)                  AS avg_turnaround_hours,
                    COUNT(r.id)                                             AS remake_count,
                    0::float                                                AS remake_rate,
                    0::float                                                AS frame_stock_value,
                    0::float                                                AS lens_stock_value,
                    0::int                                                  AS low_stock_alerts
                FROM eyekei_patient_visit v
                LEFT JOIN eyekei_insurance_claim ic ON ic.visit_id = v.id
                LEFT JOIN eyekei_lab_job lj ON lj.visit_id = v.id
                LEFT JOIN eyekei_remake_order r ON r.original_visit_id = v.id
                GROUP BY
                    date_trunc('day', v.visit_date),
                    v.branch_id
            )
        """)

    # ============================================
    # DASHBOARD DATA METHOD — called by JS component
    # ============================================

    @api.model
    def get_dashboard_data(
        self,
        date_range="today",
        branch_id=False,
        custom_date=False,
        custom_date_to=False,
    ):
        """
        Return aggregated KPI data for the CEO dashboard.

        :param date_range: 'today' | 'week' | 'month' | 'year' | 'custom'
        :param branch_id: int or False for all branches
        :param custom_date: ISO date string 'YYYY-MM-DD' — range start (or exact date)
        :param custom_date_to: ISO date string 'YYYY-MM-DD' — range end (omit for single day)
        :return: dict of KPI values
        """
        today = fields.Date.today()
        date_from, date_to = self._get_date_range(
            date_range, today, custom_date, custom_date_to
        )

        # Build visit domain
        visit_domain = [("visit_date", ">=", date_from), ("visit_date", "<=", date_to)]
        if branch_id:
            visit_domain.append(("branch_id", "=", branch_id))

        visits = self.env["eyekei.patient.visit"].search(visit_domain)

        # Basic visit KPIs
        patients_seen = len(visits.mapped("patient_id"))
        orders_created = len(
            visits.filtered(lambda v: v.state not in ("draft", "cancelled"))
        )
        spectacles_delivered = len(visits.filtered(lambda v: v.state == "closed"))
        cash_collected = sum(
            visits.filtered(lambda v: not v.is_insurance).mapped("amount_paid")
        )
        insurance_sales = sum(
            visits.filtered(lambda v: v.is_insurance).mapped("total_amount")
        )
        total_revenue = sum(visits.mapped("total_amount"))
        conversion_rate = (
            round(spectacles_delivered / orders_created * 100, 1)
            if orders_created
            else 0.0
        )

        # Insurance KPIs
        claim_domain = [
            ("submission_date", ">=", date_from),
            ("submission_date", "<=", date_to),
        ]
        if branch_id:
            claim_domain.append(("visit_id.branch_id", "=", branch_id))
        claims = self.env["eyekei.insurance.claim"].search(claim_domain)
        claims_submitted = len(claims)
        claims_received = len(claims.filtered(lambda c: c.state == "payment_received"))
        outstanding_claims = len(
            claims.filtered(lambda c: c.state in ("submitted", "partial_approved"))
        )
        collection_efficiency = (
            round(claims_received / claims_submitted * 100, 1)
            if claims_submitted
            else 0.0
        )

        # Lab KPIs
        lab_domain = [("create_date", ">=", date_from), ("create_date", "<=", date_to)]
        if branch_id:
            lab_domain.append(("branch_id", "=", branch_id))
        lab_jobs = self.env["eyekei.lab.job"].search(lab_domain)
        jobs_in_lab = len(
            lab_jobs.filtered(
                lambda j: j.state in ("received", "waiting_lens", "in_production")
            )
        )
        completed_jobs = lab_jobs.filtered(
            lambda j: j.state == "delivered" and j.turnaround_hours
        )
        avg_turnaround = (
            round(
                sum(completed_jobs.mapped("turnaround_hours")) / len(completed_jobs), 1
            )
            if completed_jobs
            else 0.0
        )

        # Remake KPIs
        remake_domain = [
            ("create_date", ">=", date_from),
            ("create_date", "<=", date_to),
        ]
        if branch_id:
            remake_domain.append(("original_visit_id.branch_id", "=", branch_id))
        remake_count = self.env["eyekei.remake.order"].search_count(remake_domain)
        remake_rate = (
            round(remake_count / orders_created * 100, 1) if orders_created else 0.0
        )

        # Visit count (all visits in period regardless of state)
        total_visits = len(visits)

        # Invoice KPIs — gather invoices linked to claims and to cash visits in range
        invoice_domain = [
            ("move_type", "=", "out_invoice"),
            ("invoice_date", ">=", date_from),
            ("invoice_date", "<=", date_to),
        ]
        if branch_id:
            invoice_domain.append(("company_id", "=", branch_id))

        all_invoices = self.env["account.move"].search(invoice_domain)

        # Invoices originating from insurance claims in this period
        claim_invoice_ids = claims.mapped("invoice_id").ids
        # Invoices from cash visits (paying_invoice_id)
        cash_invoice_ids = (
            visits.filtered(lambda v: not v.is_insurance)
            .mapped("paying_invoice_id")
            .ids
        )
        relevant_ids = list(set(claim_invoice_ids + cash_invoice_ids))
        relevant_invoices = (
            self.env["account.move"]
            .browse(relevant_ids)
            .filtered(
                lambda inv: inv.id
                and inv.invoice_date
                and inv.invoice_date >= date_from
            )
        )

        invoices_generated = len(relevant_invoices)
        invoices_paid = len(
            relevant_invoices.filtered(lambda inv: inv.payment_state == "paid")
        )
        invoices_outstanding = len(
            relevant_invoices.filtered(
                lambda inv: inv.payment_state not in ("paid", "reversed", "cancelled")
                and inv.state == "posted"
            )
        )
        invoice_paid_amount = sum(
            relevant_invoices.filtered(lambda inv: inv.payment_state == "paid").mapped(
                "amount_total"
            )
        )
        invoice_outstanding_amount = sum(
            relevant_invoices.filtered(
                lambda inv: inv.payment_state not in ("paid", "reversed", "cancelled")
                and inv.state == "posted"
            ).mapped("amount_residual")
        )

        return {
            # Date info
            "date_range": date_range,
            "date_from": date_from.isoformat() if date_from else False,
            "date_to": date_to.isoformat() if date_to else False,
            "today": today.isoformat(),
            # Visit KPIs
            "total_visits": total_visits,
            "patients_seen": patients_seen,
            "orders_created": orders_created,
            "spectacles_delivered": spectacles_delivered,
            "cash_collected": cash_collected,
            "insurance_sales": insurance_sales,
            "total_revenue": total_revenue,
            "conversion_rate": conversion_rate,
            # Invoice KPIs
            "invoices_generated": invoices_generated,
            "invoices_paid": invoices_paid,
            "invoices_outstanding": invoices_outstanding,
            "invoice_paid_amount": invoice_paid_amount,
            "invoice_outstanding_amount": invoice_outstanding_amount,
            # Insurance KPIs
            "claims_submitted": claims_submitted,
            "claims_received": claims_received,
            "outstanding_claims": outstanding_claims,
            "collection_efficiency": collection_efficiency,
            # Lab KPIs
            "jobs_in_lab": jobs_in_lab,
            "avg_turnaround_hours": avg_turnaround,
            "remake_count": remake_count,
            "remake_rate": remake_rate,
        }

    @api.model
    def _get_date_range(
        self, date_range, today, custom_date=False, custom_date_to=False
    ):
        """Return (date_from, date_to) tuple for the given range."""

        def _parse(s):
            try:
                return date_cls.fromisoformat(s)
            except (ValueError, TypeError):
                return today

        if date_range == "custom":
            date_from = _parse(custom_date) if custom_date else today
            # If no end date supplied, treat as a single day
            date_to = _parse(custom_date_to) if custom_date_to else date_from
            # Ensure from <= to
            if date_from > date_to:
                date_from, date_to = date_to, date_from
            return date_from, date_to
        elif date_range == "today":
            return today, today
        elif date_range == "week":
            return today - timedelta(days=today.weekday()), today
        elif date_range == "month":
            return today.replace(day=1), today
        elif date_range == "year":
            return today.replace(month=1, day=1), today
        return today, today


class DashboardAlert(models.Model):
    _name = "eyekei.dashboard.alert"
    _description = "CEO Dashboard Alerts"

    alert_type = fields.Selection(
        [
            ("high_remake", "High Remake Rate"),
            ("low_conversion", "Low Conversion Branch"),
            ("high_outstanding", "High Outstanding Insurance"),
            ("stock_mismatch", "Stock Mismatch Detected"),
            ("manual_adjustment", "Frequent Manual Adjustments"),
            ("external_overuse", "High External Vendor Usage"),
        ],
    )
    severity = fields.Selection(
        [
            ("low", "Low"),
            ("medium", "Medium"),
            ("high", "High"),
            ("critical", "Critical"),
        ],
    )
    branch_id = fields.Many2one("res.company", "Branch")
    message = fields.Text("Alert Message")
    is_resolved = fields.Boolean("Resolved")
    created_date = fields.Datetime("Created", default=fields.Datetime.now)

    @api.model
    def _cron_generate_alerts(self):
        """Daily alert generation — called by scheduled action"""
        branches = self.env["res.company"].search([])
        cutoff = fields.Date.today() - timedelta(days=30)

        for branch in branches:
            remakes = self.env["eyekei.remake.order"].search(
                [
                    ("original_visit_id.branch_id", "=", branch.id),
                    ("create_date", ">=", cutoff),
                ]
            )
            total_jobs = self.env["eyekei.patient.visit"].search_count(
                [
                    ("branch_id", "=", branch.id),
                    ("create_date", ">=", cutoff),
                ]
            )
            if total_jobs and (len(remakes) / total_jobs * 100) > 5:
                # Avoid duplicate alerts for same branch on same day
                existing = self.search(
                    [
                        ("alert_type", "=", "high_remake"),
                        ("branch_id", "=", branch.id),
                        ("is_resolved", "=", False),
                    ]
                )
                if not existing:
                    self.create(
                        {
                            "alert_type": "high_remake",
                            "severity": "high",
                            "branch_id": branch.id,
                            "message": (
                                f"Remake rate is "
                                f"{(len(remakes) / total_jobs * 100):.1f}% "
                                f"for last 30 days"
                            ),
                        }
                    )
