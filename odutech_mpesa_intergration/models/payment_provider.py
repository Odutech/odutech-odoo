from odoo import api, fields, models, _
from odoo.addons.payment.models.payment_provider import PaymentProvider
import requests
import base64
import json
from datetime import datetime

import logging

_logger = logging.getLogger(__name__)


class PaymentProviderMpesa(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('mpesa', "M-Pesa")],
        ondelete={'mpesa': 'set default'}
    )

    mpesa_consumer_key = fields.Char("Consumer Key")
    mpesa_consumer_secret = fields.Char("Consumer Secret")
    mpesa_short_code = fields.Char("Short Code")
    mpesa_passkey = fields.Char("Passkey")
    mpesa_base_url = fields.Char("API Base URL")
    mpesa_callback_url = fields.Char("Mpesa Callback URL")
    mpesa_registered_safaricom_url = fields.Char("Mpesa Registered Safaricom URL")

    @api.model
    def _mpesa_get_access_token(self):
        self.ensure_one()
        url = f"{self.mpesa_base_url}/oauth/v1/generate?grant_type=client_credentials"
        response = requests.get(url, auth=(self.mpesa_consumer_key, self.mpesa_consumer_secret))
        return response.json().get('access_token')

    def _mpesa_stk_push(self, reference, amount, phone_number):
        self.ensure_one()
        access_token = self._mpesa_get_access_token()
        logging.error(f"Mpesa stk_push access_token: {access_token}")
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        password = base64.b64encode(
            f"{self.mpesa_short_code}{self.mpesa_passkey}{timestamp}".encode()
        ).decode()

        payload = {
            "BusinessShortCode": self.mpesa_short_code,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": int(amount),
            "PartyA": phone_number,
            "PartyB": self.mpesa_short_code,
            "PhoneNumber": phone_number,
            "CallBackURL": f"{self.mpesa_callback_url}",
            "AccountReference": reference,
            "TransactionDesc": "Payment via Odoo"
        }

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        url = f"{self.mpesa_base_url}/mpesa/stkpush/v1/processrequest"
        res = requests.post(url, json=payload, headers=headers)

        return res.json()

    def _get_processing_values(self, transaction, **kwargs):
        """Return processing values for the Mpesa payment flow."""
        res = super()._get_processing_values(transaction, **kwargs)
        if self.code != 'mpesa':
            return res

        _logger.info("Building processing values for Mpesa transaction %s", transaction.reference)

        base_url = self.get_base_url()
        redirect_url = f"{base_url}/payment/mpesa/start"

        # Build HTML form Odoo JS expects
        form_html = f"""
            <form action="{redirect_url}" method="POST">
                <input type="hidden" name="reference" value="{transaction.reference}"/>
                <input type="hidden" name="amount" value="{transaction.amount}"/>
                <input type="hidden" name="currency_id" value="{transaction.currency_id.id}"/>
                <input type="hidden" name="partner_id" value="{transaction.partner_id.id}"/>
                <button type="submit" class="btn btn-primary d-none">Continue with M-Pesa</button>
            </form>
        """

        # This key is critical — it’s what Odoo’s frontend looks for
        res.update({
            'redirect_form_html': form_html,
        })

        _logger.info("Mpesa redirect form prepared for transaction %s", transaction.reference)
        return res