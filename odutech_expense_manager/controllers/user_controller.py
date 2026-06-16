import json

import jwt
from werkzeug.security import generate_password_hash, check_password_hash
from odoo.http import request
from odoo import http
import datetime
import logging
from .utils import _response
from .validators import validator
_logger = logging.getLogger(__name__)
today = datetime.date.today()
SENSITIVE_FIELDS = ['portal_password', 'portal_password_crypt', 'portal_new_password', 'create_uid', 'write_uid']


class UserRegistrationController(http.Controller):
    @http.route('/api/auth/register', type='json', auth='public', methods=['POST'], cors='*')
    def register_user(self, **kwargs):
        """
        Expects:email
        Creates an inactive user and sends a 6-digit verification code email.
        """
        params = request.dispatcher.jsonrequest
        email = params.get('email')
        _logger.error(f"CHECKING THE DATA COMING FROM THE BACKEND.....{params}")
        if not email:
            return _response(404,"warning","Email not provided and its required")
        # Check if user already exists
        user_exists = request.env['expense.user'].sudo().search([('email', '=', email)], limit=1)
        if user_exists:
            return _response(409,"warning","Email already registered")
        try:
            # 1. Create the user in Odoo (Set active=False so they can't log in yet)
            # We use sudo() because public/anonymous web requests cannot create users natively
            new_user = request.env['expense.user'].sudo().create({
                'email': email,
            })
            # 2. Generate the verification code
            if new_user:
                new_user.generate_verification_code()
            # 3. Send verification code email via the template
            template = request.env.ref('odutech_expense_manager.email_template_user_verification', raise_if_not_found=False)
            if template:
                template.sudo().send_mail(new_user.id, force_send=True)
            else:
                return _response(404,"warning","Email not provided and its required")
            return _response(200, "success", f"Email verification has been sent to the email {email}",{"id": new_user.id})
        except Exception as e:
            return _response(404,"warning","Email not provided and its required")

    @http.route('/api/auth/verify', type='json', auth='public', methods=['POST'], cors='*')
    def verify_email(self, **kwargs):
        """
        Expects: code
        Validates code, activates user account.
        """
        params = request.dispatcher.jsonrequest
        code = params.get('code')
        if  not code:
            return _response(404,"warning","Code not provided and its required")
        # Search inside inactive users as well by bypassing default active leaf criteria
        user = request.env['expense.user'].sudo().search([('verification_code', '=', code)], limit=1)
        if not user:
            return _response(404,"warning","Provided code in invalid or expired")
        if user.is_verified:
            return _response(404,"warning","Email already verified")
        # Check code validity and expiration
        now = datetime.datetime.utcnow()
        if user.verification_code != str(code):
            return _response(404,"warning","Verification code not valid")
        if user.verification_expiry and user.verification_expiry < now:
            return _response(404,"warning","Verification code expired")
        # 4. Activate and mark user verified
        user.write({
            'is_verified': True,
            'verification_code': False,  # Clear out token once consumed
            'verification_expiry': False
        })
        return _response(200,"success","Email verified successfully. Account is now active",{"email": user.email})

    @http.route('/api/v1/profile/update', type='json', auth='none', methods=['PUT', 'POST'], cors='*')
    def update_profile(self, **kwargs):
        """
        Expects payload: password, verification_password, dob, name, currency_id, phone, email
        Updates the currently authenticated user's profile and provisions initial accounts.
        """
        try:
            # Use request.get_json_data() if on Odoo 16+, otherwise jsonrequest works for older versions
            params = request.dispatcher.jsonrequest if hasattr(request.dispatcher,
                                                               'jsonrequest') else request.get_json_data()
        except Exception as json_err:
            return _response(404,"warning","Invalid or expired payload")
        name = params.get('name')
        phone = params.get('phone')
        date_of_birth = params.get('dob')
        currency_id = params.get('currency_id')
        password = params.get('password')
        email = params.get('email')
        verification_password = params.get('verification_password')

        if not email:
            return _response(404,"warning","Email not provided.")
        # Dictionary to hold valid write operations
        update_vals = {}

        # 1. Basic Profile Updates
        if name:
            update_vals['name'] = name
        if phone:
            update_vals['phone'] = phone

        if date_of_birth:
            try:
                datetime.datetime.strptime(date_of_birth, "%Y-%m-%d").date()
                update_vals['dob'] = date_of_birth
            except ValueError:
                return _response(404,"warning","Date of birth not provided.")

        # 2. Handle Currency Validation
        if currency_id:
            try:
                currency = request.env['res.currency'].sudo().browse(int(currency_id))
                if not currency.exists():
                    return _response(404,"warning","Currency not found.")
                update_vals['currency_id'] = int(currency_id)
            except ValueError:
                return _response(404,"warning","Currency ID not provided.")
        # 3. Handle Secure Password Reset
        if password or verification_password:
            if password != verification_password:
                return _response(401,"warning","Passwords do not match.")
            if len(password) < 6:
                return _response(401,"warning","Password must be at least 6 characters.")
            # Assuming generate_password_hash is imported or managed via Odoo fields
            update_vals['password'] = password  # Or use your custom hashing implementation

        try:
            # Locate target application user record
            checking_user = request.env['expense.user'].sudo().search([('email', '=', email)], limit=1)
            if not checking_user:
                return _response(404,"warning","Email not found.")
            # Perform the update execution if parameters were updated
            if update_vals:
                checking_user.write(update_vals)

            # 4. Handle Safe Batch Sequence generation for accounts
            accounts_type = ["income", "expense", "saving"]
            vals_list = []
            for item in accounts_type:
                seq_number = request.env['ir.sequence'].sudo().next_by_code('expense.account.sequence') or 'New'
                account_name = f"{item.capitalize()} Account ({seq_number})"
                vals_list.append({
                    'name': account_name,
                    'account_number': seq_number,
                    'type': item,
                    'user_id': checking_user.id,
                    'total_available': 0.0
                })

            # Single database write context optimization
            request.env['expense.account'].sudo().create(vals_list)

            # 5. Handle Template Welcome Emails Safely
            template = request.env.ref('odutech_expense_manager.email_template_welcome_onboarding',
                                       raise_if_not_found=False)
            if template:
                template.sudo().send_mail(checking_user.id, force_send=True)
            return  _response(200, "success", {'message': 'Email sent successfully.'})
        except Exception as e:
            _logger.error(f"Profile update execution failure: {str(e)}")
            return _response(500, "warning", f"An error occurred while updating profile information.{e}")

    @http.route('/api/auth/login', type='json', auth='public', methods=['POST'], cors='*')
    def login_user(self, **kwargs):
        """
        Expects: email, password
        Verifies credentials and returns a custom signed JWT token.
        """
        params = request.dispatcher.jsonrequest
        email = params.get('email')
        password = params.get('password')
        # 1. Validation Checks
        if not email or not password:
            return _response(404, "warning", "Both email and password are required.")

        # 2. Locate User (Bypass active rules to check verification status explicitly)
        user = request.env['expense.user'].sudo().with_context(active_test=False).search([
            ('email', '=', email)
        ], limit=1)
        if not user:
            return _response(404, "warning", "Invalid email or password.")
        # 3. Check Account Verification Status
        if not user.is_verified:
            return _response(403, "warning",
                             "Your email address is not verified yet. Please verify your account first.")
        # 4. Verify Password Hash (Using Werkzeug)
        if not user.password:
            return _response(404, "warning", "Account password configuration mismatch. Please reset your password.")
        if not check_password_hash(user.password, password):
            return _response(404, "warning", "Invalid email or password.")
        try:
            # 5. Generate JWT Token Payload
            # Set expiration for 24 hours
            expiration = datetime.datetime.utcnow() + datetime.timedelta(hours=24)
            payload = {
                'user_id': user.id,
                'email': user.email,
                'exp': expiration
            }

            # Encode JWT using your secret key
            token = jwt.encode(payload, validator.key(), algorithm='HS256')
            # 6. Save token metadata to the user record for validation persistence tracking
            user.sudo().write({
                'access_token': token,
                'expiration_date': expiration
            })

            # 7. Structure the response payload
            user_data = {
                "id": user.id,
                "name": user.name or "New User",
                "email": user.email,
                "phone": user.phone or "",
                "dob": user.dob.strftime('%Y-%m-%d') if user.dob else "",
                "currency_id": user.currency_id.id if user.currency_id else False,
                "token": token,
                "expires_at": expiration.strftime('%Y-%m-%d %H:%M:%S')
            }
            request.env['expense.user.sessions'].sudo().log_new_session(user.id)
            return _response(200, "success", "Login successful.", user_data)
        except Exception as e:
            _logger.error(f"Login unexpected crash: {str(e)}")
            return _response(500, "error", f"An internal cryptographic error occurred: {str(e)}")

    @http.route('/api/auth/forgot-password', type='json', auth='public', methods=['POST'], cors='*')
    def forgot_password(self, **kwargs):
        """
        Expects payload: identity (can be an email address OR a phone number)
        Generates recovery token and sends/logs the secure reset pathway link.
        """
        params = request.dispatcher.jsonrequest
        identity = params.get('identity')

        if not identity:
            return _response(404, "warning", "Email or Phone Number identifier is required.")
        # Clean string to handle mixed inputs safely
        identity = str(identity).strip()

        # Search by matching against either email OR phone fields
        user = request.env['expense.user'].sudo().search([
            '|', ('email', '=', identity), ('phone', '=', identity)
        ], limit=1)

        if not user:
            # Security Best Practice: Don't explicitly leak whether an identifier exists or not
            return _response(200, "success",
                             "If the account exists, a temporary password recovery option has been initiated.")
        # Generate token metadata
        token = user.generate_password_reset_token()
        # Build dynamic payload routing destination link
        reset_link = f"{user.company_id.expense_link}/auth/reset-password?token={token}"

        # Action: Route communication based on the field match
        if user.email and identity == user.email:
            template = request.env.ref('odutech_expense_manager.email_template_password_reset',raise_if_not_found=False)
            if template and user.email:
                # Use mail template logic to send immediately via mail.queue engine
                template.sudo().send_mail(user.id, force_send=True)
        else:
            _logger.info(f">>> SMS SIMULATION SENT TO {user.phone}: Use token -> {token}")

        return _response(200, "success","If the account exists, a temporary password recovery option has been initiated.")

    @http.route('/api/auth/complete-reset', type='json', auth='public', methods=['POST'], cors='*')
    def complete_reset(self, **kwargs):
        """
        Expects URL Query Parameter: ?reset_password_token=YOUR_TOKEN
        Expects JSON Body Payload:
        {
            "payload": {
                "password": "new_password123",
                "verification_password": "new_password123"
            }
        }
        Updates user credentials securely.
        """
        try:
            # Parse raw request body data
            try:
                data = json.loads(request.httprequest.data)
            except (ValueError, TypeError) as json_err:
                _logger.error(f"Failed to parse incoming payload JSON: {str(json_err)}")
                return _response(400, "error", f"Malformed JSON payload: {str(json_err)}")
            # 1. Fetch token from query parameters via kwargs or request.params fallback
            reset_password_token = request.httprequest.args.get('reset_password_token')
            # reset_password_token = kwargs.get('reset_password_token') or request.params.get('reset_password_token')
            _logger.error(f"CHECKING IF THE RESET TOKEN IS BEING PASSED....{data}")
            # Pull parameters safely from payload object mapping layer
            password = data.get('password')
            verification_password = data.get('verification_password')

            # 2. Strict Request Validations
            if not reset_password_token:
                return _response(401, "warning", "NOT AUTHORISED REQUEST")
            if not password or not verification_password:
                return _response(401, "warning", "Password and Verification Password are required.")
            if len(password) < 6:
                return _response(404, "warning", "Password must be at least 6 characters long.")

            if password != verification_password:
                return _response(401, "warning", "Password and Verification Password do not match.")

            # 3. Locate Target Identity Instance Record
            user = request.env['expense.user'].sudo().search([('reset_password_token', '=', reset_password_token)],
                                                             limit=1)
            if not user:
                return _response(404, "warning", "Provided token is not valid.")

            if user and user.expiration_date and user.expiration_date < datetime.datetime.now():
                return _response(401, "warning", "The provided token is not valid.")

            # 4. Hash Password and Update Registry State securely
            hashed_password = generate_password_hash(password, method='pbkdf2:sha512', salt_length=16)
            user.sudo().write({
                'password': hashed_password,
                'reset_password_token': False,
                'expiration_date': False
            })

            return _response(200, "success", "Password updated successfully. You can now log in.")

        except Exception as e:
            # Capture and log unexpected internal errors (DB locks, missing method dependencies, etc.)
            _logger.error(f"Unhandled operational error during password completion: {str(e)}")
            return _response(500, "error", f"An internal exception occurred: {str(e)}")