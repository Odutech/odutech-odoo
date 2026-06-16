from odoo.http import request
import logging
import jwt
import datetime
_logger = logging.getLogger(__name__)

regex = r"^[a-z0-9!#$%&'*+\/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+\/=?^_`{|}~-]+)*@(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$"


class Validator:
    def key(self):
        return '★𝕭𝖊𝖂𝖆𝖗𝖊!_λx.x²+#42_᚛᚜_🛸~[KABOOM!]~{99%_Chaos_&_1%_Coffee}_Δt=0_ツ_★_kⱭ𝔶𝒪𝓈_01101001_⸎_¡YAY!_★'
    def verify(self, token):
        record = request.env['expense.user'].sudo().search([('access_token', '=', token)], order='create_date desc', limit=1)
        _logger.error(f'Checking the wrapper functionality update..111111...{record}')
        if len(record) != 1:
            return False
        if record.expiration_date > datetime.datetime.now():
            return False
        return True

    def verify_token(self, token):
        result = {
            'status': False,
            'message': 'Token invalid or expired',
            'id': 0,
            'code': 401  # Changed to 401 (Unauthorized)
        }
        try:
            # Decoding the token
            payload = jwt.decode(token, self.key(), algorithms=["HS256"])
            _logger.error(f'Checking the wrapper functionality update..111111...{payload}')
            # Check your custom Odoo 'jwt.access_token' table logic
            if not self.verify(token):
                _logger.error(f'Checking the wrapper functionality update..2222...{self.errorToken()}')
                return self.errorToken()
            uid = payload.get('sub')
            _logger.error(f'Checking the wrapper functionality update..333333...{self.errorToken()}')
            if not uid:
                return self.errorToken()
            _logger.error(f'Checking the wrapper functionality update..444444...{uid}---{result}')
            result.update({
                'id': uid,
                'status': True,
                'code': 200,
                'message': 'Token valid'
            })
            return result

        except (jwt.InvalidTokenError, jwt.ExpiredSignatureError):
            return self.errorToken()

    def errorToken(self):
        return {
            'message': 'Token invalid or expired',
            'code': 498,
            'status': False
        }

    def do_logout(self, token):
        self.cleanup()
        request.env['jwt.access_token'].sudo().search([
            ('token', '=', token)
        ]).unlink()

    def cleanup(self):
        request.session.logout()


validator = Validator()