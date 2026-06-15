from datetime import datetime
from odoo import api, fields, models, _
from odoo import http
from odoo.http import request
import json
import logging


_logger = logging.getLogger(__name__)


class MpesaController(http.Controller):

    @http.route(['/payment/mpesa/callback'], type='json', auth='public', methods=['POST'], csrf=False)
    def mpesa_callback(self):
        """ STK Push callback from Safaricom """
        data = json.loads(request.httprequest.data or "{}")
        _logger.error(data)
        # 254716244085
        body = data.get('Body', {}).get('stkCallback', {})
        result_code = body.get('ResultCode')
        checkout_request_id = body.get('CheckoutRequestID')
        # Extract metadata
        metadata = {item.get("Name"): item.get("Value") for item in body.get("CallbackMetadata", {}).get("Item", [])}
        # metadata = {item["Name"]: item["Value"] for item in body.get("CallbackMetadata", {}).get("Item",[])}
        phone = metadata.get("PhoneNumber")
        account_ref = metadata.get("MpesaReceiptNumber")
        tx = request.env['payment.transaction'].sudo().search([('checkout_id', '=', checkout_request_id)], limit=1)
        if tx:
            if result_code == 0:
                # _logger.error("Payment not success due to ")
                tx.sudo().write({'reference':account_ref,'partner_phone':phone})
                # _logger.error(f"Payment status----{tx.state}")
                tx._set_done()
                tx._post_process()
                if tx.payment_id:
                    tx.payment_id.action_validate()
            else:
                _logger.error("Payment not failed due to ",)
                tx._set_canceled("M-Pesa payment failed")
            return {"status": "ok"}
        else:
            _logger.error("Payment not found for now ")
            return {"status": "error", "message": "Transaction not found"}

    @http.route(['/payment/c2b/confirmation'], type='json', auth='public', methods=['POST'], csrf=False)
    def mpesa_c2b_confirmation(self):
        """Receive actual C2B Payments (Paybill or Till)."""
        data = json.loads(request.httprequest.data or "{}")
        trans_id = data.get("TransID")
        amount = float(data.get("TransAmount", 0))
        bill_ref = data.get("BillRefNumber")
        phone = data.get("MSISDN")
        trans_time = data.get("TransTime")
        short_code = data.get("BusinessShortCode")
        firstname = data.get("FirstName")

        if amount or trans_id:
            # Convert TransTime (e.g. 20250220104520)
            parsed_dt = False
            try:
                parsed_dt = datetime.strptime(trans_time, "%Y%m%d%H%M%S")
            except Exception:
                parsed_dt = fields.Datetime.now()

            # Prevent duplicates
            existing = request.env['mpesa.till.payment'].sudo().search([
                ('trans_id', '=', trans_id)
            ], limit=1)

            if not existing:
                request.env['mpesa.till.payment'].sudo().create({
                    'amount': amount,
                    'masked_msisdn': phone,
                    'trans_id': trans_id,
                    'trans_time': parsed_dt,
                    'till_number': short_code,
                    'status': 'new',
                    'first_name': firstname,
                })

            return {"ResultCode": 0, "ResultDesc": "Till Payment Accepted"}

        # Try to match Paybill payment to existing transaction
        tx = request.env['payment.transaction'].sudo().search([
            ('reference', '=', bill_ref),
            ('amount', '=', amount),
            ('state', '=', 'pending')
        ], limit=1)

        if tx:
            tx._set_done()
            return {"ResultCode": 0, "ResultDesc": "Paybill Payment Accepted"}

        # No transaction found — still accept to avoid Safaricom retries
        return {"ResultCode": 0, "ResultDesc": "Accepted"}

    @http.route(['/payment/c2b/validate'], type='json', auth='public', methods=['POST'], csrf=False)
    def mpesa_c2b_validate(self):
        data = json.loads(request.httprequest.data or "{}")
        # Always accept for now
        return {"ResultCode": 0, "ResultDesc": "Accepted"}


