
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = "res.partner"
    _rec_names_search = ["name", "phone", "patient_id", "id_number", "insurance_member_no"]

    is_patient = fields.Boolean("Is Patient", index=True)
    patient_id = fields.Char("Patient ID", readonly=True, copy=False, index=True, tracking=True)
    id_number = fields.Char("ID Number", index=True, tracking=True)
    date_of_birth = fields.Date("Date of Birth", tracking=True)
    gender = fields.Selection(
        [("male", "Male"), ("female", "Female"), ("other", "Other")], tracking=True
    )
    place = fields.Char("Town/Area", tracking=True)
    insurance_provider_id = fields.Many2one("eyekei.insurance.company", "Insurance Provider", tracking=True)
    insurance_member_no = fields.Char("Insurance Member Number", tracking=True)
    scheme_id = fields.Many2one(
        "eyekei.insurance.scheme",
        "Insurance Scheme",
        domain="[('insurance_company_id', '=', insurance_provider_id)]",
    )
    corporate_name = fields.Char("Corporate Name", tracking=True)
    company_id = fields.Many2one(
        "res.company", "Registered Branch", default=lambda self: self.env.company, tracking=True
    )
    # registered_branch_id = fields.Many2one(
    #     "res.company", "Registered Branch (Legacy)", default=lambda self: self.env.company, tracking=True
    # )  # --- IGNORE THIS FIELD, KEEP FOR BACKWARD COMPATIBILITY

    # Visit history
    visit_ids = fields.One2many("eyekei.patient.visit", "patient_id", "Visit History")
    last_visit_date = fields.Date(compute="_compute_last_visit", store=True)
    visit_count = fields.Integer(compute="_compute_last_visit", store=True)

    # Duplicate control flags
    phone_duplicate_warning = fields.Boolean(compute="_compute_duplicate_warning")

    _constraints = [
        models.Constraint(
            'unique(patient_id)',
            'Patient ID must be unique!',
        ),
        models.Constraint(
            'unique(id_number)',
            'ID Number must be unique!',
        ),
    ]

    @api.onchange("company_id")
    def _onchange_company_id(self):
        for record in self:
            if record.company_id:
                record.country_id = record.company_id.country_id.id
            else:
                record.country_id = False

    @api.depends("visit_ids")
    def _compute_last_visit(self):
        for patient in self:
            visits = patient.visit_ids.sorted("visit_date", reverse=True)
            patient.last_visit_date = visits[0].visit_date if visits else False
            patient.visit_count = len(patient.visit_ids)

    @api.depends("phone")
    def _compute_duplicate_warning(self):
        for patient in self:
            patient.phone_duplicate_warning = False
            if not patient.is_patient or not patient.phone:
                continue
            duplicate_count = self.search_count([
                ("is_patient", "=", True),
                ("id", "!=", patient._origin.id or patient.id),
                ("phone", "=", patient.phone),
            ])
            patient.phone_duplicate_warning = duplicate_count > 0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("is_patient") and not vals.get("patient_id"):
                vals["patient_id"] = self.env["ir.sequence"].next_by_code(
                    "eyekei.patient",
                )
        return super().create(vals_list)

    def action_view_visits(self):
        return {
            "name": _("Visit History"),
            "type": "ir.actions.act_window",
            "res_model": "eyekei.patient.visit",
            "view_mode": "tree,form",
            "domain": [("patient_id", "=", self.id)],
            "context": {"default_patient_id": self.id},
        }

    def find_duplicate_patients(self):
        """Check for duplicates based on phone or ID number"""
        self.ensure_one()
        if not self.is_patient:
            return None

        # Build OR conditions only for fields that are set
        or_clauses = []
        if self.phone:
            or_clauses.append(("phone", "=", self.phone))
        if self.id_number:
            or_clauses.append(("id_number", "=", self.id_number))

        if not or_clauses:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("No Duplicates"),
                    "message": _("No phone or ID number to check against."),
                    "type": "info",
                },
            }

        # Build domain: base AND (phone OR id_number)
        base_domain = [
            ("is_patient", "=", True),
            ("id", "!=", self.id),
        ]
        if len(or_clauses) == 1:
            domain = base_domain + or_clauses
        else:
            # Prefix | before each pair of OR conditions
            domain = base_domain + ["|"] + or_clauses

        duplicates = self.search(domain)
        if duplicates:
            return {
                "name": _("Duplicate Patients Found"),
                "type": "ir.actions.act_window",
                "res_model": "res.partner",
                "view_mode": "tree,form",
                "domain": [("id", "in", duplicates.ids)],
                "target": "new",
            }
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("No Duplicates"),
                "message": _("No duplicate patients found."),
                "type": "success",
            },
        }

    def action_create_new_visit(self):
        self.ensure_one()
        return {
            'name': _('New Visit'),
            'type': 'ir.actions.act_window',
            'res_model': 'eyekei.patient.visit',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_patient_id': self.id,
            },
        }

    def action_generate_registration_qr(self):
        self.ensure_one()
        # Placeholder — wire up to your QR library when ready
        raise UserError(_("QR generation is not yet implemented."))

    def action_approve(self):
        self.ensure_one()
        self.write({'state': 'approved', 'remake_approved_by': self.env.user.id})
        self.message_post(
            body=_("Remake approved by %s") % self.env.user.name,
            message_type='notification',
        )

    def action_view_optical_jobs(self):
        self.ensure_one()
        return {
            'name': _('Optical Jobs'),
            'type': 'ir.actions.act_window',
            'res_model': 'eyekei.lab.job',
            'view_mode': 'list,form',
            'domain': [('external_vendor_id', '=', self.id)],
            'context': {'default_external_vendor_id': self.id},
        }

    def action_view_vendor_performance_report(self):
        self.ensure_one()
        # Wire to your actual report action ID when ready
        raise UserError(_("Vendor performance report is not yet implemented."))
