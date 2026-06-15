from odoo import models, fields, api


class StockMovement(models.Model):
    _name = "eyekei.stock.movement"
    _description = "Stock Movement Audit Trail"
    _order = "create_date desc"

    product_type = fields.Selection(
        [("frame", "Frame"), ("lens", "Lens"), ("accessory", "Accessory")]
    )
    product_id = fields.Integer("Product ID")  # Generic reference
    product_name = fields.Char("Product Name", compute="_compute_product_name")

    movement_type = fields.Selection(
        [
            ("purchase", "Purchase"),
            ("sale", "Sale"),
            ("job_usage", "Job Usage"),
            ("reserve", "Reservation"),
            ("deduct", "Stock Deduction"),
            ("adjustment", "Adjustment"),
            ("transfer", "Branch Transfer"),
            ("return", "Return"),
        ]
    )

    quantity = fields.Integer("Quantity")
    reference = fields.Char("Reference (Job/Invoice)")
    reason = fields.Text("Reason")
    user_id = fields.Many2one("res.users", "User", default=lambda self: self.env.user)
    branch_id = fields.Many2one("res.company", "Branch")
    date = fields.Datetime("Date", default=fields.Datetime.now)

    def _compute_product_name(self):
        for move in self:
            if move.product_type == "frame":
                product = self.env["eyekei.inventory.frame"].browse(move.product_id)
            elif move.product_type == "lens":
                product = self.env["eyekei.inventory.lens"].browse(move.product_id)
            else:
                product = self.env["eyekei.inventory.accessory"].browse(move.product_id)
            move.product_name = product.name if product.exists() else "Unknown"