class MpesaPaymentController(http.Controller):

    @http.route('/payment/mpesa/start', type='http', auth='public', website=True)
    def mpesa_start(self, order_id=None, **kw):
        """
        Render a page asking the user for their M-Pesa phone number before initiating STK Push.
        """
        # Validate order_id
        if not order_id:
            return request.render('odutech_mpesa_intergration.payment_error_page', {
                'error_message': 'Order ID not provided.'
            })

        try:
            sale_order = request.env['sale.order'].sudo().browse(int(order_id))
        except (ValueError, TypeError):
            return request.render('odutech_mpesa_intergration.payment_error_page', {
                'error_message': 'Invalid order ID.'
            })

        if not sale_order.exists():
            return request.render('odutech_mpesa_intergration.payment_error_page', {
                'error_message': 'Order not found.'
            })

        return f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>M-Pesa Payment</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
                background: linear-gradient(135deg, #f0f9f4, #e0f7ea);
            }}
            .payment-container {{
                background: #fff;
                padding: 2.5rem 2rem;
                border-radius: 12px;
                box-shadow: 0 8px 20px rgba(0,0,0,0.1);
                width: 100%;
                max-width: 400px;
                text-align: center;
            }}
            .mpesa-logo img {{
                max-width: 160px;
                margin-bottom: 1.5rem;
            }}
            .order-info {{
                margin-bottom: 1.5rem;
                font-weight: 600;
                font-size: 1.1rem;
                color: #333;
            }}
            form {{
                display: flex;
                flex-direction: column;
                gap: 1rem;
            }}
            .form-group {{
                text-align: left;
                width: 100%;
            }}
            label {{
                display: block;
                margin-bottom: 0.5rem;
                font-weight: 500;
                color: #555;
            }}
            input[type="text"] {{
                width: 100%;
                padding: 0.65rem;
                border: 1px solid #ccc;
                border-radius: 6px;
                font-size: 1rem;
                transition: border-color 0.2s;
                box-sizing: border-box;
            }}
            input[type="text"]:focus {{
                border-color: #00a859;
                outline: none;
            }}
            button {{
                width: 100%;
                padding: 0.75rem;
                background-color: #00a859;
                color: #fff;
                border: none;
                border-radius: 6px;
                cursor: pointer;
                font-size: 1.05rem;
                font-weight: 600;
                transition: background-color 0.3s, transform 0.2s;
                box-sizing: border-box;
            }}
            button:hover {{
                background-color: #007a45;
                transform: translateY(-2px);
            }}
            button:disabled {{
                background-color: #ccc;
                cursor: not-allowed;
                transform: none;
            }}
            .progress-container {{
                display: none;
                margin-top: 1.5rem;
            }}
            .progress-bar {{
                width: 0%;
                height: 20px;
                background-color: #00a859;
                border-radius: 6px;
                transition: width 0.3s;
            }}
            .progress-wrapper {{
                width: 100%;
                background: #e0e0e0;
                border-radius: 6px;
                overflow: hidden;
            }}
            .footer-note {{
                margin-top: 1.5rem;
                font-size: 0.85rem;
                color: #888;
            }}
        </style>
        </head>
        <body>
        <div class="payment-container">
            <div class="mpesa-logo">
                <img src="/odutech_mpesa_intergration/static/description/mpesa.jpg" alt="M-Pesa">
            </div>
            <div class="order-info">
                Order: {sale_order.name}<br>
                Amount: {sale_order.amount_total} {sale_order.currency_id.symbol}
            </div>
            <form id="mpesaForm">
                <input type="hidden" name="order_id" value="{sale_order.id}">
                <div class="form-group">
                    <label for="phone">Phone Number (2547XXXXXXXX)</label>
                    <input type="text" id="phone" name="phone" placeholder="e.g. 254712345678" required>
                </div>
                <button type="submit" id="payButton">Confirm & Pay</button>
            </form>
            <div class="progress-container" id="progressContainer">
                <div class="progress-wrapper">
                    <div class="progress-bar" id="progressBar"></div>
                </div>
                <p id="progressText">Waiting for payment...</p>
            </div>
            <div class="footer-note">
                Secure payment via M-Pesa
            </div>
        </div>

        <script>
        const form = document.getElementById('mpesaForm');
        const payButton = document.getElementById('payButton');
        const progressContainer = document.getElementById('progressContainer');
        const progressBar = document.getElementById('progressBar');
        const progressText = document.getElementById('progressText');

        form.addEventListener('submit', async function(e) {{
            e.preventDefault();
            const phone = document.getElementById('phone').value.trim();
            const orderId = form.querySelector('input[name="order_id"]').value;

            payButton.disabled = true;
            payButton.textContent = 'Processing...';
            progressContainer.style.display = 'block';
            progressBar.style.width = '10%';
            progressText.textContent = 'Initiating STK push...';

            const response = await fetch('/payment/mpesa/initiate', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ phone, order_id: orderId }})
            }});

            const data = await response.json();
            if (data.status !== 'initiated') {{
                progressText.textContent = data.error || 'Failed to initiate payment.';
                progressBar.style.backgroundColor = 'red';
                payButton.disabled = false;
                payButton.textContent = 'Confirm & Pay';
                return;
            }}

            progressText.textContent = 'Payment initiated. Waiting for completion...';
            const checkoutId = data.checkout_id;
            let progress = 10;

            const interval = setInterval(async () => {{
                progress = Math.min(progress + 10, 90);
                progressBar.style.width = progress + '%';

                const res = await fetch('/payment/mpesa/status', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ checkout_id: checkoutId }})
                }});
                const statusData = await res.json();

                if (statusData.status === 'done') {{
                    clearInterval(interval);
                    progressBar.style.width = '100%';
                    progressText.textContent = 'Payment completed!';
                    window.location.href = `/payment/status?reference=${{checkoutId}}`; 
                }} else if (statusData.status === 'failed') {{
                    clearInterval(interval);
                    progressBar.style.backgroundColor = 'red';
                    progressText.textContent = 'Payment failed. Try again.';
                    payButton.disabled = false;
                    payButton.textContent = 'Confirm & Pay';
                }}
            }}, 2000);
        }});
        </script>
        </body>
        </html>
        """

    @http.route('/payment/mpesa/initiate', type='http', auth='public', csrf=False, methods=['POST'])
    def mpesa_initiate(self, **kw):
        """Initiate M-Pesa STK Push"""
        try:
            data = json.loads(request.httprequest.data.decode('utf-8'))
        except Exception:
            data = kw  # fallback if content-type or body malformed

        order_id = data.get('order_id')
        phone_number = data.get('phone')

        if not order_id:
            return request.make_response(
                json.dumps({'status': 'failed', 'error': 'Missing order_id'}),
                headers=[('Content-Type', 'application/json')]
            )

        sale_order = request.env['sale.order'].sudo().browse(int(order_id))
        if not sale_order.exists():
            return request.make_response(
                json.dumps({'status': 'failed', 'error': 'Order not found'}),
                headers=[('Content-Type', 'application/json')]
            )

        mpesa_provider = request.env['payment.provider'].sudo().search([('code', '=', 'mpesa')], limit=1)
        if not mpesa_provider:
            return request.make_response(
                json.dumps({'status': 'failed', 'error': 'M-Pesa provider not configured'}),
                headers=[('Content-Type', 'application/json')]
            )

        # --- Initiate STK push ---
        try:
            response = mpesa_provider._mpesa_stk_push(sale_order.name, sale_order.amount_total, phone_number)
        except Exception as e:
            return request.make_response(
                json.dumps({'status': 'failed', 'error': 'Failed to contact M-Pesa gateway'}),
                headers=[('Content-Type', 'application/json')]
            )

        # --- Handle successful response ---
        if response.get('ResponseCode') == '0':
            checkout_id = response.get('CheckoutRequestID')
            payment_method = request.env['payment.method'].sudo().search([('code', '=', 'mpesa')], limit=1)
            tx = request.env['payment.transaction'].sudo().create({
                'reference': checkout_id,
                'checkout_id': checkout_id,
                'amount': sale_order.amount_total,
                'currency_id': sale_order.currency_id.id,
                'partner_id': sale_order.partner_id.id,
                'payment_method_id': payment_method.id if payment_method else False,
                'provider_id': mpesa_provider.id,
                'provider_reference': sale_order.name,
                # 'sale_order_ids': [(4, sale_order.id)]
            })
            # if tx:
            #     tx.sudo().write({"sale_order_ids": [(6, 0, [sale_order.id])]})
            return request.make_response(
                json.dumps({'status': 'initiated', 'checkout_id': checkout_id}),
                headers=[('Content-Type', 'application/json')]
            )

        # --- Handle failed STK push ---
        error_message = response.get('errorMessage', 'Failed to initiate STK Push')
        return request.make_response(
            json.dumps({'status': 'failed', 'error': error_message}),
            headers=[('Content-Type', 'application/json')]
        )

    # --- STATUS CHECK ---
    @http.route('/payment/mpesa/status', type='http', auth='public', csrf=False, methods=['POST'])
    def mpesa_status(self, **kw):
        """Check payment transaction status"""
        try:
            data = json.loads(request.httprequest.data.decode('utf-8'))
        except Exception:
            data = kw

        checkout_id = data.get('checkout_id')
        if not checkout_id:
            return request.make_response(
                json.dumps({'status': 'failed', 'error': 'Missing checkout ID'}),
                headers=[('Content-Type', 'application/json')]
            )

        tx = request.env['payment.transaction'].sudo().search([
            ('checkout_id', '=', checkout_id)
        ], limit=1)
        if not tx:
            return request.make_response(
                json.dumps({'status': 'pending'}),
                headers=[('Content-Type', 'application/json')]
            )

        if tx.state == 'done':
            status = 'done'
        elif tx.state in ('cancel', 'error'):
            status = 'failed'
        else:
            status = 'pending'

        return request.make_response(
            json.dumps({'status': status}),
            headers=[('Content-Type', 'application/json')]
        )

    @http.route('/payment/mpesa/check_payment', type='json', auth='public', csrf=False)
    def check_payment(self, phone=None, amount=None):
        """Check if payment was received on Paybill/Till"""
        if not phone or not amount:
            return {'status': 'failed', 'error': 'Missing phone or amount'}

        payment = request.env['payment.transaction'].sudo().search([
            ('partner_id.phone', '=', phone),
            ('amount', '=', amount),
            ('state', '=', 'done')
        ], limit=1)

        if payment:
            return {'status': 'done'}
        else:
            return {'status': 'pending'}