import json
import logging

from werkzeug.wrappers import Response

from odoo import _, http
from odoo.exceptions import ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)


class PortalPatientRegistration(http.Controller):

    @http.route(
        "/eyekei/register/<string:branch_code>",
        type="http",
        auth="public",
        website=True,
        sitemap=True,
    )
    def patient_registration_form(self, branch_code, **kwargs):
        """
        Patient self-registration form accessed via QR code
        URL: /eyekei/register/BR002
        """
        # Verify branch exists
        # Adjust model name based on your actual branch implementation
        branch = (
            request.env["res.company"]
            .sudo()
            .search([("id", "=", int(branch_code.upper()))], limit=1)
        )

        if not branch:
            return request.render(
                "eyekei_eyewear.invalid_branch",  # Fixed template ID
                {
                    "error_message": _("Invalid or inactive branch code: %s")
                    % branch_code,
                },
            )

        # Check if branch allows self-registration
        if (
            hasattr(branch, "allow_self_registration")
            and not branch.allow_self_registration
        ):
            return request.render(
                "eyekei_eyewear.registration_disabled",  # Fixed template ID
                {"branch_name": branch.name},
            )

        values = {
            "branch": branch,
            "branch_code": branch_code.upper(),
            "csrf_token": request.csrf_token(),
        }

        return request.render(
            "eyekei_eyewear.patient_registration_template",  # Fixed template ID
            values,
        )

    @http.route(
        "/eyekei/register/submit",
        type="http",
        auth="public",
        website=True,
        methods=["POST"],
        csrf=False,
    )
    def patient_registration_submit(self, **post):
        _logger.info("=== SUBMIT CALLED ===")
        _logger.info("Received POST data: %s", post)
        _logger.info("Received keys: %s", list(post.keys()))

        branch_code = post.get("branch_code", "").upper()
        _logger.info("Branch code from form: %s", branch_code)

        branch = (
            request.env["res.company"]
            .sudo()
            .search([("id", "=", int(branch_code))], limit=1)
        )
        _logger.info(
            "Branch found? %s (id=%s)", bool(branch), branch.id if branch else "None"
        )

        if not branch:
            _logger.warning("Invalid branch: %s", branch_code)
            return Response(
                json.dumps(
                    {
                        "status": "error",
                        "message": f"Invalid branch code: {branch_code}",
                    }
                ),
                status=400,
                mimetype="application/json",
            )

        phone = post.get("phone", "").strip()
        _logger.info("Phone from form: %s", phone)

        if (
            existing_patient := request.env["res.partner"]
            .sudo()
            .search([("phone", "=", phone)], limit=1)
        ):
            _logger.info("Duplicate found: %s", existing_patient.id)
            return Response(
                json.dumps(
                    {
                        "status": "duplicate",
                        "message": _("Patient already exists"),
                        "patient_id": existing_patient.id,
                        "patient_name": existing_patient.name,
                        # "last_visit": (
                        #     existing_patient.registration_date.strftime("%Y-%m-%d")
                        #     if existing_patient.registration_date
                        #     else "N/A"
                        # ),
                        "branch": (
                            existing_patient.company_id.name
                            if existing_patient.company_id
                            else "Unknown"
                        ),
                        "patient_url": f"/my/patient/{existing_patient.id}",
                    }
                ),
                mimetype="application/json",
            )

        # Prepare vals
        patient_vals = {
            "name": post.get("name", "").strip(),
            "date_of_birth": post.get("dob"),
            "gender": post.get("gender"),
            "phone": phone,
            "email": post.get("email", "").strip() or False,
            "id_number": post.get("id_number", "").strip(),
            "place": post.get("place", "").strip(),
            "company_id": branch.id,
            # "registered_by": "self",
            # "has_insurance": post.get("has_insurance") == "on",
        }
        _logger.info("Patient vals prepared: %s", patient_vals)

        if post.get("has_insurance") == "on":
            insurance_provider_id = (
                request.env["eyekei.insurance.company"]
                .sudo()
                .search([("code", "=", post.get("insurance_provider"))], limit=1)
            )
            patient_vals |= {
                "insurance_provider_id": insurance_provider_id.id,
                "insurance_member_number": post.get("member_number", "").strip(),
                "corporate_name": post.get("corporate_name", "").strip(),
            }

        try:
            partner_id = (
                request.env["res.partner"]
                .sudo()
                .with_context(default_branch_code=branch_code)
                .create(
                    {
                        "name": patient_vals["name"],
                        "phone": patient_vals["phone"],
                    }
                )
            )
            patient_vals["partner_id"] = partner_id.id
            patient_vals["patient_id"] = request.env["ir.sequence"].next_by_code(
                "eyekei.patient"
            )
            patient_vals["is_patient"] = True
            _logger.error("patient_vals: %s", patient_vals)
            patient = (
                request.env["res.partner"]
                .sudo()
                .with_context(default_branch_code=branch_code)
                .create(patient_vals)
            )
            _logger.info(
                "Patient CREATED successfully: %s (ID: %s)",
                patient.name,
                patient.patient_id,
            )
            # SMS etc.
            return Response(
                json.dumps(
                    {
                        "status": "success",
                        "patient_id": patient.patient_id,
                        "message": _("Registration successful"),
                        "redirect_url": f"/eyekei/registration/success/{patient.id}",
                    }
                ),
                mimetype="application/json",
            )
        except ValidationError as e:
            _logger.error("VALIDATION ERROR during create: %s", str(e))
            return Response(
                json.dumps({"status": "error", "message": str(e)}),
                status=400,
                mimetype="application/json",
            )
        except Exception as e:
            _logger.exception(
                "UNEXPECTED ERROR during create: %s", str(e)
            )  # noqa: RUF065
            return Response(
                json.dumps(
                    {
                        "status": "error",
                        "message": _("An error occurred. Please try again."),
                    }
                ),
                status=500,
                mimetype="application/json",
            )

    @http.route(
        "/eyekei/api/check-duplicate",
        type="json",  # This returns JSON directly in Odoo
        auth="public",
        methods=["POST"],
        csrf=False,  # JSON endpoints typically don't need CSRF
    )
    def check_duplicate_phone(self, **kwargs):
        """
        AJAX endpoint to check for duplicate phone number
        """
        phone = kwargs.get("phone", "").strip()
        if not phone:
            return {"duplicate": False}

        existing = (
            request.env["res.partner"].sudo().search([("phone", "=", phone)], limit=1)
        )

        if existing:
            return {
                "duplicate": True,
                "patient_id": existing.id,
                "name": existing.name,
                # "last_visit": (
                #     existing.registration_date.strftime("%Y-%m-%d")
                #     if existing.registration_date
                #     else None
                # ),
                "branch": existing.company_id.name if existing.company_id else None,
            }

        return {"duplicate": False}

    @http.route(
        "/eyekei/registration/success/<int:patient_id>",
        type="http",
        auth="public",
        website=True,
    )
    def registration_success(self, patient_id, **kwargs):
        """Show registration success page"""
        patient = request.env["res.partner"].sudo().browse(patient_id)
        if not patient.exists():
            return request.redirect("/eyekei/register/BR001")

        return request.render(
            "eyekei_eyewear.registration_success_template",  # Fixed template ID
            {
                "patient": patient,
                "branch": patient.company_id,
            },
        )

    @http.route("/my/patient/<int:patient_id>", type="http", auth="user", website=True)
    def patient_portal_view(self, patient_id, **kwargs):
        """Patient portal view (requires login)"""
        patient = request.env["res.partner"].sudo().browse(patient_id)

        # Security check - portal users can only see their own record
        if request.env.user.has_group("base.group_portal") and (
            not patient.user_id or patient.user_id.id != request.env.user.id
        ):
            return request.redirect("/my")

        return request.render(
            "eyekei_eyewear.patient_portal_view",  # Fixed template ID
            {
                "patient": patient,
            },
        )
