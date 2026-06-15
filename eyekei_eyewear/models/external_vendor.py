from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    # Optical Vendor Identification
    is_optical_vendor = fields.Boolean(
        "Is External Optical Lab",
        help="Check this if the partner is an external optical lab/vendor for glazing services",
        index=True,
    )

    vendor_category = fields.Selection(
        [
            ("external_lab", "External Optical Lab"),
            ("lens_supplier", "Lens Supplier"),
            ("frame_supplier", "Frame Supplier"),
            ("accessory_supplier", "Accessory Supplier"),
            ("other", "Other Vendor"),
        ],
        string="Vendor Category",
        default="external_lab",
    )

    # Performance tracking fields — non-stored, computed fresh on every read
    optical_jobs_sent = fields.Integer(
        "Lab Jobs Sent",
        compute="_compute_optical_stats",
        help="Total jobs sent to this external lab",
    )
    optical_jobs_completed = fields.Integer(
        "Jobs Completed",
        compute="_compute_optical_stats",
    )
    optical_complaint_count = fields.Integer(
        "Quality Complaints",
        compute="_compute_optical_stats",
    )
    average_turnaround_days = fields.Float(
        "Avg Turnaround (Days)",
        compute="_compute_optical_stats",
    )

    # Stored field — separate compute method required by Odoo 19
    optical_remake_rate = fields.Float(
        "Remake Rate %",
        compute="_compute_remake_rate",
        store=True,
    )
    optical_rating = fields.Selection(
        [("1", "Poor"), ("2", "Fair"), ("3", "Good"), ("4", "Excellent")],
        string="Performance Rating",
        tracking=True,
    )

    # Vendor details
    requires_approval = fields.Boolean(
        "Requires Manager Approval",
        default=True,
        help="Require manager approval before sending jobs to this vendor",
    )
    is_preferred_vendor = fields.Boolean("Preferred Vendor")

    # Contact specific to lab coordination
    lab_coordinator_id = fields.Many2one(
        "res.partner",
        string="Lab Coordinator",
        domain="[('parent_id', '=', id), ('type', '=', 'contact')]",
        help="Primary contact person for lab coordination",
    )

    # ============================================
    # COMPUTE METHODS
    # ============================================

    @api.depends("is_optical_vendor")
    def _compute_optical_stats(self):
        """Compute non-stored live stats for optical vendors"""
        for partner in self:
            if not partner.is_optical_vendor:
                partner.optical_jobs_sent = 0
                partner.optical_jobs_completed = 0
                partner.optical_complaint_count = 0
                partner.average_turnaround_days = 0
                continue

            jobs = self.env["eyekei.lab.job"].search(
                [
                    ("external_vendor_id", "=", partner.id),
                    ("source_type", "=", "external"),
                ]
            )

            partner.optical_jobs_sent = len(jobs)
            partner.optical_jobs_completed = len(
                jobs.filtered(lambda j: j.state == "delivered")
            )

            completed_jobs = jobs.filtered(
                lambda j: j.state == "delivered" and j.turnaround_hours
            )
            if completed_jobs:
                partner.average_turnaround_days = (
                    sum(completed_jobs.mapped("turnaround_hours"))
                    / len(completed_jobs)
                    / 24
                )
            else:
                partner.average_turnaround_days = 0

            remake_domain = [
                ("remake_type", "in", ["manufacturer_defect", "patient_complaint"]),
                ("original_visit_id.lab_job_id.external_vendor_id", "=", partner.id),
            ]
            partner.optical_complaint_count = self.env[
                "eyekei.remake.order"
            ].search_count(remake_domain)

    @api.depends("is_optical_vendor")
    def _compute_remake_rate(self):
        for partner in self:
            if not partner.is_optical_vendor:
                partner.optical_remake_rate = 0.0
                continue

            jobs_sent = self.env["eyekei.lab.job"].search_count(
                [
                    ("external_vendor_id", "=", partner.id),
                    ("source_type", "=", "external"),
                ]
            )
            complaints = self.env["eyekei.remake.order"].search_count(
                [
                    ("remake_type", "in", ["manufacturer_defect", "patient_complaint"]),
                    (
                        "original_visit_id.lab_job_id.external_vendor_id",
                        "=",
                        partner.id,
                    ),
                ]
            )
            partner.optical_remake_rate = (
                (complaints / jobs_sent * 100) if jobs_sent else 0.0
            )

    # ============================================
    # ORM OVERRIDES
    # Force is_company=True in the vals dict BEFORE the write reaches the DB.
    # This is more reliable than onchange (client may not send it back) and
    # more reliable than @api.constrains (fires after save, sees stale value).
    # ============================================

    @staticmethod
    def _apply_optical_vendor_defaults(vals):
        """
        Mutate vals in-place: if is_optical_vendor is being set to True,
        force is_company=True and default supplier_rank=1.
        Called from both create() and write() before super().
        """
        if vals.get("is_optical_vendor"):
            vals["is_company"] = True
            vals.setdefault("supplier_rank", 1)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._apply_optical_vendor_defaults(vals)
        return super().create(vals_list)

    def write(self, vals):
        self._apply_optical_vendor_defaults(vals)
        return super().write(vals)

    # ============================================
    # ONCHANGE — UI convenience only, not relied on for correctness
    # ============================================

    @api.onchange("is_optical_vendor")
    def _onchange_is_optical_vendor(self):
        """Mirror the create/write logic for immediate UI feedback"""
        if self.is_optical_vendor:
            self.is_company = True
            if not self.supplier_rank:
                self.supplier_rank = 1

    # ============================================
    # ACTIONS
    # ============================================

    def action_view_optical_jobs(self):
        """View all jobs sent to this vendor"""
        self.ensure_one()
        return {
            "name": _("Optical Jobs"),
            "type": "ir.actions.act_window",
            "res_model": "eyekei.lab.job",
            "view_mode": "list,form",
            "domain": [
                ("external_vendor_id", "=", self.id),
                ("source_type", "=", "external"),
            ],
            "context": {
                "default_external_vendor_id": self.id,
                "default_source_type": "external",
            },
        }

    def action_view_vendor_performance_report(self):
        """Detailed performance report for vendor"""
        self.ensure_one()
        return {
            "name": _("Vendor Performance"),
            "type": "ir.actions.act_window",
            "res_model": "eyekei.lab.job",
            "view_mode": "pivot,graph,list",
            "domain": [("external_vendor_id", "=", self.id)],
            "context": {
                "group_by": ["create_date:month", "state"],
                "pivot_measures": ["id", "total_external_cost"],
            },
        }
