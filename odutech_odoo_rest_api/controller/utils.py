from odoo.http import request, Response
from odoo import fields
from datetime import datetime
from odoo.exceptions import UserError
import datetime

allowed_origin = ['http://localhost:4200', 'http://dev.inkomoko.com:1082','https://81f9-41-90-144-19.ngrok-free.app']

headers = [
    ('Access-Control-Allow-Credentials', 'true'),
    ('Access-Control-Allow-Origin', allowed_origin),
    ('Access-Control-Allow-Headers', '*'),
    ('Access-Control-Allow-Credentials', 'true'),
    ('Access-Control-Allow-Methods', 'POST, OPTIONS, GET, PUT'),
    ('Access-Control-Max-Age', '3600')
]

def custom_serializer(obj):
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


def _response(code, status, message, data=None, pagination=None):
    response_data = {
        'code': code,
        'status': status,
        'message': message,
        'data': data or {},
        'pagination': pagination or {}
    }

    return response_data


def build_cors_headers():

    allowed_origins = ['http://localhost:4200','https://81f9-41-90-144-19.ngrok-free.app', 'http://dev.inkomoko.com:1082', 'http://dev.inkomoko.com:1091']

    origin = request.httprequest.headers.get('Origin')

    if origin in allowed_origins:
        return [
            ('Access-Control-Allow-Credentials', 'true'),
            ('Access-Control-Allow-Origin', origin),
            ('Access-Control-Allow-Headers', 'Content-Type, Authorization'),
            ('Access-Control-Allow-Methods', 'POST, OPTIONS, GET, PUT'),
            ('Access-Control-Max-Age', '3600'),
        ]
    return []