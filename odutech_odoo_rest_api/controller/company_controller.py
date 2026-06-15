import logging
from odoo import http
from odoo.http import request
from odoo.exceptions import ValidationError, UserError
from psycopg2 import IntegrityError
from .utils import _response

_logger = logging.getLogger(__name__)
class OdooCompanyApiController(http.Controller):
    @http.route('/api/odutech/company/create', type='json', auth='public', methods=['POST'], csrf=False)
    def create_public_company(self, **kwargs):
        params = request.get_json_data() if hasattr(request, 'get_json_data') else request.params

        # 1. Base Parameter Validations
        email = params.get('email')
        phone = params.get('phone')
        name = params.get('name')

        if not name:
            return _response(400, "Missing required field: name", False)
        if not email:
            return _response(400, "Missing required user account credentials", False)

        # 2. Strict Uniqueness Checks (Email & Phone)
        # Check if email or login already exists anywhere in critical identity models
        user_exists = request.env['res.users'].sudo().search_count([
            '|', ('login', '=', email), ('email', '=', email)
        ])
        if user_exists:
            return _response(400, "Email or login already taken.", False)

        company_exists = request.env['res.company'].sudo().search_count([
            '|', ('email', '=', email), ('name', '=', name)
        ])
        if company_exists:
            return _response(400, "A company with this email or name already exists.", False)

        partner_domain = [('email', '=', email)]
        if phone:
            partner_domain = ['|', ('email', '=', email), ('phone', '=', phone)]

        partner_exists = request.env['res.partner'].sudo().search_count(partner_domain)
        if partner_exists:
            return _response(400, "Contact information (Email or Phone number) is already registered.", False)

        try:
            # 3. Prepare and create the company
            company_vals = {
                'name': name,
                'email': email,
                'phone': phone,
                'vat': params.get('vat'),
                'company_registry': params.get('company_registry'),
                'currency_id': params.get('currency_id'),
                'country_id': params.get('country_id'),
                'street': params.get('street'),
                'city': params.get('city'),
            }
            clean_company_vals = {k: v for k, v in company_vals.items() if v is not None}
            new_company = request.env['res.company'].sudo().create(clean_company_vals)

            # 4. Prepare and create the user
            user_vals = {
                'name': name,
                'login': email,
                'email': email,
                'company_id': new_company.id,
                'company_ids': [(4, new_company.id)],
                "role": "group_system",
            }
            new_user = request.env['res.users'].sudo().create(user_vals)

            # 5. Create the API token record linked to the new user
            token_record = request.env['res.users.token'].sudo().create({
                'name': f"Registration Token for {new_user.login}",
                'user_id': new_user.id,
            })

            # 6. Handle email verification template and dispatch
            try:
                template = request.env.ref(
                    'odutech_odoo_rest_api.email_template_user_email_registration_verification',
                    raise_if_not_found=False
                )
                base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')

                if template:
                    custom_context = {
                        'verification_url': f'{base_url}/api/odutech/company/verify?verification_token={token_record.token}',
                        'verification_token': token_record.token,
                    }
                    template.sudo().with_context(**custom_context).send_mail(
                        new_user.id,
                        force_send=True
                    )
                else:
                    _logger.warning("Verification email template not found.")
            except Exception:
                _logger.exception("Failed to send verification email to user %s", new_user.login)

            # 7. Return JSON payload response
            return _response(201, "success", {
                'company': {
                    'id': new_company.id,
                    'name': new_company.name
                },
                'user': {
                    'id': new_user.id,
                    'login': new_user.login
                },
                'token': token_record.token
            })

        except (ValidationError, UserError) as e:
            request.env.cr.rollback()
            return _response(400, str(e), False)

        except IntegrityError:
            request.env.cr.rollback()
            return _response(409, "Database conflict: Information may have been captured simultaneously.", False)

        except Exception as e:
            request.env.cr.rollback()
            _logger.exception("Unexpected error during public company creation.")
            return _response(500, "An unexpected error occurred internal to the server.", False)
    @http.route('/api/odutech/company/verify', type='json', auth='public', methods=['POST'], csrf=False)
    def verify_company(self):
        params = request.params or {}
        token = params.get('verification_token')
        if not token:
            return _response(400, "Missing verification token parameter.", False)
        try:
            # Look up the company matching the unique token
            company = request.env['res.company'].sudo().search([
                ('verification_token', '=', token),
                ('is_verified', '=', False)
            ], limit=1)

            if not company:
                return _response(404, "Invalid token or company already verified.", False)

            # Mark company as verified
            company.write({
                'is_verified': True,
                'verification_token': False  # Clear token after successful activation
            })

            # Find the primary administrative user associated with this company
            user = request.env['res.users'].sudo().search([('company_id', '=', company.id)], order='id asc', limit=1)
            if user:
                try:
                    # Load and send the verification confirmation email template
                    template = request.env.ref('odutech_odoo_rest_api.email_template_user_registration_verification', raise_if_not_found=False)
                    if template:
                        template.sudo().send_mail(user.id, force_send=True)
                    else:
                        _logger.warning("Verification email template was not found.")
                except Exception as email_err:
                    _logger.error("Failed to send verification email: %s", str(email_err))

            return _response(200, "Email verification successful. Welcome aboard!", {
                'company_id': company.id,
                'subscription_code': company.subscription_code
            })

        except Exception as e:
            request.env.cr.rollback()
            _logger.error("Unexpected error during company verification: %s", str(e))
            return _response(500, "An unexpected error occurred during verification processing.", False)