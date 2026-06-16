import logging
import json
from odoo import http
from odoo.http import request, Response
from functools import wraps
from .validators import validator

_logger = logging.getLogger(__name__)


def authenticate(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        routing = http.request.endpoint.routing if hasattr(http.request, 'endpoint') else {}
        route_type = routing.get('type', 'http')
        def _build_error_response(message, status_code):
            if route_type == 'json':
                body = json.dumps({
                    "status": "FAILED",
                    "message": message,
                    "code": status_code,
                    "data": {}
                })
                request.httprequest.session.explicit_response = Response(
                    body,
                    status=status_code,
                    mimetype='application/json'
                )
                return request.httprequest.session.explicit_response
            return Response(message, status=status_code, mimetype='text/plain')

        auth_header = request.httprequest.headers.get('Authorization')
        if not auth_header:
            return _build_error_response("Authentication missing: Please provide an Authorization header.", 401)

        clean_header = auth_header.strip("'\" \t:")
        parts = clean_header.split()

        if len(parts) >= 2 and parts[-2].lower() == 'bearer':
            token = parts[-1].strip()
        elif len(parts) == 1:
            token = parts[0].strip()
        else:
            token = clean_header.replace('Bearer ', '', 1).strip("'\" \t:")

        payload, error_msg = validator.verify_token_and_decode(token)
        if error_msg:
            return _build_error_response(error_msg, 401)

        uid = payload.get('sub')
        if not uid:
            return _build_error_response("Token payload is valid but missing user context.", 401)

        request.jwt_uid = uid
        return func(*args, **kwargs)

    return wrapper