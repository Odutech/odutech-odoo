from odoo import models, fields, api, _
from odoo.exceptions import UserError


class RemakeOrder(models.Model):
    _name = "eyekei.remake.order"
    _description = "Remake/Post-Delivery Correction"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char("Remake ID", readonly=True, default="New")
    patient_id = fields.Many2one(
        "res.partner",
        tracking=True,
        domain="[('is_patient', '=', True)]",
    )
    original_visit_id = fields.Many2one(
        "eyekei.patient.visit",
        "Original Visit",
        required=True,
        domain="[('state', 'in', ['collected', 'closed', 'ready_collection', 'delivered']),('patient_id', '=', patient_id),]",  # Only allow visits that have been completed/delivered
        tracking=True,
    )
    new_visit_id = fields.Many2one(
        "eyekei.patient.visit",
        "New Visit",
        domain="[('patient_id', '=', patient_id), ('id', '!=', original_visit_id)]",
        tracking=True,
    )

    remake_type = fields.Selection(
        [
            ("clinical_error", "Clinical Error (Optometrist)"),
            ("patient_complaint", "Patient Adaptation"),
            ("manufacturer_defect", "Manufacturer Defect"),
            ("paid_upgrade", "Paid Upgrade"),
            ("goodwill", "Goodwill Replacement"),
        ],
        required=True,
        tracking=True,
    )

    # Financial classification
    cost_type = fields.Selection(
        [
            ("clinic_liability", "Clinic Liability (Free)"),
            ("patient_paid", "Patient Paid Upgrade"),
            ("insurance_internal", "Insurance - Internal Cost"),
            ("promotional", "Promotional/Goodwill"),
        ],
        tracking=True,
        compute="_compute_cost_type",
        store=True,
    )

    # Approval control
    requires_approval = fields.Boolean(
        "Requires Manager Approval", compute="_compute_requires_approval", tracking=True
    )
    approved_by = fields.Many2one("res.users", "Approved By", tracking=True)
    approval_date = fields.Date("Approval Date", tracking=True)

    # Cost tracking
    original_cost = fields.Float("Original Cost", tracking=True)
    remake_cost = fields.Float("Remake Cost", tracking=True)
    cost_impact = fields.Float(
        "Net Cost Impact",
        compute="_compute_cost_impact",
        store=True,
        aggregator="sum",
        tracking=True,
    )

    # Stock reversal
    lens_reversed = fields.Boolean("Original Lens Reversed to Stock", tracking=True)
    lens_product_id = fields.Many2one(
        "product.product",
        "Lens (Product)",
        domain="[('optical_type', '=', 'lens')]",
        tracking=True,
    )

    # Complaint details
    complaint_type = fields.Text("Complaint Description", tracking=True)
    days_after_delivery = fields.Integer("Days After Delivery", tracking=True)
    reexam_findings = fields.Text("Re-examination Findings", tracking=True)
    final_decision = fields.Selection(
        [
            ("minor_adjust", "Minor Adjustment (Regrind)"),
            ("free_replacement", "Full Free Replacement"),
            ("paid_upgrade", "Paid Upgrade"),
        ],
        tracking=True,
    )

    responsible_optometrist_id = fields.Many2one(
        "res.users", "Responsible Optometrist", tracking=True
    )
    state = fields.Selection(
        [
            ("pending_approval", "Pending Approval"),
            ("approved", "Approved"),
            ("in_production", "In Production"),
            ("completed", "Completed"),
            ("cancelled", "Cancelled"),
        ],
        default="pending_approval",
        tracking=True,
    )

    @api.onchange("remake_type")
    def _onchange_remake_type(self):
        if self.remake_type == "clinical_error":
            self.responsible_optometrist_id = self.original_visit_id.optometrist_id.id
        else:
            self.responsible_optometrist_id = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("eyekei.remake")
        return super().create(vals_list)

    @api.depends("remake_type")
    def _compute_cost_type(self):
        for remake in self:
            mapping = {
                "clinical_error": "clinic_liability",
                "patient_complaint": "clinic_liability",
                "manufacturer_defect": "clinic_liability",
                "paid_upgrade": "patient_paid",
                "goodwill": "promotional",
            }
            remake.cost_type = mapping.get(remake.remake_type, "clinic_liability")

    @api.depends("remake_type")
    def _compute_requires_approval(self):
        for remake in self:
            remake.requires_approval = remake.remake_type in [
                "clinical_error",
                "goodwill",
            ]

    @api.depends("original_cost", "remake_cost")
    def _compute_cost_impact(self):
        for remake in self:
            remake.cost_impact = remake.remake_cost - (
                remake.original_cost if remake.lens_reversed else 0
            )

    def action_approve(self):
        allowed_groups = [
            "eyekei_eyewear.group_eyekei_manager",
            "eyekei_eyewear.group_eyekei_admin",
        ]
        if not any(self.env.user.has_group(g) for g in allowed_groups):
            raise UserError(
                _("Only Managers, and Administrators can approve remakes.")
            )
        self.write(
            {
                "state": "approved",
                "approved_by": self.env.user.id,
                "approval_date": fields.Date.today(),
            },
        )

    def action_approve_no_approval(self):
        self.write(
            {
                "state": "approved",
                "approved_by": self.env.user.id,
                "approval_date": fields.Date.today(),
            },
        )

    def action_create_new_visit(self):
        """Create new visit for remake production"""
        self.ensure_one()
        new_visit = self.env["eyekei.patient.visit"].create(
            {
                "patient_id": self.patient_id.id,
                "is_remake": True,
                "original_visit_id": self.original_visit_id.id,
                "remake_reason": self.remake_type,
                "remake_approved_by": self.approved_by.id,
                "state": "draft",
            },
        )
        self.new_visit_id = new_visit.id
        return {
            "type": "ir.actions.act_window",
            "res_model": "eyekei.patient.visit",
            "res_id": new_visit.id,
            "view_mode": "form",
        }

    def action_open_new_visit(self):
        """Navigate to the already-created new visit for this remake"""
        self.ensure_one()
        if not self.new_visit_id:
            raise UserError(_("No new visit has been created for this remake yet."))
        return {
            "type": "ir.actions.act_window",
            "res_model": "eyekei.patient.visit",
            "res_id": self.new_visit_id.id,
            "view_mode": "form",
            "target": "current",
        }


