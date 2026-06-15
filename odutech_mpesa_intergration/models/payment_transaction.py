from odoo import api, fields, models, _


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    phone_number = fields.Char(string="Phone Number", size=15)
    checkout_id = fields.Char(string="Checkout ID",unique=True)

