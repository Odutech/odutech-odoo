from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = "product.template"

    # Optical Product Classification
    is_optical_product = fields.Boolean("Is Optical Product", index=True)
    optical_type = fields.Selection(
        [
            ("frame", "Eyewear Frame"),
            ("lens", "Optical Lens"),
            ("accessory", "Optical Accessory"),
            ("service", "Optical Service"),
        ],
        string="Optical Product Type",
    )

    # Frame-specific attributes
    frame_brand = fields.Many2one("eyekei.lens.type.categorization",string="Frame Brand",domain=[("lens_categorization","=","frame_brand")])
    frame_type = fields.Selection(
        [
            ("metal", "Metal"),
            ("plastic", "Plastic"),
            ("rimless", "Rimless"),
            ("kids", "Kids"),
            ("sports", "Sports"),
        ]
    )
    frame_color = fields.Char("Color")
    frame_size = fields.Char("Size (e.g., 52-18-140)")

    # Lens-specific attributes
    lens_type = fields.Many2one("eyekei.lens.type.categorization",string="Lens Type",domain=[("lens_categorization","=","lens_type")])
    lens_index = fields.Many2one("eyekei.lens.type.categorization",string="Lens Index",domain=[("lens_categorization","=","lens_index")])
    lens_coating = fields.Many2one("eyekei.lens.type.categorization",string="Lens Coating",domain=[("lens_categorization","=","lens_coating")])
    lens_material = fields.Many2one("eyekei.lens.type.categorization",string="Lens Material",domain=[("lens_categorization","=","lens_material")])
    lens_power = fields.Many2one("eyekei.lens.type.categorization",string="Lens Power",domain=[("lens_categorization","=","lens_power")])

    # Stock location preferences
    default_stock_location = fields.Selection(
        [
            ("central_lab", "Central Lab Only"),
            ("clinic", "Clinic Stock Allowed"),
            ("both", "Both Locations"),
        ],
        default="both",
    )

    # For lenses: track if it's a "semi-finished" or "finished" lens
    lens_finish_type = fields.Many2one("eyekei.lens.type.categorization",string="Lens Finish Type",domain=[("lens_categorization","=","lens_finish_type")])

    # Minimum stock alerts (optical specific)
    optical_minimum_stock = fields.Integer("Minimum Optical Stock")

    @api.constrains("optical_type", "tracking")
    def _check_optical_tracking(self):
        """Lenses should use lots for power tracking, frames can use serial or none"""
        for product in self:
            if product.optical_type == "lens" and product.tracking == "serial":
                raise ValidationError(
                    _(
                        "Lenses should use Lot tracking (for power batches), not Serial tracking"
                    )
                )

    def action_update_optical_stock(self):
        """Quick stock update wizard for optical products"""
        self.ensure_one()
        return {
            "name": _("Update Optical Stock"),
            "type": "ir.actions.act_window",
            "res_model": "eyekei.stock.update.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_product_id": self.id},
        }


class ProductProduct(models.Model):
    _inherit = "product.product"

    # Computed field to check availability for specific branch
    branch_stock_quantity = fields.Float(
        "Branch Stock",
        compute="_compute_branch_stock_quantity",
        help="Available quantity in current user branch",
        store=True,
    )

    # For lens variants: store the power/sph/cyl if using variants
    lens_power_sph = fields.Float("Sphere Power")
    lens_power_cyl = fields.Float("Cylinder Power")
    lens_power_axis = fields.Integer("Axis")

    def _compute_branch_stock_quantity(self):
        """Calculate available stock for current user's branch"""
        for product in self:
            # Get stock for current company/branch
            quants = self.env["stock.quant"].search(
                [
                    ("product_id", "=", product.id),
                    ("location_id.branch_id", "in", self.env.user.company_ids.ids),
                    ("location_id.usage", "=", "internal"),
                    ("quantity", ">", 0),
                ]
            )
            product.branch_stock_quantity = sum(quants.mapped("quantity"))

    def get_optical_stock_for_location(self, location_type="central_lab"):
        """Get stock quantity for specific location type"""
        self.ensure_one()
        locations = self.env["stock.location"].search(
            [("usage", "=", "internal"), ("location_type", "=", location_type)]
        )
        quants = self.env["stock.quant"].search(
            [("product_id", "=", self.id), ("location_id", "in", locations.ids)]
        )
        return sum(quants.mapped("quantity"))


class StockLocation(models.Model):
    _inherit = "stock.location"

    # Add type for optical business logic
    location_type = fields.Selection(
        [
            ("central_lab", "Central Lab"),
            ("clinic_stock", "Clinic Stock"),
            ("clinic_dispensary", "Clinic Dispensary"),
            ("external_vendor", "External Vendor Location"),
        ]
    )
    branch_id = fields.Many2one(
        "res.company", "Branch", default=lambda self: self.env.company
    )


class StockQuant(models.Model):
    _inherit = "stock.quant"

    # Add optical-specific context
    is_reserved_for_job = fields.Boolean("Reserved for Lab Job", default=False)
    reserved_job_id = fields.Many2one("eyekei.lab.job", "Reserved For Job")
