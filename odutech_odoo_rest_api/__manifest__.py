{
    'name': 'Universal Odoo REST API Engine',
    'version': '19.0.1.0.0',
    'summary': 'Exposes complete Odoo ecosystem functionalities via a secure RESTful interface',
    'category': 'Technical/API',
    'author': 'Odutech Solutions',
    'website': 'https://www.odutechsolutions.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'web',
        'auth_signup'
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/email_verrification_template.xml',
        'views/res_users_view.xml',

    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}