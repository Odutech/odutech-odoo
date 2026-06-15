# -*- coding: utf-8 -*-
from odoo import models, fields, api


class MaterialRequestLine(models.Model):
    _name = "material.request.line"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Material Request Line"

    request_id = fields.Many2one(
        "material.request", string="Request Reference", ondelete="cascade"
    )

    # 1. Product
    product_id = fields.Many2one(
        "product.product", string="Product", required=True
    )

    # 2. Available Product Quantity (computed dynamically based on warehouse/location)
    qty_available = fields.Float(
        string="Available Quantity",
        compute="_compute_qty_available",
        store=False,
    )

    # 3. Requested Product (Quantity)
    qty_requested = fields.Float(
        string="Requested Quantity",default=1.0
    )

    qty_received = fields.Float(
        string="Received Quantity", default=1.0
    )

    # Fixed Typo from 'ompany_id' to 'company_id'
    company_id = fields.Many2one(
        "res.company", string="Company", related="request_id.company_id", store=True, index=True
    )

    @api.depends("product_id", "request_id.location_id")
    def _compute_qty_available(self):
        """Fetches the real-time physical stock quantity inside the specified location."""
        for line in self:
            if line.product_id and line.request_id.location_id:
                # Standard Odoo context way to extract stock info for a dedicated location
                product_ctx = line.product_id.with_context(location=line.request_id.location_id.id)
                line.qty_available = product_ctx.qty_available
            else:
                line.qty_available = 0.0