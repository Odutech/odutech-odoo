from odoo import models, fields, api
from odoo.exceptions import AccessDenied
import secrets
import datetime
import bcrypt
class ResUsersToken(models.Model):
    _name = 'res.users.token'
    _description = 'API Access Tokens'

    name = fields.Char(required=True)
    user_id = fields.Many2one('res.users', string='User', required=True, ondelete='cascade')
    token = fields.Char(readonly=True, copy=False)
    expiry_date = fields.Datetime()
    is_active = fields.Boolean(default=True)

class ResUsers(models.Model):
    _inherit = 'res.users'

    api_token_ids = fields.One2many('res.users.token', 'user_id', string='API Access Tokens')
    session_ids = fields.One2many('res.users.sessions', 'user_id', string="Sessions")
    email_verified = fields.Boolean(default=False,string="Email Verified")

    def _set_password(self, password):
        """ Override Odoo's default password encryption to enforce bcrypt """
        # Encode password string to bytes
        password_bytes = password.encode('utf-8')

        # Generate salt with a secure work factor (12 rounds)
        salt = bcrypt.gensalt(rounds=12)

        # Hash the password string
        hashed_password_bytes = bcrypt.hashpw(password_bytes, salt)

        # Store as a readable UTF-8 string in Odoo's standard password field
        hashed_password_string = hashed_password_bytes.decode('utf-8')

        # Write directly to the database cursor, bypassing standard constraints
        self.env.cr.execute(
            "UPDATE res_users SET password=%s WHERE id=%s",
            (hashed_password_string, self.id)
        )
        self.invalidate_recordset(['password'])
