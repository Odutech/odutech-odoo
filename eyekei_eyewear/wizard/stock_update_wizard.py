from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class StockUpdateWizard(models.TransientModel):
    _name = "eyekei.stock.update.wizard"
    _description = "Quick Optical Stock Update"

    product_id = fields.Many2one(
        "product.product",
        "Product",
        required=True,
        domain="[('is_optical_product', '=', True), ('type', '=', 'consu')]",
    )
    location_id = fields.Many2one(
        "stock.location",
        "Location",
        required=True,
        domain="[('usage', '=', 'internal'), ('is_optical_location', '=', True)]",
        default=lambda self: self.env["stock.location"].search(
            [("usage", "=", "internal"), ("is_optical_location", "=", True)], limit=1
        ),
    )
    current_quantity = fields.Float(
        "Current Quantity", compute="_compute_current_quantity", readonly=True
    )
    new_quantity = fields.Integer("New Quantity", required=True)
    reason = fields.Text("Reason for Adjustment", required=True)

    @api.depends("product_id", "location_id")
    def _compute_current_quantity(self):
        for wizard in self:
            if wizard.product_id and wizard.location_id:
                quant = self.env["stock.quant"].search(
                    [
                        ("product_id", "=", wizard.product_id.id),
                        ("location_id", "=", wizard.location_id.id),
                    ],
                    limit=1,
                )
                wizard.current_quantity = quant.quantity if quant else 0
            else:
                wizard.current_quantity = 0

    @api.onchange("product_id")
    def _onchange_product_id(self):
        """Auto-select default location for product"""
        if self.product_id and not self.location_id:
            # Get location based on product default_stock_location
            if self.product_id.default_stock_location == "central_lab":
                self.location_id = self.env["stock.location"].search(
                    [("location_type", "=", "central_lab"), ("usage", "=", "internal")],
                    limit=1,
                )
            else:
                self.location_id = self.env["stock.location"].search(
                    [
                        ("location_type", "in", ["clinic_stock", "clinic_dispensary"]),
                        ("usage", "=", "internal"),
                    ],
                    limit=1,
                )

    def action_update_stock(self):
        """Update stock.quant directly for optical products.

        Uses direct quant update for immediate stock adjustment with proper
        audit trail and validation.
        """
        self.ensure_one()

        # Validate permissions
        if not self.env.user.has_group("eyekei_eyewear.group_eyekei_manager"):
            # Non-managers need approval for negative adjustments
            if self.new_quantity < self.current_quantity:
                raise ValidationError(
                    _(
                        "Stock reductions require manager approval. "
                        "Please contact your supervisor."
                    )
                )

        # Calculate difference
        difference = self.new_quantity - self.current_quantity

        if difference == 0:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("No Change"),
                    "message": _("New quantity is same as current quantity."),
                    "type": "info",
                    "next": {"type": "ir.actions.act_window_close"},
                },
            }

        # Get or create stock quant for this product/location
        quant = self.env["stock.quant"].search(
            [
                ("product_id", "=", self.product_id.id),
                ("location_id", "=", self.location_id.id),
                ("lot_id", "=", False),  # No lot tracking for optical products
            ],
            limit=1,
        )

        if quant:
            # Update existing quant
            old_quantity = quant.quantity
            quant.write(
                {
                    "quantity": self.new_quantity,
                }
            )
        else:
            # Create new quant if doesn't exist
            old_quantity = 0
            quant = self.env["stock.quant"].create(
                {
                    "product_id": self.product_id.id,
                    "location_id": self.location_id.id,
                    "quantity": self.new_quantity,
                }
            )

        # Create stock move for audit trail
        inventory_location = self.env["stock.location"].search(
            [
                ("usage", "=", "inventory"),
                ("company_id", "in", [self.env.company.id, False]),
            ],
            limit=1,
        )

        if not inventory_location:
            # Fallback: Use same location for both source/dest
            move_vals = {
                "reference": _("Stock Adjustment: %s") % self.product_id.name,
                "product_id": self.product_id.id,
                "product_uom_qty": abs(difference),
                "product_uom": self.product_id.uom_id.id,
                "location_id": self.location_id.id,
                "location_dest_id": self.location_id.id,
                "origin": self.reason[:50] if self.reason else "Stock Update Wizard",
                "state": "done",
            }
        else:
            # Standard inventory adjustment move
            move_vals = {
                "reference": _("Stock Adjustment: %s") % self.product_id.name,
                "product_id": self.product_id.id,
                "product_uom_qty": abs(difference),
                "product_uom": self.product_id.uom_id.id,
                "location_id": (
                    self.location_id.id if difference < 0 else inventory_location.id
                ),
                "location_dest_id": (
                    inventory_location.id if difference < 0 else self.location_id.id
                ),
                "origin": self.reason[:50] if self.reason else "Stock Update Wizard",
                "state": "done",
            }

        move = self.env["stock.move"].create(move_vals)
        move._action_done()

        # Log to optical audit trail
        self.env["eyekei.stock.audit"].create(
            {
                "product_id": self.product_id.id,
                "location_id": self.location_id.id,
                "previous_quantity": self.current_quantity,
                "new_quantity": self.new_quantity,
                "reason": self.reason,
                "user_id": self.env.user.id,
                "inventory_id": move.id,
            }
        )

        # Post message to product chatter
        self.product_id.message_post(
            body=_(
                "Stock updated via Quick Update Wizard:<br/>"
                "Location: %s<br/>"
                "Previous: %s → New: %s<br/>"
                "Reason: %s<br/>"
                "By: %s"
            )
            % (
                self.location_id.display_name,
                self.current_quantity,
                self.new_quantity,
                self.reason,
                self.env.user.name,
            ),
            message_type="comment",
        )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Stock Updated"),
                "message": _("%s quantity updated from %s to %s at %s")
                % (
                    self.product_id.name,
                    self.current_quantity,
                    self.new_quantity,
                    self.location_id.name,
                ),
                "type": "success",
                "next": {"type": "ir.actions.act_window_close"},
            },
        }

    def action_cancel(self):
        return {"type": "ir.actions.act_window_close"}


class StockAuditLog(models.Model):
    _name = "eyekei.stock.audit"
    _description = "Optical Stock Adjustment Audit Log"
    _order = "create_date desc"

    name = fields.Char("Reference", readonly=True)
    product_id = fields.Many2one(
        "product.product", "Product", required=True, index=True, readonly=True
    )
    location_id = fields.Many2one(
        "stock.location", "Location", required=True, readonly=True
    )
    previous_quantity = fields.Float("Previous Qty", readonly=True)
    new_quantity = fields.Float("New Qty", readonly=True)
    difference = fields.Float("Difference", compute="_compute_difference")
    reason = fields.Text("Reason", required=True, readonly=True)
    user_id = fields.Many2one(
        "res.users", "Adjusted By", default=lambda s: s.env.user, readonly=True
    )
    inventory_id = fields.Many2one("stock.quant", "Inventory Adjustment", readonly=True)
    create_date = fields.Datetime("Date", readonly=True)

    def _compute_difference(self):
        for audit in self:
            audit.difference = audit.new_quantity - audit.previous_quantity

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "eyekei.stock.audit"
                )
        return super().create(vals_list)
