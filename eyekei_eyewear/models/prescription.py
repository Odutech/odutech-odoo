

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class Prescription(models.Model):
    _name = "eyekei.prescription"
    _description = "Eye Prescription"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc, id desc"

    name = fields.Char("Prescription ID", readonly=True, default="New", tracking=True)
    visit_id = fields.Many2one("eyekei.patient.visit", "Visit", tracking=True)
    patient_id = fields.Many2one(
        "res.partner",
        "Patient",
        required=True,
        domain=[("is_patient", "=", True)],
        tracking=True,
    )
    prescription_type = fields.Selection(
        [("patient", "Patient Copy"), ("insurance", "Insurance Copy")],
        required=True,
        tracking=True,
    )
    state = fields.Selection(
        [("draft", "Draft"), ("finalized", "Finalized")],
        default="draft",
        tracking=True,
    )

    # Right Eye (OD)
    od_sph = fields.Float("SPH", tracking=True)
    od_cyl = fields.Float("CYL", tracking=True)
    od_axis = fields.Integer("AXIS", tracking=True)
    od_add = fields.Float("ADD", tracking=True)
    od_va = fields.Char("V/A", tracking=True)

    # Left Eye (OS)
    os_sph = fields.Float("SPH", tracking=True)
    os_cyl = fields.Float("CYL", tracking=True)
    os_axis = fields.Integer("AXIS", tracking=True)
    os_add = fields.Float("ADD", tracking=True)
    os_va = fields.Char("V/A", tracking=True)

    # Lens details
    lens_product_id = fields.Many2one(
        "product.product",
        "Lens Model",
        domain="[('optical_type', '=', 'lens')]",
        tracking=True,
    )
    lens_type = fields.Many2one("eyekei.lens.type.categorization", string="Lens Type",
                                domain=[("lens_categorization", "=", "lens_type")], related="lens_product_id.lens_type",
        store=True,
        readonly=True,
        tracking=True)
    lens_index = fields.Many2one("eyekei.lens.type.categorization", string="Lens Index", domain=[("lens_categorization", "=", "lens_index")], related="lens_product_id.lens_index", readonly=True, tracking=True)

    lens_coating = fields.Many2one("eyekei.lens.type.categorization", string="Lens Coating", domain=[("lens_categorization", "=", "lens_coating")], related="lens_product_id.lens_coating",
        store=True,
        readonly=True,
        tracking=True)
    pd = fields.Float("PD (mm)", tracking=True)
    segment_height = fields.Float("Segment Height", tracking=True)
    prism = fields.Char("Prism", tracking=True)
    lens_price = fields.Float(
        "Lens Price",
        related="lens_product_id.list_price",
        store=True,
        readonly=True,
        tracking=True,
    )

    def confirm_prescription(self):
        self.ensure_one()
        if self.state != "draft":
            raise UserError(_("Only prescriptions in 'Draft' state can be confirmed."))
        self.state = "finalized"

    def _check_clinical_access(self):
        """Raise if current user is not optometrist or admin"""
        allowed_groups = [
            "eyekei_eyewear.group_eyekei_optometrist",
            "eyekei_eyewear.group_eyekei_admin",
        ]
        if not any(self.env.user.has_group(g) for g in allowed_groups):
            raise UserError(
                _(
                    "Only Optometrists and Administrators can enter or modify prescription data.",
                ),
            )

    @api.model_create_multi
    def create(self, vals_list):
        # self._check_clinical_access()
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "eyekei.prescription",
                )
        return super().create(vals_list)

    def write(self, vals):
        # self._check_clinical_access()
        return super().write(vals)

    def action_copy_from_patient(self):
        """Copy prescription from patient version to insurance version"""
        self.ensure_one()
        if (
            self.prescription_type != "insurance"
            or not self.visit_id.prescription_patient_id
        ):
            return

        patient_rx = self.visit_id.prescription_patient_id
        self.write(
            {
                "od_sph": patient_rx.od_sph,
                "od_cyl": patient_rx.od_cyl,
                "od_axis": patient_rx.od_axis,
                "od_add": patient_rx.od_add,
                "os_sph": patient_rx.os_sph,
                "os_cyl": patient_rx.os_cyl,
                "os_axis": patient_rx.os_axis,
                "os_add": patient_rx.os_add,
                "lens_type": patient_rx.lens_type,
                "lens_product_id": patient_rx.lens_product_id,
            },
        )

    def action_save_and_duplicate(self):
        self.ensure_one()
        # Save is implicit — then duplicate
        default_vals = {
            "prescription_type": "insurance",
            "name": "New",
        }
        duplicate = self.copy(default=default_vals)
        # Link duplicate to visit as the insurance prescription
        if self.prescription_type == "patient" and self.visit_id:
            self.visit_id.prescription_insurance_id = duplicate.id

        return {
            "type": "ir.actions.act_window",
            "res_model": "eyekei.prescription",
            "res_id": duplicate.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_save_only(self):
        """Save and close the popup"""
        self.ensure_one()
        return {"type": "ir.actions.act_window_close"}
    # ── PDF helpers ──────────────────────────────────────────────────────────

    def download_prescription(self):
        """Trigger the QWeb PDF report for this prescription."""
        self.ensure_one()
        return self.env.ref(
            "eyekei_eyewear.action_report_prescription_document",
        ).report_action(self)
