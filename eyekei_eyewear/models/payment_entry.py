from odoo import models, fields, api, _


class InsuranceClaim(models.Model):
    """Extend Insurance Claim with Odoo Accounting Payment Methods"""

    _inherit = "eyekei.insurance.claim"

    # Additional fields for payment tracking
    payment_journal_id = fields.Many2one(
        "account.journal",
        "Payment Journal",
        domain="[('type', 'in', ['bank', 'cash'])]",
        help="Journal for recording insurance payments",
    )

    # Short payment handling
    has_short_payment = fields.Boolean(
        "Has Short Payment", compute="_compute_short_payment", store=True
    )

    @api.depends("billed_amount", "amount_received")
    def _compute_short_payment(self):
        for claim in self:
            claim.has_short_payment = (
                claim.billed_amount > 0
                and claim.amount_received > 0
                and claim.amount_received < claim.billed_amount
            )

    def action_register_insurance_payment(self):
        """
        Open Odoo's native payment registration with insurance-specific defaults.
        This uses Odoo's standard account.payment model.
        """
        self.ensure_one()

        if not self.invoice_id:
            msg = "Please create invoice first"
            raise ValueError(msg)

        if self.invoice_id.state != "posted":
            # Post the invoice if not already posted
            self.invoice_id.action_post()

        # Use Odoo's built-in payment registration
        # This opens the standard payment wizard
        return self.invoice_id.action_register_payment()

    def action_view_invoice(self):
        """Quick access to linked invoice"""
        self.ensure_one()
        if not self.invoice_id:
            return None
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "res_id": self.invoice_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_view_payments(self):
        """View all payments linked to this claim"""
        self.ensure_one()
        return {
            "name": "Insurance Payments",
            "type": "ir.actions.act_window",
            "res_model": "account.payment",
            "domain": [("id", "in", self.payment_ids.ids)],
            "view_mode": "tree,form",
            "target": "current",
        }


class AccountPayment(models.Model):
    """Extend Odoo's account.payment to link back to insurance claims"""

    _inherit = "account.payment"

    # Link to insurance claim (optional - for insurance payments)
    insurance_claim_id = fields.Many2one(
        "eyekei.insurance.claim",
        "Related Insurance Claim",
        help="If this payment is for an insurance claim, link it here",
        ondelete="set null",
    )

    # Additional insurance-specific fields
    is_insurance_payment = fields.Boolean(
        "Is Insurance Payment", compute="_compute_is_insurance", store=True
    )
    insurance_company_id = fields.Many2one(
        "eyekei.insurance.company",
        "Insurance Company",
        related="insurance_claim_id.insurance_company_id",
        readonly=True,
        store=True,
    )

    # Payment reference details (already exists in Odoo, but we can extend)
    bank_reference = fields.Char("Bank Reference Number")
    cheque_number = fields.Char("Cheque Number")

    @api.depends("insurance_claim_id")
    def _compute_is_insurance(self):
        for payment in self:
            payment.is_insurance_payment = bool(payment.insurance_claim_id)

    def action_post(self):
        """Override to update insurance claim status when payment is posted"""
        res = super().action_post()

        for payment in self:
            if payment.insurance_claim_id and payment.state == "posted":
                # Add this payment to the claim's payment_ids
                payment.insurance_claim_id.payment_ids = [(4, payment.id)]

                # Update claim status based on payment amount
                claim = payment.insurance_claim_id
                if claim.balance_due <= 0.01:
                    claim.write({"state": "payment_received"})
                else:
                    claim.write({"state": "partial_approved"})

        return res


class InsuranceReconciliationWizard(models.TransientModel):
    """Wizard for reconciling multiple insurance payments (bulk operation)"""

    _name = "reconciliation.wizard"
    _description = "Insurance Reconciliation Wizard"

    # Filter claims by insurance company
    insurance_company_id = fields.Many2one(
        "eyekei.insurance.company", "Insurance Company", required=True
    )

    # Claims to reconcile
    claim_ids = fields.Many2many(
        "eyekei.insurance.claim",
        string="Claims to Reconcile",
        domain="[('state', '=', 'payment_received'), ('insurance_company_id', '=', insurance_company_id)]",
    )

    # Summary
    total_reconciled = fields.Float("Total Reconciled", compute="_compute_totals")
    claim_count = fields.Integer("Claims Count", compute="_compute_totals")

    @api.depends("claim_ids")
    def _compute_totals(self):
        for wizard in self:
            wizard.total_reconciled = sum(wizard.claim_ids.mapped("amount_received"))
            wizard.claim_count = len(wizard.claim_ids)

    @api.onchange("insurance_company_id")
    def _onchange_insurance(self):
        """Auto-populate claims ready for reconciliation"""
        if self.insurance_company_id:
            claims = self.env["eyekei.insurance.claim"].search(
                [
                    ("insurance_company_id", "=", self.insurance_company_id.id),
                    ("state", "=", "payment_received"),
                    ("balance_due", "<=", 0.01),
                ]
            )
            self.claim_ids = [(6, 0, claims.ids)]

    def action_reconcile(self):
        """Mark all selected claims as reconciled"""
        for wizard in self:
            wizard.claim_ids.action_reconcile()

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Reconciliation Complete",
                "message": "%s claims reconciled successfully" % len(wizard.claim_ids),
                "type": "success",
            },
        }


class InsuranceOutstandingReport(models.TransientModel):
    """Report for insurance outstanding amounts using Odoo accounting data"""

    _name = "eyekei.insurance.outstanding.report"
    _description = "Insurance Outstanding Report"

    insurance_company_id = fields.Many2one(
        "eyekei.insurance.company", "Insurance Company", required=True
    )
    date_from = fields.Date("From Date", default=fields.Date.today)
    date_to = fields.Date("To Date", default=fields.Date.today)

    def action_generate_report(self):
        """Generate Excel report of outstanding claims"""
        # This would call a QWeb report or XLSX report
        # For now, return action to view filtered claims
        return {
            "name": "Outstanding Insurance Claims",
            "type": "ir.actions.act_window",
            "res_model": "eyekei.insurance.claim",
            "view_mode": "tree,form",
            "domain": [
                ("insurance_company_id", "=", self.insurance_company_id.id),
                ("state", "not in", ["payment_received", "reconciled"]),
                ("submission_date", ">=", self.date_from),
                ("submission_date", "<=", self.date_to),
            ],
            "context": {
                "group_by": "aging_bucket",
            },
        }
