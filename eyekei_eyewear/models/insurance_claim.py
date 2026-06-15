import base64
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class InsuranceCompany(models.Model):
    """Model for registering all Insurance Companies"""

    _name = "eyekei.insurance.company"
    _description = "Insurance Company"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char("Insurance Company Name", required=True, tracking=True)
    code = fields.Char("Insurance Code", required=True, unique=True, tracking=True)

    # Contact Information
    contact_person = fields.Char("Contact Person", tracking=True)
    phone = fields.Char("Phone", tracking=True)
    email = fields.Char("Email", tracking=True)
    address = fields.Text("Address", tracking=True)

    # Insurance Details
    payment_terms = fields.Text("Payment Terms", tracking=True)
    average_payment_days = fields.Integer("Average Payment Days", tracking=True)

    # Accounting Integration - Link to Odoo Partner
    partner_id = fields.Many2one(
        "res.partner",
        "Related Partner",
        help="Link to accounting partner for invoicing and payments",
        domain="[('is_company', '=', True)]",
        tracking=True,
    )

    # Schemes offered by this insurance
    scheme_ids = fields.One2many(
        "eyekei.insurance.scheme",
        "insurance_company_id",
        "Schemes",
        tracking=True,
    )

    # Status
    active = fields.Boolean("Active", default=True, tracking=True)

    # Claims Statistics
    total_claims = fields.Integer(
        "Total Claims", compute="_compute_statistics", tracking=True
    )
    pending_amount = fields.Float(
        "Pending Amount", compute="_compute_statistics", tracking=True
    )

    _constraints = [
        models.Constraint(
            "unique(code)",
            "Insurance Code must be unique!",
        ),
    ]

    def _compute_statistics(self):
        for company in self:
            claims = self.env["eyekei.insurance.claim"].search(
                [("insurance_company_id", "=", company.id)],
            )
            company.total_claims = len(claims)
            company.pending_amount = sum(
                claims.filtered(
                    lambda c: c.state not in ["payment_received", "reconciled"],
                ).mapped("balance_due"),
            )


class InsuranceScheme(models.Model):
    """Model for Insurance Schemes/Plans"""

    _name = "eyekei.insurance.scheme"
    _description = "Insurance Scheme"

    name = fields.Char("Scheme Name", required=True)
    insurance_company_id = fields.Many2one(
        "eyekei.insurance.company",
        "Insurance Company",
        required=True,
        tracking=True,
    )
    code = fields.Char("Scheme Code", tracking=True)

    # Coverage Details
    coverage_percentage = fields.Float("Coverage %", default=100)
    max_amount_per_claim = fields.Float("Max Amount Per Claim", tracking=True)
    waiting_period_days = fields.Integer("Waiting Period (Days)", tracking=True)

    # Benefits
    includes_optical = fields.Boolean("Includes Optical", default=True, tracking=True)
    includes_frames = fields.Boolean("Includes Frames", default=True, tracking=True)
    includes_lenses = fields.Boolean("Includes Lenses", default=True, tracking=True)

    active = fields.Boolean("Active", default=True, tracking=True)


