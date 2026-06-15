from odoo import models, fields, api


class StockLocation(models.Model):
    _inherit = "stock.location"

    location_type = fields.Selection(
        selection=[
            ("central_lab", "Central Lab"),
            ("clinic_stock", "Clinic Stock"),
            ("clinic_dispensary", "Clinic Dispensary"),
            ("external_vendor", "External Vendor Location"),
            ("production", "Production"),
            ("transit", "In Transit"),
            ("scrap", "Scrap"),
        ],
        string="Location Type",
        help="Categorizes the location for EyeKei Eyewear operations",
        index=True,
        tracking=True,
    )

    branch_id = fields.Many2one(
        "res.company",
        string="Branch",
        default=lambda self: self.env.company,
        help="The branch/company this location belongs to",
        index=True,
    )

    is_optical_location = fields.Boolean(
        default=False,
        string="Is Optical Location",
        help="True if this is a central lab, clinic stock, or dispensary location",
    )

    @api.onchange("location_type")
    def _compute_is_optical_location(self):
        optical_types = ["central_lab", "clinic_stock", "clinic_dispensary"]
        for location in self:
            location.is_optical_location = location.location_type in optical_types

    def name_get(self):
        """Override to show location type in display name."""
        result = []
        for location in self:
            name = location.name
            if location.location_type:
                name = f"[{location.location_type}] {name}"
            if location.branch_id and location.branch_id != self.env.company:
                name = f"{name} ({location.branch_id.name})"
            result.append((location.id, name))
        return result