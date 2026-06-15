import logging
import json
from odoo import http
from odoo.http import request
from odoo.exceptions import ValidationError, UserError

from .utils import _response

_logger = logging.getLogger(__name__)


class OduTechUserCRUDController(http.Controller):
    # ==========================================
    # 1. LOGIN USER (Minimalist Requirements)
    # ==========================================
    @http.route('/api/odutech/auth/login', type='json', auth='public', methods=['POST'], csrf=False)
    def api_login(self, **kwargs):
        data = json.loads(request.httprequest.data)
        login = data.get('login')
        password = data.get('password')
        subscription = data.get('subscription')
        if not login or not password or not subscription:
            return _response(400, "Missing required fields: login,subscription and password", False)
        user = request.env['res.users'].search(['|',('login', '=', login),('email','=',login),('company_id.subscription', '=', subscription)])
        if not user:
            return _response(401, "Invalid credentials or unauthorized subscription context.", False)
            # 2. Guard Constraint: Check if the user is archived
        if not user.active:
            return _response(403, "Your account has been archived. Please contact administration.", False)
        if not user.email_verified:
            return _response(403, "Your email has not been verified. Please contact administration.", False)
        return None
