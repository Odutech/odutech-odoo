{
    'name': 'EYEKEI Eyewear Management System',
    'version': '2.0',
    'category': 'Healthcare/Optical',
    'summary': 'Comprehensive optical clinic management with insurance, lab, inventory & BI',
    'description': """
        EYEKEI Eyewear Management System for Odoo 19
        ============================================
        Modules covered:
        1. Patient Registration with duplicate control
        2. Optometrist Consultation & Dual Prescriptions
        3. Lab/Workshop Management with inventory tracking
        4. Multi-location Inventory (Frames, Lenses, Accessories)
        5. Insurance Claims, Submission & Receivables
        6. CEO Dashboard & Business Intelligence
    """,
    'author': 'gkarumba',
    'depends': [
        'base', 'mail', 'product', 'stock', 'account',
        'portal', 'sms', 'web', 'resource', 'purchase',
    ],
    'data': [
        'security/eyekei_security.xml',
        'security/record_rules.xml',
        'security/ir.model.access.xml',
        'data/sequences.xml',
        'data/cron_jobs.xml',
        'data/mail_templates.xml',
        'views/patient_visit_views.xml',
        'views/res_partner_views.xml',
        'views/prescription_views.xml',
        'views/optometrist_dashboard.xml',
        'views/lab_dashboard.xml',
        'views/insurance_views.xml',
        'views/external_vendor_views.xml',
        'views/remake_views.xml',
        'views/product_views.xml',
        'views/ceo_dashboard_views.xml',
        'views/res_company_views.xml',
        'views/config_settings_views.xml',
        'views/portal_templates.xml',
        'views/stock_location_views.xml',
        'views/account_move.xml',
        'wizard/stock_update_wizard_views.xml',
        'views/menu_items.xml',
        'reports/report_templates.xml',
        'views/lens_categorizations_view.xml',
        'reports/proforma_invoice.xml',
        'reports/prescription_report.xml',
        'views/equipment_transfer_request.xml',
        'data/material_request_templates.xml',
        'data/inventory_request_email_template.xml',
        # 'views/warehouse_extend_view.xml'
    ],
    'assets': {
        'web.assets_frontend': [
            'eyekei_eyewear/static/src/js/portal_registration.js',
        ],
        'web.assets_backend': [
            'eyekei_eyewear/static/src/components/**/*',
            'eyekei_eyewear/static/src/js/*',
            'eyekei_eyewear/static/src/xml/*',
            'eyekei_eyewear/static/src/scss/dashboard.scss',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}