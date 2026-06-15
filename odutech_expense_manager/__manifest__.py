{
    'name': 'Odutech Expense Tracker',
    'version': '1.0',
    'category': 'Finance',
    'summary': 'Manage custom expenses, categories, and accounts',
    'depends': ["base","mail","web"],
    'data': [
        'security/ir.model.access.csv',
        'views/expense_views.xml',
        'views/expense_menus.xml',
        'data/mail_template_data.xml',
        "data/welcome_template_data.xml",
        "data/password_template_data.xml",
        "data/ir_sequence_data.xml"
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}