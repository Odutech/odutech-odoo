import json
import os
import logging
from odoo import http
from odoo.http import request, Response

_logger = logging.getLogger(__name__)

class OdooSwaggerController(http.Controller):

    @http.route('/api/docs', type='http', auth='public', methods=['GET'], cors='*')
    def swagger_ui(self, **kwargs):
        """Serves the interactive Swagger UI dashboard using pure Python file path traversal."""
        # __file__ is custom_jwt_auth/controllers/swagger_controller.py
        controllers_dir = os.path.dirname(__file__)
        module_root = os.path.dirname(controllers_dir)  # Go up one level to custom_jwt_auth/

        html_path = os.path.join(module_root, 'static', 'src', 'swagger', 'index.html')

        if not os.path.exists(html_path):
            return Response(
                f"Swagger HTML file template not found. Checked path: {html_path}",
                status=404
            )

        try:
            with open(html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            return Response(html_content, status=200, content_type='text/html')
        except Exception as e:
            return Response(f"Internal Server Error: {str(e)}", status=500)

    @http.route('/api/swagger/spec.json', type='http', auth='public', methods=['GET'], cors='*')
    def swagger_spec(self, **kwargs):
        """Generates the OpenAPI 3.0.0 specification matched directly to your API logic."""

        # 1. Safely extract parameter and strictly provide a string fallback
        icp_base_url = request.env['ir.config_parameter'].sudo().get_param('web.base_url')

        if not icp_base_url or icp_base_url == "False":
            base_url = "http://localhost:8069"
        else:
            base_url = str(icp_base_url).strip()

        # 2. Strip trailing slash if present to prevent malformed paths like http://localhost:8069//api/...
        if base_url.endswith('/'):
            base_url = base_url[:-1]

        spec = {
            "openapi": "3.0.0",
            "info": {
                "title": "Expense Manager API Documentation",
                "version": "1.0.0",
                "description": "Custom API specification mapping registration, validation, and profile updates."
            },
            # 3. Use an absolute path or relative path approach for the Swagger Engine
            "servers": [
                {
                    "url": base_url,
                    "description": "Configured environment base domain"
                },
                {
                    "url": "/",
                    "description": "Relative paths (safest fallback for localized browser execution)"
                }
            ],
            "components": {
                "securitySchemes": {
                    "BearerAuth": {
                        "type": "http",
                        "scheme": "bearer",
                        "bearerFormat": "JWT",
                        "description": "Enter your token as: Bearer <token>"
                    }
                }
            },
            "paths": {
                "/api/auth/register": {
                    "post": {
                        "summary": "Register a new pending user via email",
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "email": {"type": "string", "example": "user@example.com"}
                                        },
                                        "required": ["email"]
                                    }
                                }
                            }
                        },
                        "responses": {
                            "200": {"description": "Verification email broadcasted successfully."},
                            "404": {"description": "Missing inputs or template configuration faults."},
                            "409": {"description": "Email already registered."}
                        }
                    }
                },
                "/api/auth/verify": {
                    "post": {
                        "summary": "Verify registration code to activate account",
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "code": {"type": "string", "example": "123456"}
                                        },
                                        "required": ["code"]
                                    }
                                }
                            }
                        },
                        "responses": {
                            "200": {"description": "Email verified successfully; account initialized."},
                            "404": {"description": "Invalid, expired code, or missing payload parameters."}
                        }
                    }
                },
                "/api/v1/profile/update": {
                    "post": {
                        "summary": "Update an existing user profile",
                        "security": [{"BearerAuth": []}],
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "email": {"type": "string", "example": "user@example.com"},
                                            "name": {"type": "string", "example": "Alex Smith"},
                                            "phone": {"type": "string", "example": "+123456789"},
                                            "dob": {"type": "string", "example": "1990-05-15",
                                                    "description": "Format: YYYY-MM-DD"},
                                            "currency_id": {"type": "integer", "example": 1},
                                            "password": {"type": "string", "example": "newsecurepassword"},
                                            "verification_password": {"type": "string", "example": "newsecurepassword"}
                                        },
                                        "required": ["email"]
                                    }
                                }
                            }
                        },
                        "responses": {
                            "200": {"description": "Profile elements successfully saved and updated."},
                            "400": {"description": "Mismatched passwords, missing entries, or wrong currency IDs."}
                        }
                    }
                },
                "/api/auth/login": {
                    "post": {
                        "summary": "Using Email and password login for existing user",
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "email": {"type": "string", "example": "user@example.com"},
                                            "password": {"type": "string", "example": "123456789"}
                                        },
                                        "required": ["email", "password"]
                                    }
                                }
                            }
                        },
                        "responses": {
                            "200": {"description": "Login credentials are successfully."},
                            "404": {"description": "Missing inputs or template configuration faults."},
                            "409": {"description": "Email already registered."}
                        }
                    }
                },
                "/api/auth/forgot-password": {
                    "post": {
                        "summary": "Request a password recovery link/token using Email or Phone",
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "identity": {"type": "string", "example": "user@example.com",
                                                         "description": "Can be the registered Email or Phone number"}
                                        },
                                        "required": ["identity"]
                                    }
                                }
                            }
                        },
                        "responses": {
                            "200": {"description": "Recovery action processed successfully."}
                        }
                    }
                },
                "/api/auth/complete-reset": {
                    "post": {
                        "summary": "Set a new password using the validated recovery token",
                        "parameters": [
                            {
                                "name": "reset_password_token",
                                "in": "query",
                                "required": True,
                                "description": "The unique validation token sent via the password recovery link.",
                                "schema": {
                                    "type": "string",
                                    "example": "abc123xyzYOURTOKENHERE"
                                }
                            }
                        ],
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "payload": {
                                                "type": "object",
                                                "properties": {
                                                    "password": {
                                                        "type": "string",
                                                        "example": "newsecurepassword123"
                                                    },
                                                    "verification_password": {
                                                        "type": "string",
                                                        "example": "newsecurepassword123"
                                                    }
                                                },
                                                "required": ["password", "verification_password"]
                                            }
                                        },
                                        "required": ["payload"]
                                    }
                                }
                            }
                        },
                        "responses": {
                            "200": {
                                "description": "Password modified successfully."
                            },
                            "401": {
                                "description": "Unauthorized request due to missing token, payload parameters, or mismatched passwords."
                            },
                            "404": {
                                "description": "The provided token does not exist or has passed its operational expiration date limit."
                            },
                            "500": {
                                "description": "Internal server execution failure."
                            }
                        }
                    }
                },
                "/api/v1/create_transaction": {
                    "post": {
                        "summary": "The process of recording or updating a transaction within the app",
                        "security": [{"BearerAuth": []}],
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "date_creation": {
                                                "type": "string",
                                                "format": "date-time",
                                                "example": "2026-05-16 21:44:00"
                                            },
                                            "amount": {
                                                "type": "number",
                                                "format": "float",
                                                "example": 250.00
                                            },
                                            "type": {
                                                "type": "string",
                                                "enum": ["income", "saving", "expense"],
                                                "example": "expense"
                                              },
                                            "category_id": {
                                                "type": "integer",
                                                "example": 4
                                            }
                                        },
                                        "required": ["amount", "type", "category_id"]
                                    }
                                }
                            }
                        },
                        "responses": {
                            "200": {"description": "Successful request completed successfully."},
                            "401": {"description": "Unauthorized: Missing, invalid, or expired access token."},
                            "404": {"description": "Category not found or available."},
                            "500": {"description": "Internal server or authentication execution error."}
                        }
                    }
                }
            }
        }

        return Response(
            json.dumps(spec, indent=4),
            status=200,
            content_type='application/json'
        )