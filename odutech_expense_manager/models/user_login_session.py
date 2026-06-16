import logging
import requests
from odoo import models, fields, api, http

_logger = logging.getLogger(__name__)


class ExpenseUserSessions(models.Model):
    _name = 'expense.user.sessions'
    _description = 'Expense User Login Sessions'
    _order = 'login_time desc'

    ip_address = fields.Char(string="IP Address", readonly=True)
    user_id = fields.Many2one("expense.user", string="User", readonly=True)
    login_time = fields.Datetime(string="Login Time", readonly=True, default=fields.Datetime.now)
    place_of_login = fields.Char(string="Place of Login", readonly=True)

    @api.model
    def log_new_session(self, user_id):
        """Helper method to create a login session tracking log entry"""
        # Fallback values if request environment isn't present (e.g. testing or CLI)
        ip = "127.0.0.1"
        location = "Unknown"
        if http.request and http.request.httprequest:
            # Captures actual IP even if running behind an Nginx reverse proxy wrapper
            ip = http.request.httprequest.headers.get('X-Forwarded-For', http.request.httprequest.remote_addr)
            if ',' in ip:
                ip = ip.split(',')[0].strip()  # Takes client IP if multiple proxies exist
            # Optional: Simple GeoIP location lookup (skips local IPs)
            if ip not in ('127.0.0.1', 'localhost', '0.0.0.0', ''):
                try:
                    response = requests.get(f"https://ipapi.co/{ip}/json/", timeout=3).json()
                    if not response.get('error'):
                        location = f"{response.get('city', '')}, {response.get('country_name', '')}".strip(', ')
                except Exception as e:
                    _logger.warning("GeoIP location lookup failed: %s", e)
                    location = "Lookup Failed"
        return self.create({
            'user_id': user_id,
            'ip_address': ip,
            'place_of_login': location or "Unknown",
            'login_time': fields.Datetime.now(),
        })