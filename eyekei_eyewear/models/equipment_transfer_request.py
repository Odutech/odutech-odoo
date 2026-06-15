# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)
class MaterialRequest(models.Model):
    _name = "material.request"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Material Request"
    _order = "sequence_number desc"

    # 1. Sequence Number
    sequence_number = fields.Char(
        string="Sequence Number",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _("New"),
    )
    user_id = fields.Many2one(
        "res.users",
        string="Request User",
        default=lambda self: self.env.user.id,
        tracking=True
    )
    # 2. Date of Request
    date_request = fields.Date(
        string="Date of Request",
        default=fields.Date.context_today,
        required=True,
    )
    date_Dispatched = fields.Date(
        string="Date of Request",
        required=True,
    )
    rejection_reason = fields.Text(
        string="Rejection Reason",
        tracking=True,
        readonly=True,
        states={'submitted': [('readonly', False)]}
    )
    # 3. Expected Date
    date_expected = fields.Date(string="Expected Date", required=True)

    # 4. Urgency (Priority)
    priority = fields.Selection(
        [("0", "Low"), ("1", "Normal"), ("2", "High"), ("3", "Very High")],
        string="Urgency",
        default="1",
    )

    # 5. Request Warehouse/Location
    warehouse_id = fields.Many2one(
        "stock.warehouse", string="Request Warehouse", required=True
    )
    location_id = fields.Many2one(
        "stock.location", string="Request Location", required=True
    )
    origin_warehouse_id = fields.Many2one("stock.warehouse",string="Origin Warehouse")
    origin_location_id = fields.Many2one(
        "stock.location", string="Request Location"
    )
    # Context-specific: Center/Company Multi-company rule helper
    company_id = fields.Many2one(
        "res.company", string="Company", default=lambda self: self.env.company, index=True
    )

    # 6. Status
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("submitted", "Awaits Approval"),
            ("approved", "Ready for Dispatch"),
            ("dispatched", "Dispatched"),
            ("rejected", "Rejected"),
            ("confirmed", "Checked & Confirmed"),
            ("quantity_issue", "Quantity Issue"),
            ("done", "Done"),
        ],
        string="Status",
        default="draft",
        required=True,
        tracking=True,
    )

    # One2many field to the lines table
    request_line_ids = fields.One2many(
        "material.request.line", "request_id", string="Requested Products"
    )
    courier_name = fields.Char(string="Courier / Carrier Name", tracking=True)

    # Sequence generation logic (Cleaned up duplicate)
    @api.model_create_multi
    def create(self, vals_list):
        # Fetch the main distribution warehouse and its stock location once to optimize performance
        dist_warehouse = self.env['stock.warehouse'].search([('is_main_distribution_center', '=', True)], limit=1)
        dist_location_id = dist_warehouse.lot_stock_id.id if dist_warehouse else False
        for vals in vals_list:
            # 1. Sequence Auto-generation
            if vals.get("sequence_number", _("New")) == _("New"):
                vals["sequence_number"] = (
                        self.env["ir.sequence"].next_by_code("material.request") or _("New")
                )
            # 2. Origin Warehouse Autofill (Falls back to Main Distribution Hub if not explicitly sent)
            if not vals.get("origin_warehouse_id") and dist_warehouse:
                vals["origin_warehouse_id"] = dist_warehouse.id
            # 3. Origin Location Autofill (Falls back to Hub's main stock room)
            if not vals.get("origin_location_id") and dist_location_id:
                vals["origin_location_id"] = dist_location_id
        return super(MaterialRequest, self).create(vals_list)

    def action_submit_for_approval(self):
        """Changes state to submitted and sends an email notification."""
        for record in self:
            if record.state != 'draft':
                raise UserError(_("Only draft requests can be submitted for approval."))

            # 1. Update Sequence Number if still marked as "New"
            if record.sequence_number == _("New") or not record.sequence_number:
                seq = self.env['ir.sequence'].next_by_code('material.request') or '/'
                record.write({'sequence_number': seq})

            # 2. FORCE UPDATE STATE TO SUBMITTED
            # This updates the selection field 'state' to trigger your workflow
            record.write({'state': 'submitted'})

            # 3. Find and send the email template
            template = self.env.ref('eyekei_eyewear.email_template_material_request_approval_notification', raise_if_not_found=False)

            if template:
                # Sends the email immediately (force_send=True)
                template.send_mail(record.id, force_send=True)
            else:
                # Fallback safeguard by template name string if module prefix is missing
                template_domain = [('name', '=', 'email_template_material_request')]
                template_fallback = self.env['mail.template'].search(template_domain, limit=1)
                if template_fallback:
                    template_fallback.send_mail(record.id, force_send=True)
        return True

    def action_approve_transfer_request(self):
        """Approves the submitted material request, clears rejection reasons,

        and sends an automated approval email notification.
        """
        for record in self:
            if record.state != 'submitted':
                raise UserError(_("Only requests submitted for approval can be approved."))
            # 1. Update state to Approved and clear any historical rejection reasons
            record.write({
                'state': 'approved',
                'rejection_reason': False
            })

            # 2. Find and fire the Approval Email Template
            # Replace 'your_module_name' with your actual custom module folder name
            template = self.env.ref('eyekei_eyewear.email_template_material_request_approved_notification',
                                    raise_if_not_found=False)

            if template:
                # Immediately pushes the email out through the Odoo mail gateway
                template.send_mail(record.id, force_send=True)
            else:
                # Fallback safeguard: search by template name string if module prefix is missing
                template_fallback = self.env['mail.template'].search(
                    [('name', '=', 'email_template_material_request_approved')], limit=1)
                if template_fallback:
                    template_fallback.send_mail(record.id, force_send=True)

        return True

    def action_reject_transfer_request(self, reason=None):
        """Rejects the material request, records the reason, updates state to rejected,

        and sends an automated email notification.
        """
        for record in self:
            if record.state != 'submitted':
                raise UserError(_("Only requests submitted for approval can be rejected."))

            # 1. Determine the reason string safely
            actual_reason = reason or record.rejection_reason

            if not actual_reason or not actual_reason.strip():
                raise UserError(_("You must provide a valid reason for rejecting this request."))

            # 2. Update state to 'rejected' and save the reason string
            record.write({
                'state': 'rejected',  # Updated to 'rejected' as requested
                'rejection_reason': actual_reason.strip()
            })

            # 3. Find and fire the Rejection Email Template
            # Replace 'your_module_name' with your actual custom module folder name
            template = self.env.ref('eyekei_eyewear.email_template_material_request_rejected_notification',
                                    raise_if_not_found=False)

            if template:
                # Immediately pushes the email through the Odoo mail gateway
                template.send_mail(record.id, force_send=True)
            else:
                # Fallback safeguard: search by template name string if module prefix is missing
                template_fallback = self.env['mail.template'].search(
                    [('name', '=', 'email_template_material_request_rejected')], limit=1)
                if template_fallback:
                    template_fallback.send_mail(record.id, force_send=True)

        return True

    def action_confirm_receipt(self):
        """Confirms that the received quantities and items match the request,
        moves the document state to 'confirmed', and alerts HQ via email.
        """
        for record in self:
            if record.state not in ['dispatched', 'received']:
                raise UserError(_("Only dispatched or received requests can be confirmed."))

            # 1. Update the document status state
            record.write({'state': 'confirmed'})

            # 2. Find and fire the HQ Confirmation Email Template
            template = self.env.ref('eyekei_eyewear.email_template_material_request_received_perfect',
                                    raise_if_not_found=False)

            if template:
                # Send immediately to HQ
                template.send_mail(record.id, force_send=True)
            else:
                # Fallback search constraint if XML layout pathing is missed
                template_fallback = self.env['mail.template'].search(
                    [('name', '=', 'email_template_material_request_confirmed')], limit=1)
                if template_fallback:
                    template_fallback.send_mail(record.id, force_send=True)

        return True

    def action_dispatch_transfer_request(self):
        """Approves dispatch constraints and fires the formal QWeb email template framework."""
        for record in self:
            if record.state != 'approved':
                raise UserError(_("Only approved requests can be dispatched."))
            # Write layout tracking changes
            record.write({
                'state': 'dispatched',
            })

            # Fetch our cleanly structured XML Template
            template = self.env.ref('eyekei_eyewear.email_template_material_request_dispatched_notification',raise_if_not_found=False)
            if template:
                # Render and send directly out through the email gateway spool
                template.send_mail(record.id, force_send=True)

        return True

    def action_alert_request_discrepancy(self):
        """Approves dispatch constraints and fires the formal QWeb email template framework."""
        for record in self:
            if record.state != 'dispatched':
                raise UserError(_("Only dispatched requests can be actioned."))
            # Write layout tracking changes
            record.write({
                'state': 'quantity_issue',
            })
            # Fetch our cleanly structured XML Template
            template = self.env.ref('eyekei_eyewear.email_template_material_request_received_discrepancy',raise_if_not_found=False)
            if template:
                # Render and send directly out through the email gateway spool
                template.send_mail(record.id, force_send=True)
        return True

    def action_material_request_mark_done(self):
        for rec in self:
            if rec.state in ['confirmed']:
                rec.write({"state": "done"})
    class StockWarehouse(models.Model):
        _inherit = 'stock.warehouse'

        is_main_distribution_center = fields.Boolean(
            string="Main Distribution Center",
            default=False,
            help="Check this box if this warehouse acts as the primary hub for distribution requests."
        )

    class StockLocation(models.Model):
        _inherit = 'stock.location'

        # Pulls the value directly from the parent warehouse dynamically
        is_main_distribution_location = fields.Boolean(
            string="Main Distribution Location",
            related="warehouse_id.is_main_distribution_center",
            store=True,
            readonly=False,
            help="Automatically reflects whether this location belongs to the Main Distribution Center."
        )

    class ResUsers(models.Model):
        _inherit = 'res.users'

        default_warehouse_id = fields.Many2one("stock.warehouse", string="Default Warehouse")