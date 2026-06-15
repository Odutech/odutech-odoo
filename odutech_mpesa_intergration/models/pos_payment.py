from odoo import api, fields, models, _


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    is_mpesa = fields.Boolean(string="Is M-Pesa Payment?", default=False)
