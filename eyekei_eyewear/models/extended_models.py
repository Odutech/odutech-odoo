from odoo import fields, models, api


class LenseType(models.Model):
    _name = 'eyekei.lens.type.categorization'
    _description = 'Lense Type'

    name = fields.Char()
    code = fields.Char(string="Code")
    lens_categorization = fields.Selection(
        [
            ("lens_type", "Lens Type"),
            ("lens_index", "Lens Index"),
            ("lens_coating", "Lens Tint"),
            ("lens_power", "Lens Power"),
            ("lens_material", "Lens Material"),
            ("lens_finish_type", "Lens Finish Type"),
            ("frame_brand", "Frame Brand"),
        ]
    )