class InsuranceClaim(models.Model):
    """Insurance Claim - Integrated with Odoo Accounting"""

    _name = "eyekei.insurance.claim"
    _description = "Insurance Claim"
    _inherit = ["mail.thread"]
    _order = "create_date desc"

    # Identifiers
    name = fields.Char("Claim Number", readonly=True, default="New", tracking=True)
    invoice_number = fields.Char("Invoice Number", tracking=True)
    eyekei_insurance_claim_line_id = fields.One2many(
        "eyekei.insurance.claim.line","claim_id"
    )
    # Links to other modules
    visit_id = fields.Many2one("eyekei.patient.visit", "Visit", tracking=True)
    branch_id = fields.Many2one(
        "res.company",
        "Branch",
        required=True,
        related="visit_id.branch_id",
        tracking=True,
    )
    patient_id = fields.Many2one("res.partner", "Patient", required=True, tracking=True)

    # Insurance Details - Now linked to Insurance Company model
    insurance_company_id = fields.Many2one(
        "eyekei.insurance.company",
        "Insurance Company",
        required=True,
        tracking=True,
    )
    scheme_id = fields.Many2one(
        "eyekei.insurance.scheme",
        "Insurance Scheme",
        domain="[('insurance_company_id', '=', insurance_company_id)]",
        tracking=True,
    )
    member_number = fields.Char("Member Number", tracking=True)

    # Legacy field for backward compatibility (can be removed after migration)
    insurance_name = fields.Char(
        "Insurance Name (Legacy)",
        related="insurance_company_id.name",
        readonly=True,
        store=True,
    )
    scheme_name = fields.Char(
        "Scheme Name (Legacy)",
        related="scheme_id.name",
        readonly=True,
        store=True,
    )

    # Financial - Linked to Odoo Accounting
    # Instead of storing amounts here, we link to the actual Odoo invoice
    invoice_id = fields.Many2one(
        "account.move",
        "Customer Invoice",
        domain="[('move_type', '=', 'out_invoice'), ('partner_id', '=', patient_id)]",
        help="Link to the customer invoice created in accounting",
        tracking=True,
    )

    # Amounts are computed from the linked invoice for consistency
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        default=lambda self: self.env.company.currency_id,
        readonly=True,
        tracking=True,
    )
    billed_amount = fields.Monetary(
        "Billed Amount",
        related="invoice_id.amount_total",
        currency_field="currency_id",
        readonly=True,
        store=True,
        tracking=True,
    )

    # Payment tracking through Odoo payments
    payment_ids = fields.Many2many(
        "account.payment",
        "eyekei_claim_payment_rel",
        "claim_id",
        "payment_id",
        "Related Payments",
        tracking=True,
    )

    amount_received = fields.Float(
        "Amount Received",
        compute="_compute_payment_amounts",
        store=True,
        tracking=True,
    )

    adjustment_amount = fields.Float("Adjustment Amount", tracking=True)
    out_pocket_amount = fields.Float("Out Of Pocket Amount", tracking=True)
    insurance_approved_amount = fields.Float("Ins. Approved Amount", tracking=True)
    balance_due = fields.Float("Balance Due", compute="_compute_balance", store=True)
    short_payment_reason = fields.Text("Short Payment Reason", tracking=True)

    # Status workflow (Doc 5)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("billing_finished", "Billing Finished"),
            ("docs_received", "Documents Received"),
            ("preparing_submission", "Preparing Submission"),
            ("submitted", "Submitted"),
            ("payment_received", "Payment Received"),
            ("reconciled", "Reconciled"),
            ("rejected", "Rejected"),
            ("partial_approved", "Partially Approved"),
        ],
        default="billing_finished",
        tracking=True,
        index=True,
    )

    # Dates for aging
    bill_closed_date = fields.Date("Bill Closed Date", tracking=True)
    docs_received_date = fields.Date("Documents Received Date", tracking=True)
    received_by = fields.Many2one("res.users", "Received By", tracking=True)
    submission_date = fields.Date("Submission Date", tracking=True)
    submission_batch_id = fields.Many2one(
        "eyekei.submission.batch", "Submission Batch", tracking=True
    )
    payment_date = fields.Date(
        "Payment Date",
        compute="_compute_payment_date",
        store=True,
    )

    # Aging analysis
    aging_days = fields.Integer("Aging Days", compute="_compute_aging", store=True)
    aging_bucket = fields.Selection(
        [
            ("0-30", "0-30 Days"),
            ("31-60", "31-60 Days"),
            ("61-90", "61-90 Days"),
            ("90+", "90+ Days"),
        ],
        compute="_compute_aging",
        store=True,
    )

    # eTIMS
    etims_number = fields.Char("eTIMS Number", tracking=True)
    vat_number = fields.Char("VAT Number", tracking=True)

    # Document attachments
    document_ids = fields.Many2many(
        "ir.attachment",
        string="Documents",
        help="Prescription, Invoice, eTIMS, Preauth, etc.",
        tracking=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("eyekei.claim")
        return super().create(vals_list)

    @api.depends("payment_ids", "payment_ids.state", "payment_ids.amount")
    def _compute_payment_amounts(self):
        for claim in self:
            # Sum only posted payments
            claim.amount_received = sum(
                claim.payment_ids.filtered(lambda p: p.state == "posted").mapped(
                    "amount",
                ),
            )

    @api.depends("payment_ids", "payment_ids.date")
    def _compute_payment_date(self):
        for claim in self:
            posted_payments = claim.payment_ids.filtered(lambda p: p.state == "posted")
            if posted_payments:
                claim.payment_date = max(posted_payments.mapped("date"))
            else:
                claim.payment_date = False

    @api.depends("billed_amount", "amount_received", "adjustment_amount")
    def _compute_balance(self):
        for claim in self:
            claim.balance_due = (
                claim.billed_amount - claim.amount_received - claim.adjustment_amount
            )

    @api.depends("submission_date", "payment_date")
    def _compute_aging(self):
        today = fields.Date.today()
        for claim in self:
            if claim.payment_date:
                claim.aging_days = 0
                claim.aging_bucket = False
            elif claim.submission_date:
                delta = (today - claim.submission_date).days
                claim.aging_days = delta
                if delta <= 30:
                    claim.aging_bucket = "0-30"
                elif delta <= 60:
                    claim.aging_bucket = "31-60"
                elif delta <= 90:
                    claim.aging_bucket = "61-90"
                else:
                    claim.aging_bucket = "90+"
            else:
                claim.aging_days = 0
                claim.aging_bucket = False

    def move_to_billed(self):
        """Transition claim to billed state after visit completion"""
        for claim in self:
            if claim.state != "draft":
                continue  # Only move draft claims to billed
            claim.write(
                {
                    "state": "billing_finished",
                    "bill_closed_date": fields.Date.today(),
                },
            )

    def action_documents_received(self):
        self.write(
            {
                "state": "docs_received",
                "docs_received_date": fields.Date.today(),
                "received_by": self.env.user.id,
            },
        )

    def action_prepare_submission(self):
        self.write({"state": "preparing_submission"})

    def action_submit(self, batch_id=None):
        vals = {"state": "submitted", "submission_date": fields.Date.today()}
        self.action_create_customer_invoice()  # Ensure invoice is created before submission
        if batch_id:
            vals["submission_batch_id"] = batch_id
        self.write(vals)

    def action_create_invoice(self):
        """Create Odoo customer invoice with lens and frame lines from visit."""
        self.ensure_one()
        if not self.patient_id:
            raise UserError(_("Patient is required to create invoice"))

        if not self.visit_id:
            raise UserError(_("No visit linked to this claim"))

        visit = self.visit_id
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
            "ref": "Claim: %s | Insurance: %s"
            % (self.name, self.insurance_company_id.name or ""),
            "invoice_line_ids": invoice_lines,
        }

        invoice = self.env["account.move"].create(invoice_vals)
        self.invoice_id = invoice.id

        # Post the invoice immediately (optional - depends on your workflow)
        # invoice.action_post()

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

    def action_register_payment(self):
        """Open Odoo's native payment registration wizard"""
        self.ensure_one()
        if not self.invoice_id:
            msg = "No invoice linked to this claim"
            raise ValueError(msg)

        # Return action to open Odoo's payment registration
        return self.invoice_id.action_register_payment()

    def action_reject(self):
        self.write({"state": "rejected"})

    def action_reconcile(self):
        """Mark claim as reconciled when fully paid"""
        for claim in self:
            if claim.balance_due <= 0.01:  # Allow for small rounding differences
                claim.write({"state": "reconciled"})
            else:
                msg = "Cannot reconcile claim with outstanding balance"
                raise ValueError(msg)

    def action_create_customer_invoice(self):
        """Alias matching the view button name"""
        return self.action_create_invoice()

    def action_register_insurance_payment(self):
        """Register payment from insurance company"""
        self.ensure_one()
        if not self.invoice_id:
            raise UserError(
                _("Please create an invoice first before registering payment.")
            )
        return self.invoice_id.action_register_payment()

    def action_view_invoice(self):
        self.ensure_one()
        return {
            "name": _("Invoice"),
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "res_id": self.invoice_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_send_to_insurance(self):
        """Send email to insurance company with all attached documents.

        Opens the email composer pre-filled with the insurance company's email,
        a default template, and all documents linked to the claim attached.
        """
        self.ensure_one()

        # Validate that we have an insurance company with email
        if not self.insurance_company_id:
            raise UserError(_("No insurance company linked to this claim."))

        if not self.insurance_company_id.email:
            raise UserError(
                _(
                    "Insurance company '%s' does not have an email address configured. "
                    "Please update the insurance company record with a valid email."
                )
                % self.insurance_company_id.name
            )

        # Get the email template (create one if it doesn't exist, or use a generic one)
        # For now, we'll use the default mail template or create context without one
        template = self.env.ref(
            "eyekei_insurance.email_template_insurance_claim", raise_if_not_found=False
        )

        # Collect all attachment IDs from the claim's documents
        # attachment_ids = self.document_ids.ids if self.document_ids else []

        # If invoice exists, also attach the invoice PDF report
        # if self.invoice_id:
        #     try:
        #         invoice_report = self.env.ref("account.account_invoices")
        #         invoice_pdf, _ = (
        #             self.env["ir.actions.report"]
        #             .sudo()
        #             ._render_qweb_pdf(invoice_report, [self.invoice_id.id])
        #         )
        #         invoice_attachment = self.env["ir.attachment"].create(
        #             {
        #                 "name": f"Invoice_{self.invoice_id.name}.pdf",
        #                 "type": "binary",
        #                 "datas": base64.b64encode(invoice_pdf),
        #                 "res_model": "eyekei.insurance.claim",
        #                 "res_id": self.id,
        #                 "mimetype": "application/pdf",
        #             }
        #         )
        #         attachment_ids.append(invoice_attachment.id)
        #     except Exception:
        #         # If invoice report fails, continue without it
        #         pass

        # Prepare email context
        ctx = {
            "default_model": "eyekei.insurance.claim",
            "default_res_ids": self.ids,
            "default_use_template": bool(template),
            "default_template_id": template.id if template else False,
            "default_composition_mode": "comment",
            "default_partner_ids": (
                [self.insurance_company_id.partner_id.id]
                if self.insurance_company_id.partner_id
                else []
            ),
            "default_email_to": self.insurance_company_id.email,
            "default_subject": (f"Insurance Claim Submission: {self.name}"),
            "default_attachment_ids": (
                [(6, 0, self.document_ids.ids)] if self.document_ids else []
            ),
            "force_email": True,
        }

        # Open the email composer wizard
        return {
            "type": "ir.actions.act_window",
            "name": "Send to Insurance",
            "res_model": "mail.compose.message",
            "view_mode": "form",
            "target": "new",
            "context": ctx,
        }

    def action_view_payments(self):
        self.ensure_one()
        return {
            "name": _("Payments"),
            "type": "ir.actions.act_window",
            "res_model": "account.payment",
            "view_mode": "list,form",
            "domain": [("id", "in", self.payment_ids.ids)],
            "target": "current",
        }


class InsuranceClaimLine(models.Model):
    _name = 'eyekei.insurance.claim.line'
    _description = 'Insurance Claim Line'

    product_id = fields.Many2one('product.product', string='Product', required=True)
    quantity = fields.Float(string='Quantity', default=1.0)
    unit_price = fields.Float(string='Unit Price', digits='Product Price')
    tax_ids = fields.Many2many('account.tax', string='Taxes')

    # Total amount computed based on price, qty, and taxes
    price_total = fields.Monetary(compute='_compute_amount', string='Total Amount', store=True)
    currency_id = fields.Many2one('res.currency', related='claim_id.currency_id', store=True)
    claim_id = fields.Many2one('eyekei.insurance.claim', string='Claim Reference', ondelete='cascade')

    @api.depends('quantity', 'unit_price', 'tax_ids')
    def _compute_amount(self):
        for line in self:
            taxes = line.tax_ids.compute_all(line.unit_price, line.currency_id, line.quantity, product=line.product_id)
            line.price_total = taxes['total_included']
# class SubmissionBatch(models.Model):
#     """Batch submission of multiple claims to insurance"""

#     _name = "eyekei.submission.batch"
#     _description = "Insurance Submission Batch"
#     _inherit = ["mail.thread"]

#     name = fields.Char("Batch Number", readonly=True, default="New")
#     insurance_company_id = fields.Many2one(
#         "eyekei.insurance.company", "Insurance Company"
#     )
#     submission_date = fields.Date("Submission Date", default=fields.Date.today)

#     # Claims in this batch
#     claim_ids = fields.One2many(
#         "eyekei.insurance.claim", "submission_batch_id", "Claims"
#     )
#     total_amount = fields.Float("Total Amount", compute="_compute_totals")
#     claim_count = fields.Integer("Number of Claims", compute="_compute_totals")

#     # PDF Document
#     pdf_document = fields.Binary("Submission PDF")
#     pdf_filename = fields.Char("PDF Filename")

#     # Status
#     state = fields.Selection(
#         [
#             ("draft", "Draft"),
#             ("generated", "PDF Generated"),
#             ("submitted", "Submitted"),
#         ],
#         default="draft",
#     )

#     @api.model_create_multi
#     def create(self, vals_list):
#         for vals in vals_list:
#             if vals.get("name", "New") == "New":
#                 vals["name"] = self.env["ir.sequence"].next_by_code(
#                     "eyekei.submission.batch"
#                 )
#         return super().create(vals_list)

#     def _compute_totals(self):
#         for batch in self:
#             batch.total_amount = sum(batch.claim_ids.mapped("billed_amount"))
#             batch.claim_count = len(batch.claim_ids)

#     def action_generate_pdf(self):
#         """Generate submission PDF on company letterhead"""
#         # Implementation would use Odoo's report engine (qweb-pdf)
#         # This generates a PDF with company branding as per Doc 5 requirements
#         self.write({"state": "generated"})

#     def action_submit_batch(self):
#         """Mark all claims in batch as submitted"""
#         for batch in self:
#             batch.claim_ids.action_submit(batch.id)
#             batch.write({"state": "submitted"})
