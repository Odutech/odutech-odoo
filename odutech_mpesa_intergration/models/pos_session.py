from odoo import api, fields, models, _


class PosSession(models.Model):
    _inherit = "pos.session"

    def _pos_ui_payment_method_fields(self):
        fields = super()._pos_ui_payment_method_fields()
        fields.append('is_mpesa')
        return fields
