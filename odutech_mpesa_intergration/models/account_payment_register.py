import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    mpesa_phone_number = fields.Char(string="M-Pesa Phone Number", size=15)
    mpesa_code = fields.Char(
        related='payment_method_line_id.code',
        store=True,
        readonly=True,
    )

    def action_create_payments(self):
        if self.mpesa_code == 'mpesa':
            """Send STK Push using payment provider."""
            self.ensure_one()
            if not self.mpesa_phone_number:
                raise UserError(_("Please enter a phone number for M-Pesa payment."))
            # if self.currency_id.id  not in self.payment_method_line_id.payment_provider_id.available_currency_ids.ids:
            #     raise UserError(_("Please enter a currency allowed by mpesa method"))
            # # Find the M-Pesa provider
            provider = self.env['payment.provider'].sudo().search([('code', '=', 'mpesa')], limit=1)
            if not provider:
                raise UserError(_("M-Pesa payment provider is not configured."))
            # Compute reference and amount
            ref = self.communication or self.name or "Odoo Payment"
            amount = self.amount
            payment_method_id = self.env['payment.method'].search([('code', '=', 'mpesa'), ('active', '=', True)],
                                                                  limit=1)
            if not payment_method_id:
                raise UserError(_("Configure payment method with mpesa as code"))
            # Trigger STK Push via provider
            response = provider._mpesa_stk_push(
                reference=ref,
                amount=amount,
                phone_number=self.mpesa_phone_number
            )
            logging.error(f'M-Pesa Error: {response.get("CheckoutRequestID")}')
            if response.get('ResponseCode') == '0':
                payment_transactions = self.env['payment.transaction'].create({
                    'reference': response.get("CheckoutRequestID"),
                    'checkout_id': response.get("CheckoutRequestID"),
                    'amount': amount,
                    'payment_method_id': payment_method_id.id,
                    'provider_id': self.payment_method_line_id.payment_provider_id.id,
                    'partner_id': self.partner_id.id,
                    'provider_reference': ref,
                    'currency_id': self.currency_id.id,
                })
                if payment_transactions:
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': 'Success',
                            'message': 'STK Push sent successfully! Check your phone to complete payment.',
                            'next': {'type': 'ir.actions.act_window_close'},  # Optional: close the current wizard/modal
                            'sticky': False,  # True to keep it on screen until user closes
                            'type': 'success',  # Set the type for success styling
                        }
                    }
            else:
                error = response.get('errorMessage', 'Failed to initiate STK Push.')
                raise UserError(_("M-Pesa Error: %s") % error)
            return {'type': 'ir.actions.act_window_close'}
        else:
            return super(AccountPaymentRegister, self).action_create_payments()
