from odoo import http
from odoo.http import request
from .utils import _response


class UtilityApiController(http.Controller):

    @http.route('/api/odutech/countries', type='json', auth='user', methods=['POST'], csrf=False)
    def get_countries(self):
        params = request.params or {}
        center_id = params.get('centerId')

        query = """
            SELECT id, name, code, phone_code, currency_id 
            FROM res_country
        """
        query_params = []
        request.cr.execute(query, query_params)
        countries = request.cr.dictfetchall()

        return _response(200, "success", countries)

    @http.route('/api/odutech/states', type='json', auth='user', methods=['POST'], csrf=False)
    def get_states(self):
        params = request.params or {}
        country_id = params.get('countryId')
        center_id = params.get('centerId')

        query = """
                SELECT id, name, code, country_id 
                FROM res_country_state
                WHERE 1=1
            """
        query_params = []

        if country_id:
            query += " AND country_id = %s"
            query_params.append(country_id)
        query += " ORDER BY name ASC"

        request.cr.execute(query, query_params)
        states = request.cr.dictfetchall()

        return _response(200, "success", states)
    @http.route('/api/odutech/currencies', type='json', auth='user', methods=['POST'], csrf=False)
    def get_currencies(self):
        params = request.params or {}
        center_id = params.get('centerId')

        query = """
            SELECT id, name, symbol, decimal_places, currency_unit_label 
            FROM res_currency 
            WHERE active = TRUE
        """
        query_params = []
        request.cr.execute(query, query_params)
        currencies = request.cr.dictfetchall()

        return _response(200, "success", currencies)