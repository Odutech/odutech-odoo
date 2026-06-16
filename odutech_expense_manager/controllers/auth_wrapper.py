import logging
import jwt
from odoo import http, exceptions
from odoo.exceptions import AccessDenied, AccessError, UserError
from odoo.http import request, Response
from odoo.tools import date_utils
from functools import wraps

from .validators import validator

_logger = logging.getLogger(__name__)


def authenticate(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        auth_header = request.httprequest.headers.get('Authorization')
        if not auth_header:
            return Response("Unauthorized: Missing access token", status=401)
        token = auth_header.replace('Bearer ', '', 1).strip()
        try:
            auth_result = validator.verify_token(token)
            if not auth_result.get('status'):
                return Response(
                    auth_result.get('message'),
                    status=auth_result.get('code', 401)
                )
            request.jwt_uid = auth_result.get('id')
            return func(*args, **kwargs)
        except jwt.ExpiredSignatureError:
            return Response("Token has expired", status=401)
        except jwt.InvalidTokenError:
            return Response("Invalid token signature", status=401)
        except Exception as e:
            _logger.error(f"Auth Decorator Error: {str(e)}")
            return Response("Internal Authentication Error", status=500)

    return wrapper