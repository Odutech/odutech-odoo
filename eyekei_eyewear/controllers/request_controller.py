# -*- coding: utf-8 -*-
import logging
from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal,pager as portal_pager

_logger = logging.getLogger(__name__)


class MaterialRequestWebsiteController(CustomerPortal):
    def _prepare_home_portal_values(self, counters):
        """Adds a badge count for Inventory Requests on the main portal home page."""
        values = super()._prepare_home_portal_values(counters)
        if 'inventory_request_count' in counters:
            # Counts requests belonging to the current portal user's partner/user
            count = request.env['material.request'].search_count([
                ('warehouse_id', '=', request.env.user.default_warehouse_id.id)
            ])
            values['inventory_request_count'] = count
        return values
    @http.route(['/material/request'], type='http', auth='user', website=True, methods=['GET'])
    def material_request_form(self, **kwargs):
        """Renders the initial submission form."""
        warehouses = request.env['stock.warehouse'].search([])
        companies = request.env['res.company'].search([])
        products = request.env['product.product'].search([('is_optical_product', '=', True), ('sale_ok', '=', True)])
        priorities = [('0', 'Low'), ('1', 'Medium'), ('2', 'High'), ('3', 'Very High')]

        if 'company_id' not in kwargs:
            kwargs['company_id'] = str(request.env.user.company_id.id)

        return request.render('eyekei_eyewear.material_request_submit_template', {
            'warehouses': warehouses,
            'companies': companies,
            'products': products,
            'priorities': priorities,
            'error_fields': [],
            'post': kwargs,
        })

    @http.route('/material/request/create', type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def create_material_request(self, **post):
        """Processes the form data submission and redirects to the new detailed review page."""
        warehouse_id = int(post.get('warehouse_id'))
        warehouse = request.env['stock.warehouse'].browse(warehouse_id)
        location_id = warehouse.lot_stock_id.id if warehouse else False

        dist_warehouse = request.env['stock.warehouse'].search([('is_main_distribution_center', '=', True)], limit=1)
        dist_location = request.env['stock.location'].search([('is_main_distribution_location', '=', True)], limit=1)

        origin_warehouse_id = dist_warehouse.id if dist_warehouse else False
        origin_location_id = dist_location.id if dist_location else False

        product_ids = request.httprequest.form.getlist('product_ids[]')
        quantities = request.httprequest.form.getlist('quantities[]')

        line_commands = []
        for p_id, qty in zip(product_ids, quantities):
            if p_id and qty and float(qty) > 0:
                line_commands.append((0, 0, {
                    'product_id': int(p_id),
                    'qty_requested': float(qty),
                }))

        request_vals = {
            'date_request': post.get('date_request'),
            'date_expected': post.get('date_expected'),
            'priority': post.get('priority', '0'),
            'warehouse_id': warehouse_id,
            'location_id': location_id,
            'origin_warehouse_id': origin_warehouse_id,
            'origin_location_id': origin_location_id,
            'request_line_ids': line_commands,
            'state': 'draft',
        }

        material_request = request.env['material.request'].with_context(mail_create_nosubspace=True).create(
            request_vals)

        # FIXED/UPDATED: Instead of rendering directly, redirect to the unique detail view page endpoint
        return request.redirect(f'/material/request/view/{material_request.id}')

    # ================= NEW ENDPOINT: DETAIL VIEW & WORKFLOW MANAGER =================
    @http.route('/material/request/view/<int:request_id>', type='http', auth='user', website=True, methods=['GET'])
    def render_material_request_detail(self, request_id, **kwargs):
        """Fetches and displays the specifications of a single material request with workflow actions."""
        _logger.info("Loading detailed specification sheet for Request ID: %s", request_id)

        material_request = request.env['material.request'].browse(request_id)
        if not material_request.exists():
            return request.not_found()

        # Map state selection values to beautiful front-facing Bootstrap badge classes
        state_badges = {
            'draft': 'bg-secondary',
            'submitted': 'bg-warning text-dark',
            'approved': 'bg-success',
            'done': 'bg-info',
        }
        _logger.error(f"CHECKING THE RETURNED DATA-------{material_request}")
        return request.render('eyekei_eyewear.material_request_detail_template', {
            'req': material_request,
            'badge_class': state_badges.get(material_request.state, 'bg-primary')
        })

    @http.route('/material/request/submit_action/<int:request_id>', type='http', auth='user', website=True,
                methods=['POST'], csrf=True)
    def action_submit_request_to_manager(self, request_id, **post):
        """Updates request status state from 'draft' to 'submitted' for formal approval review."""
        material_request = request.env['material.request'].browse(request_id)
        if material_request.exists() and material_request.state == 'draft':
            material_request.sudo().action_submit_for_approval()
            _logger.info("Request %s has been submitted for approval.", material_request.sequence_number)
        return request.redirect(f'/material/request/view/{request_id}')

    # ================= EDIT ROUTE (GET) =================
    @http.route('/material/request/edit/<int:request_id>', type='http', auth='user', website=True, methods=['GET'])
    def edit_material_request(self, request_id, **kwargs):
        """Renders the form pre-populated with existing data for editing."""
        material_request = request.env['material.request'].browse(request_id)

        # Security & State Check: Only allow editing if it exists and is still a draft
        if not material_request.exists():
            return request.not_found()
        if material_request.state != 'draft':
            return request.redirect(f'/material/request/view/{request_id}')

        warehouses = request.env['stock.warehouse'].search([])
        companies = request.env['res.company'].search([])
        products = request.env['product.product'].search([('is_optical_product', '=', True), ('sale_ok', '=', True)])
        priorities = [('0', 'Low'), ('1', 'Medium'), ('2', 'High'), ('3', 'Very High')]

        return request.render('eyekei_eyewear.material_request_edit_template', {
            'req': material_request,
            'warehouses': warehouses,
            'companies': companies,
            'products': products,
            'priorities': priorities,
            'error_fields': [],
        })

    # ================= UPDATE ROUTE (POST) =================
    @http.route('/material/request/update/<int:request_id>', type='http', auth='user', website=True, methods=['POST'],
                csrf=True)
    def update_material_request(self, request_id, **post):
        """Processes modifications, updates the database record, and refreshes child lines."""
        material_request = request.env['material.request'].browse(request_id)

        if not material_request.exists() or material_request.state != 'draft':
            return request.redirect(f'/material/request/view/{request_id}')

        warehouse_id = int(post.get('warehouse_id'))
        warehouse = request.env['stock.warehouse'].browse(warehouse_id)
        location_id = warehouse.lot_stock_id.id if warehouse else False

        # Prepare line commands: Clear old lines and add new ones
        product_ids = request.httprequest.form.getlist('product_ids[]')
        quantities = request.httprequest.form.getlist('quantities[]')

        # (5, 0, 0) tells Odoo to delete all existing child lines from the database first
        line_commands = [(5, 0, 0)]
        for p_id, qty in zip(product_ids, quantities):
            if p_id and qty and float(qty) > 0:
                line_commands.append((0, 0, {
                    'product_id': int(p_id),
                    'qty_requested': float(qty),
                }))

        update_vals = {
            'date_request': post.get('date_request'),
            'date_expected': post.get('date_expected'),
            'priority': post.get('priority', '0'),
            'warehouse_id': warehouse_id,
            'location_id': location_id,
            'company_id': int(post.get('company_id')),
            'request_line_ids': line_commands,
        }

        material_request.write(update_vals)
        _logger.info("Material Request ID %s has been updated successfully.", request_id)

        return request.redirect(f'/material/request/view/{request_id}')

    @http.route(['/our/inventory/requests', '/my/inventory/requests/page/<int:page>'], type='http', auth="user",
                website=True)
    def portal_my_inventory_requests(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        MaterialRequest = request.env['material.request']

        # Domain filtering: Only show requests made by the logged-in user
        domain = [('warehouse_id', '=', request.env.user.default_warehouse_id.id)]

        # Count for pager
        request_count = MaterialRequest.search_count(domain)

        # Pager setup (10 records per page)
        pager = portal_pager(
            url="/our/inventory/requests",
            total=request_count,
            page=page,
            step=10
        )

        # Fetch records
        requests = MaterialRequest.search(
            domain,
            order='create_date desc',
            limit=10,
            offset=pager['offset']
        )

        values.update({
            'date': date_begin,
            'requests': requests.with_context(dirname="desc"),
            'page_name': 'inventory_request',
            'pager': pager,
            'default_url': '/our/inventory/requests',
        })
        return request.render("eyekei_eyewear.portal_my_inventory_requests_list", values)

    @http.route(['/material/request/download/<int:request_id>'], type='http', auth="user", website=True)
    def download_material_request_pdf(self, request_id, **kw):
        """Fetches the material request entry and serves it as a downloadable PDF stream."""

        # 1. Confirm record existence safely
        mat_request = request.env['material.request'].browse(request_id)
        if not mat_request.exists():
            return request.not_found()

        # 2. Basic Security/ACL Ownership check
        if mat_request.user_id.id != request.env.user.id and not request.env.user.has_group('base.group_user'):
            raise AccessError(_("You do not have administrative access permissions to view this request."))

        # 3. Call Odoo's dynamic printing report engine
        # Replace 'studio_customization.material_request_rep...' or your module technical report ID
        report_xml_id = "eyekei_eyewear.action_report_material_request"

        pdf_content, content_type = request.env['ir.actions.report']._render_qweb_pdf(
            report_xml_id,
            res_ids=[mat_request.id]
        )

        # 4. Craft safe clean filename configurations
        filename = f"Material_Request_{mat_request.sequence_number or mat_request.id}.pdf"

        # 5. Build explicit download response headers
        pdfhttpheaders = [
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(pdf_content)),
            ('Content-Disposition', f'attachment; filename="{filename}";')
        ]

        return request.make_response(pdf_content, headers=pdfhttpheaders)

    @http.route('/material/request/confirm_received/<model("material.request"):req_id>', type='http', auth='user',methods=['POST'])
    def action_confirm_received(self, req_id, **kwargs):
        for items in req_id.request_line_ids:
            items.write({'qty_received': items.qty_requested})
        req_id.sudo().action_confirm_receipt()
        return request.redirect(f'/material/request/view/{req_id.id}')

    @http.route('/material/request/discrepancy/<model("material.request"):req_id>', type='http', auth='user',
                methods=['POST'])
    def action_discrepancy(self, req_id, **kwargs):
        for items in req_id.request_line_ids:
            pass
        return request.redirect(f'/material/request/view/{req_id.id}')