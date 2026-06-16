from odoo.http import request
import logging
import datetime

_logger = logging.getLogger(__name__)

class Validator:
    def verify_token_and_decode(self, token):
        try:
            if not token:
                return None, "Token missing."
            now_naive = datetime.datetime.now()
            token_record = request.env['expense.user.token'].sudo().search([
                ('token', '=', token)
            ], limit=1)
            if not token_record:
                return None, "Invalid authentication token."
            if token_record.expiration_date <= now_naive:
                token_record.unlink()
                return None, "Your session has expired. Please log in again."

            payload = {
                'sub': token_record.user_id.id,
                'email': token_record.user_id.email
            }
            return payload, None

        except Exception as e:
            _logger.error(f"Unexpected token validation error: {str(e)}", exc_info=True)
            return None, "An unexpected error occurred while parsing the token."

    def do_logout(self, token):
        request.session.logout()
        request.env['expense.user.token'].sudo().search([
            ('token', '=', token)
        ]).unlink()

validator = Validator()