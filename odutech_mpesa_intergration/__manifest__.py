{
    'name': 'M-Pesa Payment Provider',
    'version': '1.0',
    'category': 'Accounting/Payment Providers',
    'summary': 'STK Push payment integration for M-Pesa',
    'author': 'Kadweka_codes',
    'depends': ['payment', 'point_of_sale','website_sale'],
    'data': [
        'security/ir.rule.xml',
        'data/payment_provider_data.xml',
        'views/payment_provider_views.xml',
        'views/account_payment_register_views.xml',
        'views/pos_payment_method_view.xml',
    ],
    'assets': {
        'web.assets_frontend_lazy': [
            'odutech_mpesa_intergration/static/src/js/mpesa_payment.js',
        ],

        'point_of_sale._assets_pos': [
            'odutech_mpesa_intergration/static/src/js/mpesa_verification_popup.js',
            'odutech_mpesa_intergration/static/src/js/pos_mpesa_payment.js',
            'odutech_mpesa_intergration/static/src/xml/mpesa_verification_popup.xml',
        ],

        'point_of_sale.assets': [
            'odutech_mpesa_integration/static/src/js/*.js',
            'odutech_mpesa_integration/static/src/xml/*.xml',
        ],
    },
    'installable': True,
    'application': False,
}