class RemakeWizard(models.TransientModel):
    """Quick wizard to create a remake order from a patient visit"""

    _name = "eyekei.remake.wizard"
    _description = "Create Remake Order Wizard"

    original_visit_id = fields.Many2one(
        "eyekei.patient.visit", "Original Visit", required=True, readonly=True
    )
    patient_id = fields.Many2one(
        "res.partner",
        "Patient",
        related="original_visit_id.patient_id",
        readonly=True,
    )
    reason_type = fields.Selection(
        [
            ("clinical_error", "Clinical Error (Optometrist)"),
            ("patient_complaint", "Patient Adaptation"),
            ("manufacturer_defect", "Manufacturer Defect"),
            ("paid_upgrade", "Paid Upgrade"),
            ("goodwill", "Goodwill Replacement"),
        ],
        string="Reason",
        required=True,
    )
    complaint_description = fields.Text("Complaint Description")
    days_after_delivery = fields.Integer("Days After Delivery")
    optometrist_id = fields.Many2one(
        "res.users",
        "Responsible Optometrist",
        help="Required when reason is a clinical error",
    )
    requires_manager_approval = fields.Boolean(
        "Requires Manager Approval",
        compute="_compute_requires_approval",
    )

    @api.depends("reason_type")
    def _compute_requires_approval(self):
        for wizard in self:
            wizard.requires_manager_approval = wizard.reason_type in (
                "clinical_error",
                "goodwill",
            )

    @api.constrains("reason_type", "optometrist_id")
    def _check_optometrist(self):
        for wizard in self:
            if wizard.reason_type == "clinical_error" and not wizard.optometrist_id:
                raise UserError(
                    _("Responsible Optometrist is required for Clinical Error remakes.")
                )

    def action_create_remake(self):
        """Create the RemakeOrder and open it"""
        self.ensure_one()
        remake = self.env["eyekei.remake.order"].create(
            {
                "original_visit_id": self.original_visit_id.id,
                "remake_type": self.reason_type,
                "complaint_type": self.complaint_description,
                "days_after_delivery": self.days_after_delivery,
                "responsible_optometrist_id": self.optometrist_id.id or False,
            }
        )

        # Mark the original visit as remake-requested
        self.original_visit_id.write({"state": "remake"})

        return {
            "type": "ir.actions.act_window",
            "res_model": "eyekei.remake.order",
            "res_id": remake.id,
            "view_mode": "form",
            "target": "current",
        }
