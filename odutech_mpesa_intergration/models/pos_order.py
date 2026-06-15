from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = "pos.order"

    account_reference = fields.Char("Account Reference")

    @api.model
    def check_mpesa_payment(self, full_phone, amount):
        """
        Validates a Till payment using:
          - Full phone number entered by cashier
          - Amount
        Matches against Safaricom masked MSISDN:
          e.g.  full: 254712345126
                masked: 2547*****126
        """
        TillPayment = request.env['mpesa.till.payment'].sudo()
        print("Checking payment for:", full_phone, amount)

        # Extract visible parts from full number
        prefix = full_phone[:4]  # e.g. 2547
        suffix = full_phone[-3:]  # e.g. 126

        amount = round(float(amount), 2)

        payment = TillPayment.search([
            ('amount', '=', amount),
            ('status', '=', 'new'),
            ('masked_msisdn', 'like', prefix + '%'),
            ('masked_msisdn', 'like', '%' + suffix),
        ], limit=1)

        if payment:
            payment.write({'status': 'used'})
            return {
                "status": "done",
                "message": "Payment verified",
                "trans_id": payment.trans_id
            }

        return {
            "status": "pending",
            "message": "Payment not found yet"
        }


class MpesaTillPayment(models.Model):
    _name = 'mpesa.till.payment'
    _description = 'M-Pesa Till Payment Inbox'

    amount = fields.Float()
    masked_msisdn = fields.Char()
    trans_id = fields.Char()
    trans_time = fields.Datetime()
    till_number = fields.Char()
    status = fields.Selection([
        ('new', 'New'),
        ('used', 'Used')
    ], default='new')
    pos_order_id = fields.Many2one('pos.order')
    first_name = fields.Char()
