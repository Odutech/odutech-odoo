import json
import os
import logging
from odoo import http
from odoo.http import request, Response

_logger = logging.getLogger(__name__)

class OdooSwaggerController(http.Controller):

    @http.route('/api/odutech/docs', type='http', auth='public', methods=['GET'], cors='*')
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
                "title": "Universal Odoo REST API Engine",
                "version": "1.0.0",
                "description": "Exposes complete Odoo ecosystem functionalities via a secure RESTful interface"
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
                    "/api/odutech/countries": {
                        "post": {
                            "summary": "Fetch all countries",
                            "description": "Returns a list of all countries configured in the Odoo system with their core localization metadata.",
                            "requestBody": {
                                "required": True,
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {}
                                        }
                                    }
                                }
                            },
                            "responses": {
                                "200": {
                                    "description": "List of countries retrieved successfully.",
                                    "content": {
                                        "application/json": {
                                            "schema": {
                                                "type": "object",
                                                "properties": {
                                                    "status": {
                                                        "type": "integer",
                                                        "example": 200
                                                    },
                                                    "message": {
                                                        "type": "string",
                                                        "example": "success"
                                                    },
                                                    "data": {
                                                        "type": "array",
                                                        "items": {
                                                            "type": "object",
                                                            "properties": {
                                                                "id": {
                                                                    "type": "integer",
                                                                    "example": 112
                                                                },
                                                                "name": {
                                                                    "type": "string",
                                                                    "example": "Kenya"
                                                                },
                                                                "code": {
                                                                    "type": "string",
                                                                    "example": "KE"
                                                                },
                                                                "phone_code": {
                                                                    "type": "integer",
                                                                    "example": 254
                                                                },
                                                                "currency_id": {
                                                                    "type": "array",
                                                                    "items": {
                                                                        "oneOf": [
                                                                            {
                                                                                "type": "integer"
                                                                            },
                                                                            {
                                                                                "type": "string"
                                                                            }
                                                                        ]
                                                                    },
                                                                    "example": [
                                                                        49,
                                                                        "KES"
                                                                    ]
                                                                }
                                                            }
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "/api/odutech/states": {
                    "post": {
                        "summary": "Fetch states by country",
                        "description": "Returns a list of states or provinces for a specified country, with optional filtering by center.",
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "countryId": {
                                                "type": "integer",
                                                "description": "The ID of the country to fetch states for.",
                                                "example": 112
                                            },
                                        },
                                        "required": ["countryId"]
                                    }
                                }
                            }
                        },
                        "responses": {
                            "200": {
                                "description": "List of states retrieved successfully.",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "status": {
                                                    "type": "integer",
                                                    "example": 200
                                                },
                                                "message": {
                                                    "type": "string",
                                                    "example": "success"
                                                },
                                                "data": {
                                                    "type": "array",
                                                    "items": {
                                                        "type": "object",
                                                        "properties": {
                                                            "id": {
                                                                "type": "integer",
                                                                "example": 451
                                                            },
                                                            "name": {
                                                                "type": "string",
                                                                "example": "Nairobi"
                                                            },
                                                            "code": {
                                                                "type": "string",
                                                                "example": "NB"
                                                            },
                                                            "country_id": {
                                                                "type": "integer",
                                                                "example": 112
                                                            }
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }},
                    "/api/odutech/currencies": {
                        "post": {
                            "summary": "Fetch all active currencies",
                            "description": "Returns a list of all active currencies in the Odoo system with their display and decimal metadata.",
                            "requestBody": {
                                "required": True,
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {}
                                        }
                                    }
                                }
                            },
                            "responses": {
                                "200": {
                                    "description": "List of active currencies retrieved successfully.",
                                    "content": {
                                        "application/json": {
                                            "schema": {
                                                "type": "object",
                                                "properties": {
                                                    "status": {
                                                        "type": "integer",
                                                        "example": 200
                                                    },
                                                    "message": {
                                                        "type": "string",
                                                        "example": "success"
                                                    },
                                                    "data": {
                                                        "type": "array",
                                                        "items": {
                                                            "type": "object",
                                                            "properties": {
                                                                "id": {
                                                                    "type": "integer",
                                                                    "example": 49
                                                                },
                                                                "name": {
                                                                    "type": "string",
                                                                    "example": "KES"
                                                                },
                                                                "symbol": {
                                                                    "type": "string",
                                                                    "example": "KSh"
                                                                },
                                                                "decimal_places": {
                                                                    "type": "integer",
                                                                    "example": 2
                                                                },
                                                                "currency_unit_label": {
                                                                    "type": "string",
                                                                    "example": "Shilling"
                                                                }
                                                            }
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "/api/odutech/company/create": {
                    "post": {
                        "summary": "Create a new company anonymously",
                        "description": "Public unauthenticated onboarding endpoint to register a corporate entity in the system registry.",
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "required": ["name"],
                                        "properties": {
                                            "name": {
                                                "type": "string",
                                                "example": "Acme International Ltd"
                                            },
                                            "email": {
                                                "type": "string",
                                                "example": "operations@acme.com"
                                            },
                                            "phone": {
                                                "type": "string",
                                                "example": "+254700000000"
                                            },
                                            "vat": {
                                                "type": "string",
                                                "example": "P051XXXXXXZ"
                                            },
                                            "company_registry": {
                                                "type": "string",
                                                "example": "CPR/2026/XXXXXX"
                                            },
                                            "currency_id": {
                                                "type": "integer",
                                                "example": 49
                                            },
                                            "country_id": {
                                                "type": "integer",
                                                "example": 112
                                            },
                                            "street": {
                                                "type": "string",
                                                "example": "Mombasa Road"
                                            },
                                            "city": {
                                                "type": "string",
                                                "example": "Nairobi"
                                            }
                                        }
                                    }
                                }
                            }
                        },
                        "responses": {
                            "201": {
                                "description": "Company created successfully.",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "status": {
                                                    "type": "integer",
                                                    "example": 201
                                                },
                                                "message": {
                                                    "type": "string",
                                                    "example": "success"
                                                },
                                                "data": {
                                                    "type": "object",
                                                    "properties": {
                                                        "id": {
                                                            "type": "integer",
                                                            "example": 3
                                                        },
                                                        "name": {
                                                            "type": "string",
                                                            "example": "Acme International Ltd"
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            },
                            "400": {
                                "description": "Missing required field constraints.",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "status": {
                                                    "type": "integer",
                                                    "example": 400
                                                },
                                                "message": {
                                                    "type": "string",
                                                    "example": "Missing required field: name"
                                                },
                                                "data": {
                                                    "type": "boolean",
                                                    "example": False
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                },
                    "/api/odutech/company/verify": {
                    "post": {
                        "summary": "Verify company registration token",
                        "description": "Validates a secure unique string token, marks the company as active, and emails the primary user their unique corporate subscription code.",
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "verification_token": {
                                                "type": "string",
                                                "example": "4a7b1c8d9e0f4a3b2c1d0e9f8a7b6c5d"
                                            }
                                        },
                                        "required": ["verification_token"]
                                    }
                                }
                            }
                        },
                        "responses": {
                            "200": {
                                "description": "Account activated successfully and subscription confirmation email sent.",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "status": {"type": "integer", "example": 200},
                                                "message": {"type": "string",
                                                            "example": "Email verification successful. Welcome aboard!"},
                                                "data": {
                                                    "type": "object",
                                                    "properties": {
                                                        "company_id": {"type": "integer", "example": 42},
                                                        "subscription_code": {"type": "string",
                                                                              "example": "SUB202600005"}
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            },
                            "404": {
                                "description": "Token is expired, manipulated, or already verified."
                            }
                        }
                    }
                },
                    "/api/odutech/v1/utility/modules": {
                    "post": {
                        "summary": "Fetch core system application modules",
                        "description": "Returns a comprehensive list of installed Odoo core applications including metadata such as UI icons, technical designations, categories, and deep technical descriptions.",
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {}
                                    }
                                }
                            }
                        },
                        "responses": {
                            "200": {
                                "description": "System core apps catalog retrieved successfully.",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "status": {"type": "integer", "example": 200},
                                                "message": {"type": "string", "example": "success"},
                                                "data": {
                                                    "type": "array",
                                                    "items": {
                                                        "type": "object",
                                                        "properties": {
                                                            "id": {"type": "integer", "example": 102},
                                                            "name": {"type": "string", "example": "Invoicing"},
                                                            "technical_name": {"type": "string", "example": "account"},
                                                            "icon": {"type": "string",
                                                                     "example": "/account/static/description/icon.png"},
                                                            "category": {"type": "string",
                                                                         "example": "Accounting/Accounting"},
                                                            "description": {"type": "string",
                                                                            "example": "Manage financial customer invoices, vendor bills, payments, and tax declarations tracking seamlessly."}
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
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