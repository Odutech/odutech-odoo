import logging
from odoo import http
from odoo.http import request
from .utils import _response
from .auth_wrapper import authenticate
_logger = logging.getLogger(__name__)


class OdooCoreModuleApiController(http.Controller):

    @http.route('/api/odutech/v1/utility/modules', type='json', auth='user', methods=['POST'], csrf=False)
    @authenticate
    def get_system_modules(self):
        try:
            # SQL Query joining ir_module_module with ir_module_category to get category names
            query = """
                SELECT 
                    m.id, 
                    m.shortdesc AS name, 
                    m.name AS technical_name, 
                    m.icon, 
                    c.name AS category, 
                    m.description
                FROM ir_module_module m
                LEFT JOIN ir_module_category c ON m.category_id = c.id
                WHERE m.application = TRUE AND m.state != 'installed'
                ORDER BY m.shortdesc ASC
            """
            request.cr.execute(query)
            modules = request.cr.dictfetchall()
            return _response(200, "success", modules)

        except Exception as e:
            _logger.error("Error retrieving ir.module.module list: %s", str(e))
            return _response(500, "An error occurred while fetching the modules catalog.", False)