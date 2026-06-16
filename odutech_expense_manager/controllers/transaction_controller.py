import jwt
from werkzeug.security import generate_password_hash, check_password_hash
from odoo.http import request
from odoo import http
import datetime
import logging

from .auth_wrapper import authenticate
from .utils import _response

_logger = logging.getLogger(__name__)
today = datetime.date.today()
SENSITIVE_FIELDS = ['portal_password', 'portal_password_crypt', 'portal_new_password', 'create_uid', 'write_uid']
allowed_origin = ['http://localhost:4200', 'http://dev.inkomoko.com:1082', 'http://dev.inkomoko.com:1091']

headers = [
    ('Access-Control-Allow-Credentials', 'true'),
    ('Access-Control-Allow-Origin', '*'),
    ('Access-Control-Allow-Headers', '*'),
    ('Access-Control-Allow-Credentials', 'true'),
    ('Access-Control-Allow-Methods', 'POST, OPTIONS, GET, PUT'),
    ('Access-Control-Max-Age', '3600')
]

class TransactionsController(http.Controller):
    @http.route('/api/v1/create_transaction', type='json', auth='none', methods=['POST'], csrf=False)
    @authenticate
    def create_transaction(self, **kwargs):
        """
        Expects payload: email, amount, type, category_id, date_creation (optional)
        Creates a new entry in expense.transaction.
        """
        _logger.error(f"CHECKING THE AUTHORIZATION SETUP FOR THIS TYPE ...--")
        return _response(200, "success", "Created new transaction", {})
        user_id = request.jwt_uid
        _logger.error(f"CHECKING THE AUTHORIZATION SETUP FOR THIS TYPE ...--{user_id}")
        user = request.env['expense.user'].sudo().browse(int(user_id))
        return _response(200,"success","Created new transaction",user)