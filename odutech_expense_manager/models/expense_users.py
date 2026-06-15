from odoo import models, fields, api
import random
import datetime
import secrets
class ResCompany(models.Model):
    _inherit = 'res.company'
    expense_link = fields.Char(string="Expense Link",readonly=True)


class ExpenseUser(models.Model):
    _name = 'expense.user'
    _description = 'Expense Module User'

    name = fields.Char(string="Full Name",readonly=True)
    email = fields.Char(string="Email",readonly=True)
    phone = fields.Char(string="Phone Number",readonly=True)
    dob = fields.Date(string="Date of Birth",readonly=True)
    password = fields.Char(string="Password",readonly=True)
    access_token = fields.Char(string="Access Token",readonly=True)
    expiration_date = fields.Datetime(string="Expiration Date",readonly=True)
    reset_password_token = fields.Char(string="Reset Password Token",readonly=True)
    currency_id = fields.Many2one("res.currency",string="User Account Currency",readonly=True)
    verification_code = fields.Char(string='Email Verification Code', copy=False,readonly=True)
    verification_expiry = fields.Datetime(string='Verification Code Expiry', copy=False, readonly=True)
    is_verified = fields.Boolean(string='Email Verified', default=False,readonly=True)
    company_id = fields.Many2one('res.company',readonly=True,string="Company",default=lambda self: self.env.company.id)
    partner_id = fields.Many2one('res.partner', string="Related Contact", ondelete='cascade')
    session_ids = fields.One2many('expense.user.sessions', 'user_id', string="Sessions")
    session_count = fields.Integer(string="Session Count", compute="_compute_session_count")

    def _compute_session_count(self):
        for record in self:
            record.session_count = len(record.session_ids)

    def action_view_login_sessions(self):
        return {
            'name': 'Login History',
            'type': 'ir.actions.act_window',
            'res_model': 'expense.user.sessions',
            'view_mode': 'list,form',
            'domain': [('user_id', '=', self.id)],
            'context': {'default_user_id': self.id},
        }

    def generate_password_reset_token(self):
        """Generates a secure alphanumeric reset token valid for 20 minutes."""
        token = secrets.token_urlsafe(32)
        expiry = datetime.datetime.utcnow() + datetime.timedelta(minutes=20)
        self.sudo().write({
            'reset_password_token': token,
            'expiration_date': expiry
        })
        return token
    def get_total_platform_users(self):
        """Returns the total number of users registered on the platform."""
        return self.env['expense.user'].sudo().search_count([])

    @api.model_create_multi
    def create(self, vals_list):
        """Extends create to build a corresponding res.partner record."""
        for vals in vals_list:
            # If a partner isn't already supplied, create one automatically
            if not vals.get('partner_id'):
                partner_vals = {
                    'name': vals.get('name') or vals.get('email') or "New Expense User",
                    'email': vals.get('email'),
                    'phone': vals.get('phone'),
                    'company_id': vals.get('company_id') or self.env.company.id,
                }
                # Create the partner using sudo to ensure public signups work cleanly
                new_partner = self.env['res.partner'].sudo().create(partner_vals)
                vals['partner_id'] = new_partner.id

        return super(ExpenseUser, self).create(vals_list)

    def write(self, vals):
        """Extends write to keep the corresponding res.partner synchronized."""
        res = super(ExpenseUser, self).write(vals)

        # Identify if any partner-relevant values are altering
        partner_mappings = {}
        if 'name' in vals:
            partner_mappings['name'] = vals['name']
        if 'email' in vals:
            partner_mappings['email'] = vals['email']
        if 'phone' in vals:
            partner_mappings['phone'] = vals['phone']

        # If synced fields changed, update the partner record
        if partner_mappings:
            for record in self:
                if record.partner_id:
                    record.partner_id.sudo().write(partner_mappings)

        return res

    def generate_verification_code(self):
        """Generates a random 6-digit code valid for 15 minutes."""
        code = f"{random.randint(100000, 999999)}"
        expiry = datetime.datetime.utcnow() + datetime.timedelta(minutes=15)
        # Using sudo() to allow write access during the public registration route
        self.sudo().write({
            'verification_code': code,
            'verification_expiry': expiry
        })
        return code