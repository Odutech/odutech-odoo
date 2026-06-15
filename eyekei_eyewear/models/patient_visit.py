from odoo import models, fields, api, _
from odoo.exceptions import AccessError, UserError
from datetime import datetime


class PatientVisit(models.Model):
    _name = "eyekei.patient.visit"
    _description = "Patient Visit/Encounter"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "visit_date desc, id desc"

    # Identifiers
    name = fields.Char(
        "Visit ID", readonly=True, copy=False, default="New", tracking=True
    )
    patient_id = fields.Many2one(
        "res.partner",
        "Patient",
        required=True,
        domain=[("is_patient", "=", True)],
        index=True,
        tracking=True,
    )
    phone = fields.Char(
        "Phone", related="patient_id.phone", readonly=True, tracking=True
    )
    patient_id_seq = fields.Char(
        "Patient Seq", related="patient_id.patient_id", readonly=True, tracking=True
    )
    visit_date = fields.Datetime(
        "Visit Date", default=fields.Datetime.now, required=True, tracking=True
    )
    branch_id = fields.Many2one(
        "res.company",
        "Branch",
        required=True,
        default=lambda self: self.env.company,
        tracking=True,
    )

    # Status workflow
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("waiting", "Waiting Consultation"),
            ("in_consultation", "In Consultation"),
            ("prescription_done", "Prescription Completed"),
            ("pending_insurance", "Pending Insurance Approval"),
            ("approved", "Approved - Ready for Lab"),
            ("sent_to_lab", "Sent to Lab"),
            ("in_lab", "In Lab Production"),
            ("lab_ready", "Ready from Lab"),
            ("ready_collection", "Ready for Collection"),
            ("collected", "Collected"),
            ("closed", "Closed"),
            ("remake", "Remake Requested"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        tracking=True,
        index=True,
    )

    # Staff assignment
    receptionist_id = fields.Many2one(
        "res.users", "Registered By", default=lambda self: self.env.user, tracking=True
    )
    optometrist_id = fields.Many2one(
        "res.users",
        "Optometrist",
        domain=lambda self: [
            (
                "group_ids",
                "in",
                [self.env.ref("eyekei_eyewear.group_eyekei_optometrist").id],
            ),
            ("company_ids", "in", [self.env.company.id]),
        ],
        tracking=True,
    )
    lab_technician_id = fields.Many2one(
        "res.users",
        "Lab Technician",
        domain=lambda self: [
            (
                "group_ids",
                "in",
                [
                    self.env.ref("eyekei_eyewear.group_eyekei_lab_tech").id,
                    self.env.ref("eyekei_eyewear.group_eyekei_lab_manager").id,
                ],
            ),
            ("company_ids", "in", [self.env.company.id]),
        ],
        tracking=True,
    )

    # Clinical data
    chief_complaint = fields.Text("Chief Complaint", tracking=True)
    history = fields.Text("Case History", tracking=True)
    signs_symptoms = fields.Text("Signs & Symptoms", tracking=True)
    diagnosis = fields.Text("Diagnosis", tracking=True)
    remarks = fields.Text("Remarks", tracking=True)

    # Prescriptions
    prescription_patient_id = fields.Many2one(
        "eyekei.prescription", "Patient Prescription", tracking=True
    )
    prescription_insurance_id = fields.Many2one(
        "eyekei.prescription", "Insurance Prescription", tracking=True
    )

    # Change to product.product
    frame_product_id = fields.Many2one(
        "product.product",
        "Selected Frame",
        domain="[('optical_type', '=', 'frame')]",
        context={"search_default_filter_by_branch": 1},
        tracking=True,
    )
    frame_price = fields.Float(
        "Frame Price",
        related="frame_product_id.lst_price",
        readonly=True,
        tracking=True,
    )
    # Auto-select frame creates stock reservation
    frame_reservation_id = fields.Many2one(
        "stock.move", "Frame Reservation", tracking=True
    )

    # Financial
    is_insurance = fields.Boolean("Insurance Patient", tracking=True)
    insurance_claim_id = fields.Many2one(
        "eyekei.insurance.claim", "Insurance Claim", tracking=True
    )
    invoice_id = fields.Many2one(
        "account.move",
        "Insurance Customer Invoice",
        domain="[('move_type', '=', 'out_invoice'), ('partner_id', '=', patient_id)]",
        help="Link to the customer invoice created in accounting",
        related="insurance_claim_id.invoice_id",
        tracking=True,
        store=True,
        readonly=True,
    )
    paying_invoice_id = fields.Many2one(
        "account.move",
        "Cash Customer Invoice",
        domain="[('move_type', '=', 'out_invoice'), ('partner_id', '=', patient_id)]",
        help="Invoice that the patient will pay (could be same as insurance invoice or a separate one)",
        tracking=True,
    )
    total_amount = fields.Float("Total Amount", compute="_compute_amounts", store=True)
    amount_paid = fields.Float("Amount Paid", tracking=True)
    balance_due = fields.Float("Balance Due", compute="_compute_amounts", store=True)

    # Lab integration
    lab_job_id = fields.Many2one("eyekei.lab.job", "Lab Job", tracking=True)
    lab_source = fields.Selection(
        [
            ("central", "Central Lab"),
            ("clinic_stock", "Clinic Stock"),
            ("external", "External Vendor"),
        ],
        "Lab Source",
        tracking=True,
    )
    external_vendor_id = fields.Many2one(
        "res.partner",
        string="External Vendor",
        domain="[('is_optical_vendor', '=', True), ('active', '=', True)]",
        help="Select an external optical lab/vendor",
        tracking=True,
    )

    # Remake tracking
    is_remake = fields.Boolean("Is Remake", tracking=True)
    original_visit_id = fields.Many2one(
        "eyekei.patient.visit", "Original Visit", tracking=True
    )
    remake_reason = fields.Selection(
        [
            ("clinical_error", "Clinical Error"),
            ("patient_complaint", "Patient Adaptation"),
            ("manufacturer_defect", "Manufacturer Defect"),
            ("paid_upgrade", "Paid Upgrade"),
            ("goodwill", "Goodwill Replacement"),
        ],
        tracking=True,
    )
    remake_approved_by = fields.Many2one(
        "res.users", "Remake Approved By", tracking=True
    )

    # Documents
    document_ids = fields.One2many("ir.attachment", compute="_compute_documents")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("eyekei.visit")
        return super().create(vals_list)

    def write(self, vals):
        self._check_clinical_access()
        return super().write(vals)

    @api.depends("prescription_patient_id", "prescription_insurance_id", "frame_price")
    def _compute_amounts(self):
        for visit in self:
            lens_price = 0
            if visit.prescription_patient_id:
                lens_price = visit.prescription_patient_id.lens_price
            visit.total_amount = visit.frame_price + lens_price
            visit.balance_due = visit.total_amount - visit.amount_paid

    def _compute_documents(self):
        for visit in self:
            attachments = self.env["ir.attachment"].search(
                [
                    "|",
                    "|",
                    "|",
                    ("res_model", "=", "eyekei.patient.visit"),
                    ("res_id", "=", visit.id),
                    ("res_model", "=", "eyekei.prescription"),
                    (
                        "res_id",
                        "in",
                        [
                            visit.prescription_patient_id.id,
                            visit.prescription_insurance_id.id,
                        ],
                    ),
                    ("res_model", "=", "eyekei.insurance.claim"),
                    ("res_id", "=", visit.insurance_claim_id.id),
                ]
            )
            visit.document_ids = attachments

    # Workflow actions
    def action_send_to_consultation(self):
        self.ensure_one()
        if not self.optometrist_id:
            raise UserError(
                _("Please assign an Optometrist before sending to consultation.")
            )
        self.write({"state": "waiting"})

    def action_start_consultation(self):
        self.write({"state": "in_consultation"})

    def action_open_prescription(self):
        """Open Quick Prescription Form (Popup)"""
        self.ensure_one()

        # Find or create patient prescription
        if not self.prescription_patient_id:
            prescription = self.env["eyekei.prescription"].create(
                {
                    "visit_id": self.id,
                    "patient_id": self.patient_id.id,
                    "prescription_type": "patient",
                }
            )
            self.prescription_patient_id = prescription.id

        return {
            "name": _("Enter Prescription"),
            "type": "ir.actions.act_window",
            "res_model": "eyekei.prescription",
            "res_id": self.prescription_patient_id.id,
            "view_mode": "form",
            "target": "new",  # Opens as popup
            "context": {
                "default_visit_id": self.id,
                "default_patient_id": self.patient_id.id,
                "default_prescription_type": "patient",
            },
        }

    def action_prescription_complete(self):
        if self.prescription_patient_id.state != "finalized":
            raise UserError(
                _("Please finalize the patient prescription before completing.")
            )
        self.write({"state": "prescription_done"})
        if self.is_insurance:
            self.write({"state": "pending_insurance"})
            # Create insurance claim
            claim = self.env["eyekei.insurance.claim"].create(
                {
                    "visit_id": self.id,
                    "patient_id": self.patient_id.id,
                    "insurance_company_id": self.patient_id.insurance_provider_id.id,
                    "scheme_id": (
                        self.patient_id.scheme_id.id
                        if self.patient_id.scheme_id
                        else False
                    ),
                    "member_number": self.patient_id.insurance_member_no,
                    # "billed_amount": self.total_amount,
                    "state": "billing_finished",
                },
            )
            self.insurance_claim_id = claim.id
        else:
            action_create_invoice = self.action_create_invoice()
            if action_create_invoice:
                self.write({"state": "approved"})
            else:
                raise UserError(
                    _(
                        "Failed to create invoice. Please check the visit details and try again."
                    )
                )

    def action_approve_insurance(self):
        for visit in self:
            if visit.insurance_claim_id and visit.invoice_id and visit.invoice_id.state == "posted":
                approved_amount = 0
                for invoice_line in visit.invoice_id.invoice_line_ids:
                    approved_amount += invoice_line.price_subtotal
                    self.env["eyekei.insurance.claim.line"].sudo().create(
                        {
                        'product_id': invoice_line.product_id.id,
                        'quantity': invoice_line.quantity,
                        'unit_price': invoice_line.price_unit,
                        "claim_id":visit.insurance_claim_id.id,
                        'tax_ids': [(6, 0, invoice_line.tax_ids.ids)],
                        }
                    )
                visit.insurance_claim_id.write({
                    'billed_amount': approved_amount,
                    'balance_due': approved_amount
                })
            self.write({"state": "approved"})

    def action_send_to_lab(self):
        if not self.lab_technician_id:
            raise UserError(_("Please assign a Lab Technician before sending to lab."))
        self.write({"state": "sent_to_lab"})
        # Create lab job
        if not self.lab_job_id:
            job = self.env["eyekei.lab.job"].create(
                {
                    "visit_id": self.id,
                    "patient_id": self.patient_id.id,
                    "branch_id": self.branch_id.id,
                    "technician_id": self.lab_technician_id.id,
                    "prescription_id": self.prescription_patient_id.id,
                    "frame_product_id": self.frame_product_id.id,
                    "lens_product_id": (
                        self.prescription_patient_id.lens_product_id.id
                        if self.prescription_patient_id
                        else False
                    ),
                    "source_type": self.lab_source or "central",
                    "external_vendor_id": (
                        self.external_vendor_id.id
                        if self.lab_source == "external"
                        else False
                    ),
                    "state": "draft",
                    "sent_to_lab_date": fields.Datetime.now(),
                },
            )
            self.lab_job_id = job.id

    def action_lab_ready(self):
        self.write({"state": "ready_collection"})
        # Send SMS notification
        if self.patient_id.phone:
            try:
                self.env["sms.api"].send_sms(
                    numbers=[self.patient_id.phone],
                    message=f"Dear {self.patient_id.name}, your glasses are ready for collection.",
                )
            except Exception as e:
                self.message_post(
                    body=_("Failed to send SMS notification."),
                    message_type="notification",
                )
                # _logger.error(f"Failed to send SMS notification: {e}")

    def action_close_visit(self):
        self.write({"state": "closed"})
        # Generate eTIMS invoice here (integration with fiscal device)
        if self.is_insurance and self.insurance_claim_id:
            self.insurance_claim_id.write({"state": "billing_finished"})

    def action_create_remake(self):
        self.ensure_one()
        return {
            "name": _("Create Remake"),
            "type": "ir.actions.act_window",
            "res_model": "eyekei.remake.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_original_visit_id": self.id,
            },
        }

    def action_select_frame(self):
        """Open product selection view filtered to frames with stock"""
        self.ensure_one()
        return {
            "name": _("Select Frame"),
            "type": "ir.actions.act_window",
            "res_model": "product.product",
            "view_mode": "kanban,tree,form",
            "domain": [
                ("optical_type", "=", "frame"),
                ("branch_stock_quantity", ">", 0),
                ("company_id", "in", self.env.companies.ids),
            ],
            "context": {
                "search_default_optical_type_frame": 1,
                "tree_view_ref": "eyekei_eyewear.view_product_frame_tree_select",
                "kanban_view_ref": "eyekei_eyewear.view_product_frame_kanban_select",
            },
            "target": "new",
        }

    def action_reserve_frame_for_visit(self):
        """Reserve frame when selected to prevent double-selling"""
        if not self.frame_product_id:
            return

        # Find stock location for this branch
        location = self.env["stock.location"].search(
            [("branch_id", "=", self.branch_id.id), ("usage", "=", "internal")], limit=1
        )

        # Create reservation (quants reservation)
        self.env["stock.quant"]._update_reserved_quantity(
            self.frame_product_id,
            location,
            1,
            lot_id=False,
            package_id=False,
            owner_id=False,
            strict=True,
        )

    def action_upload_insurance_docs(self):
        """Open document upload for Insurance documents"""
        self.ensure_one()
        return {
            "name": _("Upload Insurance Documents"),
            "type": "ir.actions.act_window",
            "res_model": "ir.attachment",
            "view_mode": "kanban,list,form",
            "domain": [
                ("res_model", "=", "eyekei.patient.visit"),
                ("res_id", "=", self.id),
            ],
            "context": {
                "default_res_model": "eyekei.patient.visit",
                "default_res_id": self.id,
                "default_name": "Insurance Document",
            },
            "target": "current",
        }

    def action_reject_insurance(self):
        """Reject Insurance Claim"""
        self.ensure_one()

        if not self.insurance_claim_id:
            raise UserError(_("No insurance claim found for this visit."))

        # Update insurance claim
        self.insurance_claim_id.write(
            {
                "state": "rejected",
            }
        )

        # Update visit
        self.write({"state": "pending_insurance"})

        # Return a notification + form view so user can decide next step
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Insurance Claim Rejected",
                "message": "Insurance has been rejected. You can now convert this to a Cash patient or close the case.",
                "type": "warning",
                "sticky": True,
            },
        }

    def _check_clinical_access(self):
        """Raise if current user is not optometrist or admin"""
        allowed_groups = [
            "eyekei_eyewear.group_eyekei_optometrist",
            "eyekei_eyewear.group_eyekei_admin",
        ]
        if not any(
            self.env.user.has_group(g) for g in allowed_groups
        ) and self.state in ["waiting", "in_consultation", "prescription_done"]:
            raise UserError(
                _(
                    "Only Optometrists and Administrators can enter or modify prescription data."
                )
            )

    def action_create_invoice(self):
        """Create Odoo customer invoice with lens and frame lines from visit."""
        self.ensure_one()
        if not self.patient_id:
            raise UserError(_("Patient is required to create invoice"))

        visit = self
        invoice_lines = []

        # Line 1: Lens from prescription (if exists)
        if (
            visit.prescription_patient_id
            and visit.prescription_patient_id.lens_product_id
        ):
            lens_product = visit.prescription_patient_id.lens_product_id
            lens_line_vals = self._prepare_invoice_line_vals(
                product=lens_product,
                quantity=1.0,
                description=f"Lens: {lens_product.name} (Prescription: {visit.prescription_patient_id.name})",
            )
            invoice_lines.append((0, 0, lens_line_vals))

        # Line 2: Frame from visit (if exists)
        if visit.frame_product_id:
            frame_product = visit.frame_product_id
            frame_line_vals = self._prepare_invoice_line_vals(
                product=frame_product,
                quantity=1.0,
                description=f"Frame: {frame_product.name}",
            )
            invoice_lines.append((0, 0, frame_line_vals))

        # Fallback: Error if no products found
        if not invoice_lines:
            raise UserError(
                _(
                    "No lens or frame products found in the visit. Please add products before creating invoice."
                )
            )

        # Create invoice with computed lines
        invoice_vals = {
            "move_type": "out_invoice",
            "partner_id": self.patient_id.id,
            "invoice_date": fields.Date.today(),
            "ref": f'Claim: {self.name} | Insurance: {self.insurance_claim_id.name or ""}',
            "invoice_line_ids": invoice_lines,
        }

        invoice = self.env["account.move"].create(invoice_vals)
        self.paying_invoice_id = invoice.id

        # Post the invoice immediately (optional - depends on your workflow)
        # paying_invoice_id.action_post()

        return {
            "type": "ir.actions.act_window",
            "name": _("Customer Invoice"),
            "res_model": "account.move",
            "res_id": invoice.id,
            "view_mode": "form",
            "target": "current",
        }

    def _prepare_invoice_line_vals(self, product, quantity=1.0, description=None):
        """Prepare invoice line values following Odoo 19 standards."""
        self.ensure_one()

        product = product.with_context(
            partner=self.patient_id,
            quantity=quantity,
        )

        return {
            "product_id": product.id,
            "quantity": quantity,
            "price_unit": product.lst_price or product.standard_price or 0.0,
            "name": description or product.name,
        }
